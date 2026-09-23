import pytest
from app.engine.primitives import PrimitiveEvaluator, CaseData
from decimal import Decimal
from datetime import datetime, timedelta

def test_compare_fields():
    evaluator = PrimitiveEvaluator()
    case_data = CaseData(case={}, po={"total": "100"}, invoice={"total": "105"}, grn={}, all_cases=[])

    res = evaluator.evaluate("COMPARE_FIELDS", {
        "field_a": {"document": "invoice", "field": "total"},
        "field_b": {"document": "purchase_order", "field": "total"},
        "tolerance_percent": 5,
        "operator": "=="
    }, case_data)

    assert res.passed is True


def test_compare_fields_deviation_percent_passes_within_threshold():
    evaluator = PrimitiveEvaluator()
    # unit_price deviates 4% (< 5% threshold)
    case_data = CaseData(case={}, po={"unit_price": "100"}, invoice={"unit_price": "104"}, grn={}, all_cases=[])

    res = evaluator.evaluate("COMPARE_FIELDS", {
        "field_a": {"document": "invoice", "field": "unit_price"},
        "field_b": {"document": "purchase_order", "field": "unit_price"},
        "operator": "DEVIATION_PERCENT",
        "threshold": 5,
        "direction": "ANY"
    }, case_data)

    assert res.passed is True


def test_compare_fields_deviation_percent_violates_any_direction():
    evaluator = PrimitiveEvaluator()
    # unit_price deviates 10% (> 5% threshold), direction ANY should flag it
    case_data = CaseData(case={}, po={"unit_price": "100"}, invoice={"unit_price": "110"}, grn={}, all_cases=[])

    res = evaluator.evaluate("COMPARE_FIELDS", {
        "field_a": {"document": "invoice", "field": "unit_price"},
        "field_b": {"document": "purchase_order", "field": "unit_price"},
        "operator": "DEVIATION_PERCENT",
        "threshold": 5,
        "direction": "ANY"
    }, case_data)

    assert res.passed is False


def test_compare_fields_deviation_percent_direction_filters_out_opposite_direction():
    evaluator = PrimitiveEvaluator()
    # invoice unit_price is LOWER than po unit_price by 20% (a DECREASE),
    # but direction is INCREASE, so this decrease should pass regardless of magnitude.
    case_data = CaseData(case={}, po={"unit_price": "100"}, invoice={"unit_price": "80"}, grn={}, all_cases=[])

    res = evaluator.evaluate("COMPARE_FIELDS", {
        "field_a": {"document": "invoice", "field": "unit_price"},
        "field_b": {"document": "purchase_order", "field": "unit_price"},
        "operator": "DEVIATION_PERCENT",
        "threshold": 5,
        "direction": "INCREASE"
    }, case_data)

    assert res.passed is True


def test_count_check_passes_when_below_threshold():
    evaluator = PrimitiveEvaluator()
    case = {"id": "c1", "vendor_name": "Acme Corp"}
    all_cases = [
        {"id": "c1", "vendor_name": "Acme Corp"},
        {"id": "c2", "vendor_name": "Acme Corp"},
    ]
    case_data = CaseData(case=case, po={}, invoice={}, grn={}, all_cases=all_cases)

    res = evaluator.evaluate("COUNT_CHECK", {
        "group_by": "vendor_name",
        "operator": "<=",
        "threshold": 3
    }, case_data)

    assert res.passed is True
    assert res.actual == "2"


def test_count_check_violates_when_over_threshold():
    evaluator = PrimitiveEvaluator()
    case = {"id": "c1", "vendor_name": "Acme Corp"}
    all_cases = [
        {"id": "c1", "vendor_name": "Acme Corp"},
        {"id": "c2", "vendor_name": "Acme Corp"},
        {"id": "c3", "vendor_name": "Acme Corp"},
    ]
    case_data = CaseData(case=case, po={}, invoice={}, grn={}, all_cases=all_cases)

    res = evaluator.evaluate("COUNT_CHECK", {
        "group_by": "vendor_name",
        "operator": "<=",
        "threshold": 2
    }, case_data)

    assert res.passed is False
    assert res.actual == "3"


