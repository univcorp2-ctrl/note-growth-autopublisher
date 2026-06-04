from note_growth.analyzer import analyze_documents
from note_growth.config import DEFAULT_CONFIG
from note_growth.models import SourceDocument
from note_growth.writer import build_article, max_similarity_against_sources, validate_article


def test_build_article_contains_paid_boundary_and_avoids_banned_claims() -> None:
    docs = [
        SourceDocument(
            url="https://example.com/source",
            title="source",
            text="AI活用 SNS運用 複業 在宅ワーク 実用ノウハウ 価格 価値 無料部分",
        )
    ]
    insight = analyze_documents(docs, DEFAULT_CONFIG, topic="AI副業")
    article = build_article(insight, DEFAULT_CONFIG)

    assert "<!-- paid_boundary -->" in article.body_markdown
    assert "必ず儲かる" not in article.body_markdown
    assert "絶対稼げる" not in article.body_markdown
    assert validate_article(article, docs, DEFAULT_CONFIG) == []


def test_similarity_checker_stays_low_for_original_article() -> None:
    docs = [
        SourceDocument(
            url="https://example.com/a",
            title="a",
            text="同じ文章を大量にコピーしたものではありません。" * 50,
        )
    ]
    insight = analyze_documents(docs, DEFAULT_CONFIG, topic="note収益化")
    article = build_article(insight, DEFAULT_CONFIG)

    assert max_similarity_against_sources(article, docs) < 0.32
