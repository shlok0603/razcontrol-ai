from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.agents.guard import RazGuardAgent
from app.models import ControlFinding
from app.services.control_engine import findings_summary, get_findings, update_finding_status


router = APIRouter(
    prefix="/guard",
    tags=["RazGuard"],
)


@router.post("/scan")
def scan_financial_controls(
    db: Session = Depends(get_db),
):
    """
    Runs RazGuard's deterministic financial
    control engine.
    """

    return RazGuardAgent().run(db)


@router.get("/findings")
def list_findings(limit: int = 100, db: Session = Depends(get_db)):
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    return {"total": db.query(ControlFinding).count(), "findings": get_findings(db, limit=limit)}


@router.get("/findings/summary")
def get_findings_summary(db: Session = Depends(get_db)):
    return findings_summary(db)


@router.get("/findings/control/{control_id}")
def list_control_findings(control_id: str, limit: int = 100, db: Session = Depends(get_db)):
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    return {"control_id": control_id, "findings": get_findings(db, control_id=control_id, limit=limit)}


@router.get("/findings/transaction/{transaction_id}")
def list_transaction_findings(transaction_id: str, limit: int = 100, db: Session = Depends(get_db)):
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    return {"transaction_id": transaction_id, "findings": get_findings(db, transaction_id=transaction_id, limit=limit)}


@router.patch("/findings/{finding_id}/status")
def set_finding_status(finding_id: str, status: str, db: Session = Depends(get_db)):
    try:
        finding = update_finding_status(db, finding_id, status)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding
