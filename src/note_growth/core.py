from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup
from slugify import slugify

USER_AGENT = "note-growth-autopublisher/0.1 (+https://github.com/)"
BLOCKED_NOTE_PATHS = ("/api/", "/v1/", "/v2/", "/v3/")
DEFAULT_BANNED_CLAIMS = ["必ず儲かる", "絶対稼げる", "楽して稼げる", "保証します"]

DEFAULT_CONFIG: dict[str, Any] = {
    "brand": {"name": "note収益化ラボ", "voice": "実務的で誠実"},
    "strategy": {
        "theme": "収益化につながる実用ノウハウ",
        "target_reader": "noteで有料記事やメンバーシップを伸ばしたい個人クリエイター",
        "paid_boundary_marker": "<!-- paid_boundary -->",
        "prohibited_claims": [
            "必ず儲かる",
            "絶対稼げる",
            "誰でも簡単に稼げる",
            "楽して稼げる",
            "保証します",
        ],
    },
    "research": {"sources": [], "rss": [], "max_sources": 8},
    "generation": {"output_dir": "outputs", "originality_max_similarity": 0.32},
    "publication": {"mode": "artifact"},
    "metrics": {"csv_path": "data/sample_metrics.csv"},
}

WINNING_PATTERNS = [
    "無料部分で『この記事を読むと何ができるようになるか』を先に約束する",
    "単なる体験談ではなく、読者が今日実行できる手順に変換する",
    "価格以上に回収できる実用価値を明確にする",
    "文字数を増やすより、導入・見出し・有料境界の納得感を優先する",
    "収益保証ではなく、検証可能な小さな改善を積み上げる",
]

STOP_WORDS = {"こと", "これ", "ため", "よう", "する", "ある", "です", "ます", "note"}


@dataclass(frozen=True)
class SourceDocument:
    url: str
    title: str
    text: str
    source_type: str = "url"
    fetched_at: str = field(default_factory=lambda: utc_now_iso())
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


class SourcePolicyError(ValueError):
    """Raised when a source looks like a private or unofficial API endpoint."""


class UnsupportedPublisherError(RuntimeError):
    """Raised when a publication mode would rely on unsupported automation."""


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def ensure_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_text(path: str | Path, text: str) -> Path:
    target = Path(path)
    ensure_dir(target.parent)
    target.write_text(text, encoding="utf-8")
    return target


def write_json(path: str | Path, payload: Any) -> Path:
    target = Path(path)
    ensure_dir(target.parent)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        return DEFAULT_CONFIG
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}
    return deep_merge(DEFAULT_CONFIG, loaded)


