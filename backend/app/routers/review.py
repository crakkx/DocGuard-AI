from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.finding import ComplianceFinding
from app.models.procurement_case import ProcurementCase
from app.models.review import ReviewDecision
from app.services.audit_service import audit_service

router = APIRouter()


@router.patch("/findings/{finding_id}")
async def review_finding(
    finding_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Accept, reject, or flag a finding for review."""
    result = await db.execute(
        select(ComplianceFinding).where(ComplianceFinding.id == UUID(finding_id))
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    review_status = body.get("status")
    valid_statuses = ("ACCEPTED", "REJECTED", "NEEDS_REVIEW", "OPEN")
    if review_status not in valid_statuses:
        raise HTTPException(status_code=422, detail=f"status must be one of {valid_statuses}")

    reviewer = body.get("reviewer", "REVIEWER")
    comment = body.get("reviewer_comment", "")

    finding.finding_review_status = review_status
    finding.reviewer = reviewer
    finding.reviewer_comment = comment
    finding.reviewed_at = datetime.utcnow()

    await audit_service.log(
        db,
        "FINDING_REVIEWED",
        f"Finding {finding.finding_type} → {review_status} by {reviewer}",
        case_id=finding.case_id,
        finding_id=finding.id,
        metadata={"reviewer": reviewer, "status": review_status, "comment": comment},
    )
    await db.commit()

    return {
        "id": str(finding.id),
        "finding_review_status": finding.finding_review_status,
        "reviewer": finding.reviewer,
        "reviewer_comment": finding.reviewer_comment,
        "reviewed_at": finding.reviewed_at,
    }


@router.post("/cases/{case_id}/decision")
async def make_case_decision(
    case_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Make the final case-level review decision (APPROVE / REJECT / HOLD)."""
    result = await db.execute(
        select(ProcurementCase).where(ProcurementCase.id == UUID(case_id))
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    decision = body.get("decision")
    valid_decisions = ("APPROVE", "REJECT", "HOLD")
    if decision not in valid_decisions:
        raise HTTPException(status_code=422, detail=f"decision must be one of {valid_decisions}")

    reviewer = body.get("reviewer", "REVIEWER")
    comment = body.get("comment", "")

    # Persist decision record
    review_record = ReviewDecision(
        case_id=case.id,
        decision=decision,
        reviewer=reviewer,
        comment=comment,
    )
    db.add(review_record)

    # Update case status
    status_map = {
        "APPROVE": "APPROVED",
        "REJECT": "REJECTED",
        "HOLD": "ON_HOLD",
    }
    case.status = status_map[decision]

    await audit_service.log(
        db,
        "CASE_DECISION_MADE",
        f"Case {case.case_number} → {decision} by {reviewer}",
        case_id=case.id,
        metadata={"decision": decision, "reviewer": reviewer, "comment": comment},
    )
    await db.commit()

    return {
        "case_id": case_id,
        "decision": decision,
        "reviewer": reviewer,
        "comment": comment,
        "case_status": case.status,
    }
