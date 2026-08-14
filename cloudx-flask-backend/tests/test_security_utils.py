import unittest

from security_utils import (
    is_valid_host,
    is_valid_identifier,
    is_valid_known_hosts_line,
    is_valid_scan_target,
    parse_origin_csv,
)


class SecurityValidationTests(unittest.TestCase):
    def test_valid_scan_targets(self):
        for target in (
            "127.0.0.1",
            "192.168.1.0/24",
            "2001:db8::1",
            "2001:db8::/64",
            "scanner.example.com",
        ):
            with self.subTest(target=target):
                self.assertTrue(is_valid_scan_target(target))

    def test_cli_option_and_whitespace_injection_are_rejected(self):
        for target in (
            "-iL",
            "--script=unsafe",
            "127.0.0.1 --script vuln",
            "example.com\n--script vuln",
            " example.com",
            "example.com ",
        ):
            with self.subTest(target=target):
                self.assertFalse(is_valid_scan_target(target))

    def test_shell_metacharacters_are_not_valid_hosts(self):
        for target in (
            "example.com;id",
            "example.com&&id",
            "$(id)",
            "`id`",
            "example.com|id",
        ):
            with self.subTest(target=target):
                self.assertFalse(is_valid_host(target))

    def test_deployment_identifiers_are_restricted(self):
        for value in ("agent-01", "prod.group", "default_1"):
            self.assertTrue(is_valid_identifier(value))

        for value in ("agent;id", "agent name", "$(id)", "../agent", ""):
            self.assertFalse(is_valid_identifier(value))

    def test_known_hosts_line_must_be_single_line(self):
        self.assertTrue(
            is_valid_known_hosts_line(
                "example.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEexample"
            )
        )
        self.assertFalse(
            is_valid_known_hosts_line(
                "example.com ssh-ed25519 AAAA\nattacker ssh-rsa BBBB"
            )
        )

    def test_origin_allowlist_parsing(self):
        self.assertEqual(
            parse_origin_csv(
                "https://cloudx.example.com, http://localhost:5173/"
            ),
            ["https://cloudx.example.com", "http://localhost:5173"],
        )

        for bad in (
            "javascript:alert(1)",
            "https://user:pass@example.com",
            "https://example.com/path",
        ):
            with self.subTest(origin=bad):
                with self.assertRaises(ValueError):
                    parse_origin_csv(bad)


if __name__ == "__main__":
    unittest.main()
