#!/usr/bin/env python3
"""Manage external articles and fetch their metadata."""

from __future__ import annotations

import argparse
import copy
import difflib
import ipaddress
import json
import os
import sys
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
import tomlkit
from selectolax.parser import HTMLParser
from tomlkit.exceptions import ParseError
from tomlkit.toml_document import TOMLDocument

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTENT_DIR = ROOT / "content"

MAX_RESPONSE_BYTES = 2 * 1024 * 1024

USER_AGENT = (
    "PowellBlogMetadataFetcher/0.1 " "(https://github.com/kentakom1213/powell_blog)"
)

LOCKABLE_FIELDS = frozenset(
    {
        "title",
        "description",
        "image",
        "site_name",
        "canonical_url",
        "published_at",
        "body",
    }
)


class FrontmatterError(Exception):
    """Raised when Markdown frontmatter cannot be read."""


class ExternalFetchError(Exception):
    """Raised when external metadata cannot be fetched."""


@dataclass(frozen=True)
class ParsedMarkdown:
    """A Markdown file split into frontmatter and body."""

    path: Path
    original: str
    frontmatter: TOMLDocument
    body: str


@dataclass(frozen=True)
class ExternalArticle:
    """Metadata needed to identify an external article."""

    path: Path
    url: str
    site_name: str | None
    kind: str | None
    locked_fields: frozenset[str]


@dataclass(frozen=True)
class ExternalMetadata:
    """Metadata extracted from an external web page."""

    title: str | None
    description: str | None
    image: str | None
    site_name: str
    canonical_url: str
    published_at: str | None


def display_path(path: Path) -> Path:
    """Return a repository-relative path when possible."""

    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def read_markdown(path: Path) -> ParsedMarkdown | None:
    """Read a Markdown file with TOML frontmatter."""

    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    if not lines or lines[0].strip() != "+++":
        return None

    closing_line = None

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "+++":
            closing_line = index
            break

    if closing_line is None:
        raise FrontmatterError("closing +++ delimiter is missing")

    frontmatter_source = "".join(lines[1:closing_line])
    body = "".join(lines[closing_line + 1 :])

    try:
        frontmatter = tomlkit.parse(frontmatter_source)
    except ParseError as error:
        raise FrontmatterError(f"invalid TOML: {error}") from error

    return ParsedMarkdown(
        path=path,
        original=original,
        frontmatter=frontmatter,
        body=body,
    )


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


def read_locked_fields(
    external: Mapping[str, object],
) -> frozenset[str]:
    """Read and validate fields protected from automatic updates."""

    value = external.get("lock")

    if value is None:
        return frozenset()

    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise FrontmatterError("extra.external.lock must be an array of strings")

    locked_fields: set[str] = set()

    for field in value:
        if not isinstance(field, str):
            raise FrontmatterError(
                "extra.external.lock must contain only strings",
            )

        if field not in LOCKABLE_FIELDS:
            allowed = ", ".join(sorted(LOCKABLE_FIELDS))
            raise FrontmatterError(
                f"unknown locked field {field!r}; allowed fields: {allowed}",
            )

        locked_fields.add(field)

    return frozenset(locked_fields)


def parse_external_article(path: Path) -> ExternalArticle | None:
    """Parse an external article from a Markdown file."""

    parsed = read_markdown(path)

    if parsed is None:
        return None

    extra = parsed.frontmatter.get("extra")

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
        raise FrontmatterError(
            "extra.external.url must be a non-empty string",
        )

    return ExternalArticle(
        path=path,
        url=url,
        site_name=optional_string(external, "site_name"),
        kind=optional_string(external, "kind"),
        locked_fields=read_locked_fields(external),
    )


def find_external_articles(
    content_dir: Path,
) -> Iterator[ExternalArticle]:
    """Find external articles under a content directory."""

    for path in sorted(content_dir.rglob("*.md")):
        try:
            article = parse_external_article(path)
        except (OSError, UnicodeError, FrontmatterError) as error:
            raise FrontmatterError(
                f"{display_path(path)}: {error}",
            ) from error

        if article is not None:
            yield article


def normalize_text(value: str | None) -> str | None:
    """Normalize whitespace in metadata text."""

    if value is None:
        return None

    normalized = " ".join(value.split())
    return normalized or None


def validate_external_url(url: str) -> None:
    """Reject unsupported or obviously local URLs."""

    parsed = urlsplit(url)

    if parsed.scheme not in {"http", "https"}:
        raise ExternalFetchError(
            "URL scheme must be http or https",
        )

    if parsed.hostname is None:
        raise ExternalFetchError(
            "URL does not contain a hostname",
        )

    hostname = parsed.hostname.lower()

    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ExternalFetchError(
            "localhost URLs are not allowed",
        )

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return

    if not address.is_global:
        raise ExternalFetchError(
            "private and local IP addresses are not allowed",
        )


def read_html_response(response: httpx.Response) -> str:
    """Read a size-limited HTML response."""

    content_type = response.headers.get(
        "content-type",
        "",
    ).lower()

    if content_type and not any(
        allowed in content_type
        for allowed in (
            "text/html",
            "application/xhtml+xml",
        )
    ):
        raise ExternalFetchError(
            f"response is not HTML: {content_type}",
        )

    chunks: list[bytes] = []
    total_size = 0

    for chunk in response.iter_bytes():
        total_size += len(chunk)

        if total_size > MAX_RESPONSE_BYTES:
            raise ExternalFetchError(
                "HTML response exceeds the 2 MiB limit",
            )

        chunks.append(chunk)

    raw_html = b"".join(chunks)
    encoding = response.charset_encoding or "utf-8"

    try:
        return raw_html.decode(encoding, errors="replace")
    except LookupError:
        return raw_html.decode("utf-8", errors="replace")


def meta_content(
    document: HTMLParser,
    *,
    property_name: str | None = None,
    name: str | None = None,
) -> str | None:
    """Read a meta element's content attribute."""

    if property_name is not None:
        selector = f'meta[property="{property_name}"]'
    elif name is not None:
        selector = f'meta[name="{name}"]'
    else:
        raise ValueError("property_name or name is required")

    node = document.css_first(selector)

    if node is None:
        return None

    return normalize_text(node.attributes.get("content"))


def document_title(document: HTMLParser) -> str | None:
    """Read and normalize the HTML title."""

    node = document.css_first("title")

    if node is None:
        return None

    return normalize_text(node.text(strip=True))


def extract_canonical_url(
    document: HTMLParser,
    base_url: str,
) -> str:
    """Read the canonical URL or use the response URL."""

    node = document.css_first('link[rel="canonical"]')

    if node is None:
        return base_url

    href = normalize_text(node.attributes.get("href"))

    if href is None:
        return base_url

    return urljoin(base_url, href)


def extract_metadata(
    html: str,
    *,
    final_url: str,
) -> ExternalMetadata:
    """Extract OGP and fallback metadata from HTML."""

    document = HTMLParser(html)

    title = meta_content(document, property_name="og:title") or document_title(document)

    description = meta_content(
        document, property_name="og:description"
    ) or meta_content(document, name="description")

    image_value = meta_content(
        document,
        property_name="og:image",
    )
    image = urljoin(final_url, image_value) if image_value is not None else None

    hostname = urlsplit(final_url).hostname
    fallback_site_name = hostname or final_url

    site_name = (
        meta_content(document, property_name="og:site_name") or fallback_site_name
    )

    published_at = meta_content(
        document,
        property_name="article:published_time",
    )

    return ExternalMetadata(
        title=title,
        description=description,
        image=image,
        site_name=site_name,
        canonical_url=extract_canonical_url(
            document,
            final_url,
        ),
        published_at=published_at,
    )


def fetch_external_metadata(url: str) -> ExternalMetadata:
    """Fetch and extract metadata from an external URL."""

    validate_external_url(url)

    try:
        with httpx.Client(
            follow_redirects=True,
            max_redirects=5,
            timeout=httpx.Timeout(10.0),
            headers={
                "User-Agent": USER_AGENT,
                "Accept": ("text/html," "application/xhtml+xml;q=0.9," "*/*;q=0.1"),
            },
        ) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()

                final_url = str(response.url)
                validate_external_url(final_url)

                html = read_html_response(response)

    except httpx.TooManyRedirects as error:
        raise ExternalFetchError(
            "too many redirects",
        ) from error
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        raise ExternalFetchError(
            f"server returned HTTP {status}",
        ) from error
    except httpx.RequestError as error:
        raise ExternalFetchError(
            f"request failed: {error}",
        ) from error

    return extract_metadata(
        html,
        final_url=final_url,
    )


