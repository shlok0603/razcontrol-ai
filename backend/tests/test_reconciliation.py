import unittest
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.agents.recon import RazReconAgent
from app.api.routes.reconciliation import run_reconciliation
from app.db.database import Base
from app.models import BankTransaction, ReconciliationMatch, Transaction
from app.services.reconciliation import reconcile_all


TODAY = date(2026, 9, 2)


class RazReconTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine, expire_on_commit=False)()
        self.counter = 0

    def tearDown(self):
        self.db.close()

    def bank(self, amount, description, *, when=TODAY):
        self.counter += 1
        row = BankTransaction(
            bank_transaction_id=f"BANK-{self.counter}",
            amount=Decimal(str(amount)),
            description=description,
            transaction_date=when,
        )
        self.db.add(row)
        return row

    def gl(self, amount, description, *, when=TODAY):
        self.counter += 1
        row = Transaction(
            transaction_id=f"GL-{self.counter}",
            amount=Decimal(str(amount)),
            description=description,
            transaction_date=when,
        )
        self.db.add(row)
        return row

    def result_for(self, bank):
        return (
            self.db.query(ReconciliationMatch)
            .filter_by(bank_transaction_id=bank.bank_transaction_id)
            .one()
        )

    def test_exact_match_is_consumed_and_persisted(self):
        bank = self.bank("100.00", "Office rent September")
        gl = self.gl("100.00", "Office rent September")
        result = reconcile_all(self.db)[0]

        record = self.result_for(bank)
        self.assertEqual(result["status"], "MATCHED")
        self.assertEqual(record.transaction_id, gl.transaction_id)
        self.assertEqual(bank.reconciliation_status, "MATCHED")
        self.assertEqual(record.confidence, Decimal("100.00"))

    def test_review_candidate_is_persisted_but_not_consumed(self):
        review_bank = self.bank("100.00", "unrelated narrative")
        gl = self.gl("100.00", "monthly settlement")
        exact_bank = self.bank("100.00", "monthly settlement")

        reconcile_all(self.db)

        review = self.result_for(review_bank)
        exact = self.result_for(exact_bank)
        self.assertEqual(review.status, "REVIEW")
        self.assertEqual(review.transaction_id, gl.transaction_id)
        self.assertEqual(exact.status, "MATCHED")
        self.assertEqual(exact.transaction_id, gl.transaction_id)

        # On a later run the now-consumed candidate is removed from the stale
        # review result rather than leaving an incorrect candidate reference.
        reconcile_all(self.db)
        review = self.result_for(review_bank)
        self.assertEqual(review.status, "UNMATCHED")
        self.assertIsNone(review.transaction_id)

    def test_low_confidence_candidate_is_unmatched_with_null_transaction(self):
        bank = self.bank("999.00", "unrelated narrative")
        self.gl("1.00", "different text")

        reconcile_all(self.db)

        record = self.result_for(bank)
        self.assertEqual(record.status, "UNMATCHED")
        self.assertIsNone(record.transaction_id)

    def test_no_candidate_is_unmatched_with_null_transaction(self):
        bank = self.bank("999.00", "no candidate")
        self.gl("999.00", "no candidate", when=TODAY + timedelta(days=6))

        reconcile_all(self.db)

        record = self.result_for(bank)
        self.assertEqual(record.status, "UNMATCHED")
        self.assertIsNone(record.transaction_id)
        self.assertEqual(record.confidence, Decimal("0.00"))

    def test_competing_banks_cannot_reuse_a_matched_gl_transaction(self):
        first = self.bank("42.00", "subscription charge")
        second = self.bank("42.00", "subscription charge")
        gl = self.gl("42.00", "subscription charge")

        reconcile_all(self.db)

        self.assertEqual(self.result_for(first).status, "MATCHED")
        self.assertEqual(self.result_for(first).transaction_id, gl.transaction_id)
        self.assertEqual(self.result_for(second).status, "UNMATCHED")
        self.assertIsNone(self.result_for(second).transaction_id)

    def test_rerun_refreshes_record_instead_of_creating_duplicates(self):
        bank = self.bank("77.00", "still unmatched")

        reconcile_all(self.db)
        reconcile_all(self.db)

        self.assertEqual(
            self.db.query(ReconciliationMatch)
            .filter_by(bank_transaction_id=bank.bank_transaction_id)
            .count(),
            1,
        )

    def test_previously_matched_gl_transaction_is_not_reused(self):
        original = self.bank("55.00", "phone bill")
        gl = self.gl("55.00", "phone bill")
        reconcile_all(self.db)
        contender = self.bank("55.00", "phone bill")

        reconcile_all(self.db)

        self.assertEqual(self.result_for(original).transaction_id, gl.transaction_id)
        self.assertEqual(self.result_for(contender).status, "UNMATCHED")
        self.assertIsNone(self.result_for(contender).transaction_id)

    def test_database_rejects_duplicate_automatic_gl_match(self):
        first = self.bank("10.00", "first")
        second = self.bank("20.00", "second")
        gl = self.gl("10.00", "first")
        self.db.add_all(
            [
                ReconciliationMatch(
                    bank_transaction_id=first.bank_transaction_id,
                    transaction_id=gl.transaction_id,
                    confidence=100,
                    amount_score=100,
                    date_score=100,
                    description_score=100,
                    status="MATCHED",
                    reason="test",
                ),
                ReconciliationMatch(
                    bank_transaction_id=second.bank_transaction_id,
                    transaction_id=gl.transaction_id,
                    confidence=100,
                    amount_score=100,
                    date_score=100,
                    description_score=100,
                    status="MATCHED",
                    reason="test",
                ),
            ]
        )

        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_api_response_matches_persisted_result(self):
        bank = self.bank("12.50", "cloud service")
        gl = self.gl("12.50", "cloud service")

        response = run_reconciliation(db=self.db)
        record = self.result_for(bank)

        self.assertEqual(response["agent"], RazReconAgent.name)
        self.assertEqual(response["total_processed"], 1)
        self.assertEqual(response["matched"], 1)
        self.assertEqual(response["results"][0]["transaction_id"], gl.transaction_id)
        self.assertEqual(response["results"][0]["status"], record.status)
        self.assertEqual(response["results"][0]["confidence"], float(record.confidence))


if __name__ == "__main__":
    unittest.main()
