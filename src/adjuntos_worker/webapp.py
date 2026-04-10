import argparse
import html
import json
from datetime import date, datetime
from typing import Dict, List, Optional
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from adjuntos_worker.config import AppConfig, load_config


def _require_iris_connection(config: AppConfig):
    if config.database.mode != "iris":
        raise RuntimeError("The web app currently supports only DATABASE_MODE=iris.")

    try:
        import iris  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "The intersystems-irispython package is required to run the web app."
        ) from exc

    return iris.connect(config.database.dsn, config.database.username, config.database.password)


class IrisReadModel:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def summary_counts(self) -> Dict[str, int]:
        connection = _require_iris_connection(self.config)
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                SELECT current_status, COUNT(*)
                  FROM doc_document
                 GROUP BY current_status
                """
            )
            counts = {"ALL": 0}
            for status, count in cursor.fetchall():
                counts[str(status)] = int(count)
                counts["ALL"] += int(count)
            return counts
        finally:
            cursor.close()
            connection.close()

    def list_documents(self, status: str = "", query: str = "", limit: int = 50) -> List[dict]:
        connection = _require_iris_connection(self.config)
        cursor = connection.cursor()
        try:
            sql = """
                SELECT TOP {limit}
                    d.document_id,
                    d.original_filename,
                    d.current_status,
                    d.received_at,
                    d.updated_at,
                    d.archive_path,
                    n.document_type,
                    n.issuer_name,
                    n.issue_date,
                    n.currency,
                    n.total_amount,
                    n.review_required
                  FROM doc_document d
             LEFT JOIN doc_normalized n
                    ON n.document_id = d.document_id
            """.format(limit=max(1, min(limit, 200)))
            params: List[object] = []
            filters: List[str] = []

            if status:
                filters.append("d.current_status = ?")
                params.append(status)
            if query:
                filters.append(
                    "(UPPER(d.original_filename) LIKE ? OR UPPER(COALESCE(n.issuer_name, '')) LIKE ? OR UPPER(COALESCE(n.document_type, '')) LIKE ?)"
                )
                needle = "%" + query.upper() + "%"
                params.extend([needle, needle, needle])

            if filters:
                sql += " WHERE " + " AND ".join(filters)
            sql += " ORDER BY d.document_id DESC"

            cursor.execute(sql, tuple(params))
            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "document_id": int(row[0]),
                        "original_filename": str(row[1]),
                        "current_status": str(row[2]),
                        "received_at": row[3],
                        "updated_at": row[4],
                        "archive_path": None if row[5] is None else str(row[5]),
                        "document_type": None if row[6] is None else str(row[6]),
                        "issuer_name": None if row[7] is None else str(row[7]),
                        "issue_date": row[8],
                        "currency": None if row[9] is None else str(row[9]),
                        "total_amount": row[10],
                        "review_required": None if row[11] is None else bool(row[11]),
                    }
                )
            return results
        finally:
            cursor.close()
            connection.close()

    def get_document_detail(self, document_id: int) -> Optional[dict]:
        connection = _require_iris_connection(self.config)
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    d.document_id,
                    d.attachment_hash,
                    d.original_filename,
                    d.source_path,
                    d.archive_path,
                    d.mime_type,
                    d.file_size_bytes,
                    d.received_at,
                    d.current_status,
                    n.document_type,
                    n.issuer_name,
                    n.issuer_tax_id,
                    n.issue_date,
                    n.due_date,
                    n.period_from,
                    n.period_to,
                    n.currency,
                    n.total_amount,
                    n.balance_amount,
                    n.account_ref_last4,
                    n.document_number,
                    n.confidence,
                    n.review_required,
                    n.normalized_json_path
                  FROM doc_document d
             LEFT JOIN doc_normalized n
                    ON n.document_id = d.document_id
                 WHERE d.document_id = ?
                """,
                (document_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            row = tuple(row)

            detail = {
                "document_id": int(row[0]),
                "attachment_hash": str(row[1]),
                "original_filename": str(row[2]),
                "source_path": str(row[3]),
                "archive_path": None if row[4] is None else str(row[4]),
                "mime_type": "" if row[5] is None else str(row[5]),
                "file_size_bytes": int(row[6]),
                "received_at": row[7],
                "current_status": str(row[8]),
                "document_type": None if row[9] is None else str(row[9]),
                "issuer_name": None if row[10] is None else str(row[10]),
                "issuer_tax_id": None if row[11] is None else str(row[11]),
                "issue_date": row[12],
                "due_date": row[13],
                "period_from": row[14],
                "period_to": row[15],
                "currency": None if row[16] is None else str(row[16]),
                "total_amount": row[17],
                "balance_amount": row[18],
                "account_ref_last4": None if row[19] is None else str(row[19]),
                "document_number": None if row[20] is None else str(row[20]),
                "confidence": row[21],
                "review_required": None if row[22] is None else bool(row[22]),
                "normalized_json_path": None if row[23] is None else str(row[23]),
                "parse_attempts": self._fetch_parse_attempts(cursor, document_id),
                "events": self._fetch_events(cursor, document_id),
                "exceptions": self._fetch_exceptions(cursor, document_id),
                "normalized_json": self._load_json_file(None if row[23] is None else str(row[23])),
            }
            return detail
        finally:
            cursor.close()
            connection.close()

    def _fetch_parse_attempts(self, cursor, document_id: int) -> List[dict]:
        cursor.execute(
            """
            SELECT
                parse_attempt_id,
                provider,
                provider_job_id,
                provider_tier,
                provider_version,
                started_at,
                completed_at,
                outcome,
                raw_json_path,
                raw_markdown_path,
                error_code,
                error_message
              FROM doc_parse_attempt
             WHERE document_id = ?
             ORDER BY parse_attempt_id DESC
            """,
            (document_id,),
        )
        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "parse_attempt_id": int(row[0]),
                    "provider": str(row[1]),
                    "provider_job_id": "" if row[2] is None else str(row[2]),
                    "provider_tier": "" if row[3] is None else str(row[3]),
                    "provider_version": "" if row[4] is None else str(row[4]),
                    "started_at": row[5],
                    "completed_at": row[6],
                    "outcome": str(row[7]),
                    "raw_json_path": None if row[8] is None else str(row[8]),
                    "raw_markdown_path": None if row[9] is None else str(row[9]),
                    "error_code": None if row[10] is None else str(row[10]),
                    "error_message": None if row[11] is None else str(row[11]),
                }
            )
        return results

    def _fetch_events(self, cursor, document_id: int) -> List[dict]:
        cursor.execute(
            """
            SELECT event_id, event_ts, stage, event_type, message
              FROM doc_event
             WHERE document_id = ?
             ORDER BY event_id DESC
            """,
            (document_id,),
        )
        return [
            {
                "event_id": int(row[0]),
                "event_ts": row[1],
                "stage": str(row[2]),
                "event_type": str(row[3]),
                "message": "" if row[4] is None else str(row[4]),
            }
            for row in cursor.fetchall()
        ]

    def _fetch_exceptions(self, cursor, document_id: int) -> List[dict]:
        cursor.execute(
            """
            SELECT exception_id, stage, severity, reason_code, reason_detail, opened_at, closed_at, resolution_note
              FROM doc_exception
             WHERE document_id = ?
             ORDER BY exception_id DESC
            """,
            (document_id,),
        )
        return [
            {
                "exception_id": int(row[0]),
                "stage": str(row[1]),
                "severity": str(row[2]),
                "reason_code": str(row[3]),
                "reason_detail": "" if row[4] is None else str(row[4]),
                "opened_at": row[5],
                "closed_at": row[6],
                "resolution_note": "" if row[7] is None else str(row[7]),
            }
            for row in cursor.fetchall()
        ]

    def _load_json_file(self, path: Optional[str]) -> Optional[dict]:
        if not path:
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return "{0:.2f}".format(value)
    return str(value)


def _esc(value) -> str:
    return html.escape(_fmt(value))


def _status_class(status: str) -> str:
    normalized = (status or "").upper()
    if normalized == "PROCESSED":
        return "ok"
    if normalized == "REVIEW":
        return "warn"
    if normalized == "ERROR":
        return "err"
    if normalized == "DUPLICATE":
        return "dup"
    return "neutral"


def _layout(title: str, body: str) -> bytes:
    page = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --paper: #fffdf8;
      --ink: #1f1a17;
      --muted: #6f635a;
      --line: #ded4c8;
      --accent: #a33f2f;
      --accent-soft: #f2ddd6;
      --ok: #1f6b4f;
      --ok-soft: #dcefe6;
      --warn: #8a5a14;
      --warn-soft: #f5e9cc;
      --err: #8f2d2d;
      --err-soft: #f5d9d9;
      --dup: #5f4d8a;
      --dup-soft: #e7dff7;
      --shadow: 0 12px 32px rgba(31, 26, 23, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(163, 63, 47, 0.08), transparent 28%),
        radial-gradient(circle at bottom right, rgba(31, 107, 79, 0.08), transparent 32%),
        var(--bg);
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .shell {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 60px; }}
    .hero {{
      background: linear-gradient(135deg, rgba(255,253,248,0.96), rgba(247,239,228,0.96));
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      padding: 28px;
      margin-bottom: 22px;
    }}
    .hero h1 {{ margin: 0 0 8px; font-size: 2rem; }}
    .hero p {{ margin: 0; color: var(--muted); }}
    .grid {{ display: grid; gap: 16px; }}
    .stats {{ grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); margin: 18px 0 0; }}
    .card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: var(--shadow);
      padding: 18px;
    }}
    .stat-label {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 8px; }}
    .stat-value {{ font-size: 1.8rem; font-weight: bold; }}
    .toolbar {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: end;
      margin-bottom: 18px;
    }}
    .field {{ display: flex; flex-direction: column; gap: 6px; min-width: 180px; }}
    label {{ font-size: 0.85rem; color: var(--muted); }}
    input, select {{
      border: 1px solid var(--line);
      background: white;
      border-radius: 12px;
      padding: 10px 12px;
      font: inherit;
      color: var(--ink);
    }}
    button {{
      border: 0;
      border-radius: 12px;
      padding: 11px 16px;
      background: var(--accent);
      color: white;
      font: inherit;
      cursor: pointer;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      text-align: left;
      padding: 12px 10px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-size: 0.85rem; font-weight: normal; }}
    .pill {{
      display: inline-block;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 0.78rem;
      font-weight: bold;
      letter-spacing: 0.03em;
    }}
    .pill.ok {{ background: var(--ok-soft); color: var(--ok); }}
    .pill.warn {{ background: var(--warn-soft); color: var(--warn); }}
    .pill.err {{ background: var(--err-soft); color: var(--err); }}
    .pill.dup {{ background: var(--dup-soft); color: var(--dup); }}
    .pill.neutral {{ background: #ece7df; color: #5c5149; }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .meta-item {{
      background: rgba(255,255,255,0.75);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
    }}
    .meta-item strong {{ display: block; font-size: 0.8rem; color: var(--muted); margin-bottom: 6px; }}
    pre {{
      background: #201b18;
      color: #f8efe4;
      padding: 16px;
      border-radius: 16px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .section-title {{ margin: 0 0 12px; font-size: 1.1rem; }}
    .spacer {{ height: 10px; }}
    @media (max-width: 720px) {{
      .hero h1 {{ font-size: 1.6rem; }}
      th:nth-child(5), td:nth-child(5),
      th:nth-child(6), td:nth-child(6) {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    {body}
  </div>
</body>
</html>
""".format(title=html.escape(title), body=body)
    return page.encode("utf-8")


def _render_dashboard(read_model: IrisReadModel, params: Dict[str, List[str]]) -> bytes:
    status = params.get("status", [""])[0].strip().upper()
    query = params.get("q", [""])[0].strip()
    limit = _parse_limit(params.get("limit", ["50"])[0])
    counts = read_model.summary_counts()
    documents = read_model.list_documents(status=status, query=query, limit=limit)

    stats = "".join(
        """
        <div class="card">
          <div class="stat-label">{label}</div>
          <div class="stat-value">{value}</div>
        </div>
        """.format(label=_esc(label), value=_esc(value))
        for label, value in (
            ("Total", counts.get("ALL", 0)),
            ("Processed", counts.get("PROCESSED", 0)),
            ("Review", counts.get("REVIEW", 0)),
            ("Error", counts.get("ERROR", 0)),
        )
    )

    rows = "".join(
        """
        <tr>
          <td><a href="/documents/{document_id}">#{document_id}</a></td>
          <td><a href="/documents/{document_id}">{filename}</a></td>
          <td><span class="pill {status_class}">{status}</span></td>
          <td>{document_type}</td>
          <td>{issuer_name}</td>
          <td>{issue_date}</td>
          <td>{currency}</td>
          <td>{total_amount}</td>
        </tr>
        """.format(
            document_id=_esc(document["document_id"]),
            filename=_esc(document["original_filename"]),
            status_class=_status_class(document["current_status"]),
            status=_esc(document["current_status"]),
            document_type=_esc(document["document_type"]),
            issuer_name=_esc(document["issuer_name"]),
            issue_date=_esc(document["issue_date"]),
            currency=_esc(document["currency"]),
            total_amount=_esc(document["total_amount"]),
        )
        for document in documents
    )
    if not rows:
        rows = '<tr><td colspan="8">No hay documentos para ese filtro.</td></tr>'

    body = """
    <section class="hero">
      <h1>Adjuntos101 Console</h1>
      <p>Consulta operativa sobre IRIS para documentos, parseos, eventos y excepciones.</p>
      <div class="grid stats">{stats}</div>
    </section>
    <section class="card">
      <form class="toolbar" method="get" action="/">
        <div class="field">
          <label>Estado</label>
          <select name="status">
            {status_options}
          </select>
        </div>
        <div class="field">
          <label>Buscar</label>
          <input type="text" name="q" value="{query}" placeholder="archivo, emisor o tipo">
        </div>
        <div class="field">
          <label>Limite</label>
          <input type="number" min="1" max="200" name="limit" value="{limit}">
        </div>
        <button type="submit">Filtrar</button>
      </form>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Archivo</th>
            <th>Estado</th>
            <th>Tipo</th>
            <th>Emisor</th>
            <th>Fecha</th>
            <th>Moneda</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """.format(
        stats=stats,
        status_options=_status_options(status),
        query=html.escape(query),
        limit=_esc(limit),
        rows=rows,
    )
    return _layout("Adjuntos101 Console", body)


def _status_options(selected: str) -> str:
    statuses = ["", "PROCESSED", "REVIEW", "ERROR", "PARSING", "VALIDATED", "CLAIMED"]
    labels = {"": "Todos"}
    return "".join(
        '<option value="{value}"{selected}>{label}</option>'.format(
            value=html.escape(status),
            selected=' selected="selected"' if status == selected else "",
            label=html.escape(labels.get(status, status)),
        )
        for status in statuses
    )


def _render_document_detail(read_model: IrisReadModel, document_id: int) -> bytes:
    detail = read_model.get_document_detail(document_id)
    if detail is None:
        return _layout(
            "Documento no encontrado",
            '<section class="hero"><h1>Documento no encontrado</h1><p><a href="/">Volver al listado</a></p></section>',
        )

    meta_items = "".join(
        """
        <div class="meta-item">
          <strong>{label}</strong>
          <div>{value}</div>
        </div>
        """.format(label=_esc(label), value=_esc(value))
        for label, value in (
            ("Archivo", detail["original_filename"]),
            ("Estado", detail["current_status"]),
            ("Tipo", detail["document_type"]),
            ("Emisor", detail["issuer_name"]),
            ("Fecha emision", detail["issue_date"]),
            ("Moneda", detail["currency"]),
            ("Total", detail["total_amount"]),
            ("Documento", detail["document_number"]),
            ("Hash", detail["attachment_hash"]),
            ("Archive path", detail["archive_path"]),
        )
    )

    parse_rows = "".join(
        """
        <tr>
          <td>{id}</td>
          <td>{provider}</td>
          <td>{job}</td>
          <td>{tier}</td>
          <td>{outcome}</td>
          <td>{started}</td>
          <td>{completed}</td>
        </tr>
        """.format(
            id=_esc(item["parse_attempt_id"]),
            provider=_esc(item["provider"]),
            job=_esc(item["provider_job_id"]),
            tier=_esc(item["provider_tier"]),
            outcome=_esc(item["outcome"]),
            started=_esc(item["started_at"]),
            completed=_esc(item["completed_at"]),
        )
        for item in detail["parse_attempts"]
    ) or '<tr><td colspan="7">Sin intentos de parse.</td></tr>'

    event_rows = "".join(
        """
        <tr>
          <td>{id}</td>
          <td>{ts}</td>
          <td>{stage}</td>
          <td>{event_type}</td>
          <td>{message}</td>
        </tr>
        """.format(
            id=_esc(item["event_id"]),
            ts=_esc(item["event_ts"]),
            stage=_esc(item["stage"]),
            event_type=_esc(item["event_type"]),
            message=_esc(item["message"]),
        )
        for item in detail["events"]
    ) or '<tr><td colspan="5">Sin eventos.</td></tr>'

    exception_rows = "".join(
        """
        <tr>
          <td>{id}</td>
          <td>{stage}</td>
          <td>{severity}</td>
          <td>{reason_code}</td>
          <td>{reason_detail}</td>
          <td>{opened_at}</td>
          <td>{closed_at}</td>
        </tr>
        """.format(
            id=_esc(item["exception_id"]),
            stage=_esc(item["stage"]),
            severity=_esc(item["severity"]),
            reason_code=_esc(item["reason_code"]),
            reason_detail=_esc(item["reason_detail"]),
            opened_at=_esc(item["opened_at"]),
            closed_at=_esc(item["closed_at"]),
        )
        for item in detail["exceptions"]
    ) or '<tr><td colspan="7">Sin excepciones.</td></tr>'

    normalized_json = json.dumps(detail["normalized_json"], indent=2, ensure_ascii=True, default=str)
    if detail["normalized_json"] is None:
        normalized_json = "No hay normalized.json disponible."

    body = """
    <section class="hero">
      <h1>Documento #{document_id}</h1>
      <p><a href="/">Volver al listado</a></p>
      <div class="spacer"></div>
      <span class="pill {status_class}">{status}</span>
    </section>
    <section class="card">
      <h2 class="section-title">Resumen</h2>
      <div class="meta">{meta_items}</div>
    </section>
    <section class="card">
      <h2 class="section-title">Intentos de Parse</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Provider</th>
            <th>Job</th>
            <th>Tier</th>
            <th>Outcome</th>
            <th>Started</th>
            <th>Completed</th>
          </tr>
        </thead>
        <tbody>{parse_rows}</tbody>
      </table>
    </section>
    <div class="spacer"></div>
    <section class="card">
      <h2 class="section-title">Eventos</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Timestamp</th>
            <th>Stage</th>
            <th>Event Type</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>{event_rows}</tbody>
      </table>
    </section>
    <div class="spacer"></div>
    <section class="card">
      <h2 class="section-title">Excepciones</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Stage</th>
            <th>Severity</th>
            <th>Reason Code</th>
            <th>Detail</th>
            <th>Opened</th>
            <th>Closed</th>
          </tr>
        </thead>
        <tbody>{exception_rows}</tbody>
      </table>
    </section>
    <div class="spacer"></div>
    <section class="card">
      <h2 class="section-title">Normalized JSON</h2>
      <pre>{normalized_json}</pre>
    </section>
    """.format(
        document_id=_esc(detail["document_id"]),
        status_class=_status_class(detail["current_status"]),
        status=_esc(detail["current_status"]),
        meta_items=meta_items,
        parse_rows=parse_rows,
        event_rows=event_rows,
        exception_rows=exception_rows,
        normalized_json=html.escape(normalized_json),
    )
    return _layout("Documento #{0}".format(detail["document_id"]), body)


def _parse_limit(value: str) -> int:
    try:
        return max(1, min(int(value), 200))
    except (TypeError, ValueError):
        return 50


def build_wsgi_app(config: AppConfig):
    read_model = IrisReadModel(config)

    def application(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        params = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)

        try:
            if method != "GET":
                payload = _layout("Metodo no permitido", "<section class='hero'><h1>Metodo no permitido</h1></section>")
                start_response("405 Method Not Allowed", [("Content-Type", "text/html; charset=utf-8")])
                return [payload]

            if path in ("/", "/documents"):
                payload = _render_dashboard(read_model, params)
                start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                return [payload]

            if path.startswith("/documents/"):
                tail = path.split("/", 2)[2]
                if tail.isdigit():
                    payload = _render_document_detail(read_model, int(tail))
                    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                    return [payload]

            payload = _layout(
                "No encontrado",
                "<section class='hero'><h1>Ruta no encontrada</h1><p><a href='/'>Volver al inicio</a></p></section>",
            )
            start_response("404 Not Found", [("Content-Type", "text/html; charset=utf-8")])
            return [payload]
        except Exception as exc:
            payload = _layout(
                "Error",
                """
                <section class="hero">
                  <h1>Error consultando IRIS</h1>
                  <p>{message}</p>
                  <p><a href="/">Volver</a></p>
                </section>
                """.format(message=html.escape(str(exc))),
            )
            start_response("500 Internal Server Error", [("Content-Type", "text/html; charset=utf-8")])
            return [payload]

    return application


def main() -> int:
    parser = argparse.ArgumentParser(description="Adjuntos101 web console")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", default=8080, type=int, help="Bind port")
    args = parser.parse_args()

    config = load_config(args.env_file)
    app = build_wsgi_app(config)
    with make_server(args.host, args.port, app) as server:
        print("Adjuntos101 Console listening on http://{0}:{1}".format(args.host, args.port))
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
