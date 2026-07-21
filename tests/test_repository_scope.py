"""Tests for repository allowlist parsing."""

from pathlib import Path

import pytest

from gitscope.repository_scope import RepositoryScope, RepositoryScopeError


def test_all_visible_scope_has_no_allowlist_source() -> None:
    scope = RepositoryScope.all_visible(organization="josys-src")

    assert scope.organization == "josys-src"
    assert scope.names == ()
    assert scope.source is None
    assert scope.all_repositories is True
    assert scope.source_label == "--all-repositories"


def test_repository_scope_ignores_comments_and_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "repositories"
    path.write_text(
        "# selected repositories\njosys-src/frontend\n\nJOSYS-SRC/frontend\njosys-src/backend\n",
        encoding="utf-8",
    )

    scope = RepositoryScope.from_file(path, organization="josys-src")

    assert scope.names == ("frontend", "backend")
    assert scope.all_repositories is False
    assert scope.source_label == str(path)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("frontend\n", "expected owner/name"),
        ("another-org/frontend\n", "not 'josys-src'"),
        ("josys-src/front end\n", "Invalid repository name"),
        ("# no repositories\n", "contains no repositories"),
    ],
)
def test_repository_scope_rejects_invalid_content(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    path = tmp_path / "repositories"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(RepositoryScopeError, match=message):
        RepositoryScope.from_file(path, organization="josys-src")
