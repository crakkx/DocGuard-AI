from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.compliance_rule import ComplianceRule
from app.models.finding import ComplianceFinding
from app.models.audit import AuditEntry
from app.services.audit_service import audit_service

router = APIRouter()


def _serialize(r: ComplianceRule) -> dict:
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
        "confirmed_by": r.confirmed_by,
        "confirmed_at": r.confirmed_at,
        "enabled": r.enabled,
        "created_at": r.created_at,
    }


@router.get("/")
async def list_rules(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ComplianceRule).order_by(ComplianceRule.created_at.desc())
    if status:
        stmt = stmt.where(ComplianceRule.status == status)
    result = await db.execute(stmt)
    return [_serialize(r) for r in result.scalars().all()]


@router.get("/pending")
async def list_pending_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ComplianceRule)
        .where(ComplianceRule.status == "PENDING_REVIEW")
        .order_by(ComplianceRule.created_at.desc())
    )
    return [_serialize(r) for r in result.scalars().all()]


def _parse_uuid(val: str) -> UUID:
    try:
        return UUID(str(val).strip())
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail="Rule not found")


@router.get("/{rule_id}")
async def get_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    uid = _parse_uuid(rule_id)
    result = await db.execute(
        select(ComplianceRule).where(ComplianceRule.id == uid)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _serialize(rule)


@router.patch("/{rule_id}")
async def update_rule(
    rule_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    uid = _parse_uuid(rule_id)
    result = await db.execute(
        select(ComplianceRule).where(ComplianceRule.id == uid)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    updatable = ("name", "description", "severity", "on_violation",
                 "parameters", "expression", "evaluation_prompt")
    for field in updatable:
        if field in body:
            setattr(rule, field, body[field])

    await audit_service.log(
        db, "RULE_UPDATED", f"Rule '{rule.name}' updated",
        rule_id=rule.id, metadata=body,
    )
    await db.commit()
    return _serialize(rule)


@router.post("/{rule_id}/confirm")
async def confirm_rule(
    rule_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    uid = _parse_uuid(rule_id)
    result = await db.execute(
        select(ComplianceRule).where(ComplianceRule.id == uid)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    confirmed_by = body.get("confirmed_by", "REVIEWER")
    rule.status = "CONFIRMED"
    rule.enabled = True
    rule.confirmed_by = confirmed_by
    rule.confirmed_at = datetime.utcnow()

    await audit_service.log(
        db, "RULE_CONFIRMED", f"Rule '{rule.name}' confirmed by {confirmed_by}",
        rule_id=rule.id,
    )
    await db.commit()
    return _serialize(rule)


@router.post("/{rule_id}/reject")
async def reject_rule(
    rule_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    uid = _parse_uuid(rule_id)
    result = await db.execute(
        select(ComplianceRule).where(ComplianceRule.id == uid)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.status = "REJECTED"
    rule.enabled = False
    reason = body.get("reason", "")
    await audit_service.log(
        db, "RULE_REJECTED", f"Rule '{rule.name}' rejected: {reason}",
        rule_id=rule.id,
    )
    await db.commit()
    return _serialize(rule)


@router.post("/{rule_id}/disable")
async def disable_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    uid = _parse_uuid(rule_id)
    result = await db.execute(
        select(ComplianceRule).where(ComplianceRule.id == uid)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.status = "DISABLED"
    rule.enabled = False
    await audit_service.log(
        db, "RULE_DISABLED", f"Rule '{rule.name}' disabled",
        rule_id=rule.id,
    )
    await db.commit()
    return _serialize(rule)


@router.post("/{rule_id}/enable")
async def enable_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    uid = _parse_uuid(rule_id)
    result = await db.execute(
        select(ComplianceRule).where(ComplianceRule.id == uid)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.status = "CONFIRMED"
    rule.enabled = True
    await audit_service.log(
        db, "RULE_ENABLED", f"Rule '{rule.name}' re-enabled",
        rule_id=rule.id,
    )
    await db.commit()
    return _serialize(rule)


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    uid = _parse_uuid(rule_id)
    result = await db.execute(
        select(ComplianceRule).where(ComplianceRule.id == uid)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule_name = rule.name
    # Disassociate rule_id from findings and audit entries to prevent foreign key errors
    await db.execute(
        update(ComplianceFinding).where(ComplianceFinding.rule_id == uid).values(rule_id=None)
    )
    await db.execute(
        update(AuditEntry).where(AuditEntry.rule_id == uid).values(rule_id=None)
    )

    await db.delete(rule)
    await audit_service.log(
        db, "RULE_DELETED", f"Rule '{rule_name}' permanently deleted",
    )
    await db.commit()
    return {"status": "success", "message": f"Rule '{rule_name}' deleted"}

