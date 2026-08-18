import time
import unittest

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import Flask

import auth


class ClerkJwtVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")
        cls.public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")

    def setUp(self):
        self.app = Flask(__name__)
        self.allowed_party = "https://cloudx.example"

    def _token(self, **overrides):
        now = int(time.time())
        payload = {
            "iss": "https://example.clerk.accounts.dev",
            "sub": "user_ci",
            "sid": "sess_ci",
            "azp": self.allowed_party,
            "iat": now,
            "nbf": now - 1,
            "exp": now + 60,
        }
        payload.update(overrides)
        return jwt.encode(
            payload,
            self.private_key,
            algorithm="RS256",
            headers={"typ": "JWT"},
        )

    def _verify(self, token):
        with self.app.test_request_context(
            "/api/test",
            headers={"Authorization": f"Bearer {token}"},
        ):
            return auth.authenticate_request(
                auth.request,
                jwt_key=self.public_key,
                authorized_parties=[self.allowed_party],
            )

    def test_valid_session_token_is_accepted(self):
        state = self._verify(self._token())
        self.assertTrue(state.is_signed_in)
        self.assertEqual(state.payload["sub"], "user_ci")

    def test_wrong_authorized_party_is_rejected(self):
        with self.assertRaises(jwt.InvalidTokenError):
            self._verify(self._token(azp="https://evil.example"))

    def test_pending_clerk_session_is_rejected(self):
        with self.assertRaises(jwt.InvalidTokenError):
            self._verify(self._token(sts="pending"))

    def test_expired_session_is_rejected(self):
        now = int(time.time())
        with self.assertRaises(jwt.ExpiredSignatureError):
            self._verify(self._token(exp=now - 30, nbf=now - 60))

    def test_non_rs256_token_is_rejected_before_decode(self):
        token = jwt.encode(
            {
                "iss": "https://example.clerk.accounts.dev",
                "sub": "user_ci",
                "nbf": int(time.time()) - 1,
                "exp": int(time.time()) + 60,
            },
            "unit-test-secret",
            algorithm="HS256",
            headers={"typ": "JWT"},
        )
        with self.assertRaises(jwt.InvalidAlgorithmError):
            self._verify(token)

    def test_same_origin_session_cookie_is_supported(self):
        token = self._token()
        with self.app.test_request_context("/api/test"):
            auth.request.cookies  # ensure Flask request proxy is active
        client = self.app.test_client()
        client.set_cookie("__session", token)
        with client.application.test_request_context(
            "/api/test", headers={"Cookie": f"__session={token}"}
        ):
            state = auth.authenticate_request(
                auth.request,
                jwt_key=self.public_key,
                authorized_parties=[self.allowed_party],
            )
        self.assertTrue(state.is_signed_in)


if __name__ == "__main__":
    unittest.main()
