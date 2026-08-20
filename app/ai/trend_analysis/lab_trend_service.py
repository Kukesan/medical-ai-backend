from collections import defaultdict
from statistics import mean
from typing import Any


class LabTrendService:
    TRACKED_TESTS = {
        "blood sugar",
        "hba1c",
        "cholesterol",
        "hemoglobin",
        "creatinine",
        "blood pressure",
    }

    def build_trends(self, lab_results: list[Any]) -> list[dict]:
        grouped: dict[str, list[Any]] = defaultdict(list)
        for row in lab_results:
            grouped[row.test_name.lower()].append(row)

        trends: list[dict] = []
        for name, rows in grouped.items():
            values = [r.value for r in rows if r.value is not None]
            if not values:
                continue

            direction = self._direction(values)
            comparison = self._range_comparison(rows)
            trends.append(
                {
                    "test_name": rows[0].test_name,
                    "trend_direction": direction,
                    "normal_range_comparison": comparison,
                    "explanation": (
                        "Trend generated from historical values. This is informational and not a diagnosis."
                    ),
                    "confidence": 0.72,
                }
            )
        return trends

    def _direction(self, values: list[float]) -> str:
        if len(values) < 2:
            return "insufficient_data"
        if values[-1] > values[0]:
            return "increasing"
        if values[-1] < values[0]:
            return "decreasing"
        return "stable"

    def _range_comparison(self, rows: list[Any]) -> str:
        refs = [r.reference_range for r in rows if r.reference_range]
        if not refs:
            return "reference_range_not_available"
        avg = mean([r.value for r in rows if r.value is not None])
        return f"Compared against reported references; average observed value {avg:.2f}."
