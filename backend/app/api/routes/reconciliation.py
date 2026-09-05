from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.recon import RazReconAgent
from app.models import ReconciliationMatch
from app.services.reconciliation import get_reconciliation_results
from app.db.database import get_db


router = APIRouter(
    prefix="/reconciliation",
    tags=["Reconciliation"],
)


@router.post("/run")
def run_reconciliation(
    db: Session = Depends(get_db),
):

    agent = RazReconAgent()

    result = agent.run(db)

    return result


@router.get("/results")
def list_reconciliation_results(
    limit: int = 100,
    db: Session = Depends(get_db),
):
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    return {
        "total": db.query(ReconciliationMatch).count(),
        "results": get_reconciliation_results(db, limit=limit),
    }
