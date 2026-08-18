# Cloud-X Phase 1 pilot hosting decision

**Decision snapshot:** 18 August 2026  
**Applies to:** Phase 1 appliance acceptance in #28  
**Support profile:** one dedicated Ubuntu 24.04 LTS x86_64 VM running the Cloud-X appliance; Wazuh Manager/Indexer remain connected security-engine services rather than being bundled into this VM.

## Decision

For a Kenya-resident pilot, prefer a **Safaricom Cloud virtual data centre / VM physically hosted in Kenya**, with Nairobi as the first placement and Kisumu as a DR/alternate-location option where the commercial service order supports it. Safaricom's published Cloud material describes a local server base and data centres in Nairobi and Kisumu. Procurement must still confirm the exact VM location, SLA, backup location, support boundary and current service capabilities in the signed order before Cloud-X treats the placement as Kenya-resident.

If the pilot does **not** require data to remain in Kenya, use **AWS Africa (Cape Town), `af-south-1`** as the first hyperscaler fallback. It is an active AWS Region. This is an African regional placement, not Kenya residency.

Do not make the Phase 1 pilot depend on announced-but-not-generally-available Kenya hyperscaler capacity. As of this decision date, AWS lists the Nairobi Local Zone as announced/request-interest rather than available, and Microsoft's current Azure region catalog lists its South African regions but not a generally available Kenya region. Google Cloud's current African region is Johannesburg (`africa-south1`). Recheck provider catalogs before every material hosting decision.

## Why this model

Cloud-X is currently a Compose appliance, not a Kubernetes product. A dedicated VM keeps the operational boundary inspectable: one host, digest-pinned containers, one reverse proxy, local PostgreSQL/Redis volumes, explicit backups and a small number of network paths. It also matches the product-validation goal of proving that an operator can install and support the appliance without a developer-specific platform.

## Pilot host profile

The initial validated support floor is:

| Resource | Support floor | Recommended pilot target |
|---|---:|---:|
| OS | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS |
| Architecture | x86_64 / amd64 | x86_64 / amd64 |
| CPU | 4 vCPU | 8 vCPU |
| RAM | 8 GiB | 16 GiB |
| Free persistent disk | 40 GiB | 100+ GiB SSD |
| Public ingress | TCP 80/443 | TCP 80/443 |
| Administrative ingress | SSH only from an admin CIDR/VPN | private/overlay management preferred |

These are Phase 1 support bounds, not performance claims. Increase storage based on PostgreSQL growth, retained scan results, Docker image/cache growth and the provider's snapshot/backup policy.

## Network boundary

Only the reverse proxy is host-published. Do not expose backend `5001`, PostgreSQL `5432` or Redis `6379` to the Internet. Provider firewall/security-group rules should permit 80/443 publicly, restrict SSH to known administration networks, and permit only the outbound destinations Cloud-X actually needs.

Network scanning must reach only configured/authorized target networks. If Cloud-X is hosted outside a customer's LAN, use an explicitly managed site-to-site VPN or overlay route and keep `DEPLOYMENT_TARGET_ALLOWLIST_JSON` narrower than the routed network. A public cloud route is not authorization to scan it.

## Residency boundary

Placing the Cloud-X VM in Kenya does not by itself make the whole security service Kenya-resident. Record the location and transfer posture of:

- PostgreSQL volumes, host/provider snapshots and exported backups;
- Wazuh Manager and Indexer, because they hold endpoint/security telemetry;
- centralized error tracking if enabled;
- any RMM/ticketing/integration destination added later;
- release/operational logs that contain customer identifiers.

Treat this as an engineering residency profile, not a legal conclusion about a customer's obligations under Kenyan data-protection law. Customer-specific legal classification and transfer requirements remain part of deployment approval.

## Provider evidence used for this snapshot

- Safaricom Cloud overview: https://newsroom.safaricom.co.ke/innovation/its-in-the-cloud-simple/
- Safaricom Cloud service terms: https://www.safaricom.co.ke/media-center-landing/terms-and-conditions/cloud-services
- AWS Regions: https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html
- AWS Local Zones locations: https://aws.amazon.com/about-aws/global-infrastructure/localzones/locations/
- Azure region catalog: https://azure.microsoft.com/explore/global-infrastructure/geographies
- Google Cloud locations: https://cloud.google.com/about/locations

Provider availability is time-sensitive. Revalidate this section before provisioning a new pilot.
