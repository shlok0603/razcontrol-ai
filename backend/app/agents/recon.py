from sqlalchemy.orm import Session

from app.services.reconciliation import reconcile_all


class RazReconAgent:
    """
    RazRecon is responsible for automatically
    reconciling bank transactions against GL records.
    """

    name = "RazRecon"

    def run(self, db: Session):

        results = reconcile_all(db)

        matched = sum(
            1
            for result in results
            if result["status"] == "MATCHED"
        )

        review = sum(
            1
            for result in results
            if result["status"] == "REVIEW"
        )

        unmatched = sum(
            1
            for result in results
            if result["status"] == "UNMATCHED"
        )

        return {
            "agent": self.name,
            "total_processed": len(results),
            "matched": matched,
            "review_required": review,
            "unmatched": unmatched,
            "results": results,
        }