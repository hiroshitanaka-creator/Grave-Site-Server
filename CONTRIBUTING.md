# CONTRIBUTING

このリポジトリへのコントリビューションありがとうございます。  
現在の基準バージョンは **v0.1.0**（`pyproject.toml`）です。

## 1. 環境構築

### 必要要件
- Python 3.11 以上
- GNU Make

### セットアップ
```bash
make setup
```

## 2. 実行

`make run` は `input.txt` を読み込み、`output/diary_YYYY-MM-DD.json` を生成します。

```bash
make run
```

個別実行時は以下を基準にしてください（`src/diary_cli.py` を推奨）。

```bash
python3 src/diary_cli.py --input input.txt --format json
python3 src/diary_cli.py --input input.txt --format csv --output diary.csv
python3 -m src.embedding.cli index --input output/diary_output.json --output output/embeddings.db
```

## 3. テスト

```bash
make test
pytest -q
```

### テストレイヤー運用ルール（P4-T1）

本リポジトリでは、変更の影響範囲に応じて以下のレイヤーでテストを選択します。

- **単体テスト（unit）**
  - 対象: 単一モジュール・関数のロジック
  - 例: `tests/test_diary_processor.py`, `tests/gitops/test_gitops_service.py`
- **CLI / 統合テスト（integration）**
  - 対象: 引数解釈、入出力、複数モジュール連携
  - 例: `tests/test_cli.py`, `tests/test_diary_cli.py`, `tests/embedding/test_embedding_cli.py`
- **ワークフローテスト（workflow）**
  - 対象: 定期実行やパイプラインの再実行安全性
  - 例: `tests/workflows/test_scheduled_diary_pipeline.py`
- **Goldenテスト（golden）**
  - 対象: 既知入力に対する出力の回帰検知
  - 例: `tests/golden/`, `tests/embedding/golden/`

#### 変更時の期待アクション

- ロジック変更時は、最低1つの単体テストを追加/更新する。
- CLI仕様（引数・出力フォーマット・エラーメッセージ）を変更した場合は、CLI/統合テストを更新する。
- 出力仕様を変更した場合は、対応するgoldenファイルを更新し、PR本文に「意図した差分」であることを明記する。
- ワークフロー変更時は `tests/workflows/` の該当テストを必ず実行する。

## 4. Lint / Format

`ruff` がインストールされている場合に利用できます。

```bash
make lint
make format
```

## 5. コミット規約

Conventional Commits を推奨します。

- `feat: 新機能追加`
- `fix: バグ修正`
- `docs: ドキュメント更新`
- `chore: 雑務・設定変更`
- `refactor: リファクタリング`
- `test: テスト追加/変更`

例:
```text
docs: update docs for v0.1.0 cli workflow
```

## 6. Issue / Pull Request

- 仕様変更がある場合は `README.md` / `docs/` / issue template を合わせて更新する
- PR には目的・背景・実行コマンドを記載する
- バグ報告時は再現手順と実行環境（Pythonバージョン、実行コマンド）を明記する
