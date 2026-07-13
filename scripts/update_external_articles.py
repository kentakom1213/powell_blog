#!/usr/bin/env python3
"""Find external articles and fetch their metadata."""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
import tomlkit
from selectolax.parser import HTMLParser
from tomlkit.exceptions import ParseError


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTENT_DIR = ROOT / "content"

MAX_RESPONSE_BYTES = 2 * 1024 * 1024

USER_AGENT = (
    "PowellBlogMetadataFetcher/0.1 "
    "(https://github.com/kentakom1213/powell_blog)"
)


class FrontmatterError(Exception):
    """Raised when Markdown frontmatter cannot be read."""


class ExternalFetchError(Exception):
    """Raised when external metadata cannot be fetched."""


@dataclass(frozen=True)
class ExternalArticle:
    """Metadata needed to identify an external article."""

    path: Path
    url: str
    site_name: str | None
    kind: str | None


@dataclass(frozen=True)
class ExternalMetadata:
    """Metadata extracted from an external web page."""

    title: str | None
    description: str | None
    image: str | None
    site_name: str
    canonical_url: str
    published_at: str | None


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
        raise FrontmatterError(
            "extra.external.url must be a non-empty string",
        )

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
            try:
                display_path = path.relative_to(ROOT)
            except ValueError:
                display_path = path

            raise FrontmatterError(
                f"{display_path}: {error}",
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


def read_html_response(
    response: httpx.Response,
) -> str:
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
        return raw_html.decode(
            encoding,
            errors="replace",
        )
    except LookupError:
        return raw_html.decode(
            "utf-8",
            errors="replace",
        )


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
        raise ValueError(
            "property_name or name is required",
        )

    node = document.css_first(selector)

    if node is None:
        return None

    return normalize_text(
        node.attributes.get("content"),
    )


def document_title(
    document: HTMLParser,
) -> str | None:
    """Read and normalize the HTML title."""

    node = document.css_first("title")

    if node is None:
        return None

    return normalize_text(
        node.text(strip=True),
    )


def extract_canonical_url(
    document: HTMLParser,
    base_url: str,
) -> str:
    """Read the canonical URL or use the response URL."""

    node = document.css_first(
        'link[rel="canonical"]',
    )

    if node is None:
        return base_url

    href = normalize_text(
        node.attributes.get("href"),
    )

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

    title = (
        meta_content(
            document,
            property_name="og:title",
        )
        or document_title(document)
    )

    description = (
        meta_content(
            document,
            property_name="og:description",
        )
        or meta_content(
            document,
            name="description",
        )
    )

    image_value = meta_content(
        document,
        property_name="og:image",
    )

    if image_value is None:
        image = None
    else:
        image = urljoin(
            final_url,
            image_value,
        )

    hostname = urlsplit(final_url).hostname
    fallback_site_name = hostname or final_url

    site_name = (
        meta_content(
            document,
            property_name="og:site_name",
        )
        or fallback_site_name
    )

    published_at = meta_content(
        document,
        property_name="article:published_time",
    )

    canonical_url = extract_canonical_url(
        document,
        final_url,
    )

    return ExternalMetadata(
        title=title,
        description=description,
        image=image,
        site_name=site_name,
        canonical_url=canonical_url,
        published_at=published_at,
    )


def fetch_external_metadata(
    url: str,
) -> ExternalMetadata:
    """Fetch and extract metadata from an external URL."""

    validate_external_url(url)

    try:
        with httpx.Client(
            follow_redirects=True,
            max_redirects=5,
            timeout=httpx.Timeout(10.0),
            headers={
                "User-Agent": USER_AGENT,
                "Accept": (
                    "text/html,"
                    "application/xhtml+xml;q=0.9,"
                    "*/*;q=0.1"
                ),
            },
        ) as client:
            with client.stream(
                "GET",
                url,
            ) as response:
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


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Manage external articles "
            "in the Zola content directory."
        ),
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
        help=(
            "fetch metadata from one URL "
            "and print it as JSON"
        ),
    )
    return parser.parse_args()


def list_external_articles(
    content_dir: Path,
) -> int:
    """List external articles in a content directory."""

    if not content_dir.is_dir():
        print(
            f"content directory does not exist: {content_dir}",
            file=sys.stderr,
        )
        return 2

    try:
        articles = list(
            find_external_articles(content_dir),
        )
    except FrontmatterError as error:
        print(
            f"error: {error}",
            file=sys.stderr,
        )
        return 1

    if not articles:
        print("No external articles found.")
        return 0

    for article in articles:
        try:
            display_path = article.path.relative_to(
                ROOT,
            )
        except ValueError:
            display_path = article.path

        print(display_path)
        print(f"  URL: {article.url}")
        print(
            f"  Site: "
            f"{article.site_name or '(not set)'}",
        )
        print(
            f"  Kind: "
            f"{article.kind or '(not set)'}",
        )

    print()
    print(
        f"Found {len(articles)} external article(s).",
    )

    return 0


def fetch_and_print_metadata(
    url: str,
) -> int:
    """Fetch one URL and print its metadata as JSON."""

    try:
        metadata = fetch_external_metadata(url)
    except ExternalFetchError as error:
        print(
            f"error: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            asdict(metadata),
            ensure_ascii=False,
            indent=2,
        ),
    )

    return 0


def main() -> int:
    """Run the command-line tool."""

    args = parse_arguments()

    if args.fetch_only is not None:
        return fetch_and_print_metadata(
            args.fetch_only,
        )

    return list_external_articles(
        args.content_dir.resolve(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
