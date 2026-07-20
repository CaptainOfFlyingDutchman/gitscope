"""Tests for repository and contribution-language analytics."""

from datetime import UTC, datetime

from gitscope.analytics.repositories import summarize_languages, summarize_repositories
from gitscope.git.stats import FileChangeAggregate, RepositoryCommitAnalysis
from gitscope.models.commit import CommitContribution
from gitscope.models.issue import Issue, IssueState
from gitscope.models.pull_request import PullRequest, PullRequestState
from gitscope.models.report import ReportRepository
from gitscope.models.review import PullRequestReview, ReviewState


def test_repository_and_language_summaries() -> None:
    repository = ReportRepository(
        name_with_owner="org/app",
        url="https://github.com/org/app",
        visibility="PRIVATE",
        is_archived=False,
        is_fork=False,
        primary_language="TypeScript",
        stars=0,
        forks=0,
    )
    authored_at = datetime(2026, 1, 1, tzinfo=UTC)
    commit = CommitContribution(
        sha="a",
        repository="org/app",
        authored_at=authored_at,
        additions=10,
        deletions=2,
        files_changed=1,
        is_merge=False,
    )
    analysis = RepositoryCommitAnalysis(
        repository="org/app",
        commits=(commit,),
        file_changes=(FileChangeAggregate(".ts", "TypeScript", 10, 2, 1),),
    )
    pull_request = PullRequest(
        node_id="pr",
        repository="org/app",
        number=1,
        title="PR",
        url="https://github.com/org/app/pull/1",
        state=PullRequestState.MERGED,
        is_draft=False,
        created_at=authored_at,
        updated_at=authored_at,
        merged_at=authored_at,
        additions=10,
        deletions=2,
        changed_files=1,
        commit_count=1,
    )
    review = PullRequestReview(
        node_id="review",
        repository="org/app",
        pull_request_number=2,
        pull_request_title="Reviewed PR",
        pull_request_url="https://github.com/org/app/pull/2",
        state=ReviewState.APPROVED,
        created_at=authored_at,
        submitted_at=authored_at,
        url="https://github.com/org/app/pull/2#review",
    )
    issue = Issue(
        node_id="issue",
        repository="org/app",
        number=3,
        title="Issue",
        url="https://github.com/org/app/issues/3",
        state=IssueState.OPEN,
        created_at=authored_at,
        updated_at=authored_at,
        comment_count=1,
    )

    repositories = summarize_repositories(
        (repository,),
        (analysis,),
        (pull_request,),
        (review,),
        (issue,),
    )
    languages = summarize_languages((repository,), (analysis,))

    assert repositories[0].commits == 1
    assert repositories[0].pull_requests == 1
    assert repositories[0].reviews == 1
    assert repositories[0].issues == 1
    assert repositories[0].first_contribution == authored_at
    assert languages.primary_repository_languages == {"TypeScript": 1}
    assert languages.contributed_languages[0].name == "TypeScript"
    assert languages.file_extensions[0].name == ".ts"
