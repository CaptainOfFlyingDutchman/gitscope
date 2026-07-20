"""GitHub REST API client used for authentication and targeted fallbacks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ValidationError

from gitscope.github.errors import (
    GitHubAPIError,
    InvalidGitHubResponseError,
    RepositoriesNotFoundError,
)
from gitscope.github.http import GitHubHTTPClient
from gitscope.github.models import (
    AuthenticatedUser,
    RepositorySummary,
)
from gitscope.models.repository import RepositoryVisibility

REST_API_URL = "https://api.github.com"


class GitHubRESTClient:
    """Provide the small REST surface GitScope needs."""

    def __init__(self, http: GitHubHTTPClient) -> None:
        self.http = http

    async def authenticated_user(self) -> AuthenticatedUser:
        """Return the identity associated with the configured token."""
        payload, _headers = await self.http.request_json("GET", f"{REST_API_URL}/user")
        try:
            return AuthenticatedUser.model_validate(payload)
        except ValidationError as exc:
            raise InvalidGitHubResponseError("GitHub returned an invalid user response.") from exc

    async def organization_repositories(self, organization: str) -> tuple[RepositorySummary, ...]:
        """List all visible organization repositories using REST pagination."""
        repositories: list[RepositorySummary] = []
        page = 1
        while True:
            payload, _headers = await self.http.request_json(
                "GET",
                f"{REST_API_URL}/orgs/{organization}/repos",
                params={"type": "all", "per_page": 100, "page": page},
            )
            if not isinstance(payload, list):
                raise InvalidGitHubResponseError(
                    "GitHub returned an invalid repository collection."
                )
            repositories.extend(self._repository_from_rest(item) for item in payload)
            if len(payload) < 100:
                break
            page += 1
        return tuple(repositories)

    async def repositories_by_name(
        self,
        organization: str,
        repository_names: tuple[str, ...],
    ) -> tuple[RepositorySummary, ...]:
        """Fetch only explicitly allowlisted repositories through REST."""
        repositories: list[RepositorySummary] = []
        unavailable: list[str] = []
        for name in repository_names:
            try:
                payload, _headers = await self.http.request_json(
                    "GET",
                    f"{REST_API_URL}/repos/{organization}/{name}",
                )
            except GitHubAPIError as exc:
                if exc.status_code == 404:
                    unavailable.append(f"{organization}/{name}")
                    continue
                raise
            repositories.append(self._repository_from_rest(payload))
        if unavailable:
            raise RepositoriesNotFoundError(unavailable)
        return tuple(repositories)

    @staticmethod
    def _repository_from_rest(payload: Any) -> RepositorySummary:
        if not isinstance(payload, dict):
            raise InvalidGitHubResponseError("GitHub returned invalid repository metadata.")
        owner = payload.get("owner")
        owner_login = owner.get("login") if isinstance(owner, dict) else None
        default_branch = payload.get("default_branch")
        language = payload.get("language")
        try:
            return RepositorySummary(
                node_id=payload["node_id"],
                name=payload["name"],
                name_with_owner=payload.get("full_name") or f"{owner_login}/{payload['name']}",
                url=payload["html_url"],
                visibility=RepositoryVisibility(str(payload["visibility"]).upper()),
                is_private=payload["private"],
                is_archived=payload["archived"],
                is_fork=payload["fork"],
                default_branch=default_branch if isinstance(default_branch, str) else None,
                primary_language=language if isinstance(language, str) else None,
                stars=payload.get("stargazers_count", 0),
                forks=payload.get("forks_count", 0),
                disk_usage_kib=payload.get("size"),
                created_at=datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(payload["updated_at"].replace("Z", "+00:00")),
                pushed_at=(
                    datetime.fromisoformat(payload["pushed_at"].replace("Z", "+00:00"))
                    if payload.get("pushed_at")
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise InvalidGitHubResponseError(
                "GitHub returned invalid repository metadata."
            ) from exc
