# Deployment provenance status

No deployment path from this repository to `rae-monetization-gateway` is
established. Do not deploy this recovery tree to that app.

## Source-first evidence (2026-08-26)

- Fly release `v5` is the current completed release and dates to 2026-08-03.
- Its running image digest is
  `sha256:b2cfec1e982d4c667764a57a1784f00ade587b7a8b348dd729b7234396cc2021`.
- `flyctl image show` reports no OCI source or revision labels for that image.
- The live `/healthz`, `/v1/products`, and `/openapi.json` responses still
  advertise priced, successful paid fulfillment and therefore do not match
  this repository's fail-closed behavior.
- The removed `fly.toml` named the live app but referenced a `Dockerfile` that
  is absent from the tracked tree. The repository also has no deployment
  workflow for this app. That manifest was not a reproducible source mapping.
- GitHub code search under the repository owner found no separately indexed
  source reference that binds this app and image digest to a canonical commit.

## Blocker

A deployment workflow must not be added until authoritative evidence identifies
the canonical source repository and exact revision for the running app. The
source must then provide a reproducible image build, immutable repository and
revision labels, an app-scoped reviewed release workflow, rollback instructions,
and post-deploy probes that confirm every paid route remains fail-closed.

This record documents the blocker only. It is not a deployment manifest or a
manual deployment instruction.