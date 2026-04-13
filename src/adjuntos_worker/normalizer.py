import calendar
import re
from datetime import date, datetime
from typing import Optional

from adjuntos_worker.models import DocumentClassification, NormalizedDocument, ParseResult


def normalize_document(
    classification: DocumentClassification,
    parse_result: ParseResult,
) -> NormalizedDocument:
    text = parse_result.markdown
    inferred_type = _infer_document_type(classification.document_type, text)

    issuer_name = _extract_labeled_text(text, ["issuer", "emisor", "empresa", "banco"])
    if not issuer_name and inferred_type == "invoice":
        issuer_name = _extract_invoice_issuer_name(text)
    if not issuer_name and inferred_type == "receipt":
        issuer_name = _extract_receipt_issuer_name(text)
    if not issuer_name and inferred_type == "bank_statement":
        issuer_name = _extract_bank_statement_issuer_name(text)
    issuer_tax_id = _extract_labeled_text(text, ["rut", "tax id", "issuer tax id"])
    issue_date = _extract_date(
        text,
        [
            "issue date",
            "invoice date",
            "date of issue",
            "fecha emision",
            "fecha de emision",
            "fecha",
        ],
    )
    due_date = _extract_date(
        text,
        ["due date", "date due", "next billing date", "fecha vencimiento", "vencimiento"],
    )
    if issue_date is None and inferred_type == "receipt":
        issue_date = _extract_receipt_issue_date(text)
    period_from = _extract_date(text, ["period from", "billing period", "desde", "periodo desde"])
    period_to = _extract_date(text, ["period to", "billing period", "hasta", "periodo hasta"])

    if (period_from is None or period_to is None) and "periodo" in text.lower():
        date_range = _extract_date_range(text)
        if date_range is not None:
            period_from = period_from or date_range[0]
            period_to = period_to or date_range[1]
    if period_from is None or period_to is None:
        billing_period = _extract_billing_period(text)
        if billing_period is not None:
            period_from = period_from or billing_period[0]
            period_to = period_to or billing_period[1]
    if period_from is None or period_to is None:
        month_period = _extract_month_period(text)
        if month_period is not None:
            period_from = period_from or month_period[0]
            period_to = period_to or month_period[1]

    currency = _extract_currency(text)
    total_amount = _extract_amount(
        text,
        ["invoice amount", "amount due", "total amount", "monto total", "importe total", "total"],
    )
    if inferred_type == "receipt":
        total_amount = _extract_receipt_total_amount(text) or total_amount
    balance_amount = _extract_amount(
        text,
        ["ending value", "total market value", "balance amount", "saldo", "saldo total", "balance"],
    )
    account_ref_last4 = _extract_account_last4(text)
    document_number = _extract_document_number(text)

    confidence = _calculate_confidence(
        inferred_type,
        issuer_name=issuer_name,
        currency=currency,
        issue_date=issue_date,
        period_from=period_from,
        period_to=period_to,
        total_amount=total_amount,
        balance_amount=balance_amount,
    )

    notes = classification.rationale
    if classification.document_type == "unknown" and inferred_type != "unknown":
        notes = "Document type inferred from parsed text."

    return NormalizedDocument(
        document_type=inferred_type,
        issuer_name=issuer_name,
        issuer_tax_id=issuer_tax_id,
        issue_date=issue_date,
        due_date=due_date,
        period_from=period_from,
        period_to=period_to,
        currency=currency,
        total_amount=total_amount,
        balance_amount=balance_amount,
        account_ref_last4=account_ref_last4,
        document_number=document_number,
        confidence=confidence,
        review_required=False,
        notes=notes,
    )


def _infer_document_type(current_type: str, text: str) -> str:
    if current_type != "unknown":
        return current_type

    lowered = text.lower()
    if "factura" in lowered or "invoice" in lowered:
        return "invoice"
    if "boleta" in lowered or "receipt" in lowered:
        return "receipt"
    if "fondo mutuo" in lowered or "mutual fund" in lowered:
        return "mutual_fund_statement"
    if "cartola" in lowered or "movimientos" in lowered or "bank statement" in lowered:
        return "bank_statement"
    if "tarjeta" in lowered or "billing statement" in lowered:
        return "card_statement"
    return "unknown"


def _extract_labeled_text(text: str, labels) -> str:
    for label in labels:
        for pattern in _build_label_patterns(label):
            match = pattern.search(text)
            if match:
                value = _strip_markdown(match.group(1))
                return value.splitlines()[0].strip()
    return ""


