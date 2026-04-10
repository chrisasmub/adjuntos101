-- Adjuntos101 - Query pack operativo
-- Ejecutar sobre el namespace USER de IRIS.

-- 1. Ultimos documentos procesados o revisados
SELECT TOP 20
    document_id,
    original_filename,
    current_status,
    received_at,
    updated_at
FROM doc_document
ORDER BY document_id DESC;

-- 2. Bandeja Review con detalle normalizado
SELECT
    d.document_id,
    d.original_filename,
    d.received_at,
    n.document_type,
    n.issuer_name,
    n.issue_date,
    n.currency,
    n.total_amount,
    n.confidence,
    n.normalized_json_path
FROM doc_document d
LEFT JOIN doc_normalized n
    ON n.document_id = d.document_id
WHERE d.current_status = 'REVIEW'
ORDER BY d.document_id DESC;

-- 3. Errores abiertos con contexto
SELECT
    d.document_id,
    d.original_filename,
    d.current_status,
    e.stage,
    e.severity,
    e.reason_code,
    e.reason_detail,
    e.opened_at
FROM doc_exception e
JOIN doc_document d
    ON d.document_id = e.document_id
WHERE e.closed_at IS NULL
ORDER BY e.opened_at DESC;

-- 4. Ultimos eventos por documento
SELECT TOP 50
    event_id,
    document_id,
    event_ts,
    stage,
    event_type,
    message
FROM doc_event
ORDER BY event_id DESC;

-- 5. Intentos recientes de parse
SELECT TOP 20
    p.parse_attempt_id,
    p.document_id,
    d.original_filename,
    p.provider,
    p.provider_job_id,
    p.provider_tier,
    p.outcome,
    p.started_at,
    p.completed_at
FROM doc_parse_attempt p
JOIN doc_document d
    ON d.document_id = p.document_id
ORDER BY p.parse_attempt_id DESC;

-- 6. Volumen diario por estado
SELECT
    CAST(received_at AS DATE) AS received_date,
    current_status,
    COUNT(*) AS document_count
FROM doc_document
GROUP BY CAST(received_at AS DATE), current_status
ORDER BY received_date DESC, current_status;

-- 7. Volumen diario por tipo documental
SELECT
    CAST(d.received_at AS DATE) AS received_date,
    n.document_type,
    COUNT(*) AS document_count
FROM doc_document d
JOIN doc_normalized n
    ON n.document_id = d.document_id
GROUP BY CAST(d.received_at AS DATE), n.document_type
ORDER BY received_date DESC, n.document_type;

-- 8. Historial detallado de un documento
-- Reemplazar ? por el document_id deseado.
SELECT
    d.document_id,
    d.original_filename,
    d.current_status,
    d.archive_path,
    n.document_type,
    n.issuer_name,
    n.issue_date,
    n.currency,
    n.total_amount,
    p.provider,
    p.provider_job_id,
    p.outcome
FROM doc_document d
LEFT JOIN doc_normalized n
    ON n.document_id = d.document_id
LEFT JOIN doc_parse_attempt p
    ON p.document_id = d.document_id
WHERE d.document_id = ?
ORDER BY p.parse_attempt_id DESC;
