import pytest
import io
import uuid
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.database import get_db
from app.models.policy import PolicyDocument, PolicyChunk
from app.models.compliance_rule import ComplianceRule
from app.models.finding import ComplianceFinding
from app.models.audit import AuditEntry
from app.models.procurement_case import ProcurementCase


@pytest.fixture
def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    c = AsyncClient(transport=transport, base_url="http://test")
    yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_rule_with_foreign_key_disassociation(client: AsyncClient, db):
    # 1. Create a dummy procurement case
    case = ProcurementCase(
        case_number="CASE-DEL-001",
        vendor_name="Acme Corp",
        status="OPEN",
        risk_level="LOW",
    )
    db.add(case)
    await db.flush()

    # 2. Create a rule
    rule = ComplianceRule(
        name="Rule To Delete",
        description="A rule testing permanent deletion",
        tier=1,
        severity="HIGH",
        on_violation="REJECT",
        status="CONFIRMED",
        enabled=True,
    )
    db.add(rule)
    await db.flush()

    # 3. Create a finding referencing the rule
    finding = ComplianceFinding(
        case_id=case.id,
        rule_id=rule.id,
        finding_type="TEST_FINDING",
        severity="HIGH",
        status="VIOLATION",
        finding_review_status="OPEN",
    )
    db.add(finding)
    await db.flush()

    # 4. Create an audit entry referencing the rule
    audit = AuditEntry(
        case_id=case.id,
        rule_id=rule.id,
        action="RULE_TEST",
    )
    db.add(audit)
    await db.commit()

    # 5. Call DELETE /api/rules/{rule_id}
    resp = await client.delete(f"/api/rules/{rule.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # 6. Verify rule is deleted
    rule_check = (await db.execute(select(ComplianceRule).where(ComplianceRule.id == rule.id))).scalar_one_or_none()
    assert rule_check is None

    # 7. Verify finding and audit entry still exist, but rule_id is nullified
    finding_check = (await db.execute(select(ComplianceFinding).where(ComplianceFinding.id == finding.id))).scalar_one_or_none()
    assert finding_check is not None
    assert finding_check.rule_id is None

    audit_check = (await db.execute(select(AuditEntry).where(AuditEntry.id == audit.id))).scalar_one_or_none()
    assert audit_check is not None
    assert audit_check.rule_id is None


@pytest.mark.asyncio
async def test_policy_upload_tri_case(client: AsyncClient, db):
    content_v1 = b"%PDF-1.4 Dummy PDF Content V1"
    content_v2 = b"%PDF-1.4 Dummy PDF Content V2 - Minor Change"

    with patch("app.routers.policy.ingest_policy_background", new_callable=AsyncMock):
        # Case 1: Brand new policy upload -> 202 Accepted
        file_v1 = ("policy1.pdf", io.BytesIO(content_v1), "application/pdf")
        resp1 = await client.post(
            "/api/policies/upload",
            data={"title": "General Procurement Policy", "version": "1.0"},
            files={"file": file_v1},
        )
        assert resp1.status_code == 202
        data1 = resp1.json()
        assert data1["title"] == "General Procurement Policy"
        assert data1["version"] == "1.0"
        assert data1["ingestion_status"] == "PROCESSING"

        # Case 2: Exact duplicate document uploaded -> 409 Conflict
        file_dup = ("policy1_dup.pdf", io.BytesIO(content_v1), "application/pdf")
        resp2 = await client.post(
            "/api/policies/upload",
            data={"title": "Different Title", "version": "2.0"},
            files={"file": file_dup},
        )
        assert resp2.status_code == 409
        assert "identical to 'General Procurement Policy'" in resp2.json()["detail"]

        # Case 3: Updated version of same policy (same title, new content) -> 202 Accepted, auto-bump version to 1.1
        file_v2 = ("policy_updated.pdf", io.BytesIO(content_v2), "application/pdf")
        resp3 = await client.post(
            "/api/policies/upload",
            data={"title": "General Procurement Policy"},  # no version provided -> auto bumps to 1.1
            files={"file": file_v2},
        )
        assert resp3.status_code == 202
        data3 = resp3.json()
        assert data3["title"] == "General Procurement Policy"
        assert data3["version"] == "1.1"
        assert data3["ingestion_status"] == "PROCESSING"


@pytest.mark.asyncio
async def test_delete_policy_cascades(client: AsyncClient, db):
    # 1. Create a policy document
    policy = PolicyDocument(
        title="Policy To Delete",
        version="1.0",
        file_hash="dummy_hash_for_deletion",
        ingestion_status="COMPLETED",
        is_active=True,
    )
    db.add(policy)
    await db.flush()

    # 2. Add a policy chunk
    chunk = PolicyChunk(
        policy_id=policy.id,
        chunk_index=0,
        content="Dummy chunk text",
    )
    db.add(chunk)

    # 3. Add a rule linked to this policy
    rule = ComplianceRule(
        policy_id=policy.id,
        name="Linked Rule To Policy",
        description="Linked rule description",
        tier=1,
        severity="MEDIUM",
        on_violation="REJECT",
        status="CONFIRMED",
        enabled=True,
    )
    db.add(rule)
    await db.commit()

    # 4. Call DELETE /api/policies/{policy_id}
    resp = await client.delete(f"/api/policies/{policy.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # 5. Verify policy, chunk, and rule are gone
    p_check = (await db.execute(select(PolicyDocument).where(PolicyDocument.id == policy.id))).scalar_one_or_none()
    assert p_check is None

    c_check = (await db.execute(select(PolicyChunk).where(PolicyChunk.policy_id == policy.id))).scalar_one_or_none()
    assert c_check is None

    r_check = (await db.execute(select(ComplianceRule).where(ComplianceRule.policy_id == policy.id))).scalar_one_or_none()
    assert r_check is None
