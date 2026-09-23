import json
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class LLMEvaluator:
    """Tier 3: LLM-based rule evaluation via Mistral API."""

    def __init__(self):
        self._client = None
        self._get_client()

    def _get_client(self):
        if self._client is not None:
            return self._client
        if settings.MISTRAL_API_KEY:
            try:
                from mistralai.client import Mistral
                self._client = Mistral(api_key=settings.MISTRAL_API_KEY)
            except Exception as e:
                logger.error("Failed to initialize Mistral client in LLMEvaluator: %s", e)
                self._client = None
        return self._client

    async def evaluate(
        self,
        prompt: str,
        case_data_summary: dict,
        policy_clause: str,
    ) -> dict:
        """
        Evaluate a rule via LLM. Returns dict with:
        status, explanation, expected_value, actual_value, confidence,
        prompt_used, response_received
        """
        client = self._get_client()
        if not client:
            return {
                "status": "NEEDS_REVIEW",
                "explanation": (
                    "Mistral API key not configured. "
                    "This Tier 3 (AI-assessed) rule requires manual review."
                ),
                "expected_value": None,
                "actual_value": None,
                "confidence": 0.0,
                "prompt_used": "",
                "response_received": "",
            }

        system_instruction = (
            "You are a procurement compliance analyst. Evaluate the procurement case "
            "against the specified policy clause and rule."
        )

        user_prompt = f"""POLICY CLAUSE:
{policy_clause}

CASE DATA:
{json.dumps(case_data_summary, indent=2, default=str)}

RULE TO EVALUATE:
{prompt}

Respond with ONLY a valid JSON object:
{{
  "status": "PASS" | "VIOLATION" | "NEEDS_REVIEW",
  "explanation": "Precise explanation citing policy clause and case values",
  "expected_value": "What the policy clause requires",
  "actual_value": "What was found in the case data",
  "confidence": 0.0-1.0
}}"""

        preferred_model = settings.MISTRAL_MODEL or "mistral-medium-latest"
        fallback_model = "open-mistral-7b"

        try:
            try:
                response = await client.chat.complete_async(
                    model=preferred_model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
            except Exception as call_err:
                err_msg = str(call_err)
                if "429" in err_msg or "rate limit" in err_msg.lower():
                    logger.warning(
                        "Mistral model '%s' rate limited; falling back to '%s'",
                        preferred_model,
                        fallback_model,
                    )
                    response = await client.chat.complete_async(
                        model=fallback_model,
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.1,
                    )
                else:
                    raise call_err

            raw_text = response.choices[0].message.content
            cleaned = raw_text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            result = json.loads(cleaned)
            result["prompt_used"] = user_prompt[:2000]
            result["response_received"] = raw_text[:2000]
            return result
        except Exception as exc:
            return {
                "status": "NEEDS_REVIEW",
                "explanation": f"LLM evaluation failed: {exc}. Manual review required.",
                "expected_value": None,
                "actual_value": None,
                "confidence": 0.0,
                "prompt_used": user_prompt[:2000],
                "response_received": "",
            }
