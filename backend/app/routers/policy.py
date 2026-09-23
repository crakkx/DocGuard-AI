import asyncio
from uuid import UUID
from datetime import datetime
from typing import Optional
from pathlib import Path
import hashlib
import logging
import re

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    status,
)
from sqlalchemy import select, update, delete, func, text, or_
from sqlalchemy.ext.asyncio import AsyncSession
import fitz  # PyMuPDF

from app.database import get_db, AsyncSessionLocal
from app.models.policy import PolicyDocument, PolicyChunk
from app.models.document import Document
from app.models.compliance_rule import ComplianceRule
from app.models.finding import ComplianceFinding
from app.models.audit import AuditEntry
from app.services.policy_rag import policy_rag
from app.services.rule_extractor import rule_extractor
from app.services.audit_service import audit_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _bump_version(v: Optional[str]) -> str:
    if not v:
        return "2.0"
    try:
        parts = [int(p) for p in v.split(".")]
        if len(parts) == 1:
            return f"{parts[0] + 1}.0"
        parts[-1] += 1
        return ".".join(str(p) for p in parts)
    except Exception:
        return f"{v}.1"


def _extract_text_from_pdf_file(filepath: str) -> str:
    try:
        with fitz.open(filepath) as pdf_doc:
            return "\n".join(page.get_text() for page in pdf_doc)
    except Exception as read_err:
        logger.warning("fitz could not parse %s, falling back to raw decode: %s", filepath, read_err)
        with open(filepath, "rb") as f:
            return f.read().decode("utf-8", errors="ignore")


def _extract_text_from_bytes(content: bytes) -> str:
    try:
        with fitz.open(stream=content, filetype="pdf") as pdf_doc:
            return "\n".join(page.get_text() for page in pdf_doc)
    except Exception:
        return content.decode("utf-8", errors="ignore")