def validate_public_source_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SourcePolicyError(f"Unsupported URL scheme: {url}")
    if parsed.netloc.endswith("note.com") and any(p in parsed.path.lower() for p in BLOCKED_NOTE_PATHS):
        raise SourcePolicyError("note.com unofficial API paths are blocked. Use public pages or RSS.")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def html_to_document(url: str, html: str, source_type: str = "url") -> SourceDocument:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = normalize_text(soup.title.get_text(" ")) if soup.title else url
    return SourceDocument(url=url, title=title, text=normalize_text(soup.get_text(" ")), source_type=source_type)


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
        documents.append(
            SourceDocument(
                url=entry.get("link", url),
                title=normalize_text(entry.get("title", "RSS entry")),
                text=normalize_text(entry.get("summary", "")),
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
                document = SourceDocument(url=document.url, title=str(source["label"]), text=document.text)
            documents.append(document)
        except Exception as exc:  # noqa: BLE001
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


def save_collection(documents: list[SourceDocument], errors: list[str], output_dir: str | Path) -> Path:
    payload = {"documents": [asdict(document) for document in documents], "errors": errors}
    return write_json(Path(output_dir) / "research" / "collection.json", payload)


def extract_terms(text: str, limit: int = 12) -> list[str]:
    tokens = re.findall(r"#[\wぁ-んァ-ン一-龥ー]+|[A-Za-z0-9_]{3,}|[ぁ-んァ-ン一-龥ー]{2,}", text)
    counter: Counter[str] = Counter()
    for token in tokens:
        normalized = token.strip().lower()
        if normalized not in STOP_WORDS and len(normalized) >= 2:
            counter[normalized] += 1
    return [term for term, _count in counter.most_common(limit)]


def analyze_documents(documents: list[SourceDocument], config: dict[str, Any], topic: str | None = None) -> ResearchInsight:
    fallback_topic = config.get("strategy", {}).get("theme", "収益化につながる実用ノウハウ")
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
        winning_patterns=WINNING_PATTERNS,
        content_gaps=content_gaps,
        source_urls=[document.url for document in documents],
    )


def first_terms(terms: list[str], count: int = 3) -> str:
    selected = [term.replace("#", "") for term in terms[:count]]
    return "・".join(selected) if selected else "note収益化"


def build_article(insight: ResearchInsight, config: dict[str, Any]) -> DraftArticle:
    strategy = config.get("strategy", {})
    target_reader = strategy.get("target_reader", "noteで有料記事を伸ばしたい人")
    marker = strategy.get("paid_boundary_marker", "<!-- paid_boundary -->")
    brand = config.get("brand", {}).get("name", "note収益化ラボ")
    title = f"{first_terms(insight.top_terms)}で『買われるnote』を作る3つの設計"
    patterns = "\n".join(f"- {pattern}" for pattern in insight.winning_patterns)
    gaps = "\n".join(f"- {gap}" for gap in insight.content_gaps)
    sources = "\n".join(f"- {url}" for url in insight.source_urls) or "- 収集対象なし"

    body = f"""# {title}

こんにちは、{brand}です。

この記事は、{target_reader}に向けて、公開情報から見えた「買われやすい構造」を、今日使える記事設計に落とし込んだものです。

最初に大事な前提を書きます。この記事は収益を保証するものではありません。けれど、読者が購入前に感じる不安を減らし、記事の価値が伝わる確率を上げるためのチェックポイントは作れます。

## 調査から見えた前提

{patterns}

逆に、伸びにくい記事には次のような穴が出やすいです。

{gaps}

つまり、「稼げる」と強く言うよりも、読者が自分の状況に当てはめて「この内容なら元が取れそう」と判断できる構成にすることが重要です。

## 設計1: 無料部分で約束を1つに絞る

無料部分でやることは、情報を全部見せることではありません。読者に伝えるべきなのは、読み終わったあとに何ができるようになるか、どんな人に向いているか、有料部分に何が入っているかの3点です。

## 設計2: 有料部分は量ではなく再現手順にする

有料部分で読者が買っているのは、文字数ではなくショートカットです。失敗例、判断基準、手順、テンプレート、注意点の順番に並べると、読者は「読む前」と「読んだ後」の差分を感じやすくなります。

## 設計3: タイトルは煽りではなく変化を示す

おすすめは、Before、After、Methodを入れる型です。たとえば「AI副業で稼ぐ方法」よりも、「AI副業の初案件前に作る、提案文テンプレート3点セット」のほうが、読者が得られるものを判断しやすくなります。

{marker}

## 有料パートに置くなら: 実践テンプレート

### 導入テンプレート

> この記事は、〇〇で悩んでいる人が、△△を作れるようになるための記事です。向いている人は□□です。向いていない人は◇◇です。有料部分には、チェックリスト、手順、テンプレートを入れています。

### 有料境界チェック

- 無料部分だけで、記事の価値が伝わるか
- 有料部分に、読者が保存して使える要素があるか
- 成果保証や過度な煽りになっていないか
- 自分の経験、検証、一次情報が入っているか

### 次回改善の見方

1. 表示数が少ない: タイトルとテーマを修正
2. スキ率が低い: 導入と無料部分の共感を修正
3. 購入率が低い: 有料境界と中身の約束を修正
4. コメントが少ない: 最後に読者へ聞く質問を追加

## まとめ

売れる記事を狙うほど、強い言葉を使いたくなります。けれど長く購読される記事に必要なのは、煽りよりも信頼です。

---

### リサーチメモ

{sources}
"""
    return DraftArticle(
        title=title,
        body_markdown=body,
        topic=insight.topic,
        source_urls=insight.source_urls,
        compliance_notes=[
            "収益保証表現を避けています。",
            "公開情報の傾向を要約し、本文は独自構成で作成しています。",
            "有料記事のコピーや非公開情報の再利用を前提にしていません。",
        ],
        metadata={"top_terms": insight.top_terms, "source_count": insight.source_count},
    )


def max_similarity_against_sources(article: DraftArticle, documents: list[SourceDocument]) -> float:
    if not documents:
        return 0.0
    scores = [SequenceMatcher(None, article.body_markdown[:6000], document.text[:6000]).ratio() for document in documents]
    return max(scores) if scores else 0.0


def validate_article(article: DraftArticle, documents: list[SourceDocument], config: dict[str, Any]) -> list[str]:
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


def publish_article(article: DraftArticle, config: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    mode = str(config.get("publication", {}).get("mode", "artifact"))
    if mode in {"note_api", "selenium", "browser", "cookie"}:
        raise UnsupportedPublisherError("Direct note.com posting is not implemented because note has no official public posting API.")
    if mode not in {"artifact", "manual", "note_manual"}:
        raise UnsupportedPublisherError(f"Unsupported publication mode: {mode}")
    outbox = ensure_dir(Path(output_dir) / "outbox")
    draft_path = outbox / f"{slugify(article.title, lowercase=True, max_length=80) or 'draft'}.md"
    checklist_path = outbox / f"{draft_path.stem}.checklist.md"
    source_lines = "\n".join(f"  - {url}" for url in article.source_urls) or "  - none"
    front_matter = f"---\ntitle: \"{article.title}\"\nstatus: ready_for_note_manual_post\ngenerated_at: \"{utc_now_iso()}\"\nsources:\n{source_lines}\n---\n\n"
    write_text(draft_path, front_matter + article.body_markdown)
    write_text(checklist_path, build_posting_checklist(article))
    write_json(outbox / f"{draft_path.stem}.metadata.json", asdict(article))
    manifest = {
        "mode": mode,
        "generated_at": utc_now_iso(),
        "title": article.title,
        "draft_path": str(draft_path),
        "checklist_path": str(checklist_path),
        "next_step": "Paste draft.md into the official note editor or schedule via note official UI.",
    }
    write_json(outbox / "manifest.json", manifest)
    return manifest


def build_posting_checklist(article: DraftArticle) -> str:
    return f"""# 投稿前チェックリスト: {article.title}

1. noteにログインする
2. 新規記事を作成する
3. 生成されたMarkdownを貼り付ける
4. `<!-- paid_boundary -->` の位置を有料エリア境界の候補として確認する
5. タイトル、見出し画像、ハッシュタグ、価格を設定する
6. 誇大表現、権利侵害、収益保証表現がないか確認する
7. 予約投稿を使う場合はnote公式の予約投稿機能で日時を設定する
"""


def load_metrics(path: str | Path) -> list[dict[str, Any]]:
    metrics_path = Path(path)
    if not metrics_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with metrics_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            normalized: dict[str, Any] = dict(row)
            for field_name in ("views", "likes", "comments", "sales", "price"):
                normalized[field_name] = float(row.get(field_name) or 0)
            rows.append(normalized)
    return rows


def score_row(row: dict[str, Any]) -> float:
    return row.get("views", 0) * 0.02 + row.get("likes", 0) + row.get("comments", 0) * 3 + row.get("sales", 0) * 12


def analyze_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "generated_at": utc_now_iso(),
            "row_count": 0,
            "summary": "No metrics yet. Publish at least one article and record metrics.",
            "recommendations": ["最初の3本はテーマを変えすぎず、タイトルと導入だけを比較する"],
        }
    enriched = []
    for row in rows:
        views = row.get("views", 0) or 0
        likes = row.get("likes", 0) or 0
        sales = row.get("sales", 0) or 0
        enriched.append({**row, "score": round(score_row(row), 2), "like_rate": round(likes / views, 4) if views else 0, "sales_rate": round(sales / views, 4) if views else 0})
    ranked = sorted(enriched, key=lambda item: item["score"], reverse=True)
    top = ranked[0]
    return {
        "generated_at": utc_now_iso(),
        "row_count": len(rows),
        "average_like_rate": round(mean(item["like_rate"] for item in enriched), 4),
        "average_sales_rate": round(mean(item["sales_rate"] for item in enriched), 4),
        "ranked": ranked,
        "recommendations": [
            f"次回は上位記事『{top.get('title', 'untitled')}』の読者約束を流用する",
            "viewsが低い記事は、タイトルにBefore/Afterと成果物名を入れる",
            "likesはあるのにsalesが低い記事は、有料境界の直前に中身の目次を追加する",
        ],
    }


def write_metrics_report(report: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    target_dir = ensure_dir(Path(output_dir) / "iteration")
    json_path = write_json(target_dir / "metrics_report.json", report)
    body = "# 次回改善案\n\n" + "\n".join(f"- {item}" for item in report.get("recommendations", [])) + "\n"
    md_path = write_text(target_dir / "improvement_plan.md", body)
    return {"json_path": str(json_path), "markdown_path": str(md_path)}


def output_dir(config: dict[str, Any]) -> Path:
    return ensure_dir(config.get("generation", {}).get("output_dir", "outputs"))


def run_cycle(config: dict[str, Any], topic: str | None = None) -> dict[str, Any]:
    out = output_dir(config)
    documents, errors = collect_documents(config)
    save_collection(documents, errors, out)
    insight = analyze_documents(documents, config, topic=topic)
    article = build_article(insight, config)
    problems = validate_article(article, documents, config)
    if problems:
        write_json(out / "validation_errors.json", problems)
        raise ValueError("; ".join(problems))
    manifest = publish_article(article, config, out)
    metrics_path = config.get("metrics", {}).get("csv_path", "data/sample_metrics.csv")
    metrics_paths = write_metrics_report(analyze_metrics(load_metrics(metrics_path)), out)
    summary = {"draft": manifest, "research": asdict(insight), "collection_errors": errors, "metrics": metrics_paths}
    write_json(out / "run_summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="note growth autopublisher")
    parser.add_argument("--config", default="config/example.yml")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("collect", "draft", "publish", "run-cycle"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--topic", default=None)
    metrics = subparsers.add_parser("metrics")
    metrics.add_argument("--metrics", default=None)
    return parser


def cli_main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    out = output_dir(config)
    if args.command == "collect":
        docs, errors = collect_documents(config)
        print(f"Collected {len(docs)} documents -> {save_collection(docs, errors, out)}")
        return 0
    if args.command in {"draft", "publish", "run-cycle"}:
        summary = run_cycle(config, topic=args.topic)
        print(f"Run summary -> {out / 'run_summary.json'}")
        print(f"Draft -> {summary['draft']['draft_path']}")
        return 0
    if args.command == "metrics":
        metrics_path = args.metrics or config.get("metrics", {}).get("csv_path", "data/sample_metrics.csv")
        paths = write_metrics_report(analyze_metrics(load_metrics(metrics_path)), out)
        print(f"Metrics report -> {paths['json_path']}")
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2
