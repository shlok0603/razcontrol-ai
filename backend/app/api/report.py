from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.agents.report import RazReportAgent
from app.db.database import get_db
from app.services.reporting import get_finding_report, report_csv, report_summary, transaction_risk_report

router = APIRouter(prefix="/reports", tags=["RazReport"])

@router.get("/overall")
def get_overall_report(limit: int = 100, db: Session = Depends(get_db)):
    return RazReportAgent().run(db, findings_limit=min(max(limit, 1), 500))

@router.get("/summary")
def get_report_summary(db: Session = Depends(get_db)): return report_summary(db)

@router.get("/findings/{finding_id}")
def get_finding(finding_id: str, db: Session = Depends(get_db)):
    result = get_finding_report(db, finding_id)
    if result is None: raise HTTPException(status_code=404, detail="Finding not found")
    return result

@router.get("/transactions/{transaction_id}")
def get_transaction_risk(transaction_id: str, db: Session = Depends(get_db)): return transaction_risk_report(db, transaction_id)

@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    return Response(report_csv(db), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=razreport-findings.csv"})
