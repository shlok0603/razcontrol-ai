"""End-to-end orchestration with module-boundary recovery and observability."""
from __future__ import annotations

import logging
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.agents.detect import RazDetectAgent
from app.agents.guard import RazGuardAgent
from app.agents.investigate import RazInvestigateAgent
from app.agents.recon import RazReconAgent
from app.agents.report import RazReportAgent
from app.config import settings

logger = logging.getLogger(__name__)


def _stage(db: Session, name: str, action: Callable[[], Any]) -> tuple[dict[str, Any], Any | None]:
    try:
        result = action()
        return {"stage": name, "status": "COMPLETED"}, result
    except Exception as error:
        # Each service is independently transactional. This rollback also
        # clears any unfinished state from an unexpected agent/provider error.
        db.rollback()
        # Do not expose provider exception text: it can contain upstream or
        # credential-adjacent details. The stage and exception class remain
        # sufficient for monitoring and API consumers.
        logger.error("RazControl pipeline stage failed: %s (%s)", name, type(error).__name__)
        return {"stage": name, "status": "FAILED", "error": type(error).__name__}, None


def _investigation_targets(recon: dict | None, guard: dict | None, detect: dict | None) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    for item in (detect or {}).get("anomalies", []):
        if item["severity"] == "HIGH": targets.append(("ANOMALY", item["anomaly_id"]))
    for item in (guard or {}).get("findings", []):
        if item["severity"] == "HIGH": targets.append(("CONTROL_FINDING", item["finding_id"]))
    for item in (recon or {}).get("results", []):
        if item["status"] == "UNMATCHED": targets.append(("RECONCILIATION", item["bank_transaction_id"]))
    return list(dict.fromkeys(targets))[:settings.PIPELINE_MAX_INVESTIGATIONS]


def run_pipeline(db: Session, *, investigate_high_risk: bool = True) -> dict[str, Any]:
    """Run Recon → Guard → Detect → optional Investigate → Report.

    Stages persist their own successful output. A later stage failure is
    reported without rolling back successful earlier stages.
    """
    stages: list[dict[str, Any]] = []
    recon_stage, recon = _stage(db, "RazRecon", lambda: RazReconAgent().run(db)); stages.append(recon_stage)
    guard_stage, guard = _stage(db, "RazGuard", lambda: RazGuardAgent().run(db)); stages.append(guard_stage)
    detect_stage, detect = _stage(db, "RazDetect", lambda: RazDetectAgent().run(db)); stages.append(detect_stage)

    investigation_results: list[dict[str, Any]] = []
    if investigate_high_risk:
        targets = _investigation_targets(recon, guard, detect)
        failed = 0
        for target_type, target_id in targets:
            stage, result = _stage(db, f"RazInvestigate:{target_type}:{target_id}", lambda target_type=target_type, target_id=target_id: RazInvestigateAgent().run(db, target_type, target_id))
            if stage["status"] == "FAILED": failed += 1
            elif result is not None: investigation_results.append(result)
        stages.append({"stage": "RazInvestigate", "status": "PARTIAL" if failed else "COMPLETED", "attempted": len(targets), "completed": len(investigation_results), "failed": failed})
    else:
        stages.append({"stage": "RazInvestigate", "status": "SKIPPED"})

    report_stage, report = _stage(db, "RazReport", lambda: RazReportAgent().run(db)); stages.append(report_stage)
    failures = [stage for stage in stages if stage["status"] in {"FAILED", "PARTIAL"}]
    return {"pipeline": "RazControl", "status": "PARTIAL_FAILURE" if failures else "COMPLETED", "stages": stages, "results": {"reconciliation": recon, "controls": guard, "anomalies": detect, "investigations": investigation_results, "report": report}}
