CREATE TABLE IF NOT EXISTS investigations (
    id SERIAL PRIMARY KEY, investigation_id VARCHAR(100) NOT NULL UNIQUE,
    fingerprint VARCHAR(64) NOT NULL UNIQUE, target_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(100) NOT NULL, status VARCHAR(50) NOT NULL DEFAULT 'OPEN',
    provider VARCHAR(100) NOT NULL, summary TEXT NOT NULL, risk_assessment TEXT NOT NULL,
    likely_cause TEXT NOT NULL, conflicting_evidence JSON NOT NULL, confidence NUMERIC(5,2) NOT NULL,
    recommended_next_action TEXT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS investigation_evidence (
    id SERIAL PRIMARY KEY, investigation_id VARCHAR(100) NOT NULL,
    source_type VARCHAR(100) NOT NULL, source_id VARCHAR(100) NOT NULL,
    payload JSON NOT NULL, collected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_investigations_target ON investigations (target_type, target_id);
CREATE INDEX IF NOT EXISTS ix_investigation_evidence_investigation ON investigation_evidence (investigation_id);
