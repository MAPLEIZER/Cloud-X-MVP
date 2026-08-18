# Cloud-X Phase 1 appliance operator runbook

This runbook takes a clean supported pilot host to a verified HTTPS Cloud-X appliance. It is an **acceptance procedure for pre-production candidates**, not permission to label the current product production-supported before #28 and #24 are complete.

## 1. Provision the host

Use the profile in [`PILOT_HOSTING.md`](PILOT_HOSTING.md): Ubuntu 24.04 LTS x86_64, at least 4 vCPU, 8 GiB RAM and 40 GiB free persistent disk. Assign a stable public address and create a DNS record for the Cloud-X hostname.

At the provider firewall/security-group layer:

- allow TCP 80 and 443 from intended users/ACME;
- allow TCP 22 only from the administration CIDR/VPN;
- do not publish 5001, 5432 or 6379;
- allow required outbound HTTPS/DNS/NTP plus explicitly authorized Wazuh/scan-target routes.

## 2. Install host prerequisites

Install Docker Engine from Docker's official Ubuntu repository rather than the convenience script:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg openssl python3 jq
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
sudo docker compose version
```

Install current GitHub CLI from GitHub's official APT repository; the Ubuntu community package can lag behind attestation features:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
  | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
sudo apt update
sudo apt install -y gh
gh attestation --help >/dev/null
```

## 3. Download and verify a candidate before extraction

Replace the version with the candidate being accepted:

```bash
export CLOUDX_VERSION=v0.2.0
mkdir -p "$HOME/cloudx-candidate-$CLOUDX_VERSION"
cd "$HOME/cloudx-candidate-$CLOUDX_VERSION"

gh release download "$CLOUDX_VERSION" \
  --repo MAPLEIZER/Cloud-X-MVP \
  --pattern "cloudx-appliance-$CLOUDX_VERSION.tar.gz" \
  --pattern "cloudx-appliance-$CLOUDX_VERSION.tar.gz.sha256" \
  --pattern "cloudx-appliance-$CLOUDX_VERSION.attestation.jsonl" \
  --pattern "trusted_root.jsonl"

sha256sum -c "cloudx-appliance-$CLOUDX_VERSION.tar.gz.sha256"

gh attestation verify "cloudx-appliance-$CLOUDX_VERSION.tar.gz" \
  --repo MAPLEIZER/Cloud-X-MVP \
  --signer-workflow github.com/MAPLEIZER/Cloud-X-MVP/.github/workflows/release.yml \
  --cert-oidc-issuer https://token.actions.githubusercontent.com
```

If GHCR packages are not public, authenticate an operator account/token with read-only package access before OCI verification or `docker compose pull`. Do not use a repository write token on the appliance host.

## 4. Install the bundle and configure secrets

```bash
sudo mkdir -p /opt/cloudx/releases
sudo tar -xzf "cloudx-appliance-$CLOUDX_VERSION.tar.gz" -C /opt/cloudx/releases
sudo ln -sfn "/opt/cloudx/releases/cloudx-appliance-$CLOUDX_VERSION" /opt/cloudx/current
cd /opt/cloudx/current
sudo cp .env.example .env
sudo chmod 0600 .env
sudoedit .env
```

Replace every placeholder. Keep `CLOUDX_API_BASE_URL` empty for same-origin API routing. Set `CLOUDX_PUBLIC_HOSTNAME` and `CLERK_AUTHORIZED_PARTIES` to the real HTTPS origin. Keep deployment target allow-lists narrower than the networks reachable from the host.

## 5. Provision TLS

The appliance mounts stable host-owned copies at `/etc/cloudx/tls/fullchain.pem` and `/etc/cloudx/tls/privkey.pem`. Do not point the Compose file directly at a provider's rotating/symlinked certificate archive unless its renewal semantics have been tested.

For a Let's Encrypt pilot, install current Certbot using its supported packaging path and obtain the first certificate while port 80 is free. Example with Certbot's standalone HTTP challenge:

