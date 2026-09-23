from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from app.database import Base
import uuid
from typing import Optional

# Portable JSON: renders as JSONB on Postgres (native support, indexable) but
# falls back to a generic JSON type on other dialects (e.g. SQLite in tests),
# since JSONB itself has no SQLite compiler and breaks Base.metadata.create_all().
PortableJSON = JSON().with_variant(JSONB(), "postgresql")


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("procurement_cases.id"), nullable=True
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    finding_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("compliance_findings.id", ondelete="SET NULL"), nullable=True
    )
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("compliance_rules.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(100), default="SYSTEM")
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", PortableJSON, default=dict)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    case = relationship("ProcurementCase", back_populates="audits")
