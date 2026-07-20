"""Conservative language inference for contributed file paths."""

from __future__ import annotations

from pathlib import PurePosixPath

NO_EXTENSION = "[no extension]"

_FILENAME_LANGUAGES = {
    "dockerfile": "Dockerfile",
    "gemfile": "Ruby",
    "makefile": "Makefile",
    "procfile": "Procfile",
}

_EXTENSION_LANGUAGES = {
    ".bash": "Shell",
    ".c": "C",
    ".cc": "C++",
    ".cfg": "Configuration",
    ".cjs": "JavaScript",
    ".conf": "Configuration",
    ".cpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".csv": "CSV",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".go": "Go",
    ".graphql": "GraphQL",
    ".gql": "GraphQL",
    ".hcl": "HCL",
    ".h": "C/C++ Header",
    ".hpp": "C++",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".json": "JSON",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".less": "Less",
    ".lock": "Dependency Lockfile",
    ".lua": "Lua",
    ".md": "Markdown",
    ".mdx": "MDX",
    ".mjs": "JavaScript",
    ".mts": "TypeScript",
    ".php": "PHP",
    ".proto": "Protocol Buffers",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".sass": "Sass",
    ".scala": "Scala",
    ".scss": "SCSS",
    ".sh": "Shell",
    ".sql": "SQL",
    ".snap": "Test Snapshot",
    ".svg": "SVG",
    ".svelte": "Svelte",
    ".swift": "Swift",
    ".toml": "TOML",
    ".tf": "HCL",
    ".tfvars": "HCL",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".txt": "Text",
    ".vue": "Vue",
    ".xml": "XML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".zsh": "Shell",
}


def classify_file(path: str) -> tuple[str, str]:
    """Return a normalized extension label and inferred language without retaining path."""
    file_path = PurePosixPath(path)
    filename = file_path.name.casefold()
    extension = file_path.suffix.casefold() or NO_EXTENSION
    language = _FILENAME_LANGUAGES.get(
        filename,
        _EXTENSION_LANGUAGES.get(extension, "Other"),
    )
    return extension, language
