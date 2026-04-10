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
    issuer_tax_id = _extract_labeled_text(text, ["rut", "tax id", "issuer tax id"])
    issue_date = _extract_date(
        text, ["issue date", "date of issue", "fecha emision", "fecha de emision", "fecha"]
    )
    due_date = _extract_date(text, ["due date", "date due", "fecha vencimiento", "vencimiento"])
    period_from = _extract_date(text, ["period from", "desde", "periodo desde"])
    period_to = _extract_date(text, ["period to", "hasta", "periodo hasta"])

    if (period_from is None or period_to is None) and "periodo" in text.lower():
        date_range = _extract_date_range(text)
        if date_range is not None:
            period_from = period_from or date_range[0]
            period_to = period_to or date_range[1]

    currency = _extract_currency(text)
    total_amount = _extract_amount(
        text,
        ["amount due", "total amount", "monto total", "importe total", "total"],
    )
    balance_amount = _extract_amount(text, ["balance amount", "saldo", "saldo total", "balance"])
    account_ref_last4 = _extract_account_last4(text)
    document_number = _extract_labeled_text(
        text, ["document number", "numero documento", "folio", "invoice number", "nro documento"]
    )

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
            r"{0}(?:\*\*)?(?:\s|[:#\-\|]|</?[a-z]+>)*?(?:\*\*)?(?:CLP|USD|UF|EUR|\$)\s*([0-9][0-9\.,]*)".format(
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
    ignore_values = {
        "invoice",
        "bill to",
        "invoice number",
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


def _extract_account_last4(text: str) -> str:
    match = re.search(r"(?:account|cuenta|card|tarjeta)[^0-9]*([0-9]{4})", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def _parse_amount(raw: str) -> Optional[float]:
    cleaned = raw.strip().replace(" ", "")
    if cleaned.count(",") == 1 and cleaned.count(".") > 1:
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
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%B %d, %Y", "%b %d, %Y"):
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
    escaped = re.escape(label)
    return [
        re.compile(
            r"\*\*{0}\*\*\s*(?:[:#\-]|\|)?\s*{1}".format(escaped, value_pattern),
            re.IGNORECASE,
        ),
        re.compile(
            r"{0}\s*(?:[:#\-]|\|)\s*{1}".format(escaped, value_pattern),
            re.IGNORECASE,
        ),
    ]


def _date_pattern() -> str:
    return r"([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{2}-[0-9]{2}-[0-9]{4}|[A-Za-z]{3,9}\s+[0-9]{1,2},\s+[0-9]{4})"


def _amount_pattern() -> str:
    return r"(?:\*\*)?(?:CLP|USD|UF|EUR|\$)?\s*([0-9][0-9\.,]*)(?:\s*(?:CLP|USD|UF|EUR))?(?:\*\*)?"


def _strip_markdown(value: str) -> str:
    return re.sub(r"\*\*", "", value).strip()
