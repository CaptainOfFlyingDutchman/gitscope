"""Tests for conservative path classification."""

from gitscope.git.languages import NO_EXTENSION, classify_file


def test_classify_file_by_extension() -> None:
    assert classify_file("src/component.TSX") == (".tsx", "TypeScript")
    assert classify_file("schema.graphql") == (".graphql", "GraphQL")
    assert classify_file("terraform/main.tf") == (".tf", "HCL")
    assert classify_file("component.test.tsx.snap") == (".snap", "Test Snapshot")


def test_classify_special_filename_and_unknown_extension() -> None:
    assert classify_file("services/api/Dockerfile") == (NO_EXTENSION, "Dockerfile")
    assert classify_file("asset.unknown") == (".unknown", "Other")
