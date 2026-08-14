import unittest

from security_utils import (
    is_deployment_target_allowed,
    is_valid_host,
    is_valid_identifier,
    is_valid_known_hosts_line,
    is_valid_scan_target,
    parse_deployment_target_allowlist,
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

    def test_deployment_allowlist_is_fail_closed_and_normalized(self):
        self.assertEqual(parse_deployment_target_allowlist(None), {})
        allowlist = parse_deployment_target_allowlist(
            '{"user:user_123":["10.20.30.0/24","SERVER.EXAMPLE.COM.","10.20.30.10"],'
            '"org:org_456":["2001:db8::/64"]}'
        )
        self.assertEqual(
            allowlist["user:user_123"],
            ("10.20.30.0/24", "server.example.com", "10.20.30.10"),
        )
        self.assertEqual(allowlist["org:org_456"], ("2001:db8::/64",))

    def test_deployment_allowlist_rejects_invalid_principals_and_targets(self):
        bad_values = (
            "[]",
            '{"admin":["10.0.0.1"]}',
            '{"user:user_1":"10.0.0.1"}',
            '{"user:user_1":["10.0.0.1;id"]}',
            '{"user:user_1":["example.com --flag"]}',
        )
        for value in bad_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_deployment_target_allowlist(value)

    def test_deployment_authorization_supports_user_org_exact_and_cidr(self):
        allowlist = parse_deployment_target_allowlist(
            '{"user:user_123":["10.20.30.0/24","server.example.com"],'
            '"org:org_456":["2001:db8::/64","192.0.2.50"]}'
        )

        self.assertTrue(
            is_deployment_target_allowed(
                "10.20.30.45", "user_123", None, allowlist
            )
        )
        self.assertTrue(
            is_deployment_target_allowed(
                "SERVER.EXAMPLE.COM", "user_123", None, allowlist
            )
        )
        self.assertTrue(
            is_deployment_target_allowed(
                "2001:db8::beef", "user_other", "org_456", allowlist
            )
        )
        self.assertTrue(
            is_deployment_target_allowed(
                "192.0.2.50", "user_other", "org_456", allowlist
            )
        )
        self.assertFalse(
            is_deployment_target_allowed(
                "10.20.31.45", "user_123", None, allowlist
            )
        )
        self.assertFalse(
            is_deployment_target_allowed(
                "server.example.com", "user_other", None, allowlist
            )
        )
        # CIDRs authorize literal IPs only; DNS is never resolved for policy.
        self.assertFalse(
            is_deployment_target_allowed(
                "host.example.net", "user_other", "org_456", allowlist
            )
        )


if __name__ == "__main__":
    unittest.main()
