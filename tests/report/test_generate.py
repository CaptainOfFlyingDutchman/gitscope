"""End-to-end tests for career report generation."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from gitscope.config import Settings
from gitscope.git.collection import GitCollection
from gitscope.report.generate import generate_career_report
from gitscope.repository_scope import RepositoryScope
from tests.github.test_graphql import repository_node
from tests.github.test_prs import pull_request_node, pull_request_page
from tests.github.test_reviews import reviewed_search_page


@pytest.mark.anyio
@respx.mock
async def test_generate_career_report_builds_and_writes_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "gitscope.report.generate.collect_git_contributions",
        lambda *_args, **_kwargs: GitCollection((), (), 1, 0, ()),
    )
    respx.get("https://api.github.com/user").mock(
        return_value=httpx.Response(200, json={"login": "octocat", "id": 1})
    )

    def graphql_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        query = body["query"]
        if "ScopedRepositories" in query:
            data = {
                "repo0": repository_node("frontend", private=True),
                "rateLimit": {
                    "cost": 1,
                    "remaining": 4999,
                    "resetAt": "2026-07-20T12:00:00Z",
                },
            }
        elif "AuthoredPullRequests" in query:
            data = pull_request_page(
                [pull_request_node(1)],
                has_next_page=False,
                cursor=None,
                issue_count=1,
            )
        else:
            data = reviewed_search_page(has_more_reviews=False)
        return httpx.Response(200, json={"data": data})

    respx.post("https://api.github.com/graphql").mock(side_effect=graphql_handler)
    repositories_file = tmp_path / "repositories"
    repositories_file.write_text("josys-src/frontend\n", encoding="utf-8")
    settings = Settings(
        organization="josys-src",
        username="octocat",
        github_token="secret",
        output_directory=tmp_path / "career-report",
        cache_directory=tmp_path / "cache",
    )
    scope = RepositoryScope.from_file(repositories_file, organization="josys-src")

    generated = await generate_career_report(settings, scope)

    assert generated.path.exists()
    assert generated.html_path == tmp_path / "career-report" / "report.html"
    assert generated.html_path.exists()
    assert generated.markdown_path == tmp_path / "career-report" / "report.md"
    assert generated.markdown_path.exists()
    assert generated.csv_path == tmp_path / "career-report" / "report.csv"
    assert generated.csv_path.exists()
    assert len(generated.chart_paths) == 10
    assert all(path.exists() for path in generated.chart_paths)
    assert generated.report.schema_version == "1.3"
    assert generated.report.collection.github_api_requests == 4
    assert generated.report.collection.git_repositories_processed == 1
    assert generated.report.commit_summary.total == 0
    assert generated.report.repository_analytics[0].pull_requests == 1
    assert generated.report.repository_analytics[0].reviews == 1
    assert generated.report.pull_request_summary.total == 1
    assert generated.report.review_summary.total == 1
    assert generated.report.timeline.monthly_activity[0].pull_requests == 1
    assert generated.report.timeline.monthly_activity[0].reviews == 1
    assert generated.report.repositories[0].name_with_owner == "josys-src/frontend"
