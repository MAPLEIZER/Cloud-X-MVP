# Cloud-X release appliance

Issue #28 owns the production appliance and release-engineering acceptance.

## Release boundary

Normal branch and pull-request CI remains build/test-only. Customer-consumable artifacts are produced only by `.github/workflows/release.yml` from a semantic-version tag (`vX.Y.Z`) whose commit is already contained in `main`.

The release workflow publishes:

- `ghcr.io/mapleizer/cloudx-frontend:<tag>`;
- `ghcr.io/mapleizer/cloudx-backend:<tag>`;
- OCI SBOM/provenance attestations from BuildKit;
- a `cloudx-appliance-<tag>.tar.gz` bundle whose Compose file pins Cloud-X and infrastructure images by immutable digest;
- release and archive SHA-256 checksums.

The scan worker deliberately uses the exact backend image digest used by the API.

## Environment-neutral frontend image

The frontend no longer requires a customer-specific rebuild for the API origin or Clerk publishable key.

At container startup, `deploy/frontend/10-cloudx-runtime-config.sh` writes `/cloudx-config.js` from:

- `CLOUDX_API_BASE_URL` — empty means same-origin `/api`; root-relative and HTTPS/HTTP values are also accepted;
- `CLERK_PUBLISHABLE_KEY` — required.

`index.html` loads this file before the application bundle. Vite build-time variables remain development/backward-compatible fallbacks, but supported appliance releases configure these values at runtime.

## Host prerequisites

For the first supported pilot profile:

- Linux/amd64;
- Docker Engine with Docker Compose v2;
- outbound registry access to the release image registry, unless images have been mirrored;
- a DNS name for Cloud-X;
- an existing TLS certificate and private key readable by Docker;
- Wazuh Manager/Indexer connectivity where the Wazuh integration is enabled.

The bundle does not generate or renew public certificates. Use Let's Encrypt, a managed certificate, or an organization/private PKI as appropriate for the deployment.

## Install

1. Extract the release archive.
2. Copy `.env.example` to `.env`.
3. Replace every placeholder and set `CLOUDX_TLS_CERT_FILE` / `CLOUDX_TLS_KEY_FILE`.
4. Run:

```bash
./scripts/verify.sh
./scripts/install.sh
```

Only ports 80 and 443 are published by the appliance. Port 80 redirects to HTTPS. PostgreSQL, Redis, backend, worker and frontend stay on the Compose network.

## Verification

`verify.sh`:

- validates `SHA256SUMS`;
- rejects any mutable image reference in `release.json`;
- validates the rendered Compose configuration;
- can optionally probe live readiness when `CLOUDX_VERIFY_LIVE=true` and `CLOUDX_VERIFY_ORIGIN=https://...` are set.

The release workflow itself also proves that the release tag resolves to a commit contained in `main`.

## Upgrade

Run the upgrade script from the currently deployed bundle:

```bash
./scripts/upgrade.sh /opt/cloudx/cloudx-appliance-v0.3.0
```

It carries forward `.env`, verifies the new bundle, pulls pinned images, runs `alembic upgrade head` with the new backend image, starts the new release and records the previous bundle path.

## Rollback

From the new bundle:

```bash
CLOUDX_ALLOW_SCHEMA_COMPATIBLE_ROLLBACK=true ./scripts/rollback.sh
```

Rollback is intentionally conservative: it does **not** run an Alembic downgrade automatically and is blocked unless the operator explicitly asserts schema compatibility. A release is rollback-compatible only when its migration notes explicitly say the previous application can safely run against the upgraded schema.

## Remaining #28 acceptance gates

This slice establishes the immutable release contract and appliance mechanics. Issue #28 remains open until all of the following have evidence:

- Cosign/Sigstore or equivalent release-signing identity/policy, including immediate verification of produced signatures;
- real clean-host install, upgrade and rollback acceptance;
- production certificate issuance/renewal runbook or managed-certificate path;
- pilot hosting choice, including Kenya/East-Africa data-residency considerations;
- zero unwaived exploitable Critical/High vulnerabilities at release time.

Do not create a `vX.Y.Z` release tag until those remaining support gates are intentionally accepted for the pilot release.
