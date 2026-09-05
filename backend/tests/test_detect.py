import unittest
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.detect import get_anomaly_summary, list_anomalies, list_transaction_anomalies, run_detection
from app.db.database import Base
from app.models import Anomaly, ControlFinding, Transaction
from app.services.anomaly_detection import detect_anomalies, engineer_features, score_features


class RazDetectTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine, expire_on_commit=False)()
        self.number = 0

    def tearDown(self):
        self.db.close()

    def transaction(self, amount, day, *, account="Expenses"):
        self.number += 1
        row = Transaction(transaction_id=f"TX-{self.number}", transaction_date=day, description="service cost", vendor="Vendor", account=account, amount=Decimal(str(amount)), currency="INR", transaction_type="DEBIT", source="ERP")
        self.db.add(row)
        return row

    def historical_series(self, outlier=10000):
        start = date(2026, 1, 1)
        for index in range(6): self.transaction(100, start + timedelta(days=index))
        return self.transaction(outlier, start + timedelta(days=6))

    def test_normal_transactions_do_not_create_anomalies(self):
        self.historical_series(outlier=100)
        self.assertEqual(detect_anomalies(self.db), [])
        self.assertEqual(self.db.query(Anomaly).count(), 0)

    def test_iqr_outlier_has_normalized_high_score_and_reason(self):
        outlier = self.historical_series()
        anomalies = detect_anomalies(self.db)

        self.assertEqual(len(anomalies), 1)
        anomaly = anomalies[0]
        self.assertEqual(anomaly["transaction_id"], outlier.transaction_id)
        self.assertGreaterEqual(anomaly["risk_score"], 80)
        self.assertLessEqual(anomaly["risk_score"], 100)
        self.assertEqual(anomaly["severity"], "HIGH")
        self.assertIn("historical IQR range", anomaly["explanation"])
        self.assertEqual(anomaly["detection_method"], "HISTORICAL_IQR_V1")

    def test_features_use_prior_history_only(self):
        outlier = self.historical_series()
        features = dict(engineer_features(self.db.query(Transaction).order_by(Transaction.transaction_date).all()))[outlier]
        score, reason, _ = score_features(features)
        self.assertEqual(features["history_count"], 6)
        self.assertGreaterEqual(score, 80)
        self.assertIsNotNone(reason)

    def test_guard_finding_is_explicit_score_modifier(self):
        outlier = self.historical_series()
        self.db.add(ControlFinding(finding_id="CF-1", fingerprint="f" * 64, control_id="HIGH_VALUE_TRANSACTION", record_type="Transaction", record_id=outlier.transaction_id, status="OPEN", severity="HIGH", evidence={}, explanation="Above threshold"))
        self.db.commit()

        anomaly = detect_anomalies(self.db)[0]
        modifier = anomaly["evidence"]["modifiers"][0]
        self.assertEqual(modifier["source"], "RazGuard")
        self.assertEqual(modifier["score_adjustment"], 10.0)
        self.assertEqual(anomaly["risk_score"], 100.0)

    def test_rerun_deduplicates_persisted_anomaly(self):
        self.historical_series()
        first = detect_anomalies(self.db)
        second = detect_anomalies(self.db)
        self.assertEqual(len(first), len(second))
        self.assertEqual(self.db.query(Anomaly).count(), 1)
        self.assertEqual(first[0]["anomaly_id"], second[0]["anomaly_id"])

    def test_api_handlers_filter_and_summarize_anomalies(self):
        outlier = self.historical_series()
        response = run_detection(db=self.db)
        listed = list_anomalies(severity="HIGH", db=self.db)
        by_transaction = list_transaction_anomalies(outlier.transaction_id, db=self.db)
        summary = get_anomaly_summary(db=self.db)

        self.assertEqual(response["agent"], "RazDetect")
        self.assertEqual(response["total_detected"], 1)
        self.assertEqual(len(listed["anomalies"]), 1)
        self.assertEqual(by_transaction["anomalies"][0]["transaction_id"], outlier.transaction_id)
        self.assertEqual(summary["total_anomalies"], 1)

    def test_api_handler_limits_anomaly_results(self):
        first = self.historical_series()
        self.transaction(20000, date(2026, 2, 1), account="Other")
        detect_anomalies(self.db)

        listed = list_anomalies(limit=1, db=self.db)

        self.assertEqual(len(listed["anomalies"]), 1)
        self.assertEqual(listed["anomalies"][0]["transaction_id"], first.transaction_id)


if __name__ == "__main__":
    unittest.main()
