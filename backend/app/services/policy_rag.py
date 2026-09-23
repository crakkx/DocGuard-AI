import re
import asyncio
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import PolicyChunk, PolicyDocument


@dataclass
class PolicyClauseResult:
    chunk_id: str
    content: str
    section_number: Optional[str]
    section_title: Optional[str]
    page_number: Optional[int]
    policy_title: str
    similarity_score: float


class PolicyRAGService:
    """
    Handles the full RAG lifecycle for procurement policy documents:
    - Section-aware chunking
    - Embedding via sentence-transformers
    - Cosine similarity retrieval via pgvector
    """

    SECTION_PATTERNS = [
        re.compile(r"^(?:section|article|clause)\s+\d+[\.\d]*", re.IGNORECASE | re.MULTILINE),
        re.compile(r"^\d+\.\d+\s+[A-Z]", re.MULTILINE),
        re.compile(r"^\d+\.\s+[A-Z]", re.MULTILINE),
    ]
    SECTION_HEADER_RE = re.compile(
        r"^((?:section|article|clause)\s+\d+[\.\d]*[:\s]+.*|"
        r"\d+\.\d+\s+[A-Z][^\n]*|\d+\.\s+[A-Z][^\n]*)",
        re.IGNORECASE | re.MULTILINE,
    )

    MIN_CHUNK_CHARS = 150
    MAX_CHUNK_CHARS = 2000

    def chunk_policy_text(self, full_text: str) -> list[dict]:
        """
        Split policy text into meaningful sections. Merges tiny fragments
        (like standalone headings or TOC items) into their following sections
        so that every chunk contains substantive policy text.
        """
        # 1. Clean lines that are purely Table of Contents entries (e.g. '1. Introduction .... 3')
        cleaned_lines = []
        for line in full_text.splitlines():
            stripped = line.strip()
            # Drop lines ending with multiple dots/spaces and page numbers (TOC entries)
            if re.search(r'(\.{3,}|\s{4,})\s*\d+$', stripped):
                continue
            cleaned_lines.append(line)
        cleaned_text = '\n'.join(cleaned_lines)

        # 2. Find section boundaries
        boundaries = [m.start() for m in self.SECTION_HEADER_RE.finditer(cleaned_text)]
        if not boundaries:
            return self._recursive_split(cleaned_text)

        boundaries.append(len(cleaned_text))
        raw_chunks = []
        for i, start in enumerate(boundaries[:-1]):
            end = boundaries[i + 1]
            chunk_text = cleaned_text[start:end].strip()
            if chunk_text:
                raw_chunks.append(chunk_text)

        # 3. Merge tiny chunks (< 150 chars) with subsequent or previous sections
        merged_texts: list[str] = []
        buffer = ""
        for text_block in raw_chunks:
            if not buffer:
                buffer = text_block
            elif len(buffer) < self.MIN_CHUNK_CHARS:
                # Buffer is too short (e.g. just a heading), merge next block into it
                buffer = f"{buffer}\n\n{text_block}".strip()
            elif len(text_block) < self.MIN_CHUNK_CHARS and (len(buffer) + len(text_block) < self.MAX_CHUNK_CHARS):
                # Next block is too short, merge into current buffer
                buffer = f"{buffer}\n\n{text_block}".strip()
            else:
                merged_texts.append(buffer)
                buffer = text_block
        if buffer:
            merged_texts.append(buffer)

        # 4. Create chunk records
        chunks: list[dict] = []
        for text_block in merged_texts:
            first_line = text_block.splitlines()[0].strip() if text_block else ""
            sec_num, sec_title = self._parse_section_header(first_line)

            if len(text_block) > self.MAX_CHUNK_CHARS:
                sub_chunks = self._recursive_split(text_block, size=1000, overlap=128)
                for sc in sub_chunks:
                    sc["section_number"] = sec_num
                    sc["section_title"] = sec_title
                    sc["chunk_index"] = len(chunks)
                    chunks.append(sc)
            else:
                chunks.append({
                    "chunk_index": len(chunks),
                    "content": text_block,
                    "section_number": sec_num,
                    "section_title": sec_title,
                    "page_number": None,
                })

        return chunks

    def _parse_section_header(self, line: str) -> tuple[Optional[str], Optional[str]]:
        # e.g. "Section 3.1 Price Variance"
        m = re.match(
            r"((?:section|article|clause)\s+[\d.]+|\d+\.[\d.]*)\s*(.*)",
            line,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).strip(), m.group(2).strip() or None
        return None, line[:80] if line else None

    def _recursive_split(
        self, text: str, size: int = 512, overlap: int = 64
    ) -> list[dict]:
        chunks = []
        start = 0
        idx = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunks.append({
                "chunk_index": idx,
                "content": text[start:end].strip(),
                "section_number": None,
                "section_title": None,
                "page_number": None,
            })
            start += size - overlap
            idx += 1
        return chunks

    def embed(self, texts: list[str], model) -> list[list[float]]:
        """Generate embeddings using the app's sentence-transformers model."""
        if model is None:
            return [[0.0] * 384 for _ in texts]
        embeddings = model.encode(texts, show_progress_bar=False)
        return [e.tolist() for e in embeddings]

    async def ingest_policy(
        self,
        policy_id: UUID,
        full_text: str,
        model,
        db: AsyncSession,
    ) -> int:
        """Chunk, embed, and store policy text. Returns number of chunks created."""
        # Delete old chunks
        old = await db.execute(
            text("DELETE FROM policy_chunks WHERE policy_id = CAST(:pid AS uuid)").bindparams(
                pid=str(policy_id)
            )
        )

        raw_chunks = self.chunk_policy_text(full_text)
        if not raw_chunks:
            return 0

        texts = [c["content"] for c in raw_chunks]
        embeddings = await asyncio.to_thread(self.embed, texts, model)

        for chunk_data, emb in zip(raw_chunks, embeddings):
            chunk = PolicyChunk(
                policy_id=policy_id,
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                section_number=chunk_data.get("section_number"),
                section_title=chunk_data.get("section_title"),
                page_number=chunk_data.get("page_number"),
                embedding=emb,
            )
            db.add(chunk)

        # Update total_chunks on policy document
        await db.execute(
            text(
                "UPDATE policy_documents SET total_chunks = :n "
                "WHERE id = CAST(:pid AS uuid)"
            ).bindparams(n=len(raw_chunks), pid=str(policy_id))
        )
        await db.flush()
        return len(raw_chunks)

    async def retrieve_relevant_clauses(
        self,
        query: str,
        model,
        db: AsyncSession,
        top_k: int = 3,
        similarity_threshold: float = 0.4,
    ) -> list[PolicyClauseResult]:
        """Retrieve most relevant policy chunks for a query string."""
        if model is None:
            return []

        raw_emb = await asyncio.to_thread(model.encode, [query], show_progress_bar=False)
        query_emb = raw_emb[0].tolist()

        stmt = text(
            """
            SELECT
                pc.id,
                pc.content,
                pc.section_number,
                pc.section_title,
                pc.page_number,
                pd.title AS policy_title,
                1 - (pc.embedding <=> CAST(:qe AS vector)) AS similarity
            FROM policy_chunks pc
            JOIN policy_documents pd ON pc.policy_id = pd.id
            WHERE pc.embedding IS NOT NULL
              AND 1 - (pc.embedding <=> CAST(:qe AS vector)) > :threshold
            ORDER BY pc.embedding <=> CAST(:qe AS vector)
            LIMIT :top_k
            """
        )

        result = await db.execute(
            stmt,
            {
                "qe": str(query_emb),
                "threshold": similarity_threshold,
                "top_k": top_k,
            },
        )
        rows = result.fetchall()

        return [
            PolicyClauseResult(
                chunk_id=str(row.id),
                content=row.content,
                section_number=row.section_number,
                section_title=row.section_title,
                page_number=row.page_number,
                policy_title=row.policy_title,
                similarity_score=round(float(row.similarity), 4),
            )
            for row in rows
        ]


policy_rag = PolicyRAGService()
