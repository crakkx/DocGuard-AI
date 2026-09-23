from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.database import Base
import uuid
from typing import Optional


class ComplianceFinding(Base):
    __tablename__ = "compliance_findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("procurement_cases.id"), nullable=False
    )
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("compliance_rules.id"), nullable=True
    )

    finding_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    tier: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # PRIMITIVE, EXPRESSION, LLM_EVALUATED
    rule_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Comparison values
    expected_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actual_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Policy evidence (from RAG)
    policy_clause_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    policy_document_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    policy_section: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    policy_page: Mapped[Optional[int]] = mapped_column(nullable=True)
    policy_similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # LLM evaluation metadata (Tier 3)
    llm_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Review fields
    status: Mapped[str] = mapped_column(String(50), default="VIOLATION")  # VIOLATION, NEEDS_REVIEW, OPEN
    finding_review_status: Mapped[str] = mapped_column(
        String(50), default="OPEN"
    )  # OPEN, ACCEPTED, REJECTED, NEEDS_REVIEW
    reviewer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewer_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("ProcurementCase", back_populates="findings")
    rule = relationship("ComplianceRule")
