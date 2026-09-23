from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Text, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
from decimal import Decimal

class ProcurementCase(Base):
    __tablename__ = "procurement_cases"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_number: Mapped[str] = mapped_column(String(50), unique=True)
    status: Mapped[str] = mapped_column(String(50), default="OPEN") # OPEN, COMPLIANT, NEEDS_REVIEW, VIOLATION, REJECTED, APPROVED
    
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=True)
    po_number: Mapped[str] = mapped_column(String(100), nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=True)
    department: Mapped[str] = mapped_column(String(255), nullable=True)
    project_code: Mapped[str] = mapped_column(String(100), nullable=True)

    po_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=True)
    invoice_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=True)
    grn_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=True)

    risk_level: Mapped[str] = mapped_column(String(20), default="LOW")
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    po_document = relationship("Document", foreign_keys=[po_document_id])
    invoice_document = relationship("Document", foreign_keys=[invoice_document_id])
    grn_document = relationship("Document", foreign_keys=[grn_document_id])
    
    findings = relationship("ComplianceFinding", back_populates="case", cascade="all, delete-orphan")
    reviews = relationship("ReviewDecision", back_populates="case", cascade="all, delete-orphan")
    audits = relationship("AuditEntry", back_populates="case", cascade="all, delete-orphan")
