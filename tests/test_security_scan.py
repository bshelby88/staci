import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.security_scan import KNOWN_SECRET_SHA256, scan_files


class SecurityScanTests(unittest.TestCase):
    def test_scanner_detects_credential_pattern_without_secret_content(self):
        secret = "fixture-" + "credential-" + "value"
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "candidate.py"
            candidate.write_text("API_" + "KEY = " + repr(secret), encoding="utf-8")

            findings = scan_files([candidate], fingerprints=set())

        self.assertEqual(len(findings), 1)
        rendered = "\n".join(finding.render() for finding in findings)
        self.assertNotIn(secret, rendered)
        self.assertIn("candidate.py:1", rendered)

    def test_scanner_detects_known_fingerprint_without_secret_content(self):
        secret = b"known-fixture-value"
        fingerprint = hashlib.sha256(secret).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "candidate.bin"
            candidate.write_bytes(secret)

            findings = scan_files([candidate], fingerprints={fingerprint})

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "known-fingerprint")
        self.assertNotIn(secret.decode(), findings[0].render())

    def test_repository_current_tree_is_credential_free(self):
        result = subprocess.run(
            [sys.executable, "scripts/security_scan.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("API_KEY =", result.stdout + result.stderr)

    def test_known_fingerprint_is_configured(self):
        self.assertEqual(
            KNOWN_SECRET_SHA256,
            "1be5fb19bfed4c06d8dd1e0de2a0a98b66095cb9e671813b773edf16d6d406c4",
        )


if __name__ == "__main__":
    unittest.main()
