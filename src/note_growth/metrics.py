from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean
from typing import Any

from note_growth.io import ensure_dir, write_json, write_text
from note_growth.models import utc_now_iso

NUMERIC_FIELDS = ("views", "likes", "comments", "sales", "price")


def load_metrics(path: str | Path) -> list[dict[str, Any]]:
    metrics_path = Path(path)
    if not metrics_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with metrics_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            normalized: dict[str, Any] = dict(row)
            for field in NUMERIC_FIELDS:
                normalized[field] = float(row.get(field) or 0)
            rows.append(normalized)
    return rows


def score_row(row: dict[str, Any]) -> float:
    return (
        row.get("views", 0) * 0.02
        + row.get("likes", 0) * 1.0
        + row.get("comments", 0) * 3.0
        + row.get("sales", 0) * 12.0
    )


def analyze_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "generated_at": utc_now_iso(),
            "row_count": 0,
            "summary": "No metrics yet. Publish at least one article and record metrics.",
            "recommendations": [
                "最初の3本はテーマを変えすぎず、タイトルと導入だけを比較する",
                "views、likes、comments、sales、priceをCSVへ追記する",
            ],
        }

    enriched = []
    for row in rows:
        views = row.get("views", 0) or 0
        likes = row.get("likes", 0) or 0
        sales = row.get("sales", 0) or 0
        enriched.append(
            {
                **row,
                "score": round(score_row(row), 2),
                "like_rate": round(likes / views, 4) if views else 0,
                "sales_rate": round(sales / views, 4) if views else 0,
            }
        )

    ranked = sorted(enriched, key=lambda item: item["score"], reverse=True)
    avg_like_rate = mean(item["like_rate"] for item in enriched)
    avg_sales_rate = mean(item["sales_rate"] for item in enriched)
    top = ranked[0]

    recommendations = [
        f"次回は上位記事『{top.get('title', 'untitled')}』の読者約束を流用する",
        "viewsが低い記事は、タイトルにBefore/Afterと成果物名を入れる",
        "likesはあるのにsalesが低い記事は、有料境界の直前に中身の目次を追加する",
        "salesはあるのにcommentsが低い記事は、最後に読者の状況を聞く質問を置く",
    ]

    return {
        "generated_at": utc_now_iso(),
        "row_count": len(rows),
        "average_like_rate": round(avg_like_rate, 4),
        "average_sales_rate": round(avg_sales_rate, 4),
        "ranked": ranked,
        "recommendations": recommendations,
    }


def write_metrics_report(report: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    target_dir = ensure_dir(Path(output_dir) / "iteration")
    json_path = write_json(target_dir / "metrics_report.json", report)
    recommendations = report.get("recommendations", [])
    body = "# 次回改善案\n\n" + "\n".join(f"- {item}" for item in recommendations) + "\n"
    md_path = write_text(target_dir / "improvement_plan.md", body)
    return {"json_path": str(json_path), "markdown_path": str(md_path)}
