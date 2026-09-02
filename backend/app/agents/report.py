from sqlalchemy.orm import Session
from app.services.reporting import overall_report

class RazReportAgent:
    name = "RazReport"
    def run(self, db: Session, findings_limit: int | None = None) -> dict:
        return {"agent": self.name, **overall_report(db, findings_limit=findings_limit)}
