from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.pipeline import run_pipeline

router = APIRouter(prefix="/pipeline", tags=["RazControl Integration"])

@router.post("/run")
def run_end_to_end_pipeline(investigate_high_risk: bool = True, db: Session = Depends(get_db)):
    return run_pipeline(db, investigate_high_risk=investigate_high_risk)
