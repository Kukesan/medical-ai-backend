from app.models.medical_visit import MedicalVisit


class TimelineService:
    def build(self, visits: list[MedicalVisit]) -> list[dict]:
        entries: list[dict] = []
        for visit in visits:
            entries.append(
                {
                    "visit_id": str(visit.id),
                    "visit_date": visit.visit_date.isoformat() if visit.visit_date else None,
                    "doctor_name": visit.doctor_name,
                    "hospital_name": visit.hospital_name,
                    "medications": [m.name for m in visit.medications],
                    "labs": [l.test_name for l in visit.lab_results],
                    "notes": [n.note_text for n in visit.clinical_notes],
                }
            )
        return sorted(entries, key=lambda item: item["visit_date"] or "9999-12-31")
