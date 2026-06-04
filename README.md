# note-growth-autopublisher

note.com向けに、公開情報の調査、売れやすい記事構造の抽出、オリジナル記事の作成、投稿用Markdownの出力、反応分析、次回改善案の生成までを自動化するPythonプロジェクトです。

重要: note公式ヘルプでは、現在noteが公式公開しているAPIはないとされています。そのため、このリポジトリは非公式API、ログインセッションの流用、Selenium等によるログイン自動操作、`/api/*` への直接アクセスを実装しません。自動生成された投稿用Markdownをnote公式画面へ貼り付ける、またはnoteプレミアム等の公式予約投稿機能で運用する前提です。

## 何を自動化するか

1. 公開URL/RSSから、売れているnote記事・公式市場分析・競合記事の傾向を収集
2. 「テーマ」「読者」「買われる理由」「無料部分で提示すべき価値」を抽出
3. 丸写しを避け、独自構成の記事Markdownを生成
4. 投稿用ファイル、投稿チェックリスト、出典メモをGitHub Actions artifactとして保存
5. 投稿後の反応CSVを読み込み、次回タイトル・導入・有料境界・CTAの改善案を生成
6. GitHub Actionsの手動実行または定期実行で編集サイクルを回す

## クイックスタート

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"

note-growth run-cycle --config config/example.yml --topic "AI副業で月1万円を現実的に作るロードマップ"
```

成果物は `outputs/` に出力されます。

## GitHub Actions

- `.github/workflows/ci.yml`: lint と test
- `.github/workflows/editorial-cycle.yml`: 記事生成サイクルを手動/定期実行し、`note-growth-outputs` artifactを保存

## 反応改善ループ

`data/sample_metrics.csv` と同じ形式で投稿結果を保存します。

```csv
published_at,title,views,likes,comments,sales,price
2026-01-10,AI副業の最初の1件,1200,80,12,14,980
```

次を実行すると、反応分析と改善案が出ます。

```bash
note-growth metrics --config config/example.yml --metrics data/sample_metrics.csv
```

## 投稿について

note.com自体への完全自動投稿は、公式公開APIがないため、この実装では行いません。代わりに以下を自動生成します。

- noteへ貼り付けるMarkdown本文
- タイトル候補
- 有料エリア境界候補
- 投稿前チェックリスト
- 反応分析レポート
- 次回の改善案

将来、noteが公式投稿APIを公開した場合は `src/note_growth/publisher.py` のPublisher Adapterに公式API adapterを追加できます。

## 主なファイル

- `src/note_growth/cli.py`: CLI入口
- `src/note_growth/collector.py`: 公開URL/RSS収集
- `src/note_growth/analyzer.py`: 傾向分析
- `src/note_growth/writer.py`: オリジナル記事生成
- `src/note_growth/publisher.py`: 投稿用artifact生成
- `src/note_growth/metrics.py`: 反応分析と改善案生成
- `docs/architecture.md`: 全体設計
- `docs/setup.md`: 初期設定と運用方法
- `docs/research-notes.md`: 調査結果メモ

## 注意

収益保証、誇大広告、無断転載、有料記事のコピー、情報商材的な煽りを避ける設計です。記事本文にも、成果を保証しない表現と読者が検証可能な行動計画を入れる方針です。
