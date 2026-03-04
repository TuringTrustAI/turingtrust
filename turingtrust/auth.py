"""TuringTrust SDK authentication utilities."""

import httpx
from typing import Optional
from turingtrust.config import TuringTrustConfig


class TuringTrustAuth:
    """Handles authentication with the TuringTrust gateway."""

    def __init__(self, config: Optional[TuringTrustConfig] = None):
        self.config = config or TuringTrustConfig()
        self._token: Optional[str] = None

    async def login(self, username: str, password: str) -> str:
        """Login with username/password to get a JWT token."""
        async with httpx.AsyncClient(verify=self.config.verify_ssl) as client:
            r = await client.post(
                f"{self.config.gateway_url.rstrip('/')}/api/auth/login",
                data={"username": username, "password": password},
            )
            r.raise_for_status()
            data = r.json()
            self._token = data.get("access_token")
            return self._token

    def login_sync(self, username: str, password: str) -> str:
        """Synchronous login."""
        with httpx.Client(verify=self.config.verify_ssl) as client:
            r = client.post(
                f"{self.config.gateway_url.rstrip('/')}/api/auth/login",
                data={"username": username, "password": password},
            )
            r.raise_for_status()
            data = r.json()
            self._token = data.get("access_token")
            return self._token

    @property
    def token(self) -> Optional[str]:
        return self._token

    @token.setter
    def token(self, value: str):
        self._token = value

    def get_headers(self) -> dict:
        """Get auth headers for API requests."""
        headers = dict(self.config.headers)
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers
