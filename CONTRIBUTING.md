# CONTRIBUTING

このリポジトリへのコントリビューションありがとうございます。  
現時点では「100文字日記MVP」の仕様と運用テンプレートを中心に管理しています。

## 1. 環境構築

### 必要要件
- Python 3.11 以上
- GNU Make

### セットアップ
```bash
make setup
```

## 2. 実行

現在はアプリ本体が未実装のため、`make run` は案内メッセージを表示します。

```bash
make run
```

## 3. テスト

最小チェックとして、Pythonファイルの構文チェックを実行します。

```bash
make test
```

## 4. Lint

`ruff` がインストールされている場合のみ実行されます。

```bash
make lint
```

## 5. コミット規約

以下の形式を推奨します（Conventional Commits）。

- `feat: 新機能追加`
- `fix: バグ修正`
- `docs: ドキュメント更新`
- `chore: 雑務・設定変更`
- `refactor: リファクタリング`
- `test: テスト追加/変更`

例:
```text
docs: add contribution guide and project scaffolding files
```

## 6. プルリクエスト

- 変更の目的と背景を明記する
- 実行したコマンド（`make test` など）を記載する
- 仕様変更がある場合は `README.md` を更新する
