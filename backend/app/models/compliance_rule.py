from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid

class ComplianceRule(Base):
    __tablename__ = "compliance_rules"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policy_documents.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)

    tier: Mapped[int] = mapped_column() # 1=Primitive, 2=Expression, 3=LLM
    primitive: Mapped[str] = mapped_column(String(50), nullable=True)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=True)
    expression: Mapped[dict] = mapped_column(JSON, nullable=True)
    evaluation_prompt: Mapped[str] = mapped_column(Text, nullable=True)

    severity: Mapped[str] = mapped_column(String(20)) # HIGH, MEDIUM, LOW
    on_violation: Mapped[str] = mapped_column(String(50)) # FLAG, BLOCK, NEEDS_REVIEW
    status: Mapped[str] = mapped_column(String(50), default="PENDING_REVIEW") # PENDING_REVIEW, CONFIRMED, REJECTED, DISABLED

    # Source policy traceability (populated by rule_extractor from the source policy chunk)
    source_clause: Mapped[str] = mapped_column(Text, nullable=True)
    source_section: Mapped[str] = mapped_column(String(100), nullable=True)
    source_page: Mapped[int] = mapped_column(Integer, nullable=True)

    # Human confirmation lifecycle
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # only True once CONFIRMED
    confirmed_by: Mapped[str] = mapped_column(String(255), nullable=True)
    confirmed_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    policy = relationship("PolicyDocument", back_populates="rules")
