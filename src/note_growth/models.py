from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class SourceDocument:
    url: str
    title: str
    text: str
    source_type: str = "url"
    fetched_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchInsight:
    topic: str
    source_count: int
    top_terms: list[str]
    winning_patterns: list[str]
    content_gaps: list[str]
    source_urls: list[str]


@dataclass(frozen=True)
class DraftArticle:
    title: str
    body_markdown: str
    topic: str
    source_urls: list[str]
    compliance_notes: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
