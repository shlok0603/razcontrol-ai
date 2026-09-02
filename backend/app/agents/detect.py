from sqlalchemy.orm import Session

from app.services.anomaly_detection import anomaly_summary, detect_anomalies


class RazDetectAgent:
    name = "RazDetect"

    def run(self, db: Session) -> dict:
        anomalies = detect_anomalies(db)
        return {
            "agent": self.name,
            "total_detected": len(anomalies),
            "high_risk": sum(item["severity"] == "HIGH" for item in anomalies),
            "medium_risk": sum(item["severity"] == "MEDIUM" for item in anomalies),
            "low_risk": sum(item["severity"] == "LOW" for item in anomalies),
            "anomalies": anomalies,
            "summary": anomaly_summary(db),
        }
