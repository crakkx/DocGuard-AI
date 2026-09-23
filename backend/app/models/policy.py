from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base
from pgvector.sqlalchemy import Vector
import uuid
from typing import Optional

class PolicyDocument(Base):
    __tablename__ = "policy_documents"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(50), nullable=True)
    effective_date: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)
    source_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("documents.id"), nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    total_chunks: Mapped[int] = mapped_column(default=0)
    rules_extracted: Mapped[int] = mapped_column(default=0)
    ingestion_status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    chunks = relationship("PolicyChunk", back_populates="policy", cascade="all, delete-orphan")
    rules = relationship("ComplianceRule", back_populates="policy", cascade="all, delete-orphan")

class PolicyChunk(Base):
    __tablename__ = "policy_chunks"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policy_documents.id"))
    chunk_index: Mapped[int] = mapped_column(default=0)
    section_number: Mapped[str] = mapped_column(String(50), nullable=True)
    section_title: Mapped[str] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(384), nullable=True)
    page_number: Mapped[int] = mapped_column(nullable=True)

    policy = relationship("PolicyDocument", back_populates="chunks")
