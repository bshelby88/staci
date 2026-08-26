import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("monetization_microservice.py")
SPEC = importlib.util.spec_from_file_location("monetization_microservice", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PaymentGateTests(unittest.TestCase):
    def test_format_only_hash_is_not_verified_payment(self):
        fake_hash = "0x" + "a" * 64
        self.assertFalse(MODULE.verify_base_usdc_payment(fake_hash, 5.00))

    def test_product_catalog_does_not_advertise_disabled_payment_routes(self):
        products = MODULE.list_products()["shelf_products"]
        paid_api_products = [
            product for product in products
            if product["id"] in {"prod_dispute_forge", "prod_sentry_forge_api"}
        ]

        self.assertEqual(len(paid_api_products), 2)
        for product in paid_api_products:
            self.assertEqual(product["payment_status"], "disabled")
            self.assertNotIn("x402_price_usd", product)
        self.assertEqual(MODULE.healthz()["payment_verification"], "disabled")
        self.assertIn("disabled", MODULE.app.description.lower())

    def test_dispute_route_is_unavailable_for_format_only_hash(self):
        from fastapi.testclient import TestClient

        response = TestClient(MODULE.app).post(
            "/v1/dispute/generate",
            headers={"X-402-Payment-Tx": "0x" + "a" * 64},
            json={
                "client_name": "Test User",
                "creditor_name": "Test Creditor",
                "account_number_last4": "1234",
                "dispute_reason": "Test dispute",
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"detail": "Payment verification unavailable; paid fulfillment is disabled"},
        )

    def test_sentry_route_is_unavailable_for_format_only_hash(self):
        from fastapi.testclient import TestClient

        response = TestClient(MODULE.app).post(
            "/v1/sentry/analyze-case",
            headers={"X-402-Payment-Tx": "0x" + "b" * 64},
            json={"case_summary": "Test case", "claimed_damages_usd": 1000},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"detail": "Payment verification unavailable; paid fulfillment is disabled"},
        )


if __name__ == "__main__":
    unittest.main()
