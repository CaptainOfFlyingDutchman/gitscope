"""End-to-end tests for career report generation."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from gitscope.config import Settings
from gitscope.date_range import DateRange
from gitscope.git.collection import GitCollection
from gitscope.report.generate import generate_career_report
from gitscope.repository_scope import RepositoryScope
from tests.github.test_graphql import graphql_page, repository_node
from tests.github.test_issues import issue_node, issue_page
from tests.github.test_prs import pull_request_node, pull_request_page
from tests.github.test_reviews import reviewed_search_page


@pytest.mark.anyio
@respx.mock
@pytest.mark.parametrize("all_repositories", [False, True])
async def test_generate_career_report_builds_and_writes_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    all_repositories: bool,
) -> None:
    cloned_repositories: list[tuple[str, ...]] = []
    contribution_queries: list[str] = []

    def fake_git_collection(repositories: tuple[str, ...], **_kwargs: object) -> GitCollection:
        cloned_repositories.append(repositories)
        return GitCollection((), (), len(repositories), 0, ())

    monkeypatch.setattr("gitscope.report.generate.collect_git_contributions", fake_git_collection)
    respx.get("https://api.github.com/user").mock(
        return_value=httpx.Response(200, json={"login": "octocat", "id": 1})
    )

    def graphql_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        query = body["query"]
        if "OrganizationRepositories" in query:
            data = graphql_page(
                [
                    repository_node("frontend", private=True),
                    repository_node("idle", private=True),
                ],
                has_next_page=False,
                cursor=None,
            )["data"]
        elif "ScopedRepositories" in query:
            data = {
                "repo0": repository_node("frontend", private=True),
                "rateLimit": {
                    "cost": 1,
                    "remaining": 4999,
                    "resetAt": "2026-07-20T12:00:00Z",
                },
            }
        elif "CommitPresence" in query:
            data = {
                f"repo{index}": {
                    "nameWithOwner": f"josys-src/{name}",
                    "defaultBranchRef": {"target": {"history": {"totalCount": 0}}},
                }
                for index, name in enumerate(
                    value for key, value in body["variables"].items() if key.startswith("name")
                )
            }
            data["rateLimit"] = {
                "cost": 3,
                "remaining": 4996,
                "resetAt": "2026-07-20T12:00:00Z",
            }
        elif "AuthoredPullRequests" in query:
            contribution_queries.append(body["variables"]["query"])
            data = pull_request_page(
                [pull_request_node(1)],
                has_next_page=False,
                cursor=None,
                issue_count=1,
            )
        elif "AuthoredIssues" in query:
            contribution_queries.append(body["variables"]["query"])
            data = issue_page(
                [issue_node(2)],
                has_next_page=False,
                cursor=None,
                issue_count=1,
            )
        else:
            contribution_queries.append(body["variables"]["query"])
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
    scope = (
        RepositoryScope.all_visible(organization="josys-src")
        if all_repositories
        else RepositoryScope.from_file(repositories_file, organization="josys-src")
    )
    observed_scopes: list[int] = []
    observed_git_scopes: list[tuple[int, int]] = []

    generated = await generate_career_report(
        settings,
        scope,
        date_range=DateRange.parse("2026-01-01", "2026-01-31"),
        scope_observer=lambda context: observed_scopes.append(len(context.discovery.repositories)),
        git_scope_observer=lambda inspected, selected: observed_git_scopes.append(
            (inspected, selected)
        ),
    )

    assert generated.path.exists()
    assert generated.html_path == tmp_path / "career-report" / "report.html"
    assert generated.html_path.exists()
    assert generated.markdown_path == tmp_path / "career-report" / "report.md"
    assert generated.markdown_path.exists()
    assert generated.csv_path == tmp_path / "career-report" / "report.csv"
    assert generated.csv_path.exists()
    assert len(generated.chart_paths) == 13
    assert all(path.exists() for path in generated.chart_paths)
    assert generated.report.schema_version == "1.6"
    assert generated.report.collection.analysis_start is not None
    assert generated.report.collection.analysis_start.isoformat() == "2026-01-01"
    assert generated.report.collection.analysis_end is not None
    assert generated.report.collection.analysis_end.isoformat() == "2026-01-31"
    assert generated.report.collection.github_api_requests == (6 if all_repositories else 5)
    assert generated.report.collection.git_repositories_processed == 1
    assert generated.report.commit_summary.total == 0
    assert generated.report.repository_analytics[0].pull_requests == 1
    assert generated.report.repository_analytics[0].reviews == 1
    assert generated.report.repository_analytics[0].issues == 1
    assert generated.report.pull_request_summary.total == 1
    assert generated.report.review_summary.total == 1
    assert generated.report.issue_summary.total == 1
    assert generated.report.timeline.monthly_activity[0].pull_requests == 1
    assert generated.report.timeline.monthly_activity[0].reviews == 1
    assert generated.report.timeline.monthly_activity[0].issues == 1
    assert generated.report.repositories[0].name_with_owner == "josys-src/frontend"
    expected_source = "--all-repositories" if all_repositories else str(repositories_file)
    assert generated.report.collection.repository_scope_file == expected_source
    expected_count = 2 if all_repositories else 1
    assert observed_scopes == [expected_count]
    assert observed_git_scopes == [(expected_count, 1)]
    assert cloned_repositories == [("josys-src/frontend",)]
    expected_qualifier = "org:josys-src" if all_repositories else "repo:josys-src/frontend"
    assert len(contribution_queries) == 3
    assert all(query.startswith(expected_qualifier) for query in contribution_queries)
    assert contribution_queries[0].endswith("created:2026-01-01..2026-01-31")
    assert contribution_queries[1].endswith("created:2026-01-01..2026-01-31")
    assert "created:" not in contribution_queries[2]
