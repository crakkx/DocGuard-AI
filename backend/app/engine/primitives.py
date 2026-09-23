from dataclasses import dataclass, field
from typing import Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz

@dataclass
class CaseData:
    case: dict
    po: dict
    invoice: dict
    grn: dict
    all_cases: list[dict]
    
    def get_field(self, field_spec: Any) -> Optional[str]:
        field_name = ""
        if isinstance(field_spec, dict):
            doc_type = field_spec.get("document", "")
            field_name = field_spec.get("field", "")
            if doc_type == "invoice" and self.invoice:
                val = self.invoice.get(field_name)
                if val is not None:
                    return str(val)
            elif doc_type in ("purchase_order", "po") and self.po:
                val = self.po.get(field_name)
                if val is not None:
                    return str(val)
            elif doc_type in ("goods_receipt", "grn") and self.grn:
                val = self.grn.get(field_name)
                if val is not None:
                    return str(val)
            elif doc_type == "case" and self.case:
                val = self.case.get(field_name)
                if val is not None:
                    return str(val)
            if not field_name:
                return None
        elif isinstance(field_spec, str):
            field_name = field_spec
        else:
            return None

        # Cross-resolve aliases across case, po, invoice, grn
        aliases = {
            "procurement_value": ["total_amount", "amount", "total", "subtotal", "procurement_value"],
            "total_amount": ["total_amount", "amount", "total", "subtotal", "procurement_value"],
            "amount": ["total_amount", "amount", "total", "subtotal"],
            "procurement_method": ["procurement_method", "purchase_method", "method"],
            "gem_reference": ["gem_reference", "gem_order_reference", "gem_ref"],
            "vendor_name": ["vendor_name", "vendor", "supplier"],
            "item_category": ["item_category", "items", "description", "line_items"],
            "invoice_number": ["invoice_number", "bill_number"],
            "po_number": ["po_number", "order_number"],
        }

        candidates = aliases.get(field_name, [field_name])
        for cand in candidates:
            if self.case and self.case.get(cand) is not None:
                return str(self.case.get(cand))
            if self.po and self.po.get(cand) is not None:
                return str(self.po.get(cand))
            if self.invoice and self.invoice.get(cand) is not None:
                return str(self.invoice.get(cand))
            if self.grn and self.grn.get(cand) is not None:
                return str(self.grn.get(cand))

        return None

@dataclass
class PrimitiveResult:
    passed: bool
    expected: str
    actual: str
    difference: Optional[str]
    explanation: str