def test_count_check_passes_trivially_with_no_group_value():
    evaluator = PrimitiveEvaluator()
    case = {"id": "c1"}  # no project_code
    case_data = CaseData(case=case, po={}, invoice={}, grn={}, all_cases=[])

    res = evaluator.evaluate("COUNT_CHECK", {
        "group_by": "project_code",
        "operator": "<=",
        "threshold": 2
    }, case_data)

    assert res.passed is True
    assert "No group info" in res.explanation


def test_aggregation_check_sum_within_window_violating():
    evaluator = PrimitiveEvaluator()
    now = datetime(2024, 1, 15)
    case = {"id": "c1", "vendor_name": "Acme Corp", "created_at": now}
    all_cases = [
        case,
        {"id": "c2", "vendor_name": "Acme Corp", "total_amount": "150000", "created_at": now - timedelta(days=2)},
        {"id": "c3", "vendor_name": "Acme Corp", "total_amount": "100000", "created_at": now - timedelta(days=5)},
    ]
    case_data = CaseData(case=case, po={}, invoice={}, grn={}, all_cases=all_cases)

    res = evaluator.evaluate("AGGREGATION_CHECK", {
        "function": "SUM",
        "aggregate_field": "total_amount",
        "group_by": "vendor_name",
        "window_days": 7,
        "operator": ">",
        "threshold": 200000
    }, case_data)

    assert res.passed is True  # 150000 + 100000 = 250000 > 200000


def test_aggregation_check_sum_within_window_passing():
    evaluator = PrimitiveEvaluator()
    now = datetime(2024, 1, 15)
    case = {"id": "c1", "vendor_name": "Acme Corp", "created_at": now}
    all_cases = [
        case,
        {"id": "c2", "vendor_name": "Acme Corp", "total_amount": "50000", "created_at": now - timedelta(days=2)},
    ]
    case_data = CaseData(case=case, po={}, invoice={}, grn={}, all_cases=all_cases)

    res = evaluator.evaluate("AGGREGATION_CHECK", {
        "function": "SUM",
        "aggregate_field": "total_amount",
        "group_by": "vendor_name",
        "window_days": 7,
        "operator": ">",
        "threshold": 200000
    }, case_data)

    assert res.passed is False  # only 50000, well under threshold


def test_aggregation_check_excludes_cases_outside_window():
    evaluator = PrimitiveEvaluator()
    now = datetime(2024, 1, 15)
    case = {"id": "c1", "vendor_name": "Acme Corp", "created_at": now}
    all_cases = [
        case,
        # within the 7 day window
        {"id": "c2", "vendor_name": "Acme Corp", "total_amount": "150000", "created_at": now - timedelta(days=3)},
        # far outside the window - must NOT be counted
        {"id": "c3", "vendor_name": "Acme Corp", "total_amount": "500000", "created_at": now - timedelta(days=90)},
    ]
    case_data = CaseData(case=case, po={}, invoice={}, grn={}, all_cases=all_cases)

    res = evaluator.evaluate("AGGREGATION_CHECK", {
        "function": "SUM",
        "aggregate_field": "total_amount",
        "group_by": "vendor_name",
        "window_days": 7,
        "operator": ">",
        "threshold": 200000
    }, case_data)

    # Only the 150000 in-window case counts; the 500000 far-away case is excluded.
    assert res.actual == "150000"
    assert res.passed is False


