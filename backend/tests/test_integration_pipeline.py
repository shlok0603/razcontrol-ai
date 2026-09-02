import unittest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.pipeline import run_end_to_end_pipeline
from app.db.database import Base
from app.models import Anomaly, BankTransaction, ControlFinding, Investigation, ReconciliationMatch, Transaction
from app.services.pipeline import run_pipeline


class RazControlIntegrationTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine, expire_on_commit=False)()
        self.number = 0

    def tearDown(self): self.db.close()

    def transaction(self, amount, when, description="expense", account="Expense"):
        self.number += 1
        row = Transaction(transaction_id=f"GL-{self.number}", transaction_date=when, description=description, vendor="Vendor", account=account, amount=Decimal(str(amount)), currency="INR", transaction_type="DEBIT", source="ERP")
        self.db.add(row)
        return row

    def bank(self, amount, when, description):
        self.number += 1
        row = BankTransaction(bank_transaction_id=f"BANK-{self.number}", transaction_date=when, description=description, amount=Decimal(str(amount)), currency="INR", transaction_type="DEBIT", reconciliation_status="UNMATCHED")
        self.db.add(row)
        return row

    def build_risky_data(self):
        start = date(2026, 1, 5)
        history = [self.transaction(100, start + timedelta(days=index), "regular expense") for index in range(6)]
        outlier = self.transaction(100001, start + timedelta(days=6), "high expense")
        self.transaction(500, start + timedelta(days=7), "duplicate expense")
        self.transaction(500, start + timedelta(days=7), "duplicate expense")
        matched_bank = self.bank(100001, outlier.transaction_date, "high expense")
        review_bank = self.bank(500, start + timedelta(days=7), "different bank narrative")
        unmatched_bank = self.bank(9000, start + timedelta(days=7), "no GL candidate")
        self.db.commit()
        return outlier, matched_bank, review_bank, unmatched_bank

    def test_end_to_end_pipeline_processes_all_modules(self):
        outlier, matched, review, unmatched = self.build_risky_data()
        result = run_pipeline(self.db)

        self.assertEqual(result["status"], "COMPLETED")
        statuses = {item.bank_transaction_id: item.status for item in self.db.query(ReconciliationMatch).all()}
        self.assertEqual(statuses[matched.bank_transaction_id], "MATCHED")
        self.assertEqual(statuses[review.bank_transaction_id], "REVIEW")
        self.assertEqual(statuses[unmatched.bank_transaction_id], "UNMATCHED")
        self.assertGreater(self.db.query(ControlFinding).count(), 0)
        self.assertEqual(self.db.query(Anomaly).filter_by(transaction_id=outlier.transaction_id).count(), 1)
        self.assertGreater(self.db.query(Investigation).count(), 0)
        self.assertEqual(result["results"]["report"]["summary"]["overall_risk"], "HIGH")

    def test_clean_dataset_and_api_have_no_findings(self):
        result = run_end_to_end_pipeline(investigate_high_risk=True, db=self.db)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["results"]["report"]["summary"]["overall_risk"], "LOW")
        self.assertEqual(self.db.query(Anomaly).count(), 0)
        self.assertEqual(self.db.query(Investigation).count(), 0)

    def test_rerunning_pipeline_is_idempotent(self):
        self.build_risky_data()
        run_pipeline(self.db)
        counts = (self.db.query(ReconciliationMatch).count(), self.db.query(ControlFinding).count(), self.db.query(Anomaly).count(), self.db.query(Investigation).count())
        second = run_pipeline(self.db)
        self.assertEqual(second["status"], "COMPLETED")
        self.assertEqual((self.db.query(ReconciliationMatch).count(), self.db.query(ControlFinding).count(), self.db.query(Anomaly).count(), self.db.query(Investigation).count()), counts)

    def test_guard_failure_is_observable_and_later_stages_continue(self):
        self.build_risky_data()
        with patch("app.services.pipeline.RazGuardAgent.run", side_effect=RuntimeError("guard unavailable")):
            result = run_pipeline(self.db, investigate_high_risk=False)
        failed = next(item for item in result["stages"] if item["stage"] == "RazGuard")
        self.assertEqual(result["status"], "PARTIAL_FAILURE")
        self.assertEqual(failed["status"], "FAILED")
        self.assertEqual(self.db.query(ReconciliationMatch).count(), 3)
        self.assertIsNotNone(result["results"]["report"])

    def test_investigation_failure_does_not_rollback_prior_modules(self):
        self.build_risky_data()
        with patch("app.services.pipeline.RazInvestigateAgent.run", side_effect=RuntimeError("provider unavailable")):
            result = run_pipeline(self.db)
        investigation_stage = next(item for item in result["stages"] if item["stage"] == "RazInvestigate")
        self.assertEqual(result["status"], "PARTIAL_FAILURE")
        self.assertGreater(investigation_stage["failed"], 0)
        self.assertGreater(self.db.query(ControlFinding).count(), 0)
        self.assertGreater(self.db.query(Anomaly).count(), 0)
        self.assertEqual(self.db.query(Investigation).count(), 0)


if __name__ == "__main__": unittest.main()
