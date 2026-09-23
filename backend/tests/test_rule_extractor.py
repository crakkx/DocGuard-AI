import json
from types import SimpleNamespace

import pytest

from app.models.policy import PolicyDocument, PolicyChunk
from app.models.compliance_rule import ComplianceRule
from app.services.rule_extractor import RuleExtractorService

# NOTE: Base.metadata.create_all against the in-memory SQLite `db` fixture
# (from conftest.py) was verified empirically to compile fine even with
# PolicyChunk.embedding's pgvector Vector(384) column, so we reuse that
# fixture rather than standing up a separate Postgres session for this file.


FAKE_LLM_RESPONSE = json.dumps({
    "rules": [
        {
            "is_enforceable": True,
            "rule_name": "Price variance requires justification",
            "tier": "PRIMITIVE",
            "primitive": "COMPARE_FIELDS",
            "parameters": {
                "field_a": {"document": "invoice", "field": "unit_price"},
                "field_b": {"document": "purchase_order", "field": "unit_price"},
                "operator": "DEVIATION_PERCENT",
                "threshold": 5,
            },
            "severity": "HIGH",
            "on_violation": "FLAG",
            "source_clause": "Section 3.1 - Price variances exceeding 5% require documented justification.",
            "source_section": "3.1",
            "source_page": 4,
        },
        {
            "is_enforceable": False,
            "rule_name": "Purely informational preamble",
            "tier": "PRIMITIVE",
        },
    ]
})


@pytest.fixture
async def policy_with_chunks(db):
    policy = PolicyDocument(title="Test Procurement Policy", version="1.0")
    db.add(policy)
    await db.flush()

    chunk1 = PolicyChunk(
        policy_id=policy.id,
        chunk_index=0,
        section_number="3.1",
        section_title="Price Variance",
        content="Section 3.1 - Price variances exceeding 5% of the purchase order value require documented justification.",
        page_number=4,
    )
    chunk2 = PolicyChunk(
        policy_id=policy.id,
        chunk_index=1,
        section_number="3.2",
        section_title="Quantity Match",
        content="Section 3.2 - Invoice quantities must not exceed PO or GRN quantities.",
        page_number=5,
    )
    db.add(chunk1)
    db.add(chunk2)
    await db.flush()

    return policy, [chunk1, chunk2]


class FakeMistralClient:
    """Mimics mistralai.client.Mistral's chat.complete_async interface."""

    def __init__(self, response_text: str):
        self._response_text = response_text
        self.chat = SimpleNamespace(complete_async=self._complete_async)

    async def _complete_async(self, **kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self._response_text)
                )
            ]
        )


@pytest.mark.asyncio
async def test_extract_rules_for_policy_no_client_returns_empty(monkeypatch, db, policy_with_chunks):
    """Default, realistic state: no MISTRAL_API_KEY -> self._client is None ->
    extraction must be a graceful no-op, never raising."""
    from app.config import settings
    monkeypatch.setattr(settings, "MISTRAL_API_KEY", "")
    policy, chunks = policy_with_chunks

    service = RuleExtractorService()
    assert service._get_client() is None

    result = await service.extract_rules_for_policy(policy.id, chunks, db)

    assert result == []


@pytest.mark.asyncio
async def test_extract_rules_for_policy_with_mocked_model(db, policy_with_chunks):
    policy, chunks = policy_with_chunks

    service = RuleExtractorService()
    service._client = FakeMistralClient(FAKE_LLM_RESPONSE)

    created = await service.extract_rules_for_policy(policy.id, chunks, db)

    # The batch of chunks receives the mock response and extracts the enforceable rule
    assert len(created) == 1

    for rule in created:
        assert isinstance(rule, ComplianceRule)
        assert rule.policy_id == policy.id
        assert rule.tier == 1  # PRIMITIVE -> 1
        assert rule.primitive == "COMPARE_FIELDS"
        assert rule.parameters is not None
        assert rule.expression is None
        assert rule.evaluation_prompt is None
        assert rule.severity == "HIGH"
        assert rule.on_violation == "FLAG"
        assert rule.status == "PENDING_REVIEW"
        assert rule.enabled is False
        assert rule.name == "Price variance requires justification"
        assert "Section 3.1" in rule.source_clause
        assert rule.source_section == "3.1"
        assert rule.source_page == 4


