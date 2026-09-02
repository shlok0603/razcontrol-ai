-- Apply after verifying that the query below returns no rows.  It deliberately
-- does not delete or alter source transaction data.
--
-- SELECT transaction_id, COUNT(*)
-- FROM reconciliation_matches
-- WHERE status = 'MATCHED' AND transaction_id IS NOT NULL
-- GROUP BY transaction_id
-- HAVING COUNT(*) > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_reconciliation_matches_matched_transaction
    ON reconciliation_matches (transaction_id)
    WHERE status = 'MATCHED' AND transaction_id IS NOT NULL;
