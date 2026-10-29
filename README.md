# note-growth-autopublisher

note.com向けに、公開情報の調査、売れやすい記事構造の抽出、オリジナル記事の作成、投稿用Markdownの出力、反応分析、次回改善案の生成までを自動化するPythonプロジェクトです。

重要（2026-10-29更新）: noteは2026-10-08に法人向けnote proの公式「note API」を開始しました。ただしnote pro契約企業と対応サービス、または所定のソリューションパートナーが対象で、一般アカウントで誰でも使える公開投稿APIではありません。公式一次情報: https://note.jp/n/n6e16e4dc9e26 ／ https://www.help-note.com/hc/ja/articles/46643492548121-noteが公式で公開しているAPIはありますか 。このリポジトリは現時点で非公式API、ログインCookie流用、Selenium等によるログイン自動操作を実装せず、通常アカウント用の原稿生成と公式UIでの手動公開を維持します。note pro条件を満たす場合だけ公式対応サービス経由で下書き連携を別途検証します。

## 自動化する内容

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

将来、noteが公式投稿APIを公開した場合は `src/note_growth/core.py` のPublisher Adapterに公式API adapterを追加できます。
