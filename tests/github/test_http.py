"""Tests for GitHub's authenticated HTTP transport."""

from collections.abc import Awaitable, Callable

import httpx
import pytest

from gitscope.github.errors import AuthenticationError, RateLimitError
from gitscope.github.http import API_VERSION, GitHubHTTPClient


@pytest.mark.anyio
async def test_request_sets_headers_and_retries_transient_failure() -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        assert request.headers["authorization"] == "Bearer secret-token"
        assert request.headers["x-github-api-version"] == API_VERSION
        if attempts == 1:
            return httpx.Response(503, json={"message": "temporarily unavailable"})
        return httpx.Response(200, json={"ok": True})

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        http = GitHubHTTPClient("secret-token", client=client, sleep=record_sleep)
        payload, _headers = await http.request_json("GET", "https://api.github.com/user")

    assert payload == {"ok": True}
    assert attempts == 2
    assert delays == [1.0]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status", "headers", "expected_exception"),
    [
        (401, {}, AuthenticationError),
        (403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "0"}, RateLimitError),
    ],
)
async def test_request_raises_typed_failures(
    status: int,
    headers: dict[str, str],
    expected_exception: type[Exception],
) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(status, headers=headers, json={"message": "failed"})
    )
    async with httpx.AsyncClient(transport=transport) as client:
        http = GitHubHTTPClient("secret-token", client=client)
        with pytest.raises(expected_exception):
            await http.request_json("GET", "https://api.github.com/user")


def test_type_aliases_remain_importable() -> None:
    """Keep strict-import tooling from pruning test-only async typing imports."""
    callback: Callable[[float], Awaitable[None]] | None = None
    assert callback is None
