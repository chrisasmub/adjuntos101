CREATE TABLE doc_document (
    document_id BIGINT IDENTITY NOT NULL,
    attachment_hash VARCHAR(64) NOT NULL,
    original_filename VARCHAR(512) NOT NULL,
    source_path VARCHAR(1024) NOT NULL,
    archive_path VARCHAR(1024),
    mime_type VARCHAR(255),
    file_size_bytes BIGINT NOT NULL,
    source_email VARCHAR(512),
    source_subject VARCHAR(512),
    received_at TIMESTAMP NOT NULL,
    current_status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    PRIMARY KEY (document_id),
    CONSTRAINT uq_doc_document_hash UNIQUE (attachment_hash)
);

CREATE TABLE doc_parse_attempt (
    parse_attempt_id BIGINT IDENTITY NOT NULL,
    document_id BIGINT NOT NULL,
    provider VARCHAR(64) NOT NULL,
    provider_job_id VARCHAR(255),
    provider_tier VARCHAR(64),
    provider_version VARCHAR(64),
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    outcome VARCHAR(32) NOT NULL,
    raw_json_path VARCHAR(1024),
    raw_markdown_path VARCHAR(1024),
    error_code VARCHAR(64),
    error_message VARCHAR(2048),
    PRIMARY KEY (parse_attempt_id),
    CONSTRAINT fk_doc_parse_attempt_document
        FOREIGN KEY (document_id) REFERENCES doc_document (document_id)
);

CREATE TABLE doc_normalized (
    document_id BIGINT NOT NULL,
    document_type VARCHAR(64) NOT NULL,
    issuer_name VARCHAR(255),
    issuer_tax_id VARCHAR(64),
    issue_date DATE,
    due_date DATE,
    period_from DATE,
    period_to DATE,
    currency VARCHAR(16),
    total_amount NUMERIC(18, 2),
    balance_amount NUMERIC(18, 2),
    account_ref_last4 VARCHAR(8),
    document_number VARCHAR(128),
    confidence DOUBLE,
    review_required BIT NOT NULL,
    normalized_json_path VARCHAR(1024),
    PRIMARY KEY (document_id),
    CONSTRAINT fk_doc_normalized_document
        FOREIGN KEY (document_id) REFERENCES doc_document (document_id)
);

CREATE TABLE doc_exception (
    exception_id BIGINT IDENTITY NOT NULL,
    document_id BIGINT NOT NULL,
    stage VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    reason_code VARCHAR(64) NOT NULL,
    reason_detail VARCHAR(2048),
    opened_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP,
    resolution_note VARCHAR(2048),
    PRIMARY KEY (exception_id),
    CONSTRAINT fk_doc_exception_document
        FOREIGN KEY (document_id) REFERENCES doc_document (document_id)
);

CREATE TABLE doc_event (
    event_id BIGINT IDENTITY NOT NULL,
    document_id BIGINT NOT NULL,
    event_ts TIMESTAMP NOT NULL,
    stage VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    message VARCHAR(2048),
    PRIMARY KEY (event_id),
    CONSTRAINT fk_doc_event_document
        FOREIGN KEY (document_id) REFERENCES doc_document (document_id)
);

CREATE INDEX idx_doc_document_status ON doc_document (current_status);
CREATE INDEX idx_doc_document_received_at ON doc_document (received_at);
CREATE INDEX idx_doc_normalized_document_type ON doc_normalized (document_type);
CREATE INDEX idx_doc_normalized_issue_date ON doc_normalized (issue_date);
CREATE INDEX idx_doc_normalized_period_to ON doc_normalized (period_to);
CREATE INDEX idx_doc_normalized_issuer_name ON doc_normalized (issuer_name);
CREATE INDEX idx_doc_exception_opened_at ON doc_exception (opened_at);
CREATE INDEX idx_doc_exception_severity ON doc_exception (severity);
CREATE INDEX idx_doc_exception_stage ON doc_exception (stage);

