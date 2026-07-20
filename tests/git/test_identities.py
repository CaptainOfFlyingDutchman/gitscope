"""Tests for author identity parsing and matching."""

from pathlib import Path

import pytest

from gitscope.git.identities import AuthorIdentities, IdentityFileError


def test_identities_include_github_defaults_and_explicit_aliases(tmp_path: Path) -> None:
    source = tmp_path / "identities"
    source.write_text(
        "# historical aliases\nname: Old Name\nemail: old@example.com\n",
        encoding="utf-8",
    )

    identities = AuthorIdentities.build(
        username="OctoCat",
        database_id=42,
        github_name="The Octocat",
        source=source,
    )

    assert identities.matches("unrelated", "42+octocat@users.noreply.github.com")
    assert identities.matches("the octocat", "unrelated@example.com")
    assert identities.matches("unrelated", "OLD@example.com")
    assert not identities.matches("octo", "unknown@example.com")


def test_invalid_identity_line_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "identities"
    source.write_text("nickname: octo\n", encoding="utf-8")

    with pytest.raises(IdentityFileError, match="expected"):
        AuthorIdentities.build(username="octocat", database_id=1, source=source)
