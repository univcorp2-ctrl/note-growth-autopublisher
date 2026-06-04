from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from note_growth.models import DraftArticle, ResearchInsight, SourceDocument

DEFAULT_BANNED_CLAIMS = ["必ず儲かる", "絶対稼げる", "楽して稼げる", "保証します"]


def _first_terms(terms: list[str], count: int = 3) -> str:
    selected = [term.replace("#", "") for term in terms[:count]]
    return "・".join(selected) if selected else "note収益化"


def build_article(insight: ResearchInsight, config: dict[str, Any]) -> DraftArticle:
    strategy = config.get("strategy", {})
    target_reader = strategy.get(
        "target_reader", "noteで有料記事やメンバーシップを伸ばしたい人"
    )
    marker = strategy.get("paid_boundary_marker", "<!-- paid_boundary -->")
    brand = config.get("brand", {}).get("name", "note収益化ラボ")
    theme_terms = _first_terms(insight.top_terms)
    title = f"{theme_terms}で『買われるnote』を作る3つの設計"

    patterns = "\n".join(f"- {pattern}" for pattern in insight.winning_patterns)
    gaps = "\n".join(f"- {gap}" for gap in insight.content_gaps)
    sources = "\n".join(f"- {url}" for url in insight.source_urls) or "- 収集対象なし"

    body = f"""# {title}

こんにちは、{brand}です。

この記事は、{target_reader}に向けて、公開情報から見えた「買われやすい構造」を、今日使える記事設計に落とし込んだものです。

最初に大事な前提を書きます。この記事は収益を保証するものではありません。けれど、読者が購入前に感じる不安を減らし、記事の価値が伝わる確率を上げるためのチェックポイントは作れます。

## 調査から見えた前提

今回のリサーチでは、次のような傾向を重視しました。

{patterns}

逆に、伸びにくい記事には次のような穴が出やすいです。

{gaps}

つまり、「稼げる」と強く言うよりも、読者が自分の状況に当てはめて「この内容なら元が取れそう」と判断できる構成にすることが重要です。

## 設計1: 無料部分で約束を1つに絞る

無料部分でやることは、情報を全部見せることではありません。

読者に伝えるべきなのは、次の3点です。

1. 読み終わったあとに何ができるようになるか
2. どんな人には向いていて、どんな人には向いていないか
3. 有料部分に何が入っているか

たとえば、テーマが「AI副業」なら、いきなり大量のツール紹介をするより、最初に「初案件を取る前に作るべき1枚の提案テンプレート」のように成果物を固定します。

## 設計2: 有料部分は量ではなく再現手順にする

有料部分で読者が買っているのは、文字数ではなくショートカットです。

おすすめの型は次です。

- 失敗例: なぜ失敗するのか
- 判断基準: 何を見ればよいのか
- 手順: どの順番でやるのか
- テンプレート: そのまま使える形
- 注意点: どこでつまずくのか

この型にすると、読者は「読む前」と「読んだ後」の差分を感じやすくなります。

## 設計3: タイトルは煽りではなく変化を示す

避けたいタイトルは、強い言葉だけで中身が曖昧なものです。

代わりに、次の形にします。

- Before: 何に困っている人向けか
- After: 何ができるようになるか
- Method: どうやって達成するか

例: 「AI副業で稼ぐ方法」よりも、「AI副業の初案件前に作る、提案文テンプレート3点セット」のほうが、読者が得られるものを判断しやすくなります。

{marker}

## 有料パートに置くなら: 実践テンプレート

ここから先は、実際に記事を作るためのテンプレートです。

### 1. 導入テンプレート

> この記事は、〇〇で悩んでいる人が、△△を作れるようになるための記事です。  
> 向いている人は□□です。向いていない人は◇◇です。  
> 有料部分には、チェックリスト、手順、テンプレートを入れています。

### 2. 有料境界チェック

公開前に次を確認します。

- 無料部分だけで、記事の価値が伝わるか
- 有料部分に、読者が保存して使える要素があるか
- 成果保証や過度な煽りになっていないか
- 自分の経験、検証、一次情報が入っているか

### 3. 次回改善の見方

投稿後は、次の順番で見直します。

1. 表示数が少ない: タイトルとテーマを修正
2. スキ率が低い: 導入と無料部分の共感を修正
3. 購入率が低い: 有料境界と中身の約束を修正
4. コメントが少ない: 最後に読者へ聞く質問を追加

## まとめ

売れる記事を狙うほど、強い言葉を使いたくなります。けれど長く購読される記事に必要なのは、煽りよりも信頼です。

読者が「これは自分の課題に使える」と判断できるように、約束、手順、テンプレート、注意点を明確にしていきましょう。

---

### リサーチメモ

{sources}
"""

    compliance_notes = [
        "収益保証表現を避けています。",
        "公開情報の傾向を要約し、本文は独自構成で作成しています。",
        "有料記事のコピーや非公開情報の再利用を前提にしていません。",
    ]
    return DraftArticle(
        title=title,
        body_markdown=body,
        topic=insight.topic,
        source_urls=insight.source_urls,
        compliance_notes=compliance_notes,
        metadata={"top_terms": insight.top_terms, "source_count": insight.source_count},
    )


def max_similarity_against_sources(article: DraftArticle, documents: list[SourceDocument]) -> float:
    if not documents:
        return 0.0
    article_text = article.body_markdown[:6000]
    scores = [
        SequenceMatcher(None, article_text, document.text[:6000]).ratio() for document in documents
    ]
    return max(scores) if scores else 0.0


def validate_article(
    article: DraftArticle, documents: list[SourceDocument], config: dict[str, Any]
) -> list[str]:
    problems: list[str] = []
    strategy = config.get("strategy", {})
    banned_claims = [*DEFAULT_BANNED_CLAIMS, *strategy.get("prohibited_claims", [])]
    for claim in sorted(set(banned_claims)):
        if claim and claim in article.body_markdown:
            problems.append(f"Banned claim found: {claim}")

    max_similarity = max_similarity_against_sources(article, documents)
    threshold = float(config.get("generation", {}).get("originality_max_similarity", 0.32))
    if max_similarity > threshold:
        problems.append(f"Source similarity too high: {max_similarity:.3f} > {threshold:.3f}")
    return problems