@pytest.mark.asyncio
async def test_extract_rules_without_db_session(policy_with_chunks):
    """Tests non-blocking extraction with db=None."""
    policy, chunks = policy_with_chunks

    service = RuleExtractorService()
    service._client = FakeMistralClient(FAKE_LLM_RESPONSE)

    created = await service.extract_rules_for_policy(policy.id, chunks, db=None)

    assert len(created) == 1
    assert created[0].name == "Price variance requires justification"
    assert created[0].policy_id == policy.id


@pytest.mark.asyncio
async def test_extract_rules_defaults_when_llm_omits_fields(db, policy_with_chunks):
    policy, chunks = policy_with_chunks
    single_chunk = chunks[:1]

    minimal_response = json.dumps([
        {
            "is_enforceable": True,
            "rule_name": "Some rule with missing optional fields",
            "tier": "PRIMITIVE",
            "primitive": "THRESHOLD_CHECK",
            "parameters": {"field": "total_amount", "operator": ">", "threshold": 1000000},
            # no severity, on_violation, source_clause, source_section, source_page
        }
    ])

    service = RuleExtractorService()
    service._client = FakeMistralClient(minimal_response)

    created = await service.extract_rules_for_policy(policy.id, single_chunk, db)

    assert len(created) == 1
    rule = created[0]
    # Falls back to defaults / chunk data when the LLM omits fields.
    assert rule.severity == "MEDIUM"
    assert rule.on_violation == "VIOLATION"
    assert rule.source_section == single_chunk[0].section_number
    assert rule.source_page == single_chunk[0].page_number
    assert rule.source_clause == single_chunk[0].content


@pytest.mark.asyncio
async def test_extract_rules_skips_unrecognized_tier(db, policy_with_chunks):
    policy, chunks = policy_with_chunks
    single_chunk = chunks[:1]

    bad_tier_response = json.dumps([
        {
            "is_enforceable": True,
            "rule_name": "Weird tier rule",
            "tier": "NOT_A_REAL_TIER",
        }
    ])

    service = RuleExtractorService()
    service._client = FakeMistralClient(bad_tier_response)

    created = await service.extract_rules_for_policy(policy.id, single_chunk, db)
    assert created == []


@pytest.mark.asyncio
async def test_extract_rules_handles_malformed_json_per_chunk(db, policy_with_chunks):
    """A malformed response for one chunk must not abort the whole policy;
    other chunks should still be processed."""
    policy, chunks = policy_with_chunks

    class SequencedMistralClient:
        def __init__(self, responses):
            self._responses = list(responses)
            self._i = 0
            self.chat = SimpleNamespace(complete_async=self._complete_async)

        async def _complete_async(self, **kwargs):
            text = self._responses[self._i]
            self._i += 1
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=text)
                    )
                ]
            )

    valid_response = json.dumps([
        {
            "is_enforceable": True,
            "rule_name": "Valid rule from second chunk",
            "tier": "EXPRESSION",
            "expression": {"AND": []},
            "severity": "CRITICAL",
        }
    ])

    service = RuleExtractorService()
    service.MAX_BATCH_CHARS = 10  # force 1 batch per chunk to test multi-batch resilience
    service._client = SequencedMistralClient(["not valid json {{{", valid_response])

    created = await service.extract_rules_for_policy(policy.id, chunks, db)

    assert len(created) == 1
    assert created[0].tier == 2
    assert created[0].expression == {"AND": []}
