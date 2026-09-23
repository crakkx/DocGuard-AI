from uuid import UUID
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, ExtractedData
from app.models.procurement_case import ProcurementCase


class TransactionLinker:
    """Links procurement documents (PO, Invoice, GRN) into a ProcurementCase."""

    async def auto_link(
        self, document: Document, db: AsyncSession
    ) -> ProcurementCase:
        """
        Try to link a document to an existing case by PO number.
        If none found, create a new case.
        """
        po_number = await self._get_field(document.id, "po_number", db)
        vendor_name = await self._get_field(document.id, "vendor_name", db)
        invoice_number = await self._get_field(document.id, "invoice_number", db)
        total_amount = await self._get_field(document.id, "total_amount", db)
        department = await self._get_field(document.id, "department", db)
        project_code = await self._get_field(document.id, "project_code", db)

        case: Optional[ProcurementCase] = None

        # Try to find existing case by PO number
        if po_number:
            stmt = select(ProcurementCase).where(
                ProcurementCase.po_number == po_number
            )
            result = await db.execute(stmt)
            case = result.scalar_one_or_none()

        # Create new case if not found
        if case is None:
            case_number = await self._generate_case_number(db)
            case = ProcurementCase(
                case_number=case_number,
                vendor_name=vendor_name,
                po_number=po_number,
                currency="INR",
                status="PENDING",
            )
            db.add(case)
            await db.flush()

        # Link document to the appropriate slot
        doc_type = document.user_corrected_type or document.document_type

        if doc_type == "PURCHASE_ORDER" and case.po_document_id is None:
            case.po_document_id = document.id
            if po_number:
                case.po_number = po_number
            if vendor_name:
                case.vendor_name = vendor_name
            if department:
                case.department = department
            if project_code:
                case.project_code = project_code
            if total_amount:
                try:
                    from decimal import Decimal
                    case.total_amount = Decimal(str(total_amount).replace(",", ""))
                except Exception:
                    pass

        elif doc_type == "INVOICE" and case.invoice_document_id is None:
            case.invoice_document_id = document.id
            if invoice_number:
                case.invoice_number = invoice_number
            if vendor_name and not case.vendor_name:
                case.vendor_name = vendor_name
            if total_amount:
                try:
                    from decimal import Decimal
                    case.total_amount = Decimal(str(total_amount).replace(",", ""))
                except Exception:
                    pass

        elif doc_type == "GOODS_RECEIPT" and case.grn_document_id is None:
            case.grn_document_id = document.id

        await db.flush()
        return case

    async def manual_link(
        self, case_id: UUID, document_id: UUID, db: AsyncSession
    ) -> ProcurementCase:
        """Manually link a document to a case."""
        case_result = await db.execute(
            select(ProcurementCase).where(ProcurementCase.id == case_id)
        )
        case = case_result.scalar_one_or_none()
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        doc_result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = doc_result.scalar_one_or_none()
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        doc_type = document.user_corrected_type or document.document_type

        if doc_type == "PURCHASE_ORDER":
            case.po_document_id = document_id
        elif doc_type == "INVOICE":
            case.invoice_document_id = document_id
        elif doc_type == "GOODS_RECEIPT":
            case.grn_document_id = document_id

        await db.flush()
        return case

    async def _get_field(
        self, document_id: UUID, field_name: str, db: AsyncSession
    ) -> Optional[str]:
        stmt = select(ExtractedData).where(
            ExtractedData.document_id == document_id,
            ExtractedData.field_name == field_name,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return row.field_value if row else None

    async def _generate_case_number(self, db: AsyncSession) -> str:
        from datetime import datetime
        year = datetime.utcnow().year
        count_result = await db.execute(
            select(func.count(ProcurementCase.id))
        )
        count = count_result.scalar() or 0
        return f"CASE-{year}-{count + 1:04d}"


linker = TransactionLinker()
