import re
import json
import base64
import logging
import asyncio
from typing import Optional
from pathlib import Path
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


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
    Multimodal Vision-Language Model (VLM) Document Extractor powered by Mistral Pixtral.
    Renders PDF pages directly as images and uses Mistral's Vision Language Model
    to extract structured procurement compliance data without fragile OCR or regex.
    """

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if settings.MISTRAL_API_KEY:
            try:
                from mistralai.client import Mistral
                self._client = Mistral(api_key=settings.MISTRAL_API_KEY)
                logger.info(
                    "Initialized Mistral VLM client (model: %s)",
                    settings.MISTRAL_VISION_MODEL,
                )
            except Exception as e:
                logger.warning("Could not initialize Mistral client: %s", e)
                self._client = None
        return self._client

    # ── Image Rendering ───────────────────────────────────────────────────────
    def _render_document_images(
        self, filepath: str, max_pages: int = 4, dpi: int = 150
    ) -> list[tuple[int, str]]:
        """
        Renders PDF pages or image files to base64-encoded data URLs.
        Returns a list of (page_number, data_url).
        """
        path = Path(filepath)
        images: list[tuple[int, str]] = []

        if not path.exists():
            logger.error("File does not exist: %s", filepath)
            return images

        suffix = path.suffix.lower()
        if suffix in [".png", ".jpg", ".jpeg", ".webp"]:
            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                mime = "image/png" if suffix == ".png" else "image/jpeg"
                images.append((1, f"data:{mime};base64,{b64}"))
                return images
            except Exception as e:
                logger.error("Error reading image file %s: %s", filepath, e)
                return images

        # PDF documents: render pages directly via PyMuPDF
        try:
            import fitz
            with fitz.open(str(filepath)) as doc:
                total_pages = min(len(doc), max_pages)
                for i in range(total_pages):
                    page = doc[i]
                    pix = page.get_pixmap(dpi=dpi)
                    img_bytes = pix.tobytes("jpeg")
                    b64 = base64.b64encode(img_bytes).decode("utf-8")
                    images.append((i + 1, f"data:image/jpeg;base64,{b64}"))
        except Exception as e:
            logger.warning("Failed to render PDF pages with PyMuPDF for %s: %s", filepath, e)

        return images

    # ── VLM Prompt Construction ──────────────────────────────────────────────
    def _build_vlm_prompt(self, doc_type: str) -> str:
        return (
            f"You are an expert procurement auditor and Vision-Language AI model.\n"
            f"Analyze the provided procurement document page image(s) for a '{doc_type}'.\n\n"
            f"Extract all key structured transactional fields directly from the visual document:\n"
            f"- For INVOICE: invoice_number, invoice_date, vendor_name, buyer_name, po_number, "
            f"subtotal, tax, total_amount, payment_terms, gstin_vendor, gstin_buyer, line_items\n"
            f"- For PURCHASE_ORDER: po_number, po_date, vendor_name, buyer_name, procurement_method "
            f"(e.g. GeM Direct Purchase, Tender), gem_reference, requester, approver, department, "
            f"project_code, total_amount, voucher_number, delivery_date, line_items\n"
            f"- For GOODS_RECEIPT: receipt_number, receipt_date, po_number, invoice_number, "
            f"vendor_name, received_by, accepted_quantity, total_items, inspection_status\n"
            f"- For POLICY: title, effective_date, approved_by, direct_purchase_limit, tender_threshold\n\n"
            f"CRITICAL REQUIREMENTS:\n"
            f"1. Return ONLY a valid JSON object matching this schema:\n"
            f"{{\n"
            f'  "document_type": "{doc_type}",\n'
            f'  "confidence": 0.98,\n'
            f'  "fields": [\n'
            f'    {{\n'
            f'      "field_name": "invoice_number",\n'
            f'      "field_value": "INV-2026-001",\n'
            f'      "field_type": "text",\n'
            f'      "confidence": 0.99,\n'
            f'      "source_page": 1\n'
            f'    }},\n'
            f'    {{\n'
            f'      "field_name": "total_amount",\n'
            f'      "field_value": "85000.00",\n'
            f'      "field_type": "amount",\n'
            f'      "confidence": 0.95,\n'
            f'      "source_page": 1\n'
            f'    }}\n'
            f'  ]\n'
            f"}}\n"
            f"2. 'field_type' must be: 'text', 'amount', 'date', or 'line_items'.\n"
            f"3. In amount fields (total_amount, subtotal, tax), remove currency symbols and commas (e.g. '85000.00').\n"
            f"4. 'source_page' is the 1-indexed page where the information appears.\n"
            f"5. Do NOT include markdown code fencing around the json or extra explanatory text."
        )

    # ── VLM Extraction ───────────────────────────────────────────────────────
    async def extract_vlm(self, filepath: str, doc_type: str) -> Optional[list[ExtractedFieldData]]:
        """Extract fields using Mistral Vision-Language Model (Pixtral)."""
        client = self._get_client()
        if not client or not settings.MISTRAL_API_KEY:
            logger.info("Mistral API key not configured; skipping VLM extraction.")
            return None

        images = self._render_document_images(filepath)
        if not images:
            logger.warning("No images could be rendered from %s for VLM.", filepath)
            return None

        prompt = self._build_vlm_prompt(doc_type)

        # Build multimodal message content with all rendered page images
        content_items = [{"type": "text", "text": prompt}]
        for _, img_url in images:
            content_items.append({"type": "image_url", "image_url": img_url})

        messages = [{"role": "user", "content": content_items}]

        try:
            logger.info(
                "Running Mistral VLM (%s) on %s (%d pages)...",
                settings.MISTRAL_VISION_MODEL,
                filepath,
                len(images),
            )
            response = await client.chat.complete_async(
                model=settings.MISTRAL_VISION_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            raw_text = response.choices[0].message.content
            if not raw_text:
                logger.warning("Empty response received from Mistral VLM.")
                return None

            # Clean response text if wrapped in code block
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)

            data = json.loads(cleaned)
            raw_fields = data.get("fields", [])

            # Handle model returning dict instead of list of fields
            if isinstance(raw_fields, dict):
                normalized = []
                for k, v in raw_fields.items():
                    if isinstance(v, dict) and "field_value" in v:
                        normalized.append({"field_name": k, **v})
                    else:
                        normalized.append({"field_name": k, "field_value": v})
                raw_fields = normalized
            elif not isinstance(raw_fields, list):
                # If top-level object had fields directly
                normalized = []
                for k, v in data.items():
                    if k not in ("document_type", "confidence", "fields"):
                        normalized.append({"field_name": k, "field_value": v})
                if normalized:
                    raw_fields = normalized

            results: list[ExtractedFieldData] = []
            for item in raw_fields:
                if not isinstance(item, dict):
                    continue
                fname = str(item.get("field_name") or "").strip()
                raw_val = item.get("field_value", "")
                if isinstance(raw_val, (dict, list)):
                    fval = json.dumps(raw_val)
                elif raw_val is not None:
                    fval = str(raw_val).strip()
                else:
                    fval = ""

                if not fname or not fval:
                    continue

                ftype = str(item.get("field_type") or "text").strip().lower()
                if fname in ("total_amount", "subtotal", "tax", "unit_price"):
                    if not isinstance(raw_val, (dict, list)):
                        ftype = "amount"
                        fval = fval.replace(",", "").replace("₹", "").replace("$", "").strip()

                try:
                    conf = float(item.get("confidence", 0.95))
                except (ValueError, TypeError):
                    conf = 0.95

                try:
                    spage = int(item.get("source_page", 1))
                except (ValueError, TypeError):
                    spage = 1

                results.append(
                    ExtractedFieldData(
                        field_name=fname,
                        field_value=fval,
                        field_type=ftype,
                        confidence=conf,
                        source_page=spage,
                    )
                )

            logger.info("Mistral VLM successfully extracted %d fields from %s", len(results), filepath)
            return results

        except Exception as e:
            logger.error("Mistral VLM extraction failed for %s: %s", filepath, e)
            return None

    # ── Fallback Extraction (when no VLM API key is configured) ───────────────
    def _fallback_extract(self, filepath: str, doc_type: str) -> list[ExtractedFieldData]:
        """
        Graceful offline fallback using PyMuPDF text parsing and regex.
        Ensures document uploads never break when no API key or network is available.
        """
        logger.info("Using text fallback extraction for %s (%s)", filepath, doc_type)
        full_text = ""
        page_texts: dict[int, str] = {}
        try:
            import fitz
            with fitz.open(filepath) as doc:
                for i, page in enumerate(doc, start=1):
                    pt = page.get_text()
                    page_texts[i] = pt
                    full_text += pt + "\n"
        except Exception:
            pass

        patterns = self._get_patterns(doc_type)
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

                    src_page = 1
                    for pg, pt in page_texts.items():
                        if re.search(pattern, pt, re.IGNORECASE):
                            src_page = pg
                            break

                    ftype = (
                        "amount"
                        if field_name in ("total_amount", "subtotal", "tax", "unit_price")
                        else ("date" if "date" in field_name else "text")
                    )

                    if ftype == "amount":
                        val_clean = val_clean.replace(",", "").replace("₹", "").replace("$", "").strip()

                    results.append(
                        ExtractedFieldData(
                            field_name=field_name,
                            field_value=val_clean,
                            field_type=ftype,
                            confidence=0.85,
                            source_page=src_page,
                        )
                    )
                    extracted_fields.add(field_name)
                    break

        return results

    # ── Entry Points ─────────────────────────────────────────────────────────
    async def extract_async(self, filepath: str, doc_type: str) -> list[ExtractedFieldData]:
        """
        Primary extraction entrypoint (async).
        First runs Mistral Vision-Language Model (Pixtral).
        Falls back to native text extraction if VLM is unavailable.
        """
        # 1. Run Mistral VLM
        vlm_results = await self.extract_vlm(filepath, doc_type)
        if vlm_results:
            return vlm_results

        # 2. Fallback to native text extraction
        return self._fallback_extract(filepath, doc_type)

    def extract(self, filepath: str, doc_type: str) -> list[ExtractedFieldData]:
        """Synchronous wrapper for extract_async."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If inside existing event loop, run in separate thread or fallback
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, self.extract_async(filepath, doc_type)).result()
        else:
            return asyncio.run(self.extract_async(filepath, doc_type))

    # ── Regex Pattern Reference for Fallback ─────────────────────────────────
    def _get_patterns(self, doc_type: str) -> dict[str, list[str]]:
        if doc_type == "INVOICE":
            return {
                "invoice_number": [
                    r"invoice\s*(?:no|number|#)[:\s#]*([A-Z0-9\-/]+)",
                    r"inv[.\s-]*(?:no|#)[:\s]*([A-Z0-9\-/]+)",
                    r"bill\s*no[:\s]*([A-Z0-9\-/]+)",
                ],
                "invoice_date": [
                    r"invoice\s*date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                    r"date\s*of\s*invoice[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                    r"bill\s*date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                ],
                "vendor_name": [
                    r"(?:from|seller|vendor|bill\s*from|supplier)[:\s]*([A-Za-z0-9&.,\s]+(?:Ltd|Pvt|Inc|LLC|Corp|LLP)?)",
                ],
                "po_number": [
                    r"(?:p\.?o\.?\s*(?:no|number|#)|purchase\s*order\s*(?:no|#))[:\s#]*([A-Z0-9\-/]+)",
                ],
                "subtotal": [
                    r"sub[\s-]*total[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
                    r"taxable\s*amount[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
                ],
                "tax": [
                    r"(?:gst|tax|vat|igst|cgst|sgst)[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
                ],
                "total_amount": [
                    r"(?:grand\s*total|total\s*amount|amount\s*payable|total\s*due|net\s*amount)[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
                    r"total[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
                ],
            }
        elif doc_type == "PURCHASE_ORDER":
            return {
                "po_number": [
                    r"Purchase\s+Order[\s\n]+No\.?[\s\n]+([A-Z0-9/\-]+)",
                    r"(?:purchase\s*order\s*(?:no|number|#)|po\s*(?:no|number|#)|p\.?o\.?\s*(?:no|#))[:\s#\n]*([A-Z0-9\-/]+)",
                ],
                "po_date": [
                    r"(?:order\s*date|po\s*date)[:\s\n]*(\d{1,2}[\s\w]*\d{4})",
                    r"(?:order\s*date|po\s*date|date)[:\s\n]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                ],
                "vendor_name": [
                    r"(?:^|\n)Seller[\s\n]+([A-Za-z0-9&.,\s]+(?:Pvt\.?\s*Ltd\.?|Ltd\.?|Inc\.?|Corp\.?|LLC|LLP|Enterprises|Solutions|Systems|Services))",
                    r"(?:supplier|vendor|seller)[:\s\n]+([A-Za-z0-9&.,\s]+(?:Ltd|Pvt|Inc|LLC|Corp|LLP))",
                ],
                "procurement_method": [
                    r"Procurement[\s\n]+Method[\s\n]+([A-Za-z\s]+(?:Purchase|Tender|Enquiry|Purchase))",
                    r"(?:procurement\s*method|purchase\s*method|purchase\s*mode)[:\s\n]*([A-Za-z\s]+)",
                ],
                "gem_reference": [
                    r"GeM\s+Order\s+ID[\s\n]+([A-Z0-9\-]+)",
                    r"(?:gem\s*(?:bid\s*/\s*order\s*reference|bid\s*reference|order\s*reference|order\s*id))[:\s\n]*([A-Za-z0-9\-/]+)",
                ],
                "total_amount": [
                    r"Total\s+Procurement\s+Value[\s\n]+(?:INR[\s]*)?([0-9,]+(?:\.\d{2})?)",
                    r"(?:grand\s*total|total\s*(?:order\s*)?(?:value|amount)|net\s*amount)[:\s₹$INR]*([0-9,]+(?:\.\d{2})?)",
                    r"total[:\s₹$]*([0-9,]+(?:\.\d{2})?)",
                ],
                "voucher_number": [
                    r"(?:voucher\s*no\.?|vch\s*no\.?)[\s:\n]*([A-Z0-9/\-]+)",
                ],
            }
        elif doc_type == "GOODS_RECEIPT":
            return {
                "receipt_number": [
                    r"(?:grn\s*(?:no|number|#)|receipt\s*(?:no|number|#)|delivery\s*note\s*(?:no|#))[:\s#]*([A-Z0-9\-/]+)",
                ],
                "po_number": [
                    r"(?:p\.?o\.?\s*(?:no|number|#)|purchase\s*order\s*(?:no|#))[:\s#]*([A-Z0-9\-/]+)",
                ],
                "receipt_date": [
                    r"(?:receipt\s*date|received\s*on|delivery\s*date|date)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                ],
                "received_by": [
                    r"(?:received\s*by|accepted\s*by)[:\s]*([A-Za-z\s]+)",
                ],
            }
        return {}


extractor = DocumentExtractor()
