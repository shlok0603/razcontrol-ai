CREATE TABLE IF NOT EXISTS financial_controls (
    id SERIAL PRIMARY KEY,
    control_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    default_severity VARCHAR(50) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    rule_definition JSON NOT NULL,
    detection_logic VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS control_findings (
    id SERIAL PRIMARY KEY,
    finding_id VARCHAR(100) NOT NULL UNIQUE,
    fingerprint VARCHAR(64) NOT NULL UNIQUE,
    control_id VARCHAR(100) NOT NULL,
    record_type VARCHAR(100) NOT NULL,
    record_id VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'OPEN',
    severity VARCHAR(50) NOT NULL,
    evidence JSON NOT NULL,
    explanation TEXT NOT NULL,
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_control_findings_control_id ON control_findings (control_id);
CREATE INDEX IF NOT EXISTS ix_control_findings_record_id ON control_findings (record_id);
