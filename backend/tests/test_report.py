import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.report import export_csv, get_finding, get_overall_report, get_report_summary, get_transaction_risk
from app.db.database import Base
from app.models import Anomaly, ControlFinding, Investigation, Transaction
from app.services.reporting import finding_details, overall_report, report_csv, report_summary, transaction_risk_report


class RazReportTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine, expire_on_commit=False)()

    def tearDown(self): self.db.close()

    def add_populated_records(self):
        transaction = Transaction(transaction_id="TX-1", transaction_date=date(2026, 1, 1), description="expense", vendor="Vendor", account="Expense", amount=Decimal("5000"), currency="INR", transaction_type="DEBIT", source="ERP")
        control = ControlFinding(finding_id="CF-1", fingerprint="c" * 64, control_id="HIGH_VALUE_TRANSACTION", record_type="Transaction", record_id="TX-1", status="OPEN", severity="HIGH", evidence={"amount": 5000}, explanation="Above threshold")
        anomaly = Anomaly(anomaly_id="ANOM-1", fingerprint="a" * 64, transaction_id="TX-1", anomaly_type="AMOUNT_IQR_DEVIATION", risk_score=Decimal("90"), severity="HIGH", explanation="Outside historical range", evidence={"upper_bound": 200}, status="OPEN", detected_by="RazDetect", detection_method="HISTORICAL_IQR_V1")
        investigation = Investigation(investigation_id="INV-1", fingerprint="i" * 64, target_type="ANOMALY", target_id="ANOM-1", status="REVIEW_REQUIRED", provider="evidence_only", summary="Review", risk_assessment="High", likely_cause="Unknown", conflicting_evidence=[], confidence=Decimal(".4"), recommended_next_action="Request documents")
        self.db.add_all([transaction, control, anomaly, investigation]); self.db.commit()

    def test_empty_dataset_summary(self):
        summary = report_summary(self.db)
        self.assertEqual(summary["total_transactions"], 0)
        self.assertEqual(summary["high_risk_findings"], 0)
        self.assertEqual(summary["overall_risk"], "LOW")

    def test_aggregation_and_finding_details(self):
        self.add_populated_records()
        report = overall_report(self.db)
        details = finding_details(self.db)
        self.assertEqual(report["summary"]["total_transactions"], 1)
        self.assertEqual(report["summary"]["high_risk_findings"], 2)
        self.assertEqual(report["summary"]["overall_risk"], "HIGH")
        anomaly = next(item for item in details if item["finding_id"] == "ANOM-1")
        self.assertEqual(anomaly["investigation_status"], "REVIEW_REQUIRED")
        self.assertEqual(anomaly["recommended_action"], "Request documents")

    def test_transaction_risk_and_finding_lookup(self):
        self.add_populated_records()
        transaction = transaction_risk_report(self.db, "TX-1")
        missing = transaction_risk_report(self.db, "MISSING")
        self.assertEqual(transaction["risk"], "HIGH")
        self.assertTrue(transaction["transaction_exists"])
        self.assertEqual(len(transaction["findings"]), 2)
        self.assertFalse(missing["transaction_exists"])

    def test_csv_export_contains_verified_finding_rows(self):
        self.add_populated_records()
        csv_text = report_csv(self.db)
        self.assertIn("finding_id,source", csv_text)
        self.assertIn("ANOM-1", csv_text)
        self.assertIn("CF-1", csv_text)

    def test_large_dataset_counts_without_invented_findings(self):
        self.db.add_all([Transaction(transaction_id=f"TX-{index}", transaction_date=date(2026, 1, 1), description="normal", vendor="Vendor", account="Expense", amount=Decimal("10"), currency="INR", transaction_type="DEBIT", source="ERP") for index in range(500)])
        self.db.commit()
        summary = report_summary(self.db)
        self.assertEqual(summary["total_transactions"], 500)
        self.assertEqual(summary["high_risk_findings"], 0)

    def test_api_handlers_and_csv_response(self):
        self.add_populated_records()
        overall = get_overall_report(db=self.db)
        summary = get_report_summary(db=self.db)
        finding = get_finding("ANOM-1", db=self.db)
        transaction = get_transaction_risk("TX-1", db=self.db)
        csv_response = export_csv(db=self.db)
        self.assertEqual(overall["agent"], "RazReport")
        self.assertEqual(summary["overall_risk"], "HIGH")
        self.assertEqual(finding["finding_id"], "ANOM-1")
        self.assertEqual(transaction["risk"], "HIGH")
        self.assertEqual(csv_response.media_type, "text/csv")
        self.assertIn(b"ANOM-1", csv_response.body)


if __name__ == "__main__": unittest.main()
