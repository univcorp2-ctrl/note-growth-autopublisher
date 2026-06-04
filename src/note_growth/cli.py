from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any

from note_growth.analyzer import analyze_documents
from note_growth.collector import collect_documents, save_collection
from note_growth.config import load_config
from note_growth.io import ensure_dir, write_json
from note_growth.metrics import analyze_metrics, load_metrics, write_metrics_report
from note_growth.publisher import publish_article
from note_growth.writer import build_article, validate_article


def _output_dir(config: dict[str, Any]) -> Path:
    return ensure_dir(config.get("generation", {}).get("output_dir", "outputs"))


def command_collect(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    output_dir = _output_dir(config)
    documents, errors = collect_documents(config)
    path = save_collection(documents, errors, output_dir)
    print(f"Collected {len(documents)} documents -> {path}")
    if errors:
        print("Collection warnings:")
        for error in errors:
            print(f"- {error}")
    return 0


def command_draft(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    output_dir = _output_dir(config)
    documents, errors = collect_documents(config)
    insight = analyze_documents(documents, config, topic=args.topic)
    article = build_article(insight, config)
    problems = validate_article(article, documents, config)
    if problems:
        for problem in problems:
            print(f"Validation problem: {problem}")
        return 2
    research_dir = ensure_dir(output_dir / "research")
    write_json(research_dir / "insight.json", asdict(insight))
    write_json(research_dir / "collection_errors.json", errors)
    manifest = publish_article(article, config, output_dir)
    print(f"Draft generated -> {manifest['draft_path']}")
    return 0


def command_publish(args: argparse.Namespace) -> int:
    return command_draft(args)


def command_metrics(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    metrics_path = args.metrics or config.get("metrics", {}).get("csv_path", "data/sample_metrics.csv")
    output_dir = _output_dir(config)
    rows = load_metrics(metrics_path)
    report = analyze_metrics(rows)
    paths = write_metrics_report(report, output_dir)
    print(f"Metrics report -> {paths['json_path']}")
    print(f"Improvement plan -> {paths['markdown_path']}")
    return 0


def command_run_cycle(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    output_dir = _output_dir(config)
    documents, errors = collect_documents(config)
    save_collection(documents, errors, output_dir)

    insight = analyze_documents(documents, config, topic=args.topic)
    article = build_article(insight, config)
    problems = validate_article(article, documents, config)
    if problems:
        write_json(output_dir / "validation_errors.json", problems)
        for problem in problems:
            print(f"Validation problem: {problem}")
        return 2

    manifest = publish_article(article, config, output_dir)
    metrics_path = config.get("metrics", {}).get("csv_path", "data/sample_metrics.csv")
    metrics_report = analyze_metrics(load_metrics(metrics_path))
    metrics_paths = write_metrics_report(metrics_report, output_dir)

    summary = {
        "draft": manifest,
        "research": asdict(insight),
        "collection_errors": errors,
        "metrics": metrics_paths,
    }
    write_json(output_dir / "run_summary.json", summary)
    print(f"Run summary -> {output_dir / 'run_summary.json'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="note growth autopublisher")
    parser.add_argument("--config", default="config/example.yml", help="Path to config YAML")

    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Collect public research sources")
    collect.set_defaults(func=command_collect)

    draft = subparsers.add_parser("draft", help="Generate a draft artifact")
    draft.add_argument("--topic", default=None, help="Override article topic")
    draft.set_defaults(func=command_draft)

    publish = subparsers.add_parser("publish", help="Generate publication artifact")
    publish.add_argument("--topic", default=None, help="Override article topic")
    publish.set_defaults(func=command_publish)

    metrics = subparsers.add_parser("metrics", help="Analyze post metrics CSV")
    metrics.add_argument("--metrics", default=None, help="Path to metrics CSV")
    metrics.set_defaults(func=command_metrics)

    run_cycle = subparsers.add_parser("run-cycle", help="Run research, draft, publish artifact, metrics")
    run_cycle.add_argument("--topic", default=None, help="Override article topic")
    run_cycle.set_defaults(func=command_run_cycle)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