```bash
export CLOUDX_FQDN=cloudx.example.com
export ACME_EMAIL=security@example.com
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/local/bin/certbot
sudo certbot certonly --standalone \
  --non-interactive --agree-tos \
  --email "$ACME_EMAIL" \
  -d "$CLOUDX_FQDN"

sudo mkdir -p /etc/cloudx/tls
cd /opt/cloudx/current
sudo ./scripts/sync-tls.sh \
  "/etc/letsencrypt/live/$CLOUDX_FQDN/fullchain.pem" \
  "/etc/letsencrypt/live/$CLOUDX_FQDN/privkey.pem"
```

`sync-tls.sh` validates certificate freshness and certificate/private-key matching before copying, keeps the private key mode at `0600`, and reloads nginx only after the synchronized pair validates.

For automated renewal, prefer a Certbot DNS plugin or a provider-managed certificate path that does not contend with port 80. If the standalone authenticator is retained, renewal requires a brief reverse-proxy stop while Certbot binds port 80; use pre/post hooks and call `sync-tls.sh` as the deploy hook. Test the exact hook chain with `sudo certbot renew --dry-run` before accepting the pilot.

## 6. Run host preflight and artifact verification

```bash
cd /opt/cloudx/current
sudo ./scripts/host-preflight.sh
./scripts/verify-attestations.sh
sudo ./scripts/verify.sh
```

`host-preflight.sh` rejects an unvalidated OS/architecture, insufficient pilot resources, an overly-readable `.env`, unresolved placeholders, missing DNS, invalid/mismatched TLS material, unavailable Docker/Compose, or invalid Compose configuration.

## 7. Start the appliance

```bash
cd /opt/cloudx/current
sudo ./scripts/install.sh
sudo docker compose --env-file .env -f compose.yaml ps
```

Then verify from a separate client, not only from the host:

```bash
curl --fail --show-error --silent https://cloudx.example.com/_health/live
curl --fail --show-error --silent https://cloudx.example.com/_health/ready
```

Confirm externally that only intended ports are reachable. On the host, `ss -ltnp` must not show host-published listeners for Cloud-X backend 5001, PostgreSQL 5432 or Redis 6379.

## 8. Connect Wazuh and complete #24 acceptance

Configure Manager and Indexer URLs/credentials/CA trust in `.env`, then verify a real enrolled endpoint appears in Cloud-X with live agent inventory plus real alert, SCA and FIM data. A healthy empty/mock connector is not #24 acceptance.

## 9. Upgrade and rollback discipline

Before an upgrade, take a provider snapshot **and** a logical PostgreSQL backup. Example:

```bash
cd /opt/cloudx/current
sudo mkdir -p /var/backups/cloudx
sudo docker compose --env-file .env -f compose.yaml exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | gzip -9 | sudo tee "/var/backups/cloudx/postgres-$(date -u +%Y%m%dT%H%M%SZ).sql.gz" >/dev/null
```

Verify the backup is non-empty and record its SHA-256 before migration. Then use the versioned upgrade script from the current bundle, passing the fully verified new bundle directory.

`rollback.sh` intentionally refuses automatic schema downgrade. Set `CLOUDX_ALLOW_SCHEMA_COMPATIBLE_ROLLBACK=true` only when the release notes explicitly prove the prior application is compatible with the current schema. For an incompatible migration, restore a tested pre-upgrade database backup in a maintenance window instead of guessing at Alembic downgrades.

## 10. Acceptance evidence to retain

For each pilot, retain:

- provider/region and host specification;
- DNS name and certificate issuer/expiry, never the private key;
- release tag, source commit and `release.json`;
- archive checksum and attestation verification output;
- image digests and `docker compose ps` output;
- host-preflight output;
- external liveness/readiness results;
- backup checksum and upgrade/rollback test result;
- #24 live Wazuh evidence;
- any exception/waiver used during the release.

The pilot is not a supported Cloud-X release until the evidence above exists and the remaining #28 acceptance items are closed.

## Upstream operational references

- Docker Engine on Ubuntu: https://docs.docker.com/engine/install/ubuntu/
- Docker Compose plugin: https://docs.docker.com/compose/install/linux/
- GitHub CLI Linux packages: https://github.com/cli/cli/blob/trunk/docs/install_linux.md
- GitHub attestation verification: https://cli.github.com/manual/gh_attestation_verify
- Certbot instructions: https://certbot.eff.org/instructions
