"""Tests for the remote server's domain-restricted Google sign-in."""

import asyncio
import unittest

try:
    from fastmcp.server.auth.auth import AccessToken, TokenVerifier

    from analytics_mcp.remote.auth import DomainRestrictedVerifier
except ImportError:  # The "remote" extra isn't installed.
    TokenVerifier = None


class _FakeVerifier(TokenVerifier if TokenVerifier else object):
    def __init__(self, claims):
        super().__init__()
        self._claims = claims

    async def verify_token(self, token):
        if self._claims is None:
            return None
        return AccessToken(
            token=token, client_id="sub", scopes=[], claims=self._claims
        )


@unittest.skipIf(TokenVerifier is None, "fastmcp not installed")
class DomainRestrictedVerifierTest(unittest.TestCase):

    def _verify(self, claims):
        verifier = DomainRestrictedVerifier(
            _FakeVerifier(claims), {"voxus.com.br", "voxus.tv"}
        )
        return asyncio.run(verifier.verify_token("t"))

    def test_allows_verified_email_in_allowed_domain(self):
        self.assertIsNotNone(
            self._verify({"email": "a@voxus.tv", "email_verified": "true"})
        )
        self.assertIsNotNone(
            self._verify({"email": "B@Voxus.com.br", "email_verified": True})
        )

    def test_rejects_other_domains(self):
        self.assertIsNone(
            self._verify({"email": "a@gmail.com", "email_verified": "true"})
        )
        self.assertIsNone(
            self._verify({"email": "a@evilvoxus.tv", "email_verified": "true"})
        )

    def test_rejects_unverified_or_missing_email(self):
        self.assertIsNone(
            self._verify({"email": "a@voxus.tv", "email_verified": "false"})
        )
        self.assertIsNone(self._verify({}))

    def test_rejects_when_inner_verifier_fails(self):
        self.assertIsNone(self._verify(None))


if __name__ == "__main__":
    unittest.main()
