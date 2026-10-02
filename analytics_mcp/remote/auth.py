"""Google sign-in for the remote server, restricted to allowed email domains.

Google login is only used to identify the user. Google Analytics calls use the
server's own Application Default Credentials (a service account).
"""

import logging

from fastmcp.server.auth.auth import AccessToken, TokenVerifier
from fastmcp.server.auth.providers.google import GoogleProvider

logger = logging.getLogger(__name__)


class DomainRestrictedVerifier(TokenVerifier):
    """Wraps a Google token verifier and rejects users outside allowed domains."""

    def __init__(self, inner: TokenVerifier, allowed_domains: set[str]):
        super().__init__(required_scopes=inner.required_scopes)
        self._inner = inner
        self._allowed_domains = allowed_domains

    async def verify_token(self, token: str) -> AccessToken | None:
        access_token = await self._inner.verify_token(token)
        if access_token is None:
            return None

        email = (access_token.claims.get("email") or "").lower()
        verified = access_token.claims.get("email_verified")
        domain = email.rpartition("@")[2]
        if not email or str(verified).lower() != "true" or domain not in self._allowed_domains:
            logger.warning("Rejected login from %r: domain not allowed", email)
            return None
        return access_token


def build_auth(
    client_id: str,
    client_secret: str,
    base_url: str,
    allowed_domains: set[str],
    jwt_signing_key: str | None,
) -> GoogleProvider:
    provider = GoogleProvider(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        required_scopes=["openid", "email"],
        jwt_signing_key=jwt_signing_key,
    )
    # GoogleProvider builds its own verifier; wrap it with the domain check.
    provider._token_validator = DomainRestrictedVerifier(
        provider._token_validator, allowed_domains
    )
    return provider
