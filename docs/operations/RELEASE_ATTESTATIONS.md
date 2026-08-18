# Cloud-X release attestation policy

Cloud-X release candidates use GitHub artifact attestations backed by Sigstore identity. The release workflow signs provenance for the published frontend/backend OCI digests and the appliance archive. BuildKit SBOM/provenance remains attached to the OCI images as additional evidence.

## Trusted identity

A candidate is accepted only when its attestation verifies against all of these constraints:

- repository: `MAPLEIZER/Cloud-X-MVP`;
- signer workflow: `github.com/MAPLEIZER/Cloud-X-MVP/.github/workflows/release.yml`;
- OIDC issuer: `https://token.actions.githubusercontent.com`;
- exact artifact or OCI digest being consumed.

Repository-only verification is intentionally insufficient because another workflow in the same repository should not automatically inherit release-signing authority.

## Online verification

Authenticate to GHCR before verifying OCI images. For a release bundle, `scripts/verify-attestations.sh` reads the digest-pinned image references and signing policy from `manifests/release.json`, then runs `gh attestation verify` against the repository, signer workflow and OIDC issuer.

The appliance archive itself must be verified before extraction:

```bash
gh attestation verify cloudx-appliance-v0.2.0.tar.gz \
  --repo MAPLEIZER/Cloud-X-MVP \
  --signer-workflow github.com/MAPLEIZER/Cloud-X-MVP/.github/workflows/release.yml \
  --cert-oidc-issuer https://token.actions.githubusercontent.com
```

## Offline verification

Each GitHub prerelease also carries the archive attestation bundle and a `trusted_root.jsonl` snapshot. In a disconnected environment, import the archive, attestation JSONL, trusted root and GitHub CLI, then run `gh attestation verify` with `--bundle` and `--custom-trusted-root` while retaining the same repository/signer identity constraints.

The trusted-root snapshot proves signatures against the imported trust material; it does not provide future revocation awareness. Refresh trusted roots whenever new release material is transferred into an offline environment.

## Boundary

Artifact attestations establish provenance and signer identity; they do not prove the software is vulnerability-free or operationally accepted. Release-time dependency audits, digest pinning, checksums, #24 live Wazuh acceptance and #28 real-host install/upgrade/rollback evidence remain separate gates.
