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
