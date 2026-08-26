import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "docs" / "recovery"
sys.path.insert(0, str(RECOVERY))

from credential_config import require_kernel_api_key


class CredentialConfigTests(unittest.TestCase):
    def test_missing_kernel_key_fails_clearly(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "RAE_KERNEL_API_KEY is required"):
                require_kernel_api_key()

    def test_environment_kernel_key_is_returned(self):
        with patch.dict(os.environ, {"RAE_KERNEL_API_KEY": "configured-at-runtime"}, clear=True):
            self.assertEqual(require_kernel_api_key(), "configured-at-runtime")

    def test_explicit_injection_takes_precedence(self):
        with patch.dict(os.environ, {"RAE_KERNEL_API_KEY": "environment-value"}, clear=True):
            self.assertEqual(require_kernel_api_key("injected-value"), "injected-value")


class RecoveryScriptCredentialTests(unittest.TestCase):
    CONSTRUCTORS = (
        ("bazaar_auto_indexer", "BazaarAutoIndexer"),
        ("chronicler_wallet_watcher", "ChroniclerWalletWatcher"),
        ("deterministic_envelope_harness", "DeterministicEnvelope"),
        ("hermes_directory_seeding", "HermesOutboundEngine"),
        ("nft_royalty_collector", "NFTRoyaltyCollector"),
        ("substack_weekly_publisher", "SubstackWeeklyPublisher"),
        ("tiffany_heygen_producer", "TiffanyHeyGenProducer"),
    )

    def test_affected_classes_fail_closed_without_kernel_key(self):
        with patch.dict(os.environ, {}, clear=True):
            for module_name, class_name in self.CONSTRUCTORS:
                with self.subTest(module=module_name):
                    constructor = getattr(importlib.import_module(module_name), class_name)
                    args = ("test-agent",) if class_name == "DeterministicEnvelope" else ()
                    with self.assertRaisesRegex(RuntimeError, "RAE_KERNEL_API_KEY is required"):
                        constructor(*args)

    def test_runner_checks_key_before_creating_local_state(self):
        runner = importlib.import_module("make_it_happen_runner")
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=True):
                old_cwd = os.getcwd()
                os.chdir(directory)
                try:
                    with self.assertRaisesRegex(RuntimeError, "RAE_KERNEL_API_KEY is required"):
                        runner.main()
                    self.assertEqual(list(Path(directory).iterdir()), [])
                finally:
                    os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
