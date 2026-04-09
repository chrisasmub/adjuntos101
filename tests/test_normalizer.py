import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adjuntos_worker.models import DocumentClassification, ParseResult
from adjuntos_worker.normalizer import normalize_document
from adjuntos_worker.validator import validate_normalized_document


class NormalizerTests(unittest.TestCase):
    def test_normalize_and_validate_invoice(self):
        classification = DocumentClassification(
            document_type="invoice",
            provider_tier="cost_effective",
            provider_version="latest",
            rationale="Matched factura keyword.",
        )
        parse_result = ParseResult(
            provider="mock",
            provider_job_id="job-1",
            provider_tier="cost_effective",
            provider_version="latest",
            raw_json={},
            markdown="\n".join(
                [
                    "Factura Electronica",
                    "Emisor: Comercial Demo",
                    "RUT: 76.123.456-7",
                    "Fecha Emision: 2026-04-01",
                    "Moneda: CLP",
                    "Monto Total: 15000",
                ]
            ),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            outcome="COMPLETED",
        )

        normalized = normalize_document(classification, parse_result)
        validation = validate_normalized_document(normalized)

        self.assertEqual(normalized.document_type, "invoice")
        self.assertEqual(normalized.issuer_name, "Comercial Demo")
        self.assertEqual(normalized.currency, "CLP")
        self.assertEqual(normalized.total_amount, 15000.0)
        self.assertFalse(validation.requires_review)


if __name__ == "__main__":
    unittest.main()
