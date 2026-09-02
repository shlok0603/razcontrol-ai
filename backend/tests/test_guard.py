import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.guard import (
    get_findings_summary,
    list_control_findings,
    list_findings,
    list_transaction_findings,
    scan_financial_controls,
    set_finding_status,
)
from app.models import ControlFinding, ReconciliationMatch, Transaction
from app.db.database import Base
from app.services.control_engine import run_control_engine


class RazGuardTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine, expire_on_commit=False)()
        self.number = 0

    def tearDown(self):
        self.db.close()

    def transaction(self, amount="100.00", *, description="valid expense", when=date(2026, 9, 1), vendor="Vendor A", account="Expenses", currency="INR", transaction_type="DEBIT", source="ERP"):
        self.number += 1
        row = Transaction(transaction_id=f"TX-{self.number}", amount=Decimal(amount), description=description, transaction_date=when, vendor=vendor, account=account, currency=currency, transaction_type=transaction_type, source=source)
        self.db.add(row)
        return row

    def controls(self):
        return {item["control_id"]: item for item in run_control_engine(self.db)}

    def test_high_value_positive_and_normal_transaction_negative(self):
        high = self.transaction("100001.00")
        normal = self.transaction("123.45", vendor="Vendor B")
        findings = self.controls()

        self.assertEqual(findings["HIGH_VALUE_TRANSACTION"]["record_id"], high.transaction_id)
        self.assertNotIn(normal.transaction_id, [item.record_id for item in self.db.query(ControlFinding).all() if item.control_id == "HIGH_VALUE_TRANSACTION"])
        self.assertEqual(findings["HIGH_VALUE_TRANSACTION"]["severity"], "HIGH")
        self.assertIn("100001.00", findings["HIGH_VALUE_TRANSACTION"]["explanation"])

    def test_duplicate_control_persists_specific_evidence(self):
        first = self.transaction("500.00", description="duplicate payment", vendor="Vendor D")
        second = self.transaction("500.00", description="duplicate payment", vendor="Vendor D")
        self.controls()

        findings = self.db.query(ControlFinding).filter_by(control_id="DUPLICATE_TRANSACTION").all()
        self.assertEqual(len(findings), 2)
        first_finding = next(item for item in findings if item.record_id == first.transaction_id)
        self.assertEqual(first_finding.severity, "HIGH")
        self.assertEqual(first_finding.evidence["duplicate_transaction_ids"], [second.transaction_id])

    def test_missing_and_invalid_fields_controls(self):
        transaction = self.transaction(vendor=None, account=None, currency="inr", transaction_type="WIRE", source=None)
        self.controls()

        missing = self.db.query(ControlFinding).filter_by(control_id="MISSING_TRANSACTION_INFORMATION", record_id=transaction.transaction_id).one()
        invalid = self.db.query(ControlFinding).filter_by(control_id="INVALID_TRANSACTION_FIELDS", record_id=transaction.transaction_id).one()
        self.assertEqual(missing.evidence["missing_fields"], ["vendor", "account", "source"])
        self.assertEqual(invalid.evidence["invalid_fields"], ["currency", "transaction_type"])

    def test_weekend_and_round_amount_controls(self):
        transaction = self.transaction("20000.00", when=date(2026, 9, 5))
        self.controls()

        control_ids = {item.control_id for item in self.db.query(ControlFinding).filter_by(record_id=transaction.transaction_id)}
        self.assertTrue({"ROUND_AMOUNT", "WEEKEND_TRANSACTION"}.issubset(control_ids))

    def test_reconciliation_exception_integration(self):
        record = ReconciliationMatch(bank_transaction_id="BANK-1", transaction_id=None, confidence=Decimal("0"), amount_score=Decimal("0"), date_score=Decimal("0"), description_score=Decimal("0"), status="UNMATCHED", reason="No candidate", matched_by="RazRecon")
        self.db.add(record)
        self.controls()

        finding = self.db.query(ControlFinding).filter_by(control_id="RECONCILIATION_EXCEPTION", record_id="BANK-1").one()
        self.assertEqual(finding.record_type, "BankTransaction")
        self.assertEqual(finding.severity, "HIGH")
        self.assertEqual(finding.evidence["reconciliation_status"], "UNMATCHED")

    def test_rerun_is_idempotent(self):
        self.transaction("100001.00")
        first = run_control_engine(self.db)
        count = self.db.query(ControlFinding).count()
        second = run_control_engine(self.db)

        self.assertEqual(len(first), len(second))
        self.assertEqual(self.db.query(ControlFinding).count(), count)

    def test_resolved_finding_status_is_preserved_on_rerun(self):
        self.transaction("100001.00")
        result = run_control_engine(self.db)
        finding_id = next(item["finding_id"] for item in result if item["control_id"] == "HIGH_VALUE_TRANSACTION")
        updated = set_finding_status(finding_id, "RESOLVED", db=self.db)
        run_control_engine(self.db)

        self.assertEqual(updated["status"], "RESOLVED")
        self.assertEqual(self.db.query(ControlFinding).filter_by(finding_id=finding_id).one().status, "RESOLVED")

    def test_api_functions_return_persisted_findings_and_summary(self):
        transaction = self.transaction("100001.00")
        scan = scan_financial_controls(db=self.db)
        all_findings = list_findings(db=self.db)
        by_control = list_control_findings("HIGH_VALUE_TRANSACTION", db=self.db)
        by_transaction = list_transaction_findings(transaction.transaction_id, db=self.db)
        summary = get_findings_summary(db=self.db)

        self.assertEqual(scan["agent"], "RazGuard")
        self.assertEqual(scan["total_findings"], len(scan["findings"]))
        self.assertEqual(len(all_findings["findings"]), summary["total_findings"])
        self.assertEqual(by_control["findings"][0]["control_id"], "HIGH_VALUE_TRANSACTION")
        self.assertTrue(any(item["record_id"] == transaction.transaction_id for item in by_transaction["findings"]))


if __name__ == "__main__":
    unittest.main()
