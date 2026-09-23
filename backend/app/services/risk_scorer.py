from decimal import Decimal
from app.models.finding import ComplianceFinding


SEVERITY_WEIGHTS = {
    "CRITICAL": 30,
    "HIGH": 20,
    "MEDIUM": 10,
    "LOW": 5,
}

FINDING_TYPE_BONUSES = {
    "DUPLICATE_INVOICE": 20,
    "MISSING_GRN": 10,
    "MISSING_INVOICE": 10,
    "VENDOR_MISMATCH": 10,
    "APPROVAL_THRESHOLD": 15,
    "DIRECT_PURCHASE_THRESHOLD_EXCEEDED": 20,
    "GEM_BIDDING_REQUIRED": 20,
    "LIMITED_TENDER_MANDATE": 15,
    "OPEN_TENDER_MANDATE": 15,
    "CUMULATIVE_SPEND": 10,
}


class RiskScorer:
    def calculate_risk(
        self,
        findings: list[ComplianceFinding],
        total_amount: float | None,
    ) -> tuple[str, float]:
        """
        Returns (risk_level, risk_score).
        risk_level: LOW | MEDIUM | HIGH | CRITICAL
        """
        score: float = 0.0

        violations = [f for f in findings if f.status == "VIOLATION"]
        needs_review = [f for f in findings if f.status == "NEEDS_REVIEW"]

        # Base score from violations
        for f in violations:
            score += SEVERITY_WEIGHTS.get(f.severity, 5)
            # Extra weight for specific violation types
            score += FINDING_TYPE_BONUSES.get(f.finding_type, 0)

        # Half weight for needs_review
        for f in needs_review:
            score += SEVERITY_WEIGHTS.get(f.severity, 5) * 0.5

        # Monetary risk factor
        if total_amount:
            amt = float(total_amount)
            if amt > 5_000_000:
                score += 20
            elif amt > 1_000_000:
                score += 10
            elif amt > 500_000:
                score += 5

        score = round(score, 2)

        if score < 20:
            level = "LOW"
        elif score < 50:
            level = "MEDIUM"
        elif score < 80:
            level = "HIGH"
        else:
            level = "CRITICAL"

        return level, score


risk_scorer = RiskScorer()
