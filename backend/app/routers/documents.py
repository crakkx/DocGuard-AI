import hashlib
import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.document import Document, ExtractedData
from app.services.audit_service import audit_service
from app.services.classifier import classifier
from app.services.extractor import extractor
from app.services.linker import linker

router = APIRouter()


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document, classify it, extract fields, and auto-link to a case."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    safe_name = file.filename.replace(" ", "_")
    dest = upload_dir / safe_name
    # Make unique if collision
    counter = 1
    while dest.exists():
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        dest = upload_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)

    # File hash for duplicate detection
    file_hash = hashlib.sha256(content).hexdigest()

    # Classify
    try:
        import fitz
        with fitz.open(str(dest)) as doc:
            text = "".join(page.get_text() for page in doc)
            page_count = len(doc)
    except Exception:
        text = ""
        page_count = 1

    doc_type, confidence = classifier.classify(text, file.filename)

    # Persist document
    document = Document(
        filename=dest.name,
        original_filename=file.filename,
        filepath=str(dest),
        document_type=doc_type,
        type_confidence=confidence,
        file_hash=file_hash,
        page_count=page_count,
        status="CLASSIFIED",
    )
    db.add(document)
    await db.flush()

    # Extract fields with VLM
    fields = await extractor.extract_async(str(dest), doc_type)
    for f_data in fields:
        extracted = ExtractedData(
            document_id=document.id,
            field_name=f_data.field_name,
            field_value=f_data.field_value,
            field_type=f_data.field_type,
            confidence=f_data.confidence,
            source_page=f_data.source_page,
            source_bbox=f_data.source_bbox,
        )
        db.add(extracted)
    await db.flush()

    document.status = "EXTRACTED"

    await audit_service.log(
        db,
        "DOCUMENT_UPLOADED",
        f"Uploaded {file.filename} → classified as {doc_type} ({confidence:.0%})",
        document_id=document.id,
    )

    # Auto-link to case (skip for POLICY type)
    case = None
    if doc_type != "POLICY":
        case = await linker.auto_link(document, db)
        await audit_service.log(
            db,
            "DOCUMENTS_LINKED",
            f"Linked {document.filename} to case {case.case_number}",
            case_id=case.id,
            document_id=document.id,
        )

    await db.commit()
    await db.refresh(document)

    return {
        "id": str(document.id),
        "filename": document.filename,
        "original_filename": document.original_filename,
        "document_type": document.document_type,
        "classification_confidence": document.type_confidence,
        "page_count": document.page_count,
        "uploaded_at": document.created_at,
        "case_id": str(case.id) if case else None,
        "case_number": case.case_number if case else None,
        "extracted_fields_count": len(fields),
    }


@router.get("/")
async def list_documents(
    document_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document).offset(skip).limit(limit).order_by(Document.created_at.desc())
    if document_type:
        stmt = stmt.where(Document.document_type == document_type)
    result = await db.execute(stmt)
    docs = result.scalars().all()

    out = []
    for d in docs:
        fields_result = await db.execute(
            select(ExtractedData).where(ExtractedData.document_id == d.id)
        )
        fields = fields_result.scalars().all()
        out.append({
            "id": str(d.id),
            "filename": d.filename,
            "original_filename": d.original_filename,
            "document_type": d.user_corrected_type or d.document_type,
            "classification_confidence": d.type_confidence,
            "page_count": getattr(d, "page_count", None),
            "uploaded_at": d.created_at,
            "extracted_data": [
                {
                    "id": str(f.id),
                    "field_name": f.field_name,
                    "field_value": f.field_value,
                    "field_type": f.field_type,
                    "confidence": f.confidence,
                    "source_page": f.source_page,
                }
                for f in fields
            ],
        })
    return out


