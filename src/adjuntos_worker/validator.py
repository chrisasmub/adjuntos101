from dataclasses import replace

from adjuntos_worker.models import NormalizedDocument, ValidationResult


REQUIRED_FIELDS_BY_TYPE = {
    "invoice": [
        "document_type",
        "issuer_name",
        "issue_date",
        "currency",
        "total_amount",
    ],
    "receipt": [
        "document_type",
        "issuer_name",
        "issue_date",
        "currency",
        "total_amount",
    ],
    "card_statement": [
        "document_type",
        "issuer_name",
        ("period_from", "period_to"),
        "currency",
        ("balance_amount", "total_amount"),
        "account_ref_last4",
    ],
    "bank_statement": [
        "document_type",
        "issuer_name",
        ("period_from", "period_to"),
        "currency",
    ],
    "mutual_fund_statement": [
        "document_type",
        "issuer_name",
        ("period_to", "issue_date"),
        "currency",
    ],
}


def validate_normalized_document(normalized: NormalizedDocument) -> ValidationResult:
    requirements = REQUIRED_FIELDS_BY_TYPE.get(normalized.document_type)
    if requirements is None:
        missing_fields = ["document_type"]
        return ValidationResult(
            requires_review=True,
            missing_fields=missing_fields,
            notes="Unknown document type.",
        )

    missing_fields = []
    for requirement in requirements:
        if isinstance(requirement, tuple):
            if not any(_has_value(getattr(normalized, field_name)) for field_name in requirement):
                missing_fields.append(" or ".join(requirement))
            continue
        if not _has_value(getattr(normalized, requirement)):
            missing_fields.append(requirement)

    return ValidationResult(
        requires_review=bool(missing_fields),
        missing_fields=missing_fields,
        notes="" if not missing_fields else "Missing required fields: {0}".format(", ".join(missing_fields)),
    )


def apply_validation_result(
    normalized: NormalizedDocument, validation: ValidationResult
) -> NormalizedDocument:
    notes = normalized.notes
    if validation.notes:
        notes = "{0} {1}".format(notes, validation.notes).strip()

    return replace(
        normalized,
        review_required=validation.requires_review,
        notes=notes,
    )


def _has_value(value) -> bool:
    return value not in ("", None)
