from pathlib import Path

from adjuntos_worker.config import ParseSettings
from adjuntos_worker.models import DocumentClassification


DOCUMENT_KEYWORDS = {
    "invoice": ["factura", "invoice", "factura electronica"],
    "receipt": ["boleta", "receipt"],
    "card_statement": ["billing statement", "estado de cuenta", "tarjeta", "credit card"],
    "bank_statement": ["cartola", "movimientos", "bank statement", "estado de cuenta bancario"],
    "mutual_fund_statement": ["fondo mutuo", "mutual fund"],
}


def classify_document(path: Path, text: str, parse_settings: ParseSettings) -> DocumentClassification:
    haystack = "{0}\n{text}".format(path.name.lower(), text=text.lower())

    best_type = "unknown"
    rationale = "No matching keyword; default parsing tier selected."

    for document_type, keywords in DOCUMENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in haystack:
                best_type = document_type
                rationale = "Matched keyword '{0}'.".format(keyword)
                break
        if best_type != "unknown":
            break

    complex_types = {"card_statement", "bank_statement", "mutual_fund_statement"}
    tier = parse_settings.complex_tier if best_type in complex_types else parse_settings.default_tier

    return DocumentClassification(
        document_type=best_type,
        provider_tier=tier,
        provider_version=parse_settings.version,
        rationale=rationale,
    )
