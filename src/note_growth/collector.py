from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from note_growth.io import ensure_dir, write_json
from note_growth.models import SourceDocument

USER_AGENT = "note-growth-autopublisher/0.1 (+https://github.com/)"
BLOCKED_PATH_PATTERNS = ("/api/", "/v1/", "/v2/", "/v3/")


class SourcePolicyError(ValueError):
    """Raised when a source looks like a private or unofficial API endpoint."""


def validate_public_source_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SourcePolicyError(f"Unsupported URL scheme: {url}")
    lowered_path = parsed.path.lower()
    if parsed.netloc.endswith("note.com") and any(
        pattern in lowered_path for pattern in BLOCKED_PATH_PATTERNS
    ):
        raise SourcePolicyError(
            "note.com unofficial API paths are intentionally blocked. Use public pages or RSS."
        )


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def html_to_document(url: str, html: str, source_type: str = "url") -> SourceDocument:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = normalize_text(soup.title.get_text(" ")) if soup.title else url
    body_text = normalize_text(soup.get_text(" "))
    return SourceDocument(url=url, title=title, text=body_text, source_type=source_type)


def fetch_public_url(url: str, timeout: int = 20) -> SourceDocument:
    validate_public_source_url(url)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return html_to_document(url, response.text)


def fetch_rss(url: str, limit: int = 5) -> list[SourceDocument]:
    validate_public_source_url(url)
    parsed = feedparser.parse(url, agent=USER_AGENT)
    documents: list[SourceDocument] = []
    for entry in parsed.entries[:limit]:
        title = normalize_text(entry.get("title", "RSS entry"))
        link = entry.get("link", url)
        summary = normalize_text(entry.get("summary", ""))
        documents.append(
            SourceDocument(
                url=link,
                title=title,
                text=summary,
                source_type="rss",
                metadata={"feed_url": url},
            )
        )
    return documents


def collect_documents(config: dict[str, Any]) -> tuple[list[SourceDocument], list[str]]:
    research = config.get("research", {})
    max_sources = int(research.get("max_sources", 8))
    documents: list[SourceDocument] = []
    errors: list[str] = []

    for source in research.get("sources", []):
        if len(documents) >= max_sources:
            break
        url = source.get("url") if isinstance(source, dict) else str(source)
        try:
            document = fetch_public_url(url)
            if isinstance(source, dict) and source.get("label"):
                document = SourceDocument(
                    url=document.url,
                    title=str(source["label"]),
                    text=document.text,
                    source_type=document.source_type,
                    metadata=document.metadata,
                )
            documents.append(document)
        except Exception as exc:  # noqa: BLE001 - continue collecting other sources
            errors.append(f"{url}: {exc}")

    remaining = max(0, max_sources - len(documents))
    for feed in research.get("rss", []):
        if remaining <= 0:
            break
        feed_url = feed.get("url") if isinstance(feed, dict) else str(feed)
        try:
            rss_documents = fetch_rss(feed_url, limit=remaining)
            documents.extend(rss_documents)
            remaining = max(0, max_sources - len(documents))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{feed_url}: {exc}")

    return documents[:max_sources], errors


def save_collection(
    documents: list[SourceDocument], errors: list[str], output_dir: str | Path
) -> Path:
    target_dir = ensure_dir(Path(output_dir) / "research")
    payload = {
        "documents": [asdict(document) for document in documents],
        "errors": errors,
    }
    return write_json(target_dir / "collection.json", payload)