def _extract_date(text: str, labels) -> Optional[date]:
    for label in labels:
        for pattern in _build_label_patterns(label, value_pattern=_date_pattern()):
            match = pattern.search(text)
            if match:
                return _parse_date(_strip_markdown(match.group(1)))
    return None


def _extract_date_range(text: str):
    pattern = re.compile(
        r"([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{2}-[0-9]{2}-[0-9]{4})\s+(?:a|to|hasta|-)\s+([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{2}-[0-9]{2}-[0-9]{4})",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    start_date = _parse_date(match.group(1))
    end_date = _parse_date(match.group(2))
    if start_date and end_date:
        return start_date, end_date
    return None


def _extract_billing_period(text: str):
    match = re.search(
        r"billing period\s*(?:[:#\-]|\|)?\s*(?:\*\*)?([A-Za-z]{3,9}\s+[0-9]{1,2})\s+(?:to|a|hasta|-)\s+([A-Za-z]{3,9}\s+[0-9]{1,2},\s*[0-9]{4})(?:\*\*)?",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    end_date = _parse_date(_strip_markdown(match.group(2)))
    if end_date is None:
        return None

    start_raw = "{0} {1}".format(_strip_markdown(match.group(1)), end_date.year)
    start_date = _parse_date(start_raw)
    if start_date is None:
        return None

    return start_date, end_date


def _extract_month_period(text: str):
    month_names = (
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    )
    match = re.search(
        r"(?:period\s*(?:[:#\-]|\|)?\s*)?(" + "|".join(month_names) + r")\s*[-/]\s*([0-9]{4})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    month_name = match.group(1).lower()
    year = int(match.group(2))
    month = month_names.index(month_name) + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _extract_currency(text: str) -> str:
    for currency in ("CLP", "USD", "UF", "EUR"):
        if re.search(r"\b{0}\b".format(currency), text, re.IGNORECASE):
            return currency
    if "$" in text:
        return "CLP"
    return ""


def _extract_amount(text: str, labels) -> Optional[float]:
    for label in labels:
        for pattern in _build_label_patterns(label, value_pattern=_amount_pattern()):
            match = pattern.search(text)
            if match:
                amount = _parse_amount(_strip_markdown(match.group(1)))
                if amount is not None:
                    return amount
        loose_match = re.search(
            r"(?<!\w){0}(?!\w)(?:\*\*)?(?:\s|[:#\-\|]|</?[a-z]+>)*?(?:\*\*)?(?:CLP|USD|UF|EUR|\$)\s*([0-9][0-9\.,]*)".format(
                re.escape(label)
            ),
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if loose_match:
            amount = _parse_amount(_strip_markdown(loose_match.group(1)))
            if amount is not None:
                return amount
    return None


def _extract_invoice_issuer_name(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if line.lower() != "# invoice":
            continue
        for candidate in lines[index + 1 :]:
            if not candidate or candidate.startswith("<!--"):
                continue
            lowered = _strip_markdown(candidate).strip().lower()
            if (
                lowered.startswith("invoice ")
                or lowered.startswith("date ")
                or lowered.startswith("amount ")
                or lowered.startswith("billing period")
                or lowered.startswith("next billing date")
                or lowered.startswith("paid")
            ):
                break
            if lowered in {"paid", "billed to", "subscription", "payments", "notes"}:
                continue
            if re.match(r"^[0-9]{4,}", lowered):
                continue
            return _strip_markdown(candidate).strip()

    ignore_values = {
        "invoice",
        "bill to",
        "invoice number",
        "invoice #",
        "invoice date",
        "date of issue",
        "date due",
        "amount due",
    }
    for match in re.finditer(r"\*\*(.+?)\*\*", text):
        value = _strip_markdown(match.group(1)).strip()
        lowered = value.lower()
        if lowered in ignore_values:
            continue
        if value.startswith("$"):
            continue
        if re.search(r"\d{4}", value):
            continue
        return value
    return ""


def _extract_bank_statement_issuer_name(text: str) -> str:
    issuers = []
    for match in re.finditer(r"!\[([^\]]+?)\s+logo\]", text, re.IGNORECASE):
        issuer = _strip_markdown(match.group(1)).strip()
        if issuer and issuer not in issuers:
            issuers.append(issuer)
    if issuers:
        return " / ".join(issuers)

    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if "monthly statement" not in line.lower():
            continue
        for candidate in reversed(lines[:index]):
            if not candidate or candidate.startswith("![") or candidate.startswith("----"):
                continue
            if re.search(r"[0-9]{3,}", candidate):
                continue
            if "," in candidate:
                continue
            return _strip_markdown(candidate)
    return ""


def _extract_receipt_issuer_name(text: str) -> str:
    company_pattern = re.compile(r"^[A-Z0-9][A-Z0-9 .,&\-]{4,}$")
    preferred_suffixes = ("S.A.", "S.A", "SPA", "LTDA", "LTDA.", "LIMITADA")

    candidates = []
    for line in text.splitlines():
        candidate = _strip_markdown(line)
        if not candidate:
            continue
        lowered = candidate.lower()
        if "boleta electronica" in lowered or "sii " in lowered or lowered.startswith("rut "):
            continue
        if candidate.startswith("-"):
            continue
        if company_pattern.match(candidate) and any(ch.isalpha() for ch in candidate):
            candidates.append(candidate)

    for candidate in candidates:
        upper = candidate.upper()
        if any(upper.endswith(suffix) for suffix in preferred_suffixes):
            return candidate
    for candidate in candidates:
        if "." in candidate and " " not in candidate:
            continue
        return candidate
    return ""


def _extract_receipt_issue_date(text: str) -> Optional[date]:
    match = re.search(r"\b([0-9]{2}/[0-9]{2}/[0-9]{2})\b(?:\s+[0-9]{2}:[0-9]{2})?", text)
    if not match:
        return None
    return _parse_date(match.group(1))


def _extract_receipt_total_amount(text: str) -> Optional[float]:
    match = re.search(r"^TOTAL\s+\$\s*([0-9\.\,]+)\s*$", text, re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return _parse_amount(match.group(1))


def _extract_account_last4(text: str) -> str:
    match = re.search(r"(?:account|cuenta|card|tarjeta)[^0-9]*([0-9]{4,})", text, re.IGNORECASE)
    if match:
        return match.group(1)[-4:]
    return ""


def _extract_document_number(text: str) -> str:
    document_number = _extract_labeled_text(
        text,
        [
            "document number",
            "numero documento",
            "folio",
            "invoice number",
            "nro documento",
        ],
    )
    if document_number:
        return document_number

    match = re.search(r"invoice\s*#\s*(?:\*\*)?([A-Za-z0-9\-]+)(?:\*\*)?", text, re.IGNORECASE)
    if match:
        return _strip_markdown(match.group(1))
    return ""


def _parse_amount(raw: str) -> Optional[float]:
    cleaned = raw.strip().replace(" ", "")
    if re.match(r"^[0-9]{1,3}(?:\.[0-9]{3})+$", cleaned):
        cleaned = cleaned.replace(".", "")
    elif cleaned.count(",") == 1 and cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif cleaned.count(",") == 1 and cleaned.count(".") == 0:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_date(raw: str) -> Optional[date]:
    cleaned = raw.strip()
    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
    ):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _calculate_confidence(document_type: str, **fields) -> float:
    available = sum(1 for value in fields.values() if value not in ("", None))
    total = len(fields)
    base = available / total if total else 0.0
    if document_type != "unknown":
        base += 0.1
    return round(min(base, 0.99), 2)


def _build_label_patterns(label: str, value_pattern: str = r"([^\n]+)") -> list[re.Pattern]:
    escaped = r"(?<!\w){0}(?!\w)".format(re.escape(label))
    return [
        re.compile(
            r"\*\*{0}\*\*\s*(?:[:#\-]|\|)?\s*(?:\*\*)?{1}(?:\*\*)?".format(escaped, value_pattern),
            re.IGNORECASE,
        ),
        re.compile(
            r"{0}\s*(?:[:#\-]|\|)?\s*(?:\*\*)?{1}(?:\*\*)?".format(escaped, value_pattern),
            re.IGNORECASE,
        ),
    ]


def _date_pattern() -> str:
    return r"([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{2}-[0-9]{2}-[0-9]{4}|[A-Za-z]{3,9}\s+[0-9]{1,2},\s+[0-9]{4})"


def _amount_pattern() -> str:
    return r"(?:\*\*)?(?:CLP|USD|UF|EUR|\$)?\s*([0-9][0-9\.,]*)(?:\s*(?:CLP|USD|UF|EUR))?(?:\*\*)?"


def _strip_markdown(value: str) -> str:
    return re.sub(r"\*\*", "", value).strip()
