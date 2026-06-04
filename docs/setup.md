# Setup Guide

## 1. ローカル実行

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest
```

## 2. 記事生成

```bash
note-growth run-cycle --config config/example.yml --topic "AI副業で最初の1件を作る方法"
```

出力先:

- `outputs/outbox/*.md`: noteへ貼り付ける記事本文
- `outputs/outbox/*.checklist.md`: 投稿前チェックリスト
- `outputs/research/collection.json`: 収集した公開情報
- `outputs/iteration/improvement_plan.md`: 次回改善案

## 3. GitHub Actionsで実行

1. GitHubのリポジトリ画面を開く
2. Actionsタブを開く
3. `Editorial Cycle` を選ぶ
4. `Run workflow` を押す
5. 必要に応じてtopicを入力
6. 実行完了後、artifact `note-growth-outputs` をダウンロード

## 4. noteへの投稿

note公式ヘルプ上、公式公開APIがないため、非公式APIやブラウザ自動操作による投稿は実装していません。

推奨運用:

1. artifactからMarkdownを開く
2. note公式エディタへ貼り付ける
3. `<!-- paid_boundary -->` を有料エリアの候補として調整する
4. 見出し画像、価格、ハッシュタグを設定する
5. 予約投稿したい場合はnote公式の予約投稿機能を使う

## 5. 反応分析

投稿後に、次の形式でCSVを更新します。

```csv
published_at,title,views,likes,comments,sales,price
2026-01-10,AI副業の最初の1件,1200,80,12,14,980
```

分析:

```bash
note-growth metrics --config config/example.yml --metrics data/sample_metrics.csv
```

## 6. 本番運用で必要なもの

- GitHub Actionsを使えるGitHubリポジトリ
- noteアカウント
- 有料/定期購読/予約投稿を使う場合はnote側の該当機能の有効化
- 投稿結果を記録するCSV運用

## 7. 将来拡張

- 公式APIを持つCMS adapter
- LLM provider adapter
- Google Sheets metrics importer
- タイトルA/Bテスト generator
- 画像生成ワークフローとの連携
