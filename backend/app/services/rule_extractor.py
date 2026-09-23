import json
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.compliance_rule import ComplianceRule
from app.models.policy import PolicyChunk

logger = logging.getLogger(__name__)

# Maps the LLM-facing string tier (per the implementation plan's Step 4 schema)
# to the integer tier stored on ComplianceRule (1=PRIMITIVE, 2=EXPRESSION, 3=LLM_EVALUATED).
TIER_STRING_TO_INT = {
    "PRIMITIVE": 1,
    "EXPRESSION": 2,
    "LLM_EVALUATED": 3,
}

VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_ON_VIOLATION = {"VIOLATION", "NEEDS_REVIEW", "FLAG", "BLOCK"}

SYSTEM_INSTRUCTION = (
    "You are a specialized procurement compliance analyst. Your SOLE focus is to extract "
    "TRANSACTIONAL compliance rules that can be audited against procurement documents "
    "(such as Purchase Orders, Invoices, Goods Receipts, Tenders, Quotations, and payment vouchers).\n\n"
    "CRITICAL FILTERING CRITERIA:\n"
    "1. WHAT TO EXTRACT (TRANSACTIONAL RULES ONLY):\n"
    "   - Spending & threshold limits (e.g. direct purchase <= ₹25,000, tender limits, quotation requirements).\n"
    "   - Document presence requirements for payment/approval (e.g. GRN required before payment, bill & voucher certification).\n"
    "   - Price variance / quantity tolerances between PO, Invoice, and GRN.\n"
    "   - Platform & procurement route mandates for transactions (e.g. mandatory GeM usage, e-tendering for open tenders).\n"
    "   - Item & product restrictions verifiable on line-items (e.g. prohibition of single-use plastics).\n"
    "   - Required vendor quotation counts (e.g. minimum 3 quotes for LPC, 3 manufacturers on GeM).\n\n"
    "2. WHAT NOT TO EXTRACT (STRICTLY EXCLUDE):\n"
    "   - DO NOT extract high-level aspirational principles (e.g., 'transparency', 'value for money', 'ethical sourcing', 'adherence to GFR 2017').\n"
    "   - DO NOT extract institutional governance / periodic administration tasks (e.g. 'annual procurement reports', 'regular internal/external audits', 'periodic policy review', 'dispute resolution committees').\n"
    "   - DO NOT extract general HR / personnel ethics (e.g. 'bribery prohibition', 'recusal for conflict of interest', 'employees must act professionally').\n"
    "   - If a clause cannot be verified against an individual Purchase Order, Invoice, Goods Receipt, or transaction file, SET is_enforceable=false and DO NOT create a rule."
)


