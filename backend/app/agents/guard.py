from sqlalchemy.orm import Session

from app.services.control_engine import findings_summary, run_control_engine


class RazGuardAgent:
    """Runs deterministic RazGuard financial controls."""

    name = "RazGuard"

    def run(self, db: Session) -> dict:
        findings = run_control_engine(db)
        summary = findings_summary(db)
        return {
            "agent": self.name,
            "total_findings": len(findings),
            "high_risk": sum(item["severity"] == "HIGH" for item in findings),
            "medium_risk": sum(item["severity"] == "MEDIUM" for item in findings),
            "low_risk": sum(item["severity"] == "LOW" for item in findings),
            "findings": findings,
            "summary": summary,
        }