async def ingest_policy_background(
    policy_id: UUID,
    doc_id: UUID,
    filepath: str,
    title: str,
    previous_policy_id: Optional[UUID],
    embedding_model,
):
    """Background worker to extract text, chunk, embed, and extract rules without blocking event loop."""
    logger.info("Starting background ingestion for policy %s ('%s')", policy_id, title)
    try:
        # 1. Extract full text in worker thread (non-blocking)
        full_text = await asyncio.to_thread(_extract_text_from_pdf_file, filepath)

        # 2. Ingest into RAG (chunk + embed) inside a dedicated, short DB transaction
        async with AsyncSessionLocal() as session:
            chunk_count = await policy_rag.ingest_policy(
                policy_id, full_text, embedding_model, session
            )

            await audit_service.log(
                session,
                "POLICY_INGESTED",
                f"Policy '{title}' ingested: {chunk_count} chunks",
                document_id=doc_id,
                metadata={"chunk_count": chunk_count},
            )

            # Retrieve chunks for rule extraction
            chunks_result = await session.execute(
                select(PolicyChunk)
                .where(PolicyChunk.policy_id == policy_id)
                .order_by(PolicyChunk.chunk_index)
            )
            chunks = list(chunks_result.scalars().all())
            await session.commit()

        # 3. Extract candidate rules (batched LLM extraction) WITHOUT holding any DB session
        created_rules = await rule_extractor.extract_rules_for_policy(
            policy_id, chunks, db=None
        )

        # 4. Save rules, reconcile with previous policy, and mark COMPLETED in dedicated DB transaction
        async with AsyncSessionLocal() as session:
            for rule in created_rules:
                session.add(rule)

            # Case 3 reconciliation if updating a previous policy
            if previous_policy_id:
                prev_rules_res = await session.execute(
                    select(ComplianceRule).where(ComplianceRule.policy_id == previous_policy_id)
                )
                prev_rules = list(prev_rules_res.scalars().all())
                prev_by_name = {r.name.strip().lower(): r for r in prev_rules}

                # Reconcile status of existing rules into new rules
                for new_r in created_rules:
                    norm = new_r.name.strip().lower()
                    if norm in prev_by_name:
                        matched = prev_by_name[norm]
                        new_r.status = matched.status
                        new_r.enabled = matched.enabled
                        new_r.confirmed_by = matched.confirmed_by
                        new_r.confirmed_at = matched.confirmed_at
                        session.add(new_r)

                # Disable old rules
                for old_r in prev_rules:
                    old_r.enabled = False
                    session.add(old_r)

                # Mark previous policy inactive
                prev_pol = await session.get(PolicyDocument, previous_policy_id)
                if prev_pol:
                    prev_pol.is_active = False
                    session.add(prev_pol)

                await audit_service.log(
                    session,
                    "POLICY_UPDATED",
                    f"Policy '{title}' updated. Rules reconciled with previous version.",
                    document_id=doc_id,
                )

            # Update policy status to COMPLETED
            pol = await session.get(PolicyDocument, policy_id)
            if pol:
                pol.rules_extracted = len(created_rules)
                pol.total_chunks = chunk_count
                pol.ingestion_status = "COMPLETED"
                session.add(pol)

            await audit_service.log(
                session,
                "RULES_EXTRACTED",
                f"Extracted {len(created_rules)} candidate rule(s) from '{title}'",
                document_id=doc_id,
                metadata={"count": len(created_rules)},
            )
            await session.commit()
            logger.info("Policy ingestion completed successfully for %s", policy_id)

    except Exception as e:
        logger.exception("Failed background ingestion for policy %s: %s", policy_id, e)
        try:
            async with AsyncSessionLocal() as err_session:
                pol = await err_session.get(PolicyDocument, policy_id)
                if pol:
                    pol.ingestion_status = "FAILED"
                    pol.error_message = str(e)
                    err_session.add(pol)
                    await err_session.commit()
        except Exception as inner_e:
            logger.error("Failed to mark policy %s as FAILED: %s", policy_id, inner_e)


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_policy(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    version: str = Form(None),
    existing_policy_id: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a policy PDF.
    - Case 1: Totally new policy document -> extract rules in background, stage for approval.
    - Case 2: Exact duplicate document (matching file_hash or content_hash) -> reject with HTTP 409 Conflict.
    - Case 3: Updated version of existing policy -> accept, reconcile rules with previous version.
    """
    clean_title = title.strip()
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # Extract text from PDF to compute normalized content_hash (non-blocking)
    full_text = await asyncio.to_thread(_extract_text_from_bytes, content)

    normalized_text = re.sub(r"\s+", " ", full_text).strip().lower()
    content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest() if normalized_text else file_hash

    # Case 2 check: Exact duplicate file_hash OR content_hash in active policies
    dup_res = await db.execute(
        select(PolicyDocument).where(
            or_(
                PolicyDocument.file_hash == file_hash,
                PolicyDocument.content_hash == content_hash,
            ),
            PolicyDocument.is_active == True,  # noqa: E712
        )
    )
    dup = dup_res.scalars().first()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This policy document is identical to '{dup.title}' (Version {dup.version or '1.0'}). Duplicate upload rejected.",
        )

    # Case 3 check: Updated version of an existing policy
    existing_policy = None
    if existing_policy_id and existing_policy_id.strip():
        try:
            existing_policy = await db.get(PolicyDocument, UUID(existing_policy_id.strip()))
            if existing_policy and not existing_policy.is_active:
                existing_policy = None
        except Exception:
            existing_policy = None

    if not existing_policy:
        existing_res = await db.execute(
            select(PolicyDocument).where(
                func.lower(PolicyDocument.title) == func.lower(clean_title),
                PolicyDocument.is_active == True,  # noqa: E712
            )
        )
        existing_policy = existing_res.scalars().first()

    previous_policy_id = existing_policy.id if existing_policy else None

    # Determine assigned version
    if version and version.strip():
        assigned_version = version.strip()
    elif existing_policy:
        assigned_version = _bump_version(existing_policy.version)
    else:
        assigned_version = "1.0"

    # Save file to disk
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = file.filename.replace(" ", "_")
    dest = upload_dir / safe_name
    counter = 1
    while dest.exists():
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        dest = upload_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    with open(dest, "wb") as f:
        f.write(content)

    # Create document record
    doc = Document(
        filename=dest.name,
        original_filename=file.filename,
        filepath=str(dest),
        document_type="POLICY",
        type_confidence=1.0,
        status="EXTRACTED",
    )
    db.add(doc)
    await db.flush()

    # Create policy document record with PROCESSING status
    policy = PolicyDocument(
        title=clean_title,
        version=assigned_version,
        source_file_id=doc.id,
        file_hash=file_hash,
        content_hash=content_hash,
        ingestion_status="PROCESSING",
        is_active=True,
    )
    db.add(policy)
    await db.flush()

    await audit_service.log(
        db, "POLICY_UPLOADED", f"Policy '{clean_title}' uploaded (Version {assigned_version})",
        document_id=doc.id,
    )
    await db.commit()

    # Enqueue background ingestion task
    embedding_model = getattr(request.app.state, "embedding_model", None)
    background_tasks.add_task(
        ingest_policy_background,
        policy.id,
        doc.id,
        str(dest),
        clean_title,
        previous_policy_id,
        embedding_model,
    )

    return {
        "id": str(policy.id),
        "document_id": str(doc.id),
        "title": clean_title,
        "version": assigned_version,
        "total_chunks": 0,
        "rules_extracted": 0,
        "ingestion_status": "PROCESSING",
        "is_active": True,
        "uploaded_at": policy.created_at,
    }


@router.get("/")
async def list_policies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PolicyDocument).order_by(PolicyDocument.created_at.desc())
    )
    policies = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "document_id": str(p.source_file_id) if p.source_file_id else None,
            "title": p.title,
            "version": p.version,
            "effective_date": p.effective_date,
            "total_chunks": p.total_chunks,
            "rules_extracted": p.rules_extracted,
            "ingestion_status": getattr(p, "ingestion_status", "COMPLETED"),
            "error_message": getattr(p, "error_message", None),
            "is_active": getattr(p, "is_active", True),
            "uploaded_at": p.created_at,
        }
        for p in policies
    ]


@router.get("/{policy_id}")
async def get_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PolicyDocument).where(PolicyDocument.id == UUID(policy_id))
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {
        "id": str(policy.id),
        "title": policy.title,
        "version": policy.version,
        "total_chunks": policy.total_chunks,
        "rules_extracted": policy.rules_extracted,
        "ingestion_status": getattr(policy, "ingestion_status", "COMPLETED"),
        "error_message": getattr(policy, "error_message", None),
        "is_active": getattr(policy, "is_active", True),
    }


@router.get("/{policy_id}/chunks")
async def get_policy_chunks(
    policy_id: str,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PolicyChunk)
        .where(PolicyChunk.policy_id == UUID(policy_id))
        .order_by(PolicyChunk.chunk_index)
        .offset(skip)
        .limit(limit)
    )
    chunks = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "policy_id": str(c.policy_id),
            "chunk_index": c.chunk_index,
            "content": c.content,
            "section_number": getattr(c, "section_number", None),
            "section_title": c.section_title,
            "page_number": c.page_number,
        }
        for c in chunks
    ]


@router.get("/{policy_id}/rules")
async def get_policy_rules(policy_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ComplianceRule).where(ComplianceRule.policy_id == UUID(policy_id))
        .order_by(ComplianceRule.created_at)
    )
    rules = result.scalars().all()
    return [_serialize_rule(r) for r in rules]


@router.delete("/{policy_id}")
async def delete_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    pid = UUID(policy_id)
    result = await db.execute(select(PolicyDocument).where(PolicyDocument.id == pid))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    title = policy.title
    doc_id = policy.source_file_id

    # 1. Collect rule IDs
    rules_res = await db.execute(select(ComplianceRule.id).where(ComplianceRule.policy_id == pid))
    rule_ids = rules_res.scalars().all()

    # 2. Nullify rule references in findings and audit entries
    if rule_ids:
        await db.execute(
            update(ComplianceFinding).where(ComplianceFinding.rule_id.in_(rule_ids)).values(rule_id=None)
        )
        await db.execute(
            update(AuditEntry).where(AuditEntry.rule_id.in_(rule_ids)).values(rule_id=None)
        )
        # Delete rules
        await db.execute(delete(ComplianceRule).where(ComplianceRule.id.in_(rule_ids)))

    # 3. Delete policy chunks
    await db.execute(delete(PolicyChunk).where(PolicyChunk.policy_id == pid))

    # 4. Delete policy record
    await db.delete(policy)

    # 5. Nullify document references and delete Document record
    if doc_id:
        await db.execute(update(AuditEntry).where(AuditEntry.document_id == doc_id).values(document_id=None))
        await db.execute(delete(Document).where(Document.id == doc_id))

    await audit_service.log(
        db, "POLICY_DELETED", f"Policy '{title}' and its associated rules/chunks deleted"
    )
    await db.commit()
    return {"status": "success", "message": f"Policy '{title}' deleted"}


def _serialize_rule(r: ComplianceRule) -> dict:
    return {
        "id": str(r.id),
        "name": r.name,
        "description": r.description,
        "tier": str(r.tier),
        "primitive": r.primitive,
        "parameters": r.parameters,
        "expression": r.expression,
        "evaluation_prompt": r.evaluation_prompt,
        "severity": r.severity,
        "on_violation": r.on_violation,
        "source_policy_id": str(r.policy_id) if r.policy_id else None,
        "source_clause": r.source_clause,
        "source_section": r.source_section,
        "source_page": r.source_page,
        "status": r.status,
        "enabled": r.enabled,
        "created_at": r.created_at,
    }
