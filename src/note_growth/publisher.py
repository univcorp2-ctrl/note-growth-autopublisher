from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from slugify import slugify

from note_growth.io import ensure_dir, write_json, write_text
from note_growth.models import DraftArticle, utc_now_iso

SUPPORTED_ARTIFACT_MODES = {"artifact", "manual", "note_manual"}
UNSUPPORTED_DIRECT_MODES = {"note_api", "selenium", "browser", "cookie"}


class UnsupportedPublisherError(RuntimeError):
    """Raised when a requested publication mode would rely on unsupported automation."""


def _front_matter(article: DraftArticle) -> str:
    escaped_title = article.title.replace('"', '\\"')
    source_lines = "\n".join(f"  - {url}" for url in article.source_urls)
    return f"""---
title: "{escaped_title}"
status: "ready_for_note_manual_post"
generated_at: "{utc_now_iso()}"
sources:
{source_lines or "  - none"}
---

"""


def build_posting_checklist(article: DraftArticle) -> str:
    return f"""# 投稿前チェックリスト: {article.title}

## note公式画面で行うこと

1. noteにログインする
2. 新規記事を作成する
3. `draft.md` の本文を貼り付ける
4. `<!-- paid_boundary -->` の位置を有料エリア境界の候補として確認する
5. タイトル、見出し画像、ハッシュタグ、価格を設定する
6. 誇大表現、権利侵害、収益保証表現がないか確認する
7. 予約投稿を使う場合はnote公式の予約投稿機能で日時を設定する

## 品質チェック

- 無料部分だけで記事の価値が伝わる
- 有料部分にテンプレート、手順、チェックリストがある
- 他者記事の丸写しではなく、自分の経験や検証を追記している
- 「必ず儲かる」「絶対稼げる」などの断定を避けている
- 投稿後の反応をCSVへ記録する準備ができている
"""


def publish_article(article: DraftArticle, config: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    mode = str(config.get("publication", {}).get("mode", "artifact"))
    if mode in UNSUPPORTED_DIRECT_MODES:
        raise UnsupportedPublisherError(
            "Direct note.com posting is not implemented because note has no official public "
            "posting API. Use artifact/manual mode or add an official API adapter if note "
            "publishes one in the future."
        )
    if mode not in SUPPORTED_ARTIFACT_MODES:
        raise UnsupportedPublisherError(f"Unsupported publication mode: {mode}")

    outbox = ensure_dir(Path(output_dir) / "outbox")
    slug = slugify(article.title, lowercase=True, max_length=80) or "draft"
    draft_path = outbox / f"{slug}.md"
    checklist_path = outbox / f"{slug}.checklist.md"
    metadata_path = outbox / f"{slug}.metadata.json"

    write_text(draft_path, _front_matter(article) + article.body_markdown)
    write_text(checklist_path, build_posting_checklist(article))
    write_json(metadata_path, asdict(article))

    manifest = {
        "mode": mode,
        "generated_at": utc_now_iso(),
        "title": article.title,
        "draft_path": str(draft_path),
        "checklist_path": str(checklist_path),
        "metadata_path": str(metadata_path),
        "next_step": "Paste draft.md into the official note editor or schedule via note official UI.",
    }
    write_text(outbox / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest
