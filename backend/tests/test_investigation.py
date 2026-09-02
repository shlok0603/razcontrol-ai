import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.investigate import retrieve_evidence, retrieve_investigation, run_investigation, set_investigation_status
from app.db.database import Base
from app.models import Anomaly, ControlFinding, Investigation, InvestigationEvidence, Transaction
from app.services.investigation import EvidenceOnlyProvider, InvestigationResult, collect_evidence, investigate


class MockProvider:
    name = "mock"
    def investigate(self, target_type, target_id, evidence, instructions):
        assert all(item.source_id for item in evidence)
        assert "Do not invent transactions" in instructions
        return InvestigationResult("Reviewed sourced evidence.", "HIGH based on supplied anomaly.", "Hypothesis: unusual amount requires validation.", [f"{item.source_type}:{item.source_id}" for item in evidence], [], .75, "Request supporting documentation.")


class RazInvestigateTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine, expire_on_commit=False)()
        self.transaction = Transaction(transaction_id="TX-1", transaction_date=date(2026, 1, 7), description="unusual service", vendor="Vendor", account="Expense", amount=Decimal("9000"), currency="INR", transaction_type="DEBIT", source="ERP")
        self.anomaly = Anomaly(anomaly_id="ANOM-1", fingerprint="a" * 64, transaction_id="TX-1", anomaly_type="AMOUNT_IQR_DEVIATION", risk_score=Decimal("90"), severity="HIGH", explanation="Outside IQR", evidence={"upper_bound": 500}, status="OPEN", detected_by="RazDetect", detection_method="HISTORICAL_IQR_V1")
        self.control = ControlFinding(finding_id="CF-1", fingerprint="c" * 64, control_id="HIGH_VALUE_TRANSACTION", record_type="Transaction", record_id="TX-1", status="OPEN", severity="HIGH", evidence={"threshold": 1000}, explanation="Above threshold")
        self.db.add_all([self.transaction, self.anomaly, self.control]); self.db.commit()

    def tearDown(self): self.db.close()

    def test_collects_citable_target_transaction_and_control_evidence(self):
        evidence = collect_evidence(self.db, "ANOMALY", "ANOM-1")
        citations = {(item.source_type, item.source_id) for item in evidence}
        self.assertIn(("Anomaly", "ANOM-1"), citations)
        self.assertIn(("Transaction", "TX-1"), citations)
        self.assertIn(("ControlFinding", "CF-1"), citations)

    def test_mock_provider_result_is_structured_and_persisted(self):
        result = investigate(self.db, "ANOMALY", "ANOM-1", MockProvider())
        self.assertEqual(result["provider"], "mock")
        self.assertEqual(result["confidence"], .75)
        self.assertTrue(result["evidence"])
        self.assertEqual(self.db.query(Investigation).count(), 1)
        self.assertEqual(self.db.query(InvestigationEvidence).count(), len(result["evidence"]))

    def test_evidence_only_provider_does_not_make_unsourced_causal_claim(self):
        result = investigate(self.db, "ANOMALY", "ANOM-1", EvidenceOnlyProvider())
        self.assertIn("no causal conclusion", result["likely_cause"])
        self.assertIn("ANOMALY:ANOM-1", result["summary"])

    def test_insufficient_or_invalid_target_returns_none(self):
        self.assertIsNone(investigate(self.db, "ANOMALY", "MISSING", MockProvider()))
        with self.assertRaises(ValueError): collect_evidence(self.db, "INVALID", "x")

    def test_repeated_investigation_is_idempotent(self):
        first = investigate(self.db, "ANOMALY", "ANOM-1", MockProvider())
        second = investigate(self.db, "ANOMALY", "ANOM-1", MockProvider())
        self.assertEqual(first["investigation_id"], second["investigation_id"])
        self.assertEqual(self.db.query(Investigation).count(), 1)
        self.assertEqual(self.db.query(InvestigationEvidence).filter_by(investigation_id=first["investigation_id"]).count(), len(second["evidence"]))

    def test_api_handlers_retrieve_evidence_and_update_status(self):
        result = run_investigation("ANOMALY", "ANOM-1", db=self.db)
        loaded = retrieve_investigation(result["investigation_id"], db=self.db)
        evidence = retrieve_evidence(result["investigation_id"], db=self.db)
        updated = set_investigation_status(result["investigation_id"], "INVESTIGATING", db=self.db)
        self.assertEqual(loaded["investigation_id"], result["investigation_id"])
        self.assertTrue(evidence["evidence"])
        self.assertEqual(updated["status"], "INVESTIGATING")


if __name__ == "__main__": unittest.main()
