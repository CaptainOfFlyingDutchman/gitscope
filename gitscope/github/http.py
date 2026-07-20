"""Shared authenticated HTTP transport for GitHub APIs."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from gitscope import __version__
from gitscope.github.errors import AuthenticationError, GitHubAPIError, RateLimitError

API_VERSION = "2026-03-10"
TRANSIENT_STATUS_CODES = frozenset({429, 502, 503, 504})

type Sleep = Callable[[float], Awaitable[None]]


class GitHubHTTPClient:
    """Send authenticated requests with bounded retries and safe errors."""

    def __init__(
        self,
        token: str,
        *,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
        sleep: Sleep = asyncio.sleep,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.sleep = sleep
        self._headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": f"GitScope/{__version__}",
            "X-GitHub-Api-Version": API_VERSION,
        }
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
        )

    async def __aenter__(self) -> GitHubHTTPClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> tuple[Any, httpx.Headers]:
        """Return decoded JSON and response headers or raise a typed failure."""
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(
                    method,
                    url,
                    headers=self._headers,
                    params=params,
                    json=json_body,
                )
            except httpx.TransportError as exc:
                if attempt >= self.max_retries:
                    raise GitHubAPIError(0, "network request failed") from exc
                await self.sleep(self._backoff_seconds(attempt))
                continue

            message = self._response_message(response)
            if response.status_code == 401:
                raise AuthenticationError(
                    "GitHub rejected GITHUB_TOKEN. Check that it is valid and not expired."
                )

            if self._is_primary_rate_limit(response):
                raise RateLimitError(self._rate_limit_reset(response.headers))

            if self._is_retryable(response, message) and attempt < self.max_retries:
                await self.sleep(self._retry_delay(response, attempt))
                continue

            if response.is_error:
                raise GitHubAPIError(response.status_code, message)

            try:
                return response.json(), response.headers
            except ValueError as exc:
                raise GitHubAPIError(response.status_code, "response was not valid JSON") from exc

        raise AssertionError("retry loop exited unexpectedly")

    @staticmethod
    def _response_message(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return response.reason_phrase or "request failed"
        if isinstance(body, dict):
            message = body.get("message")
            if isinstance(message, str):
                return message
        return response.reason_phrase or "request failed"

    @staticmethod
    def _is_primary_rate_limit(response: httpx.Response) -> bool:
        return response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0"

    @staticmethod
    def _is_retryable(response: httpx.Response, message: str) -> bool:
        return response.status_code in TRANSIENT_STATUS_CODES or (
            response.status_code == 403
            and ("secondary rate limit" in message.lower() or "retry-after" in response.headers)
        )

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return self._backoff_seconds(attempt)

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        return min(2.0**attempt, 8.0)

    @staticmethod
    def _rate_limit_reset(headers: httpx.Headers) -> datetime | None:
        reset = headers.get("x-ratelimit-reset")
        if reset:
            try:
                return datetime.fromtimestamp(float(reset), tz=UTC)
            except (ValueError, OverflowError):
                return None
        reset_http_date = headers.get("retry-after")
        if reset_http_date:
            try:
                return parsedate_to_datetime(reset_http_date)
            except (TypeError, ValueError, OverflowError):
                return None
        return None
