from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


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
    "generation": {
        "output_dir": "outputs",
        "article_count": 1,
        "originality_max_similarity": 0.32,
    },
    "publication": {"mode": "artifact"},
    "metrics": {"csv_path": "data/sample_metrics.csv"},
}


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
