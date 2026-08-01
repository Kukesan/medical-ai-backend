class ConfidenceService:
    def normalize(self, value: float | None) -> float:
        if value is None:
            return 0.0
        return max(0.0, min(1.0, float(value)))

    def requires_warning(self, risk_level: str, confidence: float) -> bool:
        return risk_level == "high" or confidence < 0.5
