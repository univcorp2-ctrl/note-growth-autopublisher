# CODEX.md

## 開発方針

このプロジェクトは、note.com向けの記事運用を安全に自動化するためのものです。

## 守ること

- noteの非公式API、Cookie、ログイン自動操作、Selenium投稿を追加しない。
- 他者の有料記事や非公開情報を収集対象にしない。
- 公開URL/RSSのみを扱う。
- 記事本文は必ず独自構成にする。
- 収益保証や誇大表現を追加しない。
- テスト、README、docs、GitHub Actionsを更新する。

## よく使うコマンド

```bash
pip install -e ".[dev]"
ruff check .
pytest
note-growth run-cycle --config config/example.yml
```
