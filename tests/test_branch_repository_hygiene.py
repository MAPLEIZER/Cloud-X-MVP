from pathlib import Path, PurePosixPath
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RepositoryHygieneTests(unittest.TestCase):
    @staticmethod
    def _tracked_files():
        output = subprocess.check_output(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
        )
        return [path for path in output.decode().split("\0") if path]

    def test_forbidden_local_artifacts_are_not_tracked(self):
        forbidden_suffixes = {".db", ".sqlite", ".sqlite3", ".pfx", ".p12", ".key", ".pem"}
        forbidden_directories = {"node_modules", "venv", ".venv", "__pycache__"}
        violations = []

        for tracked in self._tracked_files():
            path = PurePosixPath(tracked)
            if forbidden_directories.intersection(path.parts):
                violations.append(tracked)
                continue
            if path.suffix.lower() in forbidden_suffixes:
                violations.append(tracked)
                continue
            if path.name == "cloudx-code-signing.cer":
                violations.append(tracked)
                continue
            if path.name == ".env" or (
                path.name.startswith(".env.") and path.name != ".env.example"
            ):
                violations.append(tracked)

        self.assertEqual(violations, [], f"Forbidden tracked artifacts: {violations}")

    def test_canonical_environment_example_covers_cross_stack_configuration(self):
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        required_names = (
            "VITE_API_BASE_URL",
            "VITE_CLERK_PUBLISHABLE_KEY",
            "CLERK_SECRET_KEY",
            "CLERK_AUTHORIZED_PARTIES",
            "CLERK_ALLOWED_USER_IDS",
            "DEPLOYMENT_TARGET_ALLOWLIST_JSON",
            "DATABASE_URL",
            "WAZUH_API_URL",
            "WAZUH_API_USERNAME",
            "WAZUH_API_PASSWORD",
            "WAZUH_API_VERIFY_TLS",
            "WAZUH_INDEXER_URL",
            "WAZUH_INDEXER_USERNAME",
            "WAZUH_INDEXER_PASSWORD",
            "WAZUH_INDEXER_VERIFY_TLS",
            "WAZUH_REQUEST_TIMEOUT_SECONDS",
            "WAZUH_CACHE_TTL_SECONDS",
        )
        for name in required_names:
            with self.subTest(name=name):
                self.assertIn(f"{name}=", env_example)

    def test_gitignore_blocks_common_secret_and_runtime_artifacts(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (
            ".env.*",
            "venv/",
            "*.db",
            "*.sqlite3",
            "__pycache__/",
            "*.pfx",
            "*.p12",
            "*.key",
            "*.pem",
        ):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, gitignore)


if __name__ == "__main__":
    unittest.main()
