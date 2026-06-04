import json

import pytest

from note_growth.core import (
    DEFAULT_CONFIG,
    SourceDocument,
    SourcePolicyError,
    UnsupportedPublisherError,
    analyze_documents,
    analyze_metrics,
    build_article,
    html_to_document,
    publish_article,
    score_row,
    validate_article,
    validate_public_source_url,
)


def test_html_to_document_extracts_title_and_blocks_script_text() -> None:
    doc = html_to_document(
        "https://example.com",
        "<html><head><title>Test</title></head><body><h1>Hello</h1><script>x</script></body></html>",
    )
    assert doc.title == "Test"
    assert "Hello" in doc.text
    assert "script" not in doc.text.lower()


def test_note_api_paths_are_blocked() -> None:
    with pytest.raises(SourcePolicyError):
        validate_public_source_url("https://note.com/api/v3/notes")


def test_build_article_contains_paid_boundary_and_avoids_banned_claims() -> None:
    docs = [SourceDocument(url="https://example.com/source", title="source", text="AI活用 SNS運用 複業")]
    insight = analyze_documents(docs, DEFAULT_CONFIG, topic="AI副業")
    article = build_article(insight, DEFAULT_CONFIG)

    assert "<!-- paid_boundary -->" in article.body_markdown
    assert "必ず儲かる" not in article.body_markdown
    assert "絶対稼げる" not in article.body_markdown
    assert validate_article(article, docs, DEFAULT_CONFIG) == []


def test_publish_article_writes_artifacts(tmp_path) -> None:
    docs = [SourceDocument(url="https://example.com", title="example", text="AI活用 SNS運用")]
    article = build_article(analyze_documents(docs, DEFAULT_CONFIG), DEFAULT_CONFIG)
    manifest = publish_article(article, DEFAULT_CONFIG, tmp_path)

    assert "draft_path" in manifest
    draft_path = tmp_path / "outbox" / manifest["draft_path"].split("outbox/")[-1]
    assert draft_path.exists()
    assert "ready_for_note_manual_post" in draft_path.read_text(encoding="utf-8")
    manifest_path = tmp_path / "outbox" / "manifest.json"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["mode"] == "artifact"


def test_direct_note_api_mode_is_blocked(tmp_path) -> None:
    docs = [SourceDocument(url="https://example.com", title="example", text="AI活用 SNS運用")]
    article = build_article(analyze_documents(docs, DEFAULT_CONFIG), DEFAULT_CONFIG)
    config = {**DEFAULT_CONFIG, "publication": {"mode": "note_api"}}

    with pytest.raises(UnsupportedPublisherError):
        publish_article(article, config, tmp_path)


def test_metrics_report_ranks_sales_heavily() -> None:
    row = {"views": 100, "likes": 10, "comments": 1, "sales": 2, "price": 980}
    assert score_row(row) == 39
    report = analyze_metrics([row | {"title": "A", "published_at": "2026-01-01"}])
    assert report["row_count"] == 1
    assert report["ranked"][0]["title"] == "A"
    assert report["recommendations"]
