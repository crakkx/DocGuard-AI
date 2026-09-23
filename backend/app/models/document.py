from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum

class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    CLASSIFIED = "CLASSIFIED"
    EXTRACTED = "EXTRACTED"
    FAILED = "FAILED"

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=True)
    filepath: Mapped[str] = mapped_column(String(512))
    document_type: Mapped[str] = mapped_column(String(50), nullable=True) # PURCHASE_ORDER, INVOICE, GOODS_RECEIPT
    user_corrected_type: Mapped[str] = mapped_column(String(50), nullable=True)
    type_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=True)
    page_count: Mapped[int] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=DocumentStatus.UPLOADED)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    extracted_data = relationship("ExtractedData", back_populates="document", cascade="all, delete-orphan")
    
class ExtractedData(Base):
    __tablename__ = "extracted_data"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"))
    field_name: Mapped[str] = mapped_column(String(100))
    field_value: Mapped[str] = mapped_column(Text)
    field_type: Mapped[str] = mapped_column(String(50)) # text, amount, date, line_items
    confidence: Mapped[float] = mapped_column(Float)
    source_page: Mapped[int] = mapped_column(nullable=True)
    source_bbox: Mapped[str] = mapped_column(String(255), nullable=True)

    document = relationship("Document", back_populates="extracted_data")
