from __future__ import annotations

import re
from collections import Counter
from typing import Any

from note_growth.models import ResearchInsight, SourceDocument

DEFAULT_WINNING_PATTERNS = [
    "無料部分で『この記事を読むと何ができるようになるか』を先に約束する",
    "単なる体験談ではなく、読者が今日実行できる手順に変換する",
    "価格以上に回収できる実用価値を明確にする",
    "文字数を増やすより、導入・見出し・有料境界の納得感を優先する",
    "収益保証ではなく、検証可能な小さな改善を積み上げる",
]

STOP_WORDS = {
    "こと",
    "これ",
    "ため",
    "よう",
    "する",
    "ある",
    "です",
    "ます",
    "note",
    "https",
    "www",
    "com",
}


def extract_terms(text: str, limit: int = 12) -> list[str]:
    hashtags = re.findall(r"#[\wぁ-んァ-ン一-龥ー]+", text)
    words = re.findall(r"[A-Za-z0-9_]{3,}|[ぁ-んァ-ン一-龥ー]{2,}", text)
    counter: Counter[str] = Counter()
    for token in [*hashtags, *words]:
        normalized = token.strip().lower()
        if normalized in STOP_WORDS or len(normalized) < 2:
            continue
        counter[normalized] += 1
    return [term for term, _count in counter.most_common(limit)]


def analyze_documents(
    documents: list[SourceDocument], config: dict[str, Any], topic: str | None = None
) -> ResearchInsight:
    strategy = config.get("strategy", {})
    fallback_topic = strategy.get("theme", "収益化につながる実用ノウハウ")
    joined_text = " ".join(document.text for document in documents)
    top_terms = extract_terms(joined_text) if joined_text else []
    if not top_terms:
        top_terms = ["AI活用", "SNS運用", "複業", "在宅ワーク", "実用ノウハウ"]

    content_gaps = [
        "成功談だけで終わり、読者の最初の一歩が明確でない記事が多い",
        "無料部分で価値を伝えきれず、有料境界の納得感が弱くなりがち",
        "稼げる表現が強すぎると信頼を落とすため、期待値調整が必要",
    ]

    return ResearchInsight(
        topic=topic or fallback_topic,
        source_count=len(documents),
        top_terms=top_terms,
        winning_patterns=DEFAULT_WINNING_PATTERNS,
        content_gaps=content_gaps,
        source_urls=[document.url for document in documents],
    )
