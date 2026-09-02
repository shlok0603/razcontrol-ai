from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.detect import RazDetectAgent
from app.db.database import get_db
from app.services.anomaly_detection import anomaly_summary, get_anomalies


router = APIRouter(prefix="/detect", tags=["RazDetect"])


@router.post("/run")
def run_detection(db: Session = Depends(get_db)):
    return RazDetectAgent().run(db)


@router.get("/anomalies")
def list_anomalies(severity: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    return {"anomalies": get_anomalies(db, severity=severity, status=status)}


@router.get("/anomalies/summary")
def get_anomaly_summary(db: Session = Depends(get_db)):
    return anomaly_summary(db)


@router.get("/anomalies/transaction/{transaction_id}")
def list_transaction_anomalies(transaction_id: str, db: Session = Depends(get_db)):
    return {"transaction_id": transaction_id, "anomalies": get_anomalies(db, transaction_id=transaction_id)}
