# mypy: ignore-errors
"""Risk Scoring Engine for RedactAI."""

from dataclasses import dataclass

from redactai.engine.detectors.base import Match


@dataclass
class RiskAssessment:
    """The overall risk assessment for a payload."""

    score: float  # 0.0 to 100.0
    risk_level: str  # SAFE, LOW, MEDIUM, HIGH, CRITICAL
    factors: list[str]  # Explanations for the score

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 2),
            "risk_level": self.risk_level,
            "factors": self.factors,
        }


class RiskScorer:
    """Calculate aggregate risk scores based on detected Matches."""

    # Base points for each severity level
    SEVERITY_WEIGHTS = {
        "LOW": 5.0,
        "MEDIUM": 15.0,
        "HIGH": 40.0,
        "CRITICAL": 85.0,
    }

    def evaluate(self, matches: list[Match]) -> RiskAssessment:
        if not matches:
            return RiskAssessment(
                score=0.0, risk_level="SAFE", factors=["No sensitive data detected."]
            )

        score = 0.0
        factors = []

        critical_count = 0
        high_count = 0

        for m in matches:
            weight = self.SEVERITY_WEIGHTS.get(m.severity, 5.0)
            score += weight * m.confidence

            if m.severity == "CRITICAL":
                critical_count += 1
            elif m.severity == "HIGH":
                high_count += 1

        # Cap score at 100.0
        score = min(100.0, score)

        if critical_count > 0:
            factors.append(f"Contains {critical_count} CRITICAL findings (e.g. Credentials/Keys).")
        if high_count > 0:
            factors.append(f"Contains {high_count} HIGH severity findings.")

        if score >= 85.0:
            level = "CRITICAL"
        elif score >= 60.0:
            level = "HIGH"
        elif score >= 30.0:
            level = "MEDIUM"
        else:
            level = "LOW"

        return RiskAssessment(score=score, risk_level=level, factors=factors)
