from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import Base, engine
from app.models import (
    Anomaly,
    AuditLog,
    BankTransaction,
    Company,
    Invoice,
    JournalEntry,
    Transaction,
    Vendor,
    FinancialControl,
    ControlFinding,
    Investigation,
    InvestigationEvidence,
)

from app.api.routes.reconciliation import router as reconciliation_router
from app.api.guard import router as guard_router
from app.api.detect import router as detect_router
from app.api.investigate import router as investigate_router
from app.api.report import router as report_router
from app.api.pipeline import router as pipeline_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered autonomous finance control platform",
)


@app.on_event("startup")
def startup():

    Base.metadata.create_all(
        bind=engine
    )


app.include_router(
    reconciliation_router,
)

app.include_router(
    guard_router,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

app.include_router(
    detect_router,
)

app.include_router(
    investigate_router,
)

app.include_router(
    report_router,
)

app.include_router(
    pipeline_router,
)

@app.get("/")
def root():

    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
def health():

    return {
        "status": "healthy",
    }
