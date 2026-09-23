import json
from types import SimpleNamespace
import pytest
from app.engine.llm_evaluator import LLMEvaluator


class FakeMistralClient:
    """Mimics mistralai.client.Mistral's chat.complete_async interface."""

    def __init__(self, response_text: str):
        self._response_text = response_text
        self.call_count = 0
        self.chat = SimpleNamespace(complete_async=self._complete_async)

    async def _complete_async(self, **kwargs):
        self.call_count += 1
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self._response_text)
                )
            ]
        )


@pytest.mark.asyncio
async def test_llm_evaluator_no_api_key_returns_needs_review(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "MISTRAL_API_KEY", "")

    evaluator = LLMEvaluator()
    evaluator._client = None

    result = await evaluator.evaluate(
        prompt="Check if invoice is valid",
        case_data_summary={"amount": 100},
        policy_clause="Direct purchase limit 25000",
    )

    assert result["status"] == "NEEDS_REVIEW"
    assert "Mistral API key not configured" in result["explanation"]
    assert result["confidence"] == 0.0


@pytest.mark.asyncio
async def test_llm_evaluator_successful_pass():
    fake_json = json.dumps({
        "status": "PASS",
        "explanation": "PO value ₹15,000 is under the direct purchase limit of ₹25,000.",
        "expected_value": "<= 25000",
        "actual_value": "15000",
        "confidence": 0.95,
    })

    evaluator = LLMEvaluator()
    evaluator._client = FakeMistralClient(fake_json)

    result = await evaluator.evaluate(
        prompt="Verify purchase under limit",
        case_data_summary={"total_amount": 15000},
        policy_clause="Direct purchase limit is 25000",
    )

    assert result["status"] == "PASS"
    assert result["confidence"] == 0.95
    assert result["actual_value"] == "15000"
    assert "PO value" in result["explanation"]


@pytest.mark.asyncio
async def test_llm_evaluator_strips_markdown_fences():
    fenced_response = "```json\n" + json.dumps({
        "status": "VIOLATION",
        "explanation": "No tender issued for purchase exceeding ₹5,00,000.",
        "expected_value": "Tender required",
        "actual_value": "Direct PO",
        "confidence": 0.9,
    }) + "\n```"

    evaluator = LLMEvaluator()
    evaluator._client = FakeMistralClient(fenced_response)

    result = await evaluator.evaluate(
        prompt="Check tender requirement",
        case_data_summary={"amount": 600000},
        policy_clause="Purchases over 500000 require tender",
    )

    assert result["status"] == "VIOLATION"
    assert result["actual_value"] == "Direct PO"


@pytest.mark.asyncio
async def test_llm_evaluator_fallback_on_429():
    class RateLimitedClient:
        def __init__(self):
            self.calls = []
            self.chat = SimpleNamespace(complete_async=self._complete_async)

        async def _complete_async(self, **kwargs):
            model = kwargs.get("model")
            self.calls.append(model)
            if model == "mistral-medium-latest":
                raise Exception("429 Rate limit exceeded (code 1300)")
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=json.dumps({
                                "status": "PASS",
                                "explanation": "Evaluated via fallback model.",
                                "expected_value": "Any",
                                "actual_value": "Match",
                                "confidence": 0.85,
                            })
                        )
                    )
                ]
            )

    client = RateLimitedClient()
    evaluator = LLMEvaluator()
    evaluator._client = client

    result = await evaluator.evaluate(
        prompt="Test fallback",
        case_data_summary={},
        policy_clause="Sample clause",
    )

    assert result["status"] == "PASS"
    assert "Evaluated via fallback model." in result["explanation"]
    assert client.calls == ["mistral-medium-latest", "open-mistral-7b"]
