from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.audit import AuditEntry


class AuditService:
    async def log(
        self,
        db: AsyncSession,
        action: str,
        detail: str = "",
        actor: str = "SYSTEM",
        case_id: Optional[UUID] = None,
        document_id: Optional[UUID] = None,
        finding_id: Optional[UUID] = None,
        rule_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            action=action,
            detail=detail,
            actor=actor,
            case_id=case_id,
            document_id=document_id,
            finding_id=finding_id,
            rule_id=rule_id,
            metadata_=metadata or {},
        )
        db.add(entry)
        await db.flush()
        return entry

    async def get_case_audit(self, case_id: UUID, db: AsyncSession) -> list[AuditEntry]:
        stmt = (
            select(AuditEntry)
            .where(AuditEntry.case_id == case_id)
            .order_by(AuditEntry.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


audit_service = AuditService()
