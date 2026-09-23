from app.engine.dsl_interpreter import DSLInterpreter
from app.engine.primitives import CaseData

def test_dsl_interpreter():
    interpreter = DSLInterpreter()
    case_data = CaseData(case={}, po={"total": "100"}, invoice={"total": "100"}, grn={}, all_cases=[])
    
    node = {
        "operator": "AND",
        "operands": [
            {
                "primitive": "COMPARE_FIELDS",
                "parameters": {
                    "field_a": {"document": "invoice", "field": "total"},
                    "field_b": {"document": "purchase_order", "field": "total"},
                    "operator": "=="
                }
            }
        ]
    }
    
    res = interpreter.evaluate(node, case_data)
    assert res.passed is True
