from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.investigate import RazInvestigateAgent
from app.db.database import get_db
from app.services.investigation import get_investigation, get_investigations, update_investigation_status

router = APIRouter(prefix="/investigations", tags=["RazInvestigate"])

@router.post("/run")
def run_investigation(target_type: Literal["ANOMALY", "CONTROL_FINDING", "RECONCILIATION"], target_id: str, db: Session = Depends(get_db)):
    try:
        result = RazInvestigateAgent().run(db, target_type, target_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None: raise HTTPException(status_code=404, detail="Investigation target not found")
    return result

@router.get("")
def list_investigations(limit: int = 100, db: Session = Depends(get_db)):
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    return {"investigations": get_investigations(db, limit=limit)}

@router.get("/{investigation_id}")
def retrieve_investigation(investigation_id: str, db: Session = Depends(get_db)):
    result = get_investigation(db, investigation_id)
    if result is None: raise HTTPException(status_code=404, detail="Investigation not found")
    return result

@router.get("/{investigation_id}/evidence")
def retrieve_evidence(investigation_id: str, db: Session = Depends(get_db)):
    result = get_investigation(db, investigation_id)
    if result is None: raise HTTPException(status_code=404, detail="Investigation not found")
    return {"investigation_id": investigation_id, "evidence": result["evidence"]}

@router.patch("/{investigation_id}/status")
def set_investigation_status(investigation_id: str, status: Literal["OPEN", "INVESTIGATING", "REVIEW_REQUIRED", "RESOLVED"], db: Session = Depends(get_db)):
    try: result = update_investigation_status(db, investigation_id, status)
    except ValueError as error: raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None: raise HTTPException(status_code=404, detail="Investigation not found")
    return result
