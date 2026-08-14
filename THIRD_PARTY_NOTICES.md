# Third-Party Notices

Cloud-X combines Cloud-X-authored code with open-source dependencies and integrates with separately distributed security products/components. The MIT license in this repository applies only to Cloud-X-authored code unless a file or component states otherwise.

This document is a project-level provenance guide, not a substitute for the license files distributed with each dependency or component. Before a commercial release, generate a release-specific SBOM and license inventory from the exact dependency lockfiles and container images.

## Primary integrated / evaluated projects

| Project | Role in / around Cloud-X | Upstream license (project-level) | Notes |
|---|---|---|---|
| Wazuh | Initial endpoint/security-event engine | GPL-2.0 | Remains a separate upstream component; Cloud-X integrates through supported APIs/configuration surfaces. |
| shadcn/ui | UI component source/patterns | MIT | Preserve notices for copied/adapted source where required. |
| shadcn-admin | Historical dashboard inspiration/source material | MIT at upstream project at time of review | Legacy `Cloud-X-Dashboard` contained substantial upstream README/provenance material; preserve attribution when migrating unique UI code. |
| Suricata | Candidate optional NIDS sensor | GPL-2.0 | Not part of the MVP core. |
| Zeek | Candidate optional network-analysis sensor | BSD-style license | Not part of the MVP core. |
| Velociraptor | Candidate optional DFIR integration | AGPL-3.0 | Not part of the MVP core; service/distribution obligations require review before product packaging. |
| Greenbone/OpenVAS/GVM | Candidate optional vulnerability-scanning integration | GPL/AGPL-family licenses across components | Not part of the MVP core. |

## Important dependency rule

Do not copy third-party source into Cloud-X merely to simplify deployment. Prefer supported APIs, package repositories, container images or separately distributed upstream artifacts. When source is copied or adapted, retain the original copyright/license notice and document the provenance here.

## Release requirements

Before any supported release:

- generate an SPDX or CycloneDX SBOM;
- run a license-policy scan over production dependencies;
- retain upstream notices required by shipped artifacts;
- document the exact Wazuh compatibility range;
- record hashes/signatures for downloadable endpoint packages;
- obtain legal review for any distribution/service model involving strong-copyleft or source-available components where the intended use is unclear.

## Upstream references

- Wazuh: https://github.com/wazuh/wazuh
- shadcn/ui: https://github.com/shadcn-ui/ui
- shadcn-admin: https://github.com/satnaing/shadcn-admin
- Suricata: https://github.com/OISF/suricata
- Zeek: https://github.com/zeek/zeek
- Velociraptor: https://github.com/Velocidex/velociraptor
- Greenbone Community Edition: https://github.com/greenbone
