from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from app.models.enums import RiskLevel


class DrugInteractionService:
    INTERACTION_RULES = {
        frozenset(["warfarin", "aspirin"]): (RiskLevel.HIGH, "Bleeding risk may be increased"),
        frozenset(["ibuprofen", "lisinopril"]): (RiskLevel.MEDIUM, "NSAID may reduce ACE inhibitor effect"),
    }

    @staticmethod
    def _evidence(med: Any, snippet: str) -> dict:
        visit = med.visit
        return {
            "source_document_id": str(visit.document_id) if getattr(visit, "document_id", None) else None,
            "record_id": str(visit.record_id) if getattr(visit, "record_id", None) else None,
            "record_type": getattr(visit, "record_type", None),
            "snippet": snippet,
            "page": None,
        }

    def analyze(self, medications: list[Any], allergies: set[str]) -> dict:
        duplicate_alerts = self._find_duplicates(medications)
        interaction_alerts = self._find_interactions(medications)
        conflict_alerts = self._find_conflicting_dosages(medications)
        expired_alerts = self._find_expired(medications)
        allergy_alerts = self._find_allergy_conflicts(medications, allergies)

        return {
            "duplicate_medications": duplicate_alerts,
            "drug_interactions": interaction_alerts,
            "conflicting_dosages": conflict_alerts,
            "expired_prescriptions": expired_alerts,
            "medication_changes": [],
            "allergy_alerts": allergy_alerts,
        }

    def _find_duplicates(self, medications: list[Any]) -> list[dict]:
        grouped: dict[str, list[Any]] = defaultdict(list)
        for med in medications:
            grouped[med.name.lower()].append(med)

        alerts: list[dict] = []
        for med_name, rows in grouped.items():
            if len(rows) > 1:
                alerts.append(
                    {
                        "category": "duplicate_medication",
                        "details": f"{rows[0].name} appears in multiple visits.",
                        "assessment": {
                            "risk_level": RiskLevel.MEDIUM,
                            "explanation": "Potential duplicate therapy detected.",
                            "evidence": [
                                self._evidence(r, f"{r.name} {r.dosage or ''} {r.frequency or ''}".strip())
                                for r in rows
                            ],
                            "confidence": 0.75,
                        },
                    }
                )
        return alerts

    def _find_interactions(self, medications: list[Any]) -> list[dict]:
        names = {m.name.lower(): m for m in medications}
        alerts: list[dict] = []
        for pair, (risk, explanation) in self.INTERACTION_RULES.items():
            if pair.issubset(names.keys()):
                name_a, name_b = sorted(pair)
                med_a = names[name_a]
                med_b = names[name_b]
                alerts.append(
                    {
                        "category": "drug_interaction",
                        "details": f"Possible interaction between {med_a.name} and {med_b.name}.",
                        "assessment": {
                            "risk_level": risk,
                            "explanation": explanation,
                            "evidence": [
                                self._evidence(med_a, med_a.name),
                                self._evidence(med_b, med_b.name),
                            ],
                            "confidence": 0.7,
                        },
                    }
                )
        return alerts

    def _find_conflicting_dosages(self, medications: list[Any]) -> list[dict]:
        grouped: dict[str, set[str]] = defaultdict(set)
        for med in medications:
            if med.dosage:
                grouped[med.name.lower()].add(med.dosage)

        alerts: list[dict] = []
        for name, dosages in grouped.items():
            if len(dosages) > 1:
                alerts.append(
                    {
                        "category": "conflicting_dosage",
                        "details": f"{name.title()} has multiple dosage instructions: {', '.join(dosages)}.",
                        "assessment": {
                            "risk_level": RiskLevel.MEDIUM,
                            "explanation": "Different dosage instructions found across documents.",
                            "evidence": [],
                            "confidence": 0.8,
                        },
                    }
                )
        return alerts

    def _find_expired(self, medications: list[Any]) -> list[dict]:
        now = datetime.now(UTC).date()
        alerts: list[dict] = []
        for med in medications:
            if med.end_date and med.end_date < now:
                alerts.append(
                    {
                        "category": "expired_prescription",
                        "details": f"{med.name} appears expired on {med.end_date.isoformat()}.",
                        "assessment": {
                            "risk_level": RiskLevel.LOW,
                            "explanation": "Prescription end date is in the past.",
                            "evidence": [
                                self._evidence(med, f"End date {med.end_date.isoformat()}")
                            ],
                            "confidence": 0.9,
                        },
                    }
                )
        return alerts

    def _find_allergy_conflicts(self, medications: list[Any], allergies: set[str]) -> list[dict]:
        alerts: list[dict] = []
        allergy_lc = {a.lower() for a in allergies}
        for med in medications:
            if med.name.lower() in allergy_lc:
                alerts.append(
                    {
                        "category": "allergy_conflict",
                        "details": f"Medication {med.name} matches recorded allergy.",
                        "assessment": {
                            "risk_level": RiskLevel.HIGH,
                            "explanation": "Potential allergy conflict between known allergy and prescribed medicine.",
                            "evidence": [
                                self._evidence(med, med.name)
                            ],
                            "confidence": 0.85,
                        },
                    }
                )
        return alerts
