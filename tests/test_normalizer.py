import sys
import unittest
from datetime import date, datetime
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

    def test_normalize_realistic_markdown_invoice(self):
        classification = DocumentClassification(
            document_type="invoice",
            provider_tier="cost_effective",
            provider_version="latest",
            rationale="Matched invoice keyword.",
        )
        parse_result = ParseResult(
            provider="llamaparse",
            provider_job_id="job-2",
            provider_tier="cost_effective",
            provider_version="latest",
            raw_json={},
            markdown="\n".join(
                [
                    "# Invoice",
                    "",
                    "**Invoice number** IN-61952233",
                    "**Date of issue** April 9, 2026",
                    "**Date due** April 9, 2026",
                    "",
                    "**Cloudflare, Inc.**",
                    "101 Townsend Street",
                    "",
                    "## $0.00 USD due April 9, 2026",
                    "",
                    "| Description | Qty | Unit Price | Total |",
                    "| --- | --- | --- | --- |",
                    "| Total | $0.00 | | |",
                    "| **Amount due** | **$0.00 USD** | | |",
                ]
            ),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            outcome="COMPLETED",
        )

        normalized = normalize_document(classification, parse_result)
        validation = validate_normalized_document(normalized)

        self.assertEqual(normalized.document_type, "invoice")
        self.assertEqual(normalized.issuer_name, "Cloudflare, Inc.")
        self.assertEqual(normalized.issue_date, date(2026, 4, 9))
        self.assertEqual(normalized.due_date, date(2026, 4, 9))
        self.assertEqual(normalized.currency, "USD")
        self.assertEqual(normalized.total_amount, 0.0)
        self.assertEqual(normalized.document_number, "IN-61952233")
        self.assertFalse(validation.requires_review)

    def test_normalize_sharetribe_invoice_with_llamaparse_markdown(self):
        classification = DocumentClassification(
            document_type="invoice",
            provider_tier="cost_effective",
            provider_version="latest",
            rationale="Matched invoice keyword.",
        )
        parse_result = ParseResult(
            provider="llamaparse",
            provider_job_id="job-3",
            provider_tier="cost_effective",
            provider_version="latest",
            raw_json={},
            markdown="\n".join(
                [
                    "# INVOICE",
                    "",
                    "Sharetribe Ltd",
                    "Erottajankatu 19 B",
                    "00130 Helsinki",
                    "Finland",
                    "",
                    "Invoice # **109300**",
                    "Invoice Date **Apr 08, 2026**",
                    "Invoice Amount **$39.00 (USD)**",
                    "",
                    "**SUBSCRIPTION**",
                    "Billing Period **Apr 08 to May 08, 2026**",
                    "Next Billing Date **May 08, 2026**",
                    "",
                    "**PAYMENTS**",
                    "**$39.00 (USD)** was paid on 08 Apr, 2026 15:02 UTC by Visa card ending 4361.",
                    "",
                    "**NOTES**",
                    "Currency is USD.",
                ]
            ),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            outcome="COMPLETED",
        )

        normalized = normalize_document(classification, parse_result)
        validation = validate_normalized_document(normalized)

        self.assertEqual(normalized.document_type, "invoice")
        self.assertEqual(normalized.issuer_name, "Sharetribe Ltd")
        self.assertEqual(normalized.issue_date, date(2026, 4, 8))
        self.assertEqual(normalized.period_from, date(2026, 4, 8))
        self.assertEqual(normalized.period_to, date(2026, 5, 8))
        self.assertEqual(normalized.currency, "USD")
        self.assertEqual(normalized.total_amount, 39.0)
        self.assertEqual(normalized.account_ref_last4, "4361")
        self.assertEqual(normalized.document_number, "109300")
        self.assertFalse(validation.requires_review)

    def test_normalize_monthly_bank_statement_markdown(self):
        classification = DocumentClassification(
            document_type="bank_statement",
            provider_tier="agentic",
            provider_version="latest",
            rationale="Matched cartola keyword.",
        )
        parse_result = ParseResult(
            provider="llamaparse",
            provider_job_id="job-4",
            provider_tier="agentic",
            provider_version="latest",
            raw_json={},
            markdown="\n".join(
                [
                    "![Alpaca logo](page_1_image_1_v2.jpg)",
                    "![Fintual logo](page_1_image_2_v2.jpg)",
                    "",
                    "12 E 49th Street",
                    "Providencia 229, Providencia",
                    "",
                    "**Christian Asmussen Blanco**",
                    "**Monthly Statement**",
                    "**Period:** MARCH - 2026",
                    "",
                    "**Account No:** 901121620",
                    "",
                    "| Account Summary | |",
                    "| --- | --- |",
                    "| Total Market Value | $713.14 |",
                    "",
                    "USD",
                ]
            ),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            outcome="COMPLETED",
        )

        normalized = normalize_document(classification, parse_result)
        validation = validate_normalized_document(normalized)

        self.assertEqual(normalized.document_type, "bank_statement")
        self.assertEqual(normalized.issuer_name, "Alpaca / Fintual")
        self.assertEqual(normalized.period_from, date(2026, 3, 1))
        self.assertEqual(normalized.period_to, date(2026, 3, 31))
        self.assertEqual(normalized.currency, "USD")
        self.assertEqual(normalized.balance_amount, 713.14)
        self.assertEqual(normalized.account_ref_last4, "1620")
        self.assertFalse(validation.requires_review)

    def test_normalize_receipt_markdown(self):
        classification = DocumentClassification(
            document_type="receipt",
            provider_tier="cost_effective",
            provider_version="latest",
            rationale="Matched boleta keyword.",
        )
        parse_result = ParseResult(
            provider="llamaparse",
            provider_job_id="job-5",
            provider_tier="cost_effective",
            provider_version="latest",
            raw_json={},
            markdown="\n".join(
                [
                    "JUMBO.CL",
                    "RUT 81201000-K",
                    "BOLETA ELECTRONICA Nº3346465534",
                    "SII PROVIDENCIA",
                    "",
                    "CENCOSUD RETAIL S.A.",
                    "AV. A. BELLO 2447 LOCAL 0500",
                    "PROVIDENCIA - SANTIAGO",
                    "",
                    "SUB TOTAL $ 172.078",
                    "DESCUENTOS $ 34.809",
                    "TOTAL $ 137.269",
                    "NETO $ 115.348",
                    "",
                    "FECHA HORA LOCAL CA TRX ID",
                    "08/04/26 12:57 1411 300 5178 750",
                ]
            ),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            outcome="COMPLETED",
        )

        normalized = normalize_document(classification, parse_result)
        validation = validate_normalized_document(normalized)

        self.assertEqual(normalized.document_type, "receipt")
        self.assertEqual(normalized.issuer_name, "CENCOSUD RETAIL S.A.")
        self.assertEqual(normalized.issue_date, date(2026, 4, 8))
        self.assertEqual(normalized.currency, "CLP")
        self.assertEqual(normalized.total_amount, 137269.0)
        self.assertFalse(validation.requires_review)


if __name__ == "__main__":
    unittest.main()
