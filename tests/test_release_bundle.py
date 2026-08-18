import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "release" / "build_release_bundle.py"
DIGEST = "a" * 64


class ReleaseBundleTests(unittest.TestCase):
    def _command(self, output: Path) -> list[str]:
        digest = f"sha256:{DIGEST}"
        return [
            sys.executable,
            str(BUILDER),
            "--version",
            "v0.2.0",
            "--source-tag",
            "v0.2.0",
            "--source-commit",
            "1" * 40,
            "--migration-revision",
            "20260814_0002",
            "--frontend-image",
            f"ghcr.io/mapleizer/cloudx-frontend@{digest}",
            "--backend-image",
            f"ghcr.io/mapleizer/cloudx-backend@{digest}",
            "--postgres-image",
            f"postgres@{digest}",
            "--redis-image",
            f"redis@{digest}",
            "--nginx-image",
            f"nginx@{digest}",
            "--repository",
            "MAPLEIZER/Cloud-X-MVP",
            "--signer-workflow",
            "github.com/MAPLEIZER/Cloud-X-MVP/.github/workflows/release.yml",
            "--output",
            str(output),
        ]

    def test_bundle_is_digest_pinned_signed_and_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "cloudx-appliance-v0.2.0"
            subprocess.run(self._command(output), cwd=ROOT, check=True)

            compose = (output / "compose.yaml").read_text(encoding="utf-8")
            self.assertIn("ghcr.io/mapleizer/cloudx-frontend@sha256:", compose)
            self.assertIn("ghcr.io/mapleizer/cloudx-backend@sha256:", compose)
            self.assertNotIn("__FRONTEND_IMAGE__", compose)

            manifest = json.loads(
                (output / "manifests" / "release.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["version"], "0.2.0")
            self.assertEqual(
                manifest["database"]["migration_revision"], "20260814_0002"
            )
            self.assertTrue(
                manifest["images"]["backend"].startswith(
                    "ghcr.io/mapleizer/cloudx-backend@sha256:"
                )
            )
            policy = manifest["evidence"]["signature_policy"]
            self.assertEqual(policy["type"], "github-artifact-attestation")
            self.assertEqual(policy["repository"], "MAPLEIZER/Cloud-X-MVP")
            self.assertEqual(
                policy["signer_workflow"],
                "github.com/MAPLEIZER/Cloud-X-MVP/.github/workflows/release.yml",
            )
            self.assertTrue((output / "scripts" / "verify-attestations.sh").is_file())
            self.assertTrue((output / "SHA256SUMS").is_file())

    def test_mutable_image_tag_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "bundle"
            command = self._command(output)
            index = command.index("--frontend-image") + 1
            command[index] = "ghcr.io/mapleizer/cloudx-frontend:v0.2.0"
            result = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("immutable OCI digest reference", result.stderr)

    def test_signer_workflow_is_repository_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "bundle"
            command = self._command(output)
            index = command.index("--signer-workflow") + 1
            command[index] = "github.com/attacker/repo/.github/workflows/release.yml"
            result = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("signer-workflow must be", result.stderr)

    def test_release_workflow_enforces_attestation_identity_and_immutability(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("id-token: write", workflow)
        self.assertIn("attestations: write", workflow)
        self.assertIn("actions/attest@508db95dd578ae2727ebd6217d5ba78e4fbda05d", workflow)
        self.assertIn("--signer-workflow", workflow)
        self.assertIn("--cert-oidc-issuer", workflow)
        self.assertIn("--prerelease", workflow)
        self.assertNotIn("--clobber", workflow)
        self.assertLess(
            workflow.index("Refuse existing release mutation"),
            workflow.index("Build and publish frontend"),
        )


if __name__ == "__main__":
    unittest.main()
