from sqlalchemy.orm import Session

from app.services.investigation import investigate


class RazInvestigateAgent:
    name = "RazInvestigate"

    def run(self, db: Session, target_type: str, target_id: str) -> dict | None:
        return investigate(db, target_type, target_id)
