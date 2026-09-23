import re
import json
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ExtractedFieldData:
    field_name: str
    field_value: str
    field_type: str  # text, amount, date, line_items
    confidence: float
    source_page: int = 1
    source_bbox: str = ""


class DocumentExtractor:
    """
    Extracts structured fields from procurement documents.
    Uses PyMuPDF for text extraction + regex patterns per document type.
    Falls back to RapidOCR for image-based PDFs.
    """

    # ── Regex patterns ────────────────────────────────────────────────────────
    INVOICE_PATTERNS = {
        "invoice_number": [
            r"invoice\s*(?:no|number|#)[:\s#]*([A-Z0-9\-/]+)",
            r"inv[.\s-]*(?:no|#)[:\s]*([A-Z0-9\-/]+)",
            r"bill\s*no[:\s]*([A-Z0-9\-/]+)",
        ],
        "invoice_date": [
            r"invoice\s*date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"date\s*of\s*invoice[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"bill\s*date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"date[:\s]*(\d{1,2}[-/]\w{3,9}[-/]\d{2,4})",
        ],
        "vendor_name": [
            r"(?:from|seller|vendor|bill\s*from|supplier)[:\s]*([A-Za-z0-9&.,\s]+(?:Ltd|Pvt|Inc|LLC|Corp|LLP)?)",
        ],
        "po_number": [
            r"(?:p\.?o\.?\s*(?:no|number|#)|purchase\s*order\s*(?:no|#))[:\s#]*([A-Z0-9\-/]+)",
            r"ref[:\s]+(?:po[:\s]*)([A-Z0-9\-/]+)",
        ],
        "subtotal": [
            r"sub[\s-]*total[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
            r"taxable\s*amount[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
        ],
        "tax": [
            r"(?:gst|tax|vat|igst|cgst|sgst)[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
            r"tax\s*amount[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
        ],
        "total_amount": [
            r"(?:grand\s*total|total\s*amount|amount\s*payable|total\s*due|net\s*amount)[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
            r"total[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
        ],
    }

    PO_PATTERNS = {
        "po_number": [
            # Multi-line format: "Purchase Order\nNo.\nMNIT/..."
            r"Purchase\s+Order[\s\n]+No\.?[\s\n]+([A-Z0-9/\-]+)",
            r"(?:purchase\s*order\s*(?:no|number|#)|po\s*(?:no|number|#)|p\.?o\.?\s*(?:no|#)|order\s*(?:no|number|#))[:\s#\n]*([A-Z0-9\-/]+)",
            r"order\s*(?:no|number|#)[:\s#\n]*([A-Z0-9\-/]+)",
        ],
        "po_date": [
            r"(?:order\s*date|po\s*date|po\s*date)[:\s\n]*(\d{1,2}[\s\w]*\d{4})",
            r"(?:order\s*date|po\s*date|date)[:\s\n]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"date[:\s\n]*(\d{1,2}[-/]\w{3,9}[-/]\d{2,4})",
        ],
        "vendor_name": [
            # Direct "Seller\nName" layout (newline between label and value)
            r"(?:^|\n)Seller[\s\n]+([A-Za-z0-9&.,\s]+(?:Pvt\.?\s*Ltd\.?|Ltd\.?|Inc\.?|Corp\.?|LLC|LLP|Enterprises|Solutions|Systems|Services))",
            r"(?:supplier|vendor|seller|issued\s*to)[\s:\n]*(?:bill\s*to[^\n]*\n)?([A-Za-z0-9&.,\s]+(?:Pvt\.?\s*Ltd\.?|Ltd\.?|Inc\.?|Corp\.?|LLC|LLP|Enterprises|Solutions|Systems))",
            r"(?:supplier|vendor|seller)[:\s\n]+([A-Za-z0-9&.,\s]+(?:Ltd|Pvt|Inc|LLC|Corp|LLP))",
            r"(?:supplier|vendor|seller)[:\s\n]+([A-Za-z0-9&.,\s]+)",
        ],
        "procurement_method": [
            # Multi-line layout: "Procurement\nMethod\nGeM Direct Purchase"
            r"Procurement[\s\n]+Method[\s\n]+([A-Za-z\s]+(?:Purchase|Tender|Enquiry|Purchase))",
            r"(?:procurement\s*method|purchase\s*method|purchase\s*mode|mode\s*of\s*procurement)[:\s\n]*([A-Za-z\s]+)",
        ],
        "gem_reference": [
            # Multi-line: "GeM Order ID\nGEMC-511687742190398"
            r"GeM\s+Order\s+ID[\s\n]+([A-Z0-9\-]+)",
            # Bid/Order reference inline
            r"(?:gem\s*(?:bid\s*/\s*order\s*reference|bid\s*reference|order\s*reference|order\s*id|order\s*no|bid\s*id))[:\s\n]*([A-Za-z0-9\-/]+)",
            # Fallback
            r"GeM[\s/]*(?:Order|Bid|Ref(?:erence)?)[:\s\n]*([A-Za-z0-9\-/]+)",
        ],
        "requester": [
            r"(?:requested\s*by|raised\s*by|prepared\s*by)[:\s]*([A-Za-z\s]+)",
        ],
        "approver": [
            r"(?:approved\s*by|authorised\s*by|authorized\s*by)[:\s]*([A-Za-z\s]+)",
        ],
        "department": [
            r"(?:department|dept|division)[:\s]*(?:of\s+)?([A-Za-z\s&]+)",
        ],
        "project_code": [
            r"(?:project\s*(?:code|no|id)|cost\s*center|budget\s*head)[:\s]*([A-Z0-9\-]+)",
        ],
        "total_amount": [
            # Multi-line: "Total Procurement Value\nINR 23,600.00"
            r"Total\s+Procurement\s+Value[\s\n]+(?:INR[\s]*)?([0-9,]+(?:\.\d{2})?)",
            # Certified amount from bill/voucher page
            r"Total\s+Certified\s+Amount[\s\n]+(?:INR[\s]*)?([0-9,]+(?:\.\d{2})?)",
            r"(?:grand\s*total|total\s*(?:order\s*)?(?:value|amount)|net\s*amount)[:\s₹$INR]*([0-9,]+(?:\.\d{2})?)",
            r"total[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
        ],
        "voucher_number": [
            r"(?:voucher\s*no\.?|vch\s*no\.?)[\s:\n]*([A-Z0-9/\-]+)",
        ],
        "certified_by": [
            r"(?:certified\s*by|certification\s*status)[:\s\n]*([A-Za-z\s]+)",
        ],
    }

    GRN_PATTERNS = {
        "receipt_number": [
            r"(?:grn\s*(?:no|number|#)|receipt\s*(?:no|number|#)|delivery\s*note\s*(?:no|#))[:\s#]*([A-Z0-9\-/]+)",
        ],
        "po_number": [
            r"(?:p\.?o\.?\s*(?:no|number|#)|purchase\s*order\s*(?:no|#))[:\s#]*([A-Z0-9\-/]+)",
            r"ref[:\s]+(?:po[:\s]*)([A-Z0-9\-/]+)",
        ],
        "receipt_date": [
            r"(?:receipt\s*date|received\s*on|delivery\s*date|date)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ],
        "received_by": [
            r"(?:received\s*by|accepted\s*by)[:\s]*([A-Za-z\s]+)",
        ],
    }

    def extract(self, filepath: str, doc_type: str) -> list[ExtractedFieldData]:
        """Main extraction entry point."""
        text, page_texts = self._extract_text(filepath)
        if not text.strip():
            # Try OCR
            text = self._ocr_extract(filepath)
            page_texts = {1: text}

        results: list[ExtractedFieldData] = []

        if doc_type == "INVOICE":
            results = self._extract_with_patterns(text, page_texts, self.INVOICE_PATTERNS, "text")
            results.extend(self._retype_amounts(results, ["subtotal", "tax", "total_amount"]))
        elif doc_type == "PURCHASE_ORDER":
            results = self._extract_with_patterns(text, page_texts, self.PO_PATTERNS, "text")
            results.extend(self._retype_amounts(results, ["total_amount"]))
        elif doc_type == "GOODS_RECEIPT":
            results = self._extract_with_patterns(text, page_texts, self.GRN_PATTERNS, "text")

        return results

    def _extract_text(self, filepath: str) -> tuple[str, dict[int, str]]:
        """Extract text using PyMuPDF. Returns (full_text, {page_no: page_text})."""
        try:
            import fitz  # PyMuPDF
            page_texts: dict[int, str] = {}
            full = ""
            with fitz.open(filepath) as doc:
                for i, page in enumerate(doc, start=1):
                    pt = page.get_text()
                    page_texts[i] = pt
                    full += pt + "\n"
            return full, page_texts
        except Exception:
            return "", {}

    def _ocr_extract(self, filepath: str) -> str:
        """Fallback OCR using RapidOCR."""
        try:
            from rapidocr_onnxruntime import RapidOCR
            engine = RapidOCR()
            result, _ = engine(filepath)
            if result:
                return "\n".join([line[1] for line in result])
        except Exception:
            pass
        return ""

    def _extract_with_patterns(
        self,
        full_text: str,
        page_texts: dict[int, str],
        patterns: dict[str, list[str]],
        default_type: str,
    ) -> list[ExtractedFieldData]:
        results: list[ExtractedFieldData] = []
        extracted_fields: set[str] = set()

        for field_name, field_patterns in patterns.items():
            if field_name in extracted_fields:
                continue
            for pattern in field_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    val_clean = match.group(1).splitlines()[0].strip().rstrip(".,;")
                    if field_name == "vendor_name" and val_clean.lower().startswith("bill to"):
                        continue
                    value = val_clean
                    # Find source page
                    src_page = 1
                    for pg, pt in page_texts.items():
                        if re.search(pattern, pt, re.IGNORECASE):
                            src_page = pg
                            break

                    ftype = "amount" if field_name in (
                        "total_amount", "subtotal", "tax", "unit_price"
                    ) else ("date" if "date" in field_name else "text")

                    results.append(ExtractedFieldData(
                        field_name=field_name,
                        field_value=value,
                        field_type=ftype,
                        confidence=0.85,
                        source_page=src_page,
                    ))
                    extracted_fields.add(field_name)
                    break

        return results

    def _retype_amounts(
        self, results: list[ExtractedFieldData], amount_fields: list[str]
    ) -> list[ExtractedFieldData]:
        """Fix field_type for known amount fields."""
        for r in results:
            if r.field_name in amount_fields:
                r.field_type = "amount"
                # Clean up value
                r.field_value = r.field_value.replace(",", "").replace("₹", "").replace("$", "").strip()
        return []  # already mutated in place, return empty to avoid duplicates


extractor = DocumentExtractor()
