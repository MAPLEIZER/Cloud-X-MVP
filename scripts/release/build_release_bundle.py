#!/usr/bin/env python3
"""Render a digest-pinned Cloud-X appliance bundle and release manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / "deploy" / "appliance"

SEMVER = re.compile(r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
DIGEST_REF = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-tag", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--migration-revision", required=True)
    parser.add_argument("--frontend-image", required=True)
    parser.add_argument("--backend-image", required=True)
    parser.add_argument("--postgres-image", required=True)
    parser.add_argument("--redis-image", required=True)
    parser.add_argument("--nginx-image", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--signer-workflow", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def normalized_version(value: str) -> str:
    if not SEMVER.fullmatch(value):
        raise ValueError(f"version must be semantic vX.Y.Z or X.Y.Z: {value}")
    return value.removeprefix("v")


def validate_digest_ref(name: str, value: str) -> str:
    if not DIGEST_REF.fullmatch(value):
        raise ValueError(f"{name} must be an immutable OCI digest reference: {value}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    version = normalized_version(args.version)
    if not REPOSITORY.fullmatch(args.repository):
        raise ValueError("repository must be owner/name")
    expected_workflow = f"github.com/{args.repository}/.github/workflows/release.yml"
    if args.signer_workflow != expected_workflow:
        raise ValueError(f"signer-workflow must be {expected_workflow}")

    images = {
        "frontend": validate_digest_ref("frontend-image", args.frontend_image),
        "backend": validate_digest_ref("backend-image", args.backend_image),
        "postgres": validate_digest_ref("postgres-image", args.postgres_image),
        "redis": validate_digest_ref("redis-image", args.redis_image),
        "nginx": validate_digest_ref("nginx-image", args.nginx_image),
    }

    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    (output / "scripts").mkdir(parents=True)
    (output / "manifests").mkdir()
    (output / "evidence").mkdir()

    compose = (TEMPLATE_DIR / "compose.template.yaml").read_text(encoding="utf-8")
    replacements = {
        "__CLOUDX_VERSION__": version,
        "__FRONTEND_IMAGE__": images["frontend"],
        "__BACKEND_IMAGE__": images["backend"],
        "__POSTGRES_IMAGE__": images["postgres"],
        "__REDIS_IMAGE__": images["redis"],
        "__NGINX_IMAGE__": images["nginx"],
    }
    for token, replacement in replacements.items():
        compose = compose.replace(token, replacement)
    unresolved = sorted(set(re.findall(r"__[A-Z0-9_]+__", compose)))
    if unresolved:
        raise ValueError(f"unresolved bundle template tokens: {', '.join(unresolved)}")

    (output / "compose.yaml").write_text(compose, encoding="utf-8")
    shutil.copy2(TEMPLATE_DIR / "nginx.conf.template", output / "nginx.conf.template")
    shutil.copy2(TEMPLATE_DIR / ".env.example", output / ".env.example")
    scripts = ("install.sh", "verify.sh", "verify-attestations.sh", "upgrade.sh", "rollback.sh")
    for script in scripts:
        target = output / "scripts" / script
        shutil.copy2(TEMPLATE_DIR / "scripts" / script, target)
        target.chmod(0o755)

    manifest = {
        "schema_version": 1,
        "version": version,
        "source": {
            "tag": args.source_tag,
            "commit": args.source_commit,
        },
        "supported_architectures": ["linux/amd64"],
        "runtime_requirements": {
            "docker_engine": "supported current Docker Engine",
            "docker_compose": "Compose v2",
        },
        "compatibility": {
            "manifest": None,
            "sha256": None,
            "status": "shared compatibility contract is tracked in #93",
        },
        "database": {
            "migration_revision": args.migration_revision,
        },
        "endpoint_artifacts": {},
        "images": images,
        "evidence": {
            "oci_sbom": "BuildKit SBOM attestation attached to each Cloud-X OCI image",
            "oci_provenance": "GitHub artifact attestation attached to each Cloud-X OCI image and pushed to the registry",
            "release_checksums": "SHA256SUMS",
            "signature_policy": {
                "type": "github-artifact-attestation",
                "repository": args.repository,
                "signer_workflow": args.signer_workflow,
                "oidc_issuer": "https://token.actions.githubusercontent.com",
                "operator_verifier": "scripts/verify-attestations.sh",
                "archive_attestation": "published beside the appliance archive in the GitHub prerelease",
            },
        },
    }
    manifest_path = output / "manifests" / "release.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    checksum_targets = [
        output / "compose.yaml",
        output / "nginx.conf.template",
        output / ".env.example",
        manifest_path,
        *(output / "scripts" / name for name in scripts),
    ]
    lines = []
    for path in checksum_targets:
        relative = path.relative_to(output)
        lines.append(f"{sha256_file(path)}  {relative.as_posix()}")
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