class RuleExtractorService:
    """
    LLM-based rule extraction from policy chunks (Policy Ingestion Pipeline,
    Step 4). For each policy chunk, asks Mistral to identify zero or more
    enforceable rules and classify each into one of the three rule tiers.

    Degrades gracefully (returns no rules) when no Mistral API key is
    configured, mirroring app/engine/llm_evaluator.py's LLMEvaluator.
    """

    def __init__(self):
        self._client = None
        self._get_client()

    def _get_client(self):
        if self._client is not None:
            return self._client
        if settings.MISTRAL_API_KEY:
            try:
                from mistralai.client import Mistral
                self._client = Mistral(api_key=settings.MISTRAL_API_KEY)
                logger.info("Initialized Mistral client for rule extraction")
            except Exception as e:
                logger.error("Failed to initialize Mistral client: %s", e)
                self._client = None
        return self._client

    MIN_RULE_CHUNK_CHARS = 50
    MAX_BATCH_CHARS = 25000

    def _batch_chunks(self, chunks: list[PolicyChunk]) -> list[list[PolicyChunk]]:
        """
        Filter out tiny/empty chunks (< 100 chars) and bundle the remaining
        substantive chunks into large batches (up to ~25,000 characters)
        so that an entire 10-15 page policy can be extracted in 1 single LLM call.
        """
        valid_chunks = [c for c in chunks if c.content and len(c.content.strip()) >= self.MIN_RULE_CHUNK_CHARS]
        if not valid_chunks:
            # Fallback if chunks were short
            valid_chunks = [c for c in chunks if c.content and len(c.content.strip()) > 20]

        if not valid_chunks:
            return []

        batches: list[list[PolicyChunk]] = []
        current_batch: list[PolicyChunk] = []
        current_len = 0

        for chunk in valid_chunks:
            chunk_len = len(chunk.content)
            if current_batch and (current_len + chunk_len > self.MAX_BATCH_CHARS):
                batches.append(current_batch)
                current_batch = [chunk]
                current_len = chunk_len
            else:
                current_batch.append(chunk)
                current_len += chunk_len

        if current_batch:
            batches.append(current_batch)

        return batches

    def _build_prompt(self, clause_text: str) -> str:
        """Single-clause prompt backward compatibility."""
        return f"""{SYSTEM_INSTRUCTION}

POLICY CLAUSE:
{clause_text}

A clause may contain MULTIPLE distinct enforceable rules, or NONE at all.

For each rule found, output an object of this exact shape:
{{
  "is_enforceable": true/false,
  "rule_name": "human-readable name",
  "tier": "PRIMITIVE" | "EXPRESSION" | "LLM_EVALUATED",
  "primitive": "COMPARE_FIELDS" | "THRESHOLD_CHECK" | "PRESENCE_CHECK" | "MATCH_CHECK" | "AGGREGATION_CHECK" | "TIME_WINDOW_CHECK" | "COUNT_CHECK" (only if tier=PRIMITIVE),
  "parameters": {{ ... }} (only if tier=PRIMITIVE),
  "expression": {{ ... }} (only if tier=EXPRESSION, e.g. {{"AND": [...]}} / {{"OR": [...]}} / {{"NOT": {{...}}}}),
  "evaluation_prompt": "..." (only if tier=LLM_EVALUATED),
  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "source_clause": "exact text from policy",
  "source_section": "3.1",
  "source_page": 4
}}

If the clause is informational (not an enforceable rule), set is_enforceable=false.

Respond with ONLY valid JSON (no markdown fences, no explanation outside JSON):
either a JSON array of rule objects, or an object of the form {{"rules": [ ... ]}}."""

    def _build_batch_prompt(self, batch_chunks: list[PolicyChunk]) -> str:
        """Batch prompt combining multiple chunks into a single context window."""
        sections_text = []
        for chunk in batch_chunks:
            header = f"=== [CHUNK #{chunk.chunk_index}] Section: {chunk.section_number or 'N/A'} - {chunk.section_title or ''} ==="
            sections_text.append(f"{header}\n{chunk.content}")

        joined_sections = "\n\n".join(sections_text)

        return f"""{SYSTEM_INSTRUCTION}

Read the policy sections below and extract ONLY actionable, document-verifiable TRANSACTIONAL compliance rules.

POLICY SECTIONS:
{joined_sections}

A section may contain MULTIPLE distinct enforceable transactional rules, or NONE at all (e.g. background, definitions, ethics statements).
STRICT INSTRUCTION: Only extract rules verifiable on a transaction document (PO, Invoice, GRN, Quotation, Tender). Ignore general governance, annual audits, annual reporting, employee ethics, and aspirational declarations.

For each transactional rule found, output an object of this exact shape:
{{
  "is_enforceable": true,
  "rule_name": "clear descriptive name (e.g. Direct Purchase Threshold <= ₹25,000)",
  "chunk_index": <int, matching the CHUNK # where this rule originated>,
  "tier": "PRIMITIVE" | "EXPRESSION" | "LLM_EVALUATED",
  "primitive": "COMPARE_FIELDS" | "THRESHOLD_CHECK" | "PRESENCE_CHECK" | "MATCH_CHECK" | "AGGREGATION_CHECK" | "TIME_WINDOW_CHECK" | "COUNT_CHECK" (only if tier=PRIMITIVE),
  "parameters": {{ ... }} (only if tier=PRIMITIVE),
  "expression": {{ ... }} (only if tier=EXPRESSION, e.g. {{"AND": [...]}} / {{"OR": [...]}} / {{"NOT": {{...}}}}),
  "evaluation_prompt": "..." (only if tier=LLM_EVALUATED),
  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "on_violation": "VIOLATION" | "NEEDS_REVIEW" | "FLAG" | "BLOCK",
  "source_clause": "exact text from policy",
  "source_section": "section number, e.g. 4.2"
}}

Respond with ONLY valid JSON (no markdown fences, no explanation outside JSON):
either a JSON array of rule objects, or an object of the form {{"rules": [ ... ]}}."""

    def _parse_response_text(self, text: str) -> list[dict]:
        """Strip markdown code fences (same defensive approach as
        LLMEvaluator.evaluate) and coerce the parsed JSON into a list of
        rule dicts, handling both a bare array and {"rules": [...]}."""
        cleaned = text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            rules = parsed.get("rules", [])
        elif isinstance(parsed, list):
            rules = parsed
        else:
            rules = []

        return [r for r in rules if isinstance(r, dict)]

    def _normalize_parameters(self, primitive: str | None, params: dict) -> dict:
        """
        Remap LLM-generated parameter key names to the canonical keys that
        primitives.py reads. The LLM is inconsistent about key names across
        policy re-extractions; this normalizer makes rules portable.
        """
        if not params:
            return params

        p = dict(params)  # shallow copy so we don't mutate

        # --- THRESHOLD_CHECK / COUNT_CHECK ---
        # LLM sometimes outputs "thresholds" (plural) instead of "threshold"
        if "thresholds" in p and "threshold" not in p:
            p["threshold"] = p.pop("thresholds")

        # LLM sometimes outputs "procurement_method" when primitives.py also
        # accepts "method" (we keep both but canonicalize to "method")
        if "procurement_method" in p and "method" not in p:
            p["method"] = p.pop("procurement_method")

        # --- MATCH_CHECK ---
        # Single-use plastics rule: LLM may use "excluded_values", "forbidden_values",
        # or "exclusion" — primitives.py reads params.get("exclusion")
        if primitive == "MATCH_CHECK":
            if "excluded_values" in p or "forbidden_values" in p:
                vals = p.pop("excluded_values", None) or p.pop("forbidden_values", None)
                if isinstance(vals, list) and any("plastic" in str(v).lower() for v in vals):
                    p["exclusion"] = "single_use_plastics"
                elif "exclusion" not in p:
                    p["exclusion"] = vals

        # --- PRESENCE_CHECK ---
        # "document_type" used as presence target — map to "document"
        if primitive == "PRESENCE_CHECK":
            if "document_type" in p and "document" not in p:
                p["document"] = p.pop("document_type").lower().replace(" ", "_")
            # Map "procurement_method" → "method"
            if "procurement_method" in p and "method" not in p:
                p["method"] = p.pop("procurement_method")

        # --- COUNT_CHECK ---
        # "vendor_count" / "vendor_quotations" → "field" already fine; just ensure
        # procurement_method → method
        if primitive == "COUNT_CHECK":
            if "procurement_method" in p and "method" not in p:
                p["method"] = p.pop("procurement_method")

        return p

    async def extract_rules_for_policy(
        self,
        policy_id: UUID,
        chunks: list[PolicyChunk],
        db: Optional[AsyncSession] = None,
    ) -> list[ComplianceRule]:
        """
        Run LLM rule extraction over policy chunks using context-window batching.
        Instead of calling LLM once per chunk, chunks are grouped into large
        batches (up to 25,000 characters), enabling typical 5-15 page documents
        to be processed in 1 single LLM call.
        """
        client = self._get_client()
        if client is None:
            logger.warning("Rule extraction skipped: Mistral client is not initialized (check MISTRAL_API_KEY).")
            return []

        batches = self._batch_chunks(chunks)
        if not batches:
            logger.info("Rule extraction: no substantive chunks to process.")
            return []

        logger.info(
            "Batched %d policy chunks into %d LLM call(s) (context window optimized).",
            len(chunks),
            len(batches),
        )

        created: list[ComplianceRule] = []
        preferred_model = settings.MISTRAL_MODEL or "mistral-medium-latest"
        fallback_model = "open-mistral-7b"

        for batch_idx, batch in enumerate(batches, start=1):
            try:
                # If batch has only 1 chunk and it has no chunk_index, fallback to single prompt
                if len(batch) == 1 and not getattr(batch[0], "chunk_index", None):
                    prompt = self._build_prompt(batch[0].content)
                else:
                    prompt = self._build_batch_prompt(batch)

                try:
                    response = await client.chat.complete_async(
                        model=preferred_model,
                        messages=[
                            {"role": "system", "content": SYSTEM_INSTRUCTION},
                            {"role": "user", "content": prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.1,
                    )
                except Exception as call_err:
                    err_msg = str(call_err)
                    if "429" in err_msg or "rate limit" in err_msg.lower():
                        logger.warning(
                            "Mistral model '%s' rate limited; falling back to '%s'",
                            preferred_model,
                            fallback_model,
                        )
                        response = await client.chat.complete_async(
                            model=fallback_model,
                            messages=[
                                {"role": "system", "content": SYSTEM_INSTRUCTION},
                                {"role": "user", "content": prompt},
                            ],
                            response_format={"type": "json_object"},
                            temperature=0.1,
                        )
                    else:
                        raise call_err

                raw_text = response.choices[0].message.content
                rule_dicts = self._parse_response_text(raw_text)
                logger.info(
                    "Batch %d/%d (%d chunks): extracted %d candidate rule(s)",
                    batch_idx,
                    len(batches),
                    len(batch),
                    len(rule_dicts),
                )
            except Exception as exc:
                logger.warning(
                    "Rule extraction LLM/parse failure on batch %d/%d: %s",
                    batch_idx,
                    len(batches),
                    exc,
                )
                continue

            # Lookup mapping for chunk metadata
            chunk_by_idx = {c.chunk_index: c for c in batch if hasattr(c, "chunk_index")}
            chunk_by_sec = {
                str(c.section_number).strip(): c
                for c in batch
                if getattr(c, "section_number", None)
            }

            for rule_data in rule_dicts:
                try:
                    is_enforceable = rule_data.get("is_enforceable")
                    if isinstance(is_enforceable, str):
                        is_enforceable = is_enforceable.lower() in ("true", "1", "yes")
                    if not is_enforceable:
                        continue

                    tier_str = str(rule_data.get("tier") or "").upper().strip()
                    tier_int = TIER_STRING_TO_INT.get(tier_str)
                    if tier_int is None:
                        logger.warning("Unrecognized tier '%s' for rule '%s'", tier_str, rule_data.get("rule_name"))
                        continue

                    name = str(rule_data.get("rule_name") or "Unnamed rule")[:255]
                    description = rule_data.get("rule_name") or name

                    primitive = None
                    parameters = None
                    expression = None
                    evaluation_prompt = None
                    if tier_int == 1:
                        primitive = rule_data.get("primitive")
                        parameters = self._normalize_parameters(
                            primitive, rule_data.get("parameters") or {}
                        )
                    elif tier_int == 2:
                        expression = rule_data.get("expression")
                    elif tier_int == 3:
                        evaluation_prompt = rule_data.get("evaluation_prompt")

                    severity = rule_data.get("severity")
                    if severity not in VALID_SEVERITIES:
                        severity = "MEDIUM"

                    on_violation = rule_data.get("on_violation")
                    if on_violation not in VALID_ON_VIOLATION:
                        on_violation = "VIOLATION"

                    # Resolve source chunk
                    source_chunk = None
                    raw_chunk_idx = rule_data.get("chunk_index")
                    if raw_chunk_idx is not None and raw_chunk_idx in chunk_by_idx:
                        source_chunk = chunk_by_idx[raw_chunk_idx]
                    elif rule_data.get("source_section") and str(rule_data["source_section"]).strip() in chunk_by_sec:
                        source_chunk = chunk_by_sec[str(rule_data["source_section"]).strip()]
                    elif batch:
                        source_chunk = batch[0]

                    source_clause = rule_data.get("source_clause") or (source_chunk.content[:1000] if source_chunk and source_chunk.content else None)
                    source_section = rule_data.get("source_section") or (source_chunk.section_number if source_chunk else None)
                    source_page = rule_data.get("source_page") or (source_chunk.page_number if source_chunk else None)

                    rule = ComplianceRule(
                        policy_id=policy_id,
                        name=name,
                        description=description,
                        tier=tier_int,
                        primitive=primitive,
                        parameters=parameters,
                        expression=expression,
                        evaluation_prompt=evaluation_prompt,
                        severity=severity,
                        on_violation=on_violation,
                        source_clause=source_clause,
                        source_section=source_section,
                        source_page=source_page,
                        status="PENDING_REVIEW",
                        enabled=False,
                    )
                    if db is not None:
                        db.add(rule)
                    created.append(rule)
                except Exception:
                    continue

        if created and db is not None:
            await db.flush()

        return created


rule_extractor = RuleExtractorService()