class PrimitiveEvaluator:
    def evaluate(self, primitive: str, params: dict, case_data: CaseData) -> PrimitiveResult:
        handlers = {
            "COMPARE_FIELDS": self._compare_fields,
            "THRESHOLD_CHECK": self._threshold_check,
            "PRESENCE_CHECK": self._presence_check,
            "MATCH_CHECK": self._match_check,
            "AGGREGATION_CHECK": self._aggregation_check,
            "TIME_WINDOW_CHECK": self._time_window_check,
            "COUNT_CHECK": self._count_check,
        }
        handler = handlers.get(primitive)
        if not handler:
            raise ValueError(f"Unknown primitive: {primitive}")
        return handler(params, case_data)
    
    def _compare_fields(self, params: dict, case_data: CaseData) -> PrimitiveResult:
        field_a_spec = params.get("field_a", {})
        field_b_spec = params.get("field_b", {})
        operator = params.get("operator", "==")
        tolerance = params.get("tolerance_percent", 0.0)

        val_a = case_data.get_field(field_a_spec)
        val_b = case_data.get_field(field_b_spec)

        if val_a is None or val_b is None:
            return PrimitiveResult(False, "Values present", "Missing values", None, "Missing fields for comparison.")

        if operator == "DEVIATION_PERCENT":
            dec_a = self._to_decimal(val_a)
            dec_b = self._to_decimal(val_b)
            if dec_a is None or dec_b is None:
                return PrimitiveResult(False, "Valid numeric values", f"{val_a} vs {val_b}", None, "Invalid numeric format for deviation check.")

            threshold = Decimal(str(params.get("threshold", 0)))
            direction = params.get("direction", "ANY")

            diff = dec_a - dec_b
            percent_diff = (abs(diff) / dec_b) * 100 if dec_b != 0 else Decimal(100)
            actual_direction = "INCREASE" if diff > 0 else ("DECREASE" if diff < 0 else "NONE")

            # A deviation in a direction we're not watching for always passes,
            # regardless of how large the raw percentage difference is.
            if direction == "INCREASE" and actual_direction != "INCREASE":
                passed = True
            elif direction == "DECREASE" and actual_direction != "DECREASE":
                passed = True
            else:
                passed = percent_diff <= threshold

            return PrimitiveResult(
                passed,
                f"Deviation <= {threshold}% ({direction})",
                f"{percent_diff:.2f}% {actual_direction}",
                str(diff),
                f"Deviation within {threshold}% tolerance" if passed else f"Deviation exceeded {threshold}% tolerance"
            )

        if operator in [">", "<", ">=", "<=", "==", "!="] and "percent" not in operator.lower():
            dec_a = self._to_decimal(val_a)
            dec_b = self._to_decimal(val_b)
            if dec_a is not None and dec_b is not None:
                if tolerance > 0:
                    diff = abs(dec_a - dec_b)
                    percent_diff = (diff / dec_b) * 100 if dec_b != 0 else Decimal(100)
                    passed = percent_diff <= Decimal(str(tolerance))
                    return PrimitiveResult(
                        passed,
                        f"Difference <= {tolerance}%",
                        f"{percent_diff:.2f}%",
                        str(diff),
                        f"Fields matched within {tolerance}% tolerance" if passed else f"Fields mismatch exceeded {tolerance}% tolerance"
                    )
                passed = self._apply_operator(dec_a, dec_b, operator)
                return PrimitiveResult(
                    passed,
                    f"{field_a_spec.get('field')} {operator} {field_b_spec.get('field')}",
                    f"{dec_a} vs {dec_b}",
                    str(dec_a - dec_b),
                    f"Condition met." if passed else "Condition not met."
                )
            else:
                passed = self._apply_operator_str(val_a, val_b, operator)
                return PrimitiveResult(
                    passed,
                    f"{val_a} {operator} {val_b}",
                    f"{val_a} vs {val_b}",
                    None,
                    "String match condition"
                )

        return PrimitiveResult(False, "", "", None, "Unknown comparison format.")
    
    def _threshold_check(self, params: dict, case_data: CaseData) -> PrimitiveResult:
        field_spec = params.get("field", "procurement_value")
        raw_threshold = params.get("threshold", 0)
        raw_op = params.get("operator", ">")
        op = self.OP_MAP.get(str(raw_op).strip(), str(raw_op).strip())

        val = case_data.get_field(field_spec)
        if val is None:
            val = case_data.get_field("total_amount") or case_data.get_field("procurement_value")
        if val is None:
            return PrimitiveResult(False, f"{op} {raw_threshold}", "Missing", None, "Procurement value missing for threshold check.")

        dec_val = self._to_decimal(val)
        if dec_val is None:
            return PrimitiveResult(False, f"{op} {raw_threshold}", str(val), None, "Invalid numeric format.")

        rule_method = str(params.get("procurement_method") or params.get("method", "")).lower()
        platform = str(params.get("platform", "")).lower()
        case_method = (case_data.get_field("procurement_method") or "").lower()
        gem_ref = case_data.get_field("gem_reference")

        # 1. Direct Purchase threshold (e.g. ≤ ₹25,000)
        if "direct_purchase" in rule_method or "direct" in rule_method:
            if "direct" in case_method:
                thresh_dec = self._to_decimal(raw_threshold) or Decimal(25000)
                passed = dec_val <= thresh_dec
                return PrimitiveResult(
                    passed,
                    f"Direct Purchase ≤ ₹{thresh_dec:,.2f}",
                    f"₹{dec_val:,.2f} ({case_method.title()})",
                    str(dec_val - thresh_dec),
                    "Direct purchase within allowable threshold." if passed else f"Direct purchase threshold exceeded: ₹{dec_val:,.2f} exceeds limit of ₹{thresh_dec:,.2f}."
                )
            else:
                return PrimitiveResult(
                    True,
                    f"Direct Purchase ≤ ₹{raw_threshold}",
                    f"Method: {case_method or 'N/A'}",
                    None,
                    f"Not applicable: procurement method is '{case_method or 'Not Direct Purchase'}'."
                )

        # 2. GeM Online Bidding Mandate (> ₹5,00,000)
        if platform == "gem" and "online_bidding" in rule_method:
            thresh_dec = self._to_decimal(raw_threshold) or Decimal(500000)
            if dec_val > thresh_dec:
                gem_available = bool(gem_ref and str(gem_ref).strip().lower() not in ("not available", "n/a", "none", "na", "no", ""))
                passed = gem_available
                return PrimitiveResult(
                    passed,
                    f"GeM Online Bidding (for > ₹{thresh_dec:,.2f})",
                    f"GeM Ref: {gem_ref or 'Not available'} (Value: ₹{dec_val:,.2f})",
                    None,
                    "GeM online bidding reference verified." if passed else f"GeM online bidding mandated for procurements exceeding ₹{thresh_dec:,.2f}, but GeM reference is '{gem_ref or 'Not available'}'."
                )
            else:
                return PrimitiveResult(
                    True,
                    f"GeM Bidding > ₹{thresh_dec:,.2f}",
                    f"₹{dec_val:,.2f}",
                    None,
                    f"Not applicable: procurement value ₹{dec_val:,.2f} does not exceed ₹{thresh_dec:,.2f} threshold."
                )

        # 3. Limited Tender Enquiry Mandate (₹2,50,001–₹25,00,000)
        if "limited_tender" in rule_method:
            min_t, max_t = (Decimal(250001), Decimal(2500000))
            if isinstance(raw_threshold, (list, tuple)) and len(raw_threshold) == 2:
                min_t = self._to_decimal(raw_threshold[0]) or min_t
                max_t = self._to_decimal(raw_threshold[1]) or max_t
            if min_t <= dec_val <= max_t:
                is_limited = "limited" in case_method
                return PrimitiveResult(
                    is_limited,
                    f"Limited Tender Enquiry (₹{min_t:,.2f}–₹{max_t:,.2f})",
                    f"Procurement Method: {case_method or 'Direct Purchase'} (₹{dec_val:,.2f})",
                    None,
                    "Limited Tender Enquiry used as required." if is_limited else f"Procurement value ₹{dec_val:,.2f} requires Limited Tender Enquiry (₹{min_t:,.2f}–₹{max_t:,.2f}), but method used was '{case_method or 'Direct Purchase'}'."
                )
            else:
                return PrimitiveResult(
                    True,
                    f"Range ₹{min_t:,.2f}–₹{max_t:,.2f}",
                    f"₹{dec_val:,.2f}",
                    None,
                    f"Not applicable: procurement value ₹{dec_val:,.2f} outside Limited Tender range."
                )

        # 4. Local Purchase Committee (₹25,001–₹2,50,000)
        if "local_purchase_committee" in rule_method:
            min_t, max_t = (Decimal(25001), Decimal(250000))
            if isinstance(raw_threshold, (list, tuple)) and len(raw_threshold) == 2:
                min_t = self._to_decimal(raw_threshold[0]) or min_t
                max_t = self._to_decimal(raw_threshold[1]) or max_t
            if min_t <= dec_val <= max_t:
                is_lpc = "committee" in case_method or "lpc" in case_method
                return PrimitiveResult(
                    is_lpc,
                    f"Local Purchase Committee (₹{min_t:,.2f}–₹{max_t:,.2f})",
                    f"Method: {case_method or 'Direct Purchase'}",
                    None,
                    "Local Purchase Committee process followed." if is_lpc else f"Procurement value ₹{dec_val:,.2f} requires Local Purchase Committee, but method was '{case_method or 'Direct Purchase'}'."
                )
            else:
                return PrimitiveResult(
                    True,
                    f"Range ₹{min_t:,.2f}–₹{max_t:,.2f}",
                    f"₹{dec_val:,.2f}",
                    None,
                    f"Not applicable: procurement value ₹{dec_val:,.2f} outside Local Purchase Committee range."
                )

        # 5. Open Tender Enquiry Mandate (> ₹25,00,000)
        if "open_tender" in rule_method:
            thresh_dec = self._to_decimal(raw_threshold) or Decimal(2500000)
            if dec_val > thresh_dec:
                is_open = "open" in case_method
                return PrimitiveResult(
                    is_open,
                    f"Open Tender Enquiry (> ₹{thresh_dec:,.2f})",
                    f"Method: {case_method or 'Direct Purchase'}",
                    None,
                    "Open Tender Enquiry followed." if is_open else f"Procurement value ₹{dec_val:,.2f} exceeds ₹{thresh_dec:,.2f} requiring Open Tender Enquiry, but method was '{case_method or 'Direct Purchase'}'."
                )
            else:
                return PrimitiveResult(
                    True,
                    f"Open Tender > ₹{thresh_dec:,.2f}",
                    f"₹{dec_val:,.2f}",
                    None,
                    f"Not applicable: procurement value ₹{dec_val:,.2f} does not exceed Open Tender threshold (₹{thresh_dec:,.2f})."
                )

        # 6. Other GeM tier rules
        if platform == "gem":
            if op in ("<=", "<"):
                thresh_dec = self._to_decimal(raw_threshold) or Decimal(25000)
                if dec_val > thresh_dec:
                    return PrimitiveResult(True, f"≤ ₹{thresh_dec}", f"₹{dec_val}", None, f"Not applicable: applies to procurements ≤ ₹{thresh_dec}.")
            elif op == "BETWEEN":
                if isinstance(raw_threshold, (list, tuple)) and len(raw_threshold) == 2:
                    min_t = self._to_decimal(raw_threshold[0]) or Decimal(0)
                    max_t = self._to_decimal(raw_threshold[1]) or Decimal(0)
                    if not (min_t <= dec_val <= max_t):
                        return PrimitiveResult(True, f"₹{min_t}–₹{max_t}", f"₹{dec_val}", None, f"Not applicable: value outside ₹{min_t:,.2f}–₹{max_t:,.2f} range.")

        # 7. Generic / standard threshold checks (and BETWEEN operator)
        if op == "BETWEEN" and isinstance(raw_threshold, (list, tuple)) and len(raw_threshold) == 2:
            min_t = self._to_decimal(raw_threshold[0]) or Decimal(0)
            max_t = self._to_decimal(raw_threshold[1]) or Decimal(0)
            passed = min_t <= dec_val <= max_t
            return PrimitiveResult(
                passed,
                f"{min_t} <= val <= {max_t}",
                str(dec_val),
                None,
                "Value within threshold range." if passed else "Value outside threshold range."
            )

        thresh_dec = self._to_decimal(raw_threshold) or Decimal(0)
        passed = self._apply_operator(dec_val, thresh_dec, op)
        return PrimitiveResult(
            passed,
            f"{op} {thresh_dec}",
            str(dec_val),
            str(dec_val - thresh_dec),
            "Threshold passed" if passed else "Threshold failed"
        )
    
    def _presence_check(self, params: dict, case_data: CaseData) -> PrimitiveResult:
        target_type = params.get("target_type")
        doc_type = params.get("document_type") or params.get("document")

        tot_val = case_data.get_field("total_amount") or case_data.get_field("procurement_value")
        amt = self._to_decimal(tot_val) or Decimal(0)
        case_method = (case_data.get_field("procurement_method") or "").lower()

        # Method context guard: skip presence checks meant for a different procurement method
        rule_method_req = str(params.get("method", "")).lower().replace("_", " ")
        if rule_method_req:
            if "limited tender" in rule_method_req and "limited" not in case_method and "lte" not in case_method:
                if not (250001 <= float(amt or 0) <= 2500000):
                    return PrimitiveResult(True, "N/A", "N/A", None,
                        f"Not applicable: rule is for limited tender enquiry but case method is '{case_method}'.")
            if ("open tender" in rule_method_req or "e tendering" in rule_method_req or "e-tendering" in rule_method_req):
                if amt <= 2500000 and "open" not in case_method:
                    return PrimitiveResult(True, "N/A", "N/A", None,
                        f"Not applicable: rule is for open tender but case method is '{case_method}'.")
            if "local purchase committee" in rule_method_req:
                if not (25001 <= float(amt or 0) <= 250000) and "committee" not in case_method and "lpc" not in case_method:
                    return PrimitiveResult(True, "N/A", "N/A", None,
                        f"Not applicable: rule is for LPC but case method is '{case_method}'.")

        # Scope guards for tier-specific documents:
        # Open Tender document / e-tendering
        if doc_type in ("tender_document", "open_tender_document"):
            if amt <= 2500000 and "open" not in case_method:
                return PrimitiveResult(
                    True, "N/A", "N/A", None,
                    "Not applicable: procurement value does not exceed Open Tender threshold (₹25,00,000)."
                )

        # LPC comparative statement
        if doc_type in ("comparative_statement_of_quotations", "comparative_statement", "quotations"):
            if not (25000 < amt <= 250000) and "committee" not in case_method and "lpc" not in case_method:
                return PrimitiveResult(
                    True, "N/A", "N/A", None,
                    "Not applicable: procurement is not in Local Purchase Committee tier (₹25,001–₹2,50,000)."
                )

        if doc_type or target_type == "DOCUMENT":
            doc_norm = str(doc_type).lower() if doc_type else ""
            should_exist = params.get("condition", "EXISTS") == "EXISTS"
            
            exists = False
            if doc_norm in ("invoice", "tax_invoice", "bill", "bill_and_voucher", "voucher"):
                # First check if an invoice document is linked
                exists = bool(case_data.case.get("invoice_document_id"))
                # Also accept if the PO document contains voucher evidence (bill & voucher on same PDF)
                if not exists:
                    exists = bool(
                        case_data.po.get("voucher_number") or
                        case_data.po.get("certified_by") or
                        case_data.po.get("certification_status")
                    )
            elif doc_norm in ("purchase_order", "po"):
                exists = bool(case_data.case.get("po_document_id"))
            elif doc_norm in ("goods_receipt", "grn", "delivery_note"):
                exists = bool(case_data.case.get("grn_document_id"))
            elif doc_norm in ("tender_document", "comparative_statement_of_quotations"):
                exists = False

            passed = exists == should_exist
            doc_label = doc_norm.replace("_", " ").title()
            explanation = f"{doc_label} verified present." if passed and exists else (
                f"{doc_label} missing from case records." if not passed else f"{doc_label} condition satisfied."
            )
            return PrimitiveResult(passed, f"Exists={should_exist}", f"Exists={exists}", None, explanation)
        else:
            field_spec = params.get("field", {})
            val = case_data.get_field(field_spec)
            should_exist = params.get("condition", "EXISTS") == "EXISTS"
            exists = val is not None
            passed = exists == should_exist
            return PrimitiveResult(passed, f"Exists={should_exist}", f"Exists={exists}", None, "Field presence check.")
    
    def _match_check(self, params: dict, case_data: CaseData) -> PrimitiveResult:
        field_spec = params.get("field", {})
        val = case_data.get_field(field_spec)
        match_type = params.get("match_type", "EQUALS")
        target_value = params.get("target_value", "")
        across = params.get("across", "case") # case or cases

        # Single-use plastics check
        exclusion = params.get("exclusion")
        if exclusion == "single_use_plastics":
            item_desc = str(val or "").lower()
            banned = ["plastic bag", "single use plastic", "disposable plastic", "thermocol", "polythene", "single-use plastic"]
            has_banned = any(b in item_desc for b in banned)
            passed = not has_banned
            return PrimitiveResult(
                passed,
                "No single-use plastics",
                f"Items: {val or 'Compliant'}",
                None,
                "Compliant with single-use plastics prohibition policy." if passed else "Violation: Single-use plastics detected in item description."
            )

        if val is None:
            return PrimitiveResult(False, target_value, "None", None, "Value missing for match check.")

        if across == "cases":
            # Check for duplicates essentially. Two cases only count as a real
            # duplicate when they also share the same vendor (otherwise two
            # unrelated vendors reusing the same invoice numbering would
            # false-positive).
            my_vendor = case_data.case.get("vendor_name")
            matches = 0
            for c in case_data.all_cases:
                if c.get("id") == case_data.case.get("id"): continue
                other_val = self._get_case_dict_field(c, field_spec)
                if other_val != val:
                    continue
                if my_vendor and c.get("vendor_name") != my_vendor:
                    continue
                matches += 1

            passed = matches == 0 # assuming we don't want matches across cases for duplicate checks
            same_vendor_note = " from the same vendor" if my_vendor else ""
            return PrimitiveResult(passed, "Unique", f"Found {matches} matches{same_vendor_note}", None, f"Duplicate check{same_vendor_note}.")
        
        # Simple match
        if match_type == "EQUALS":
            passed = str(val).lower() == str(target_value).lower()
            return PrimitiveResult(passed, target_value, str(val), None, "Exact match.")
        elif match_type == "FUZZY_MATCH":
            ratio = fuzz.ratio(str(val).lower(), str(target_value).lower())
            passed = ratio > 85
            return PrimitiveResult(passed, f"Fuzzy > 85 ({target_value})", f"Ratio {ratio} ({val})", None, "Fuzzy match.")
        
        return PrimitiveResult(False, "", "", None, "Unknown match type")

    def _aggregation_check(self, params: dict, case_data: CaseData) -> PrimitiveResult:
        group_by = params.get("group_by") # vendor_name, project_code
        # The plan's own JSON examples sometimes call this "field" instead of
        # "aggregate_field" - accept either.
        aggregate_field = params.get("aggregate_field") or params.get("field")
        operator = params.get("operator", "<")
        threshold = Decimal(str(params.get("threshold", 0)))
        function = str(params.get("function", "SUM")).upper()
        window_days = params.get("window_days")

        my_group = case_data.case.get(group_by) if group_by else None
        if not my_group:
            return PrimitiveResult(True, "", "", None, "No group info, passing")

        matched = self._collect_group_cases(case_data, group_by, my_group, window_days)

        if function == "COUNT":
            result_value = Decimal(len(matched))
        else:
            amounts = self._collect_amounts(matched, aggregate_field)
            if function == "AVG":
                result_value = (sum(amounts, Decimal("0")) / len(amounts)) if amounts else Decimal("0")
            else:  # SUM (default)
                result_value = sum(amounts, Decimal("0"))

        passed = self._apply_operator(result_value, threshold, operator)
        window_note = f" within {window_days} days" if window_days else ""
        return PrimitiveResult(
            passed,
            f"{operator} {threshold}",
            str(result_value),
            str(result_value - threshold),
            f"{function} aggregation over {group_by}{window_note}."
        )

    def _time_window_check(self, params: dict, case_data: CaseData) -> PrimitiveResult:
        window_days = params.get("window_days", 30)
        group_by = params.get("group_by", "vendor_name")
        operator = params.get("operator", "<")
        threshold_raw = params.get("threshold", 1)
        aggregate_field = params.get("aggregate_field") or params.get("field")
        function = str(params.get("function", "COUNT")).upper()

        my_group = case_data.case.get(group_by)
        if not my_group:
            return PrimitiveResult(True, "", "", None, "No group info")

        matched = self._collect_group_cases(case_data, group_by, my_group, window_days)

        if aggregate_field and function != "COUNT":
            amounts = self._collect_amounts(matched, aggregate_field)
            if function == "AVG":
                result_value = (sum(amounts, Decimal("0")) / len(amounts)) if amounts else Decimal("0")
            else:  # SUM
                result_value = sum(amounts, Decimal("0"))
            threshold = Decimal(str(threshold_raw))
            passed = self._apply_operator(result_value, threshold, operator)
            return PrimitiveResult(
                passed,
                f"{operator} {threshold}",
                str(result_value),
                str(result_value - threshold),
                f"Time window {function} check for {window_days} days."
            )

        count = len(matched)
        threshold = Decimal(str(threshold_raw))
        passed = self._apply_operator(Decimal(count), threshold, operator)
        return PrimitiveResult(passed, f"{operator} {threshold}", str(count), None, f"Time window check for {window_days} days.")

    def _count_check(self, params: dict, case_data: CaseData) -> PrimitiveResult:
        group_by = params.get("group_by")
        operator = params.get("operator", ">=")
        threshold = Decimal(str(params.get("threshold", 0)))
        window_days = params.get("window_days")

        my_group = case_data.case.get(group_by) if group_by else None
        if not my_group:
            return PrimitiveResult(True, "", "", None, "No group info, passing")

        matched = self._collect_group_cases(case_data, group_by, my_group, window_days)
        count = len(matched)

        passed = self._apply_operator(Decimal(count), threshold, operator)
        window_note = f" within {window_days} days" if window_days else ""
        return PrimitiveResult(
            passed,
            f"count {operator} {threshold}",
            str(count),
            str(Decimal(count) - threshold),
            f"Count check over {group_by}{window_note}."
        )

    def _get_case_dict_field(self, c: dict, field_spec: dict) -> Optional[str]:
        """Resolve a field_spec against an entry from CaseData.all_cases (a
        flat case dict, not the invoice/po/grn document dicts). Mirrors the
        document -> field mapping convention used by CaseData.get_field."""
        doc_type = field_spec.get("document", "")
        field_name = field_spec.get("field", "")
        if doc_type == "invoice":
            return c.get("invoice_number")
        elif doc_type == "purchase_order":
            return c.get("po_number")
        elif doc_type == "case":
            return c.get(field_name)
        return None

    def _parse_datetime(self, value: Any) -> datetime:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return datetime.utcnow()
        elif not value:
            return datetime.utcnow()
        return value

    def _collect_group_cases(self, case_data: CaseData, group_by: str, group_value: Any, window_days: Optional[int] = None) -> list[dict]:
        """Return the entries of case_data.all_cases sharing group_value for
        group_by, optionally restricted to those whose created_at falls
        within window_days of the current case's created_at. Shared by
        _count_check, _aggregation_check, and _time_window_check so the
        date-window filtering logic lives in exactly one place."""
        case_date = None
        if window_days is not None:
            case_date = self._parse_datetime(case_data.case.get("created_at"))

        matched = []
        for c in case_data.all_cases:
            if c.get(group_by) != group_value:
                continue
            if window_days is not None:
                dt = self._parse_datetime(c.get("created_at"))
                try:
                    diff = abs((case_date - dt).days)
                    if diff > window_days:
                        continue
                except Exception:
                    continue
            matched.append(c)
        return matched

    def _collect_amounts(self, cases: list[dict], field_name: Optional[str]) -> list[Decimal]:
        amounts = []
        if not field_name:
            return amounts
        for c in cases:
            amt = c.get(field_name)
            if amt:
                dec = self._to_decimal(amt)
                if dec is not None:
                    amounts.append(dec)
        return amounts


    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        if value is None: return None
        try:
            return Decimal(str(value).replace(',', '').replace('₹', '').replace('$', '').strip())
        except Exception:
            return None
            
    OP_MAP = {
        ">": ">",
        "GREATER_THAN": ">",
        "GT": ">",
        ">=": ">=",
        "GREATER_THAN_OR_EQUAL": ">=",
        "GTE": ">=",
        "<": "<",
        "LESS_THAN": "<",
        "LT": "<",
        "<=": "<=",
        "LESS_THAN_OR_EQUAL": "<=",
        "LTE": "<=",
        "==": "==",
        "EQUALS": "==",
        "EQ": "==",
        "!=": "!=",
        "BETWEEN": "BETWEEN",
        "RANGE": "BETWEEN",
    }

    def _apply_operator(self, a: Decimal, b: Decimal, operator: str) -> bool:
        op = self.OP_MAP.get(str(operator).strip(), str(operator).strip())
        ops = {
            ">": lambda x, y: x > y,
            "<": lambda x, y: x < y,
            ">=": lambda x, y: x >= y,
            "<=": lambda x, y: x <= y,
            "==": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
        }
        if op in ops:
            return ops[op](a, b)
        return False

    def _apply_operator_str(self, a: str, b: str, operator: str) -> bool:
        ops = {
            "==": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
        }
        return ops.get(operator, lambda x, y: False)(a, b)