def test_aggregation_check_count_function():
    evaluator = PrimitiveEvaluator()
    case = {"id": "c1", "vendor_name": "Acme Corp"}
    all_cases = [
        case,
        {"id": "c2", "vendor_name": "Acme Corp"},
        {"id": "c3", "vendor_name": "Acme Corp"},
    ]
    case_data = CaseData(case=case, po={}, invoice={}, grn={}, all_cases=all_cases)

    res = evaluator.evaluate("AGGREGATION_CHECK", {
        "function": "COUNT",
        "group_by": "vendor_name",
        "operator": ">=",
        "threshold": 3
    }, case_data)

    assert res.passed is True
    assert res.actual == "3"


def test_aggregation_check_avg_function():
    evaluator = PrimitiveEvaluator()
    case = {"id": "c1", "vendor_name": "Acme Corp", "total_amount": "100"}
    all_cases = [
        case,
        {"id": "c2", "vendor_name": "Acme Corp", "total_amount": "300"},
    ]
    case_data = CaseData(case=case, po={}, invoice={}, grn={}, all_cases=all_cases)

    res = evaluator.evaluate("AGGREGATION_CHECK", {
        "function": "AVG",
        "aggregate_field": "total_amount",
        "group_by": "vendor_name",
        "operator": "==",
        "threshold": 200
    }, case_data)

    assert res.passed is True
    assert res.actual == "200"


def test_time_window_check_sum_of_vendor_spend():
    # Plan Section 6.2: "Vendor spending exceeding ₹5,00,000 in 30 days requires review"
    evaluator = PrimitiveEvaluator()
    now = datetime(2024, 3, 1)
    case = {"id": "c1", "vendor_name": "Acme Corp", "created_at": now}
    all_cases = [
        case,
        {"id": "c2", "vendor_name": "Acme Corp", "total_amount": "300000", "created_at": now - timedelta(days=10)},
        {"id": "c3", "vendor_name": "Acme Corp", "total_amount": "250000", "created_at": now - timedelta(days=20)},
        # outside the 30 day window
        {"id": "c4", "vendor_name": "Acme Corp", "total_amount": "999999", "created_at": now - timedelta(days=60)},
    ]
    case_data = CaseData(case=case, po={}, invoice={}, grn={}, all_cases=all_cases)

    res = evaluator.evaluate("TIME_WINDOW_CHECK", {
        "group_by": "vendor_name",
        "window_days": 30,
        "aggregate_field": "total_amount",
        "function": "SUM",
        "operator": ">",
        "threshold": 500000
    }, case_data)

    assert res.passed is True  # 300000 + 250000 = 550000 > 500000
    assert res.actual == "550000"


def test_match_check_across_cases_same_invoice_different_vendor_not_duplicate():
    evaluator = PrimitiveEvaluator()
    case = {"id": "c1", "vendor_name": "Vendor A", "invoice_number": "INV-100"}
    all_cases = [
        case,
        {"id": "c2", "vendor_name": "Vendor B", "invoice_number": "INV-100"},
    ]
    case_data = CaseData(case=case, po={}, invoice={"invoice_number": "INV-100"}, grn={}, all_cases=all_cases)

    res = evaluator.evaluate("MATCH_CHECK", {
        "field": {"document": "invoice", "field": "invoice_number"},
        "across": "cases"
    }, case_data)

    assert res.passed is True  # unique, since the other case is a different vendor


def test_match_check_across_cases_same_invoice_same_vendor_is_duplicate():
    evaluator = PrimitiveEvaluator()
    case = {"id": "c1", "vendor_name": "Vendor A", "invoice_number": "INV-100"}
    all_cases = [
        case,
        {"id": "c2", "vendor_name": "Vendor A", "invoice_number": "INV-100"},
    ]
    case_data = CaseData(case=case, po={}, invoice={"invoice_number": "INV-100"}, grn={}, all_cases=all_cases)

    res = evaluator.evaluate("MATCH_CHECK", {
        "field": {"document": "invoice", "field": "invoice_number"},
        "across": "cases"
    }, case_data)

    assert res.passed is False  # same invoice number AND same vendor -> duplicate