@router.get("/{doc_id}")
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == UUID(doc_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    fields_result = await db.execute(
        select(ExtractedData).where(ExtractedData.document_id == doc.id)
    )
    fields = fields_result.scalars().all()

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "document_type": doc.user_corrected_type or doc.document_type,
        "classification_confidence": doc.type_confidence,
        "page_count": getattr(doc, "page_count", None),
        "uploaded_at": doc.created_at,
        "extracted_data": [
            {
                "id": str(f.id),
                "field_name": f.field_name,
                "field_value": f.field_value,
                "field_type": f.field_type,
                "confidence": f.confidence,
                "source_page": f.source_page,
            }
            for f in fields
        ],
    }


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Permanently delete a document and unlink it from any cases."""
    result = await db.execute(select(Document).where(Document.id == UUID(doc_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from app.models.procurement_case import ProcurementCase
    from app.models.finding import ComplianceFinding
    from app.models.review import ReviewDecision
    from app.models.document import ExtractedData
    from app.models.audit import AuditEntry
    from app.models.policy import PolicyDocument
    from sqlalchemy import update, delete

    uid = UUID(doc_id)

    # 1. Delete or unlink related cases
    cases_result = await db.execute(
        select(ProcurementCase).where(
            (ProcurementCase.po_document_id == uid)
            | (ProcurementCase.invoice_document_id == uid)
            | (ProcurementCase.grn_document_id == uid)
        )
    )
    linked_cases = cases_result.scalars().all()

    for c in linked_cases:
        other_docs = [
            did for did in (c.po_document_id, c.invoice_document_id, c.grn_document_id)
            if did and did != uid
        ]
        if not other_docs:
            # Case only had this document: delete the entire case and its findings/audits
            await db.execute(update(AuditEntry).where(AuditEntry.case_id == c.id).values(finding_id=None))
            await db.execute(delete(ComplianceFinding).where(ComplianceFinding.case_id == c.id))
            await db.execute(delete(ReviewDecision).where(ReviewDecision.case_id == c.id))
            await db.execute(delete(AuditEntry).where(AuditEntry.case_id == c.id))
            await db.delete(c)
        else:
            # Case has other document(s); unlink this deleted document
            if c.po_document_id == uid:
                c.po_document_id = None
            if c.invoice_document_id == uid:
                c.invoice_document_id = None
            if c.grn_document_id == uid:
                c.grn_document_id = None

    # Also clean up any empty orphaned cases without any documents
    orphaned_res = await db.execute(
        select(ProcurementCase).where(
            ProcurementCase.po_document_id.is_(None)
            & ProcurementCase.invoice_document_id.is_(None)
            & ProcurementCase.grn_document_id.is_(None)
        )
    )
    for oc in orphaned_res.scalars().all():
        await db.execute(update(AuditEntry).where(AuditEntry.case_id == oc.id).values(finding_id=None))
        await db.execute(delete(ComplianceFinding).where(ComplianceFinding.case_id == oc.id))
        await db.execute(delete(ReviewDecision).where(ReviewDecision.case_id == oc.id))
        await db.execute(delete(AuditEntry).where(AuditEntry.case_id == oc.id))
        await db.delete(oc)

    # 2. Nullify references in policy documents
    await db.execute(update(PolicyDocument).where(PolicyDocument.source_file_id == uid).values(source_file_id=None))

    # 3. Delete extracted data associated with this document
    await db.execute(delete(ExtractedData).where(ExtractedData.document_id == uid))

    # 4. Nullify existing audit entries referencing this document
    await db.execute(update(AuditEntry).where(AuditEntry.document_id == uid).values(document_id=None))

    # 5. Delete physical file if present
    try:
        import os
        if doc.filepath and os.path.exists(doc.filepath):
            os.remove(doc.filepath)
    except Exception:
        pass

    filename_for_log = doc.original_filename or doc.filename

    # 6. Delete document record
    await db.delete(doc)
    await db.flush()

    # 7. Log audit event without referencing deleted document_id FK
    await audit_service.log(
        db,
        "DOCUMENT_DELETED",
        f"Deleted document {filename_for_log}",
        metadata={"deleted_document_id": str(uid)},
    )
    await db.commit()
    return {"deleted": True, "id": doc_id}


@router.patch("/{doc_id}/classify")
async def reclassify_document(
    doc_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == UUID(doc_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    new_type = body.get("document_type")
    if new_type not in ("INVOICE", "PURCHASE_ORDER", "GOODS_RECEIPT", "POLICY"):
        raise HTTPException(status_code=422, detail="Invalid document_type")

    doc.user_corrected_type = new_type
    await audit_service.log(
        db,
        "DOCUMENT_CLASSIFIED",
        f"User reclassified {doc.filename} as {new_type}",
        document_id=doc.id,
    )
    await db.commit()
    return {"id": str(doc.id), "document_type": new_type, "user_corrected": True}
