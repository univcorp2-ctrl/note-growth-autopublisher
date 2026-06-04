import json

from note_growth.analyzer import analyze_documents
from note_growth.config import DEFAULT_CONFIG
from note_growth.models import SourceDocument
from note_growth.publisher import UnsupportedPublisherError, publish_article
from note_growth.writer import build_article


def _article():
    docs = [SourceDocument(url="https://example.com", title="example", text="AI活用 SNS運用")]
    insight = analyze_documents(docs, DEFAULT_CONFIG, topic="AI副業")
    return build_article(insight, DEFAULT_CONFIG)


def test_publish_article_writes_artifacts(tmp_path) -> None:
    article = _article()
    manifest = publish_article(article, DEFAULT_CONFIG, tmp_path)

    assert "draft_path" in manifest
    assert "checklist_path" in manifest
    draft_path = tmp_path / "outbox" / manifest["draft_path"].split("outbox/")[-1]
    assert draft_path.exists()
    assert "ready_for_note_manual_post" in draft_path.read_text(encoding="utf-8")
    manifest_path = tmp_path / "outbox" / "manifest.json"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["mode"] == "artifact"


def test_direct_note_api_mode_is_blocked(tmp_path) -> None:
    config = {**DEFAULT_CONFIG, "publication": {"mode": "note_api"}}
    try:
        publish_article(_article(), config, tmp_path)
    except UnsupportedPublisherError as exc:
        assert "official" in str(exc)
    else:
        raise AssertionError("Expected UnsupportedPublisherError")
