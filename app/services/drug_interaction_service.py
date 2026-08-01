from app.ai.interaction_checker.drug_interaction_service import DrugInteractionService as AIDrugService


class DrugInteractionService:
    def __init__(self) -> None:
        self.impl = AIDrugService()

    def analyze(self, medications, allergies: set[str]) -> dict:
        return self.impl.analyze(medications, allergies)
