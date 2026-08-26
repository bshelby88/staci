#!/usr/bin/env python3
"""Fail-closed credential scan for the repository's tracked current tree.

Findings deliberately report only path, line, and rule name. Matched content is
never printed.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

KNOWN_SECRET_SHA256 = (
    "1be5fb19bfed4c06d8dd1e0de2a0a98b66095cb9e671813b773edf16d6d406c4"
)

_CREDENTIAL_PATTERNS = (
    (
        "credential-assignment",
        re.compile(
            rb"(?i)\b(?:api[_-]?key|secret|access[_-]?token|auth[_-]?token|"
            rb"password|passwd)\b\s*[:=]\s*[\"'][^\"'\r\n]{12,}[\"']"
        ),
    ),
    ("private-key", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("github-token", re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("slack-token", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
)
_TOKEN = re.compile(rb"[A-Za-z0-9._~+/=-]{12,}")


class ScanError(RuntimeError):
    """Raised when the scan cannot completely inspect its requested scope."""


@dataclass(frozen=True, order=True)
class Finding:
    path: Path
    line: int
    kind: str

    def render(self) -> str:
        return f"{self.path.as_posix()}:{self.line}: {self.kind}"


def _line_number(content: bytes, offset: int) -> int:
    return content.count(b"\n", 0, offset) + 1


def scan_files(
    paths: Iterable[Path], *, fingerprints: set[str] | None = None
) -> list[Finding]:
    """Scan every supplied file, failing if any file cannot be read."""
    fingerprints = {KNOWN_SECRET_SHA256} if fingerprints is None else fingerprints
    findings: set[Finding] = set()

    for path in paths:
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise ScanError(f"unable to read tracked file: {path.as_posix()}") from exc

        for kind, pattern in _CREDENTIAL_PATTERNS:
            for match in pattern.finditer(content):
                findings.add(Finding(path, _line_number(content, match.start()), kind))

        for token in _TOKEN.finditer(content):
            digest = hashlib.sha256(token.group()).hexdigest()
            if digest in fingerprints:
                findings.add(
                    Finding(path, _line_number(content, token.start()), "known-fingerprint")
                )

    return sorted(findings)


def tracked_files(root: Path) -> list[Path]:
    """Return Git-tracked files; fail closed if Git cannot enumerate them."""
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=False
    )
    if result.returncode != 0:
        raise ScanError("unable to enumerate Git-tracked files")

    relative_paths = [item for item in result.stdout.split(b"\0") if item]
    if not relative_paths:
        raise ScanError("Git reported no tracked files")

    return [root / item.decode("utf-8", errors="surrogateescape") for item in relative_paths]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        findings = scan_files(tracked_files(root))
    except ScanError as exc:
        print(f"credential scan ERROR: {exc}", file=sys.stderr)
        return 2

    if findings:
        print(f"credential scan FAILED: {len(findings)} finding(s)", file=sys.stderr)
        for finding in findings:
            try:
                relative = finding.path.relative_to(root)
            except ValueError:
                relative = finding.path
            print(Finding(relative, finding.line, finding.kind).render(), file=sys.stderr)
        return 1

    print("credential scan passed: all tracked current-tree files inspected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
