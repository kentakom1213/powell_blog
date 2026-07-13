#!/usr/bin/env python3
"""Find external articles managed as Zola Markdown files."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

import tomlkit
from tomlkit.exceptions import ParseError


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTENT_DIR = ROOT / "content"


class FrontmatterError(Exception):
    """Raised when Markdown frontmatter cannot be read."""


@dataclass(frozen=True)
class ExternalArticle:
    """Metadata needed to identify an external article."""

    path: Path
    url: str
    site_name: str | None
    kind: str | None


def read_frontmatter(path: Path) -> Mapping[str, object] | None:
    """Read TOML frontmatter from a Markdown file.

    Returns None when the file has no TOML frontmatter.
    """

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    if not lines or lines[0].strip() != "+++":
        return None

    closing_line = None

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "+++":
            closing_line = index
            break

    if closing_line is None:
        raise FrontmatterError("closing +++ delimiter is missing")

    source = "".join(lines[1:closing_line])

    try:
        return tomlkit.parse(source)
    except ParseError as error:
        raise FrontmatterError(f"invalid TOML: {error}") from error


def optional_string(
    mapping: Mapping[str, object],
    key: str,
) -> str | None:
    """Read an optional string from a mapping."""

    value = mapping.get(key)

    if value is None:
        return None

    if not isinstance(value, str):
        raise FrontmatterError(f"{key} must be a string")

    return value


def parse_external_article(path: Path) -> ExternalArticle | None:
    """Parse an external article from a Markdown file."""

    frontmatter = read_frontmatter(path)

    if frontmatter is None:
        return None

    extra = frontmatter.get("extra")

    if extra is None:
        return None

    if not isinstance(extra, Mapping):
        raise FrontmatterError("extra must be a table")

    external = extra.get("external")

    if external is None:
        return None

    if not isinstance(external, Mapping):
        raise FrontmatterError("extra.external must be a table")

    url = external.get("url")

    if not isinstance(url, str) or not url.strip():
        raise FrontmatterError("extra.external.url must be a non-empty string")

    return ExternalArticle(
        path=path,
        url=url,
        site_name=optional_string(external, "site_name"),
        kind=optional_string(external, "kind"),
    )


def find_external_articles(
    content_dir: Path,
) -> Iterator[ExternalArticle]:
    """Find external articles under a content directory."""

    for path in sorted(content_dir.rglob("*.md")):
        try:
            article = parse_external_article(path)
        except (OSError, UnicodeError, FrontmatterError) as error:
            relative_path = path.relative_to(ROOT)
            raise FrontmatterError(f"{relative_path}: {error}") from error

        if article is not None:
            yield article


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find external articles in the Zola content directory.",
    )
    parser.add_argument(
        "--content-dir",
        type=Path,
        default=DEFAULT_CONTENT_DIR,
        help="content directory to inspect",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    content_dir = args.content_dir.resolve()

    if not content_dir.is_dir():
        print(
            f"content directory does not exist: {content_dir}",
            file=sys.stderr,
        )
        return 2

    try:
        articles = list(find_external_articles(content_dir))
    except FrontmatterError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if not articles:
        print("No external articles found.")
        return 0

    for article in articles:
        try:
            display_path = article.path.relative_to(ROOT)
        except ValueError:
            display_path = article.path

        print(display_path)
        print(f"  URL: {article.url}")
        print(f"  Site: {article.site_name or '(not set)'}")
        print(f"  Kind: {article.kind or '(not set)'}")

    print()
    print(f"Found {len(articles)} external article(s).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