def current_timestamp() -> str:
    """Return the current UTC timestamp."""

    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def serialize_markdown(
    parsed: ParsedMarkdown,
    frontmatter: TOMLDocument,
) -> str:
    """Serialize frontmatter and the original Markdown body."""

    serialized = tomlkit.dumps(frontmatter)

    if not serialized.endswith("\n"):
        serialized += "\n"

    return "+++\n" f"{serialized}" "+++\n" f"{parsed.body}"


def escape_markdown_link_text(value: str) -> str:
    """Escape text used as a Markdown link label."""

    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def render_external_article_body(
    *,
    title: str,
    site_name: str,
    url: str,
) -> str:
    """Render the managed body of an external article."""

    escaped_title = escape_markdown_link_text(title)

    return (
        f"\nこの記事は{site_name}に掲載しています．\n"
        f"\n[{escaped_title} ↗]({url})\n"
    )


def render_updated_markdown(
    parsed: ParsedMarkdown,
    metadata: ExternalMetadata,
    *,
    fetched_at: str,
) -> str:
    """Render an updated external article."""

    frontmatter = copy.deepcopy(parsed.frontmatter)

    extra = frontmatter.get("extra")

    if not isinstance(extra, Mapping):
        raise FrontmatterError("extra must be a table")

    external = extra.get("external")

    if not isinstance(external, Mapping):
        raise FrontmatterError(
            "extra.external must be a table",
        )

    had_fetched_at = "fetched_at" in external
    locked_fields = read_locked_fields(external)

    if "title" not in locked_fields and metadata.title is not None:
        frontmatter["title"] = metadata.title

    if "description" not in locked_fields and metadata.description is not None:
        frontmatter["description"] = metadata.description

    if "site_name" not in locked_fields:
        external["site_name"] = metadata.site_name

    if "canonical_url" not in locked_fields:
        external["canonical_url"] = metadata.canonical_url

    if "image" not in locked_fields and metadata.image is not None:
        external["image"] = metadata.image

    if "published_at" not in locked_fields and metadata.published_at is not None:
        external["published_at"] = metadata.published_at

    if "body" not in locked_fields:
        title = frontmatter.get("title")
        url = external.get("url")
        site_name = external.get("site_name")

        if not isinstance(title, str) or not title.strip():
            raise FrontmatterError("title must be a non-empty string")

        if not isinstance(url, str) or not url.strip():
            raise FrontmatterError(
                "extra.external.url must be a non-empty string",
            )

        if not isinstance(site_name, str) or not site_name.strip():
            raise FrontmatterError(
                "extra.external.site_name must be a non-empty string",
            )

        parsed = ParsedMarkdown(
            path=parsed.path,
            original=parsed.original,
            frontmatter=parsed.frontmatter,
            body=render_external_article_body(
                title=title,
                site_name=site_name,
                url=url,
            ),
        )

    candidate = serialize_markdown(
        parsed,
        frontmatter,
    )

    if candidate == parsed.original and had_fetched_at:
        return parsed.original

    external["fetched_at"] = fetched_at

    return serialize_markdown(
        parsed,
        frontmatter,
    )


def unified_markdown_diff(
    parsed: ParsedMarkdown,
    updated: str,
) -> str:
    """Create a unified diff for a Markdown update."""

    path = str(display_path(parsed.path))

    return "".join(
        difflib.unified_diff(
            parsed.original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        ),
    )


def write_markdown_atomically(
    path: Path,
    content: str,
) -> None:
    """Replace a Markdown file atomically."""

    original_mode = path.stat().st_mode & 0o777
    temporary_path: Path | None = None

    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            text=True,
        )
        temporary_path = Path(temporary_name)

        with os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())

        os.chmod(
            temporary_path,
            original_mode,
        )
        os.replace(
            temporary_path,
            path,
        )
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def resolve_requested_articles(
    paths: list[Path],
    content_dir: Path,
) -> list[ExternalArticle]:
    """Resolve explicitly requested or all external articles."""

    if not paths:
        return list(find_external_articles(content_dir))

    articles: list[ExternalArticle] = []

    for requested_path in paths:
        path = requested_path

        if not path.is_absolute():
            path = ROOT / path

        path = path.resolve()

        if not path.is_file():
            raise FrontmatterError(
                f"{display_path(path)}: file does not exist",
            )

        article = parse_external_article(path)

        if article is None:
            raise FrontmatterError(
                f"{display_path(path)}: " "not an external article",
            )

        articles.append(article)

    return articles


