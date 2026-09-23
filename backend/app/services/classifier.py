import re
import json
from pathlib import Path
from typing import Optional


class DocumentClassifier:
    """Document classifier with header prioritization and keyword scoring."""

    HEADER_TITLES: dict[str, list[str]] = {
        "PURCHASE_ORDER": ["purchase order", "procurement order", "purchase requisition", "po number"],
        "INVOICE": ["tax invoice", "commercial invoice", "gst invoice", "proforma invoice", "invoice"],
        "GOODS_RECEIPT": ["goods receipt", "goods received note", "material receipt note", "delivery note", "grn"],
        "POLICY": ["procurement policy", "procurement manual", "policy document", "procurement guidelines"],
    }

    KEYWORDS: dict[str, list[str]] = {
        "INVOICE": [
            "tax invoice", "invoice no", "invoice number", "inv-", "amount due",
            "payment due", "remit to", "gst invoice", "billed to", "invoice date",
        ],
        "PURCHASE_ORDER": [
            "purchase order", "po number", "po no", "order number",
            "purchase requisition", "procurement order", "order to", "ship to",
            "delivery address", "ordered by", "authorised by", "po date",
        ],
        "GOODS_RECEIPT": [
            "goods receipt", "grn", "goods received note", "delivery note",
            "receipt note", "goods received", "delivery receipt",
            "received by", "items received", "material receipt",
        ],
        "POLICY": [
            "compliance policy", "section", "clause", "article",
            "procurement policy", "effective date", "approved by",
        ],
    }

    def classify(self, text: str, filename: Optional[str] = None) -> tuple[str, float]:
        """Return (document_type, confidence) based on header match and keywords."""
        text_lower = text.lower()
        header = text_lower[:1200]
        scores: dict[str, int] = {k: 0 for k in self.KEYWORDS}

        # 1. Check prominent headers (high weight)
        for doc_type, titles in self.HEADER_TITLES.items():
            for title in titles:
                if title in header:
                    scores[doc_type] += 10
                    break

        # 2. Check filename hints (moderate weight)
        if filename:
            fn_lower = filename.lower()
            if "po" in fn_lower or "purchase_order" in fn_lower:
                scores["PURCHASE_ORDER"] += 5
            elif "inv" in fn_lower or "invoice" in fn_lower:
                scores["INVOICE"] += 5
            elif "grn" in fn_lower or "receipt" in fn_lower:
                scores["GOODS_RECEIPT"] += 5
            elif "policy" in fn_lower:
                scores["POLICY"] += 5

        # 3. Keyword matching
        for doc_type, keywords in self.KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    scores[doc_type] += 1

        total = sum(scores.values())
        if total == 0:
            return "INVOICE", 0.3  # default

        best_type = max(scores, key=lambda k: scores[k])
        confidence = min(round(scores[best_type] / (total + 5) + 0.5, 2), 0.99)
        return best_type, confidence


classifier = DocumentClassifier()
