import importlib.util
import json
import re
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

RECOVERY_DIR = Path(__file__).parents[1] / "docs" / "recovery"


def load_module(name: str):
    path = RECOVERY_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MONETIZATION = load_module("monetization_microservice")
CREDIT = load_module("credit_score_simulation_api")
SUBSCRIPTION = load_module("recurring_subscription_gateway")

FAKE_HASH = "0x" + "a" * 64
PAYMENT_DISABLED_DETAIL = (
    "Payment verification unavailable; paid fulfillment is disabled"
)

ENDPOINTS = (
    (
        MONETIZATION,
        "/v1/dispute/generate",
        {
            "client_name": "Test User",
            "creditor_name": "Test Creditor",
            "account_number_last4": "1234",
            "dispute_reason": "Test dispute",
        },
    ),
    (
        MONETIZATION,
        "/v1/sentry/analyze-case",
        {"case_summary": "Test case", "claimed_damages_usd": 1000},
    ),
    (
        CREDIT,
        "/v1/credit/simulate",
        {
            "current_score": 620,
            "total_credit_limit": 10000,
            "current_revolving_balance": 8000,
        },
    ),
    (
        SUBSCRIPTION,
        "/v1/subscription/subscribe",
        {"subscriber_wallet": "0x" + "1" * 40},
    ),
)


class PaymentGateFailClosedTests(unittest.TestCase):
    def test_every_paid_route_rejects_missing_and_format_only_hashes_with_503(self):
        for module, path, payload in ENDPOINTS:
            client = TestClient(module.app)
            for headers in ({}, {"X-402-Payment-Tx": FAKE_HASH}):
                with self.subTest(path=path, headers=headers):
                    response = client.post(path, headers=headers, json=payload)
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(
                        response.json(), {"detail": PAYMENT_DISABLED_DETAIL}
                    )

        self.assertEqual(SUBSCRIPTION.store.active_subscriptions, {})

    def test_hash_shape_is_never_treated_as_payment_verification(self):
        self.assertFalse(MONETIZATION.verify_base_usdc_payment(FAKE_HASH, 5.00))
        self.assertFalse(CREDIT.verify_base_usdc_payment(FAKE_HASH))
        self.assertFalse(SUBSCRIPTION.verify_tx_hash(FAKE_HASH))

    def test_health_catalog_and_api_info_make_no_price_or_active_claims(self):
        metadata = [
            MONETIZATION.healthz(),
            MONETIZATION.list_products(),
            CREDIT.healthz(),
            SUBSCRIPTION.healthz(),
        ]
        metadata.extend(
            module.app.openapi()["info"]
            for module in (MONETIZATION, CREDIT, SUBSCRIPTION)
        )

        serialized = json.dumps(metadata).lower()
        for forbidden in (
            '"price',
            '"active',
            '"wallet',
            "checkout_url",
            "payment required",
            "$",
            "/mo",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, serialized)

        for module in (MONETIZATION, CREDIT, SUBSCRIPTION):
            health = module.healthz()
            self.assertEqual(health["payment_verification"], "disabled")
            self.assertEqual(health["paid_fulfillment"], "unavailable")

    def test_openapi_documents_503_and_no_paid_success_response(self):
        for module, path, _payload in ENDPOINTS:
            responses = module.app.openapi()["paths"][path]["post"]["responses"]
            with self.subTest(path=path):
                self.assertIn("503", responses)
                self.assertNotIn("200", responses)
                self.assertNotIn("201", responses)
                self.assertNotIn("402", responses)

    def test_repository_has_no_unreproducible_fly_manifest(self):
        fly_manifest = RECOVERY_DIR / "fly.toml"
        if not fly_manifest.exists():
            return

        manifest = fly_manifest.read_text(encoding="utf-8")
        dockerfile_match = re.search(r'dockerfile\s*=\s*"([^"]+)"', manifest)
        self.assertIsNotNone(dockerfile_match)
        self.assertTrue((RECOVERY_DIR / dockerfile_match.group(1)).is_file())

    def test_tracked_runtime_sources_have_no_format_only_hash_acceptor(self):
        hash_regex_gate = re.compile(
            r"re\.(?:match|fullmatch)\([^\n]*0x[^\n]*\{64\}", re.IGNORECASE
        )
        offenders = []
        for source_path in RECOVERY_DIR.glob("*.py"):
            if source_path.name.startswith("test_"):
                continue
            if hash_regex_gate.search(source_path.read_text(encoding="utf-8")):
                offenders.append(source_path.name)

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