def process_updates(
    paths: list[Path],
    content_dir: Path,
    *,
    write: bool,
) -> int:
    """Fetch metadata and preview or write Markdown changes."""

    try:
        articles = resolve_requested_articles(
            paths,
            content_dir,
        )
    except FrontmatterError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if not articles:
        print("No external articles found.")
        return 0

    fetched_at = current_timestamp()
    failed = False
    changed_count = 0

    for article in articles:
        path_label = display_path(article.path)

        print(
            f"Fetching {path_label}...",
            file=sys.stderr,
        )

        try:
            metadata = fetch_external_metadata(article.url)
            parsed = read_markdown(article.path)

            if parsed is None:
                raise FrontmatterError(
                    "TOML frontmatter is missing",
                )

            updated = render_updated_markdown(
                parsed,
                metadata,
                fetched_at=fetched_at,
            )

            if updated == parsed.original:
                print(
                    f"No changes: {path_label}",
                    file=sys.stderr,
                )
                continue

            if write:
                write_markdown_atomically(
                    article.path,
                    updated,
                )
                print(f"Updated {path_label}")
            else:
                diff = unified_markdown_diff(
                    parsed,
                    updated,
                )
                print(diff, end="")

            changed_count += 1

        except (
            ExternalFetchError,
            FrontmatterError,
            OSError,
            UnicodeError,
        ) as error:
            print(
                f"error: {path_label}: {error}",
                file=sys.stderr,
            )
            failed = True

    if changed_count == 0 and not failed:
        print("No changes.")

    if write and changed_count > 0:
        print()
        print(
            f"Updated {changed_count} external article(s).",
        )

    return 1 if failed else 0


def list_external_articles(content_dir: Path) -> int:
    """List external articles in a content directory."""

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
        print(display_path(article.path))
        print(f"  URL: {article.url}")
        print(f"  Site: {article.site_name or '(not set)'}")
        print(f"  Kind: {article.kind or '(not set)'}")
        locked = ", ".join(sorted(article.locked_fields)) or "(none)"
        print(f"  Locked: {locked}")

    print()
    print(f"Found {len(articles)} external article(s).")

    return 0


def fetch_and_print_metadata(url: str) -> int:
    """Fetch one URL and print its metadata as JSON."""

    try:
        metadata = fetch_external_metadata(url)
    except ExternalFetchError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            asdict(metadata),
            ensure_ascii=False,
            indent=2,
        ),
    )

    return 0


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Manage external articles " "in the Zola content directory."),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="external article Markdown files",
    )
    parser.add_argument(
        "--content-dir",
        type=Path,
        default=DEFAULT_CONTENT_DIR,
        help="content directory to inspect",
    )
    parser.add_argument(
        "--fetch-only",
        metavar="URL",
        help=("fetch metadata from one URL " "and print it as JSON"),
    )

    update_mode = parser.add_mutually_exclusive_group()

    update_mode.add_argument(
        "--dry-run",
        action="store_true",
        help=("fetch metadata and show Markdown changes " "without writing files"),
    )
    update_mode.add_argument(
        "--write",
        action="store_true",
        help="fetch metadata and update Markdown files",
    )
    return parser.parse_args()


def main() -> int:
    """Run the command-line tool."""

    args = parse_arguments()

    if args.fetch_only is not None:
        if args.dry_run or args.write or args.paths:
            print(
                "error: --fetch-only cannot be combined "
                "with paths, --dry-run, or --write",
                file=sys.stderr,
            )
            return 2

        return fetch_and_print_metadata(
            args.fetch_only,
        )

    content_dir = args.content_dir.resolve()

    if not content_dir.is_dir():
        print(
            f"content directory does not exist: {content_dir}",
            file=sys.stderr,
        )
        return 2

    if args.dry_run:
        return process_updates(
            args.paths,
            content_dir,
            write=False,
        )

    if args.write:
        return process_updates(
            args.paths,
            content_dir,
            write=True,
        )

    if args.paths:
        print(
            "error: paths require --dry-run or --write",
            file=sys.stderr,
        )
        return 2

    return list_external_articles(content_dir)


if __name__ == "__main__":
    raise SystemExit(main())
