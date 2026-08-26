# Credential handling

Recovery utilities that dispatch to the RAE kernel require
`RAE_KERNEL_API_KEY` from the runtime environment. Callers may inject the same
value explicitly where a constructor supports it. The utilities fail before
protected work or local-state mutation when configuration is absent; no
fallback credential is embedded in source.

Run the repository security gate with:

```text
python scripts/security_scan.py
python -m unittest discover -s tests -v
```

The scanner inspects every Git-tracked file in the current checkout, applies
credential-pattern rules, and checks a one-way fingerprint for the credential
removed by PR #2. Findings contain only path, line number, and rule name; the
scanner never prints matched content. An unreadable file or inability to
enumerate tracked files is an error, so the gate fails closed.

## Operator-required incident follow-up

Removing credential material from the current source tree does **not** revoke
or rotate it, and does **not** remove it from existing Git history. An
authorized operator must separately:

1. rotate or revoke the exposed credential at its provider;
2. update the runtime secret configuration with the replacement; and
3. assess and perform Git-history remediation, including coordination with
   maintainers and downstream clones, if required by the incident response
   policy.

This repository change performs none of those provider or history operations.
