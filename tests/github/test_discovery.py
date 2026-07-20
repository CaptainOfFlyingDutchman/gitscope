"""Tests for the complete GitHub discovery workflow."""

import stat
from pathlib import Path

import pytest
import respx
from httpx import Response

from gitscope.config import Settings
from gitscope.github.discovery import discover_repositories
from tests.github.test_graphql import graphql_page, repository_node


@pytest.mark.anyio
@respx.mock
async def test_discovery_validates_user_and_lists_repositories(tmp_path: Path) -> None:
    respx.get("https://api.github.com/user").mock(
        return_value=Response(200, json={"login": "octocat", "id": 1})
    )
    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(
            200,
            json=graphql_page(
                [repository_node("private", private=True)],
                has_next_page=False,
                cursor=None,
            ),
        )
    )
    settings = Settings(
        organization="josys-src",
        username="CaptainOfFlyingDutchman",
        github_token="secret",
        cache_directory=tmp_path,
    )

    context = await discover_repositories(settings)

    assert context.authenticated_user.login == "octocat"
    assert context.discovery.repositories[0].name == "private"
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o700
