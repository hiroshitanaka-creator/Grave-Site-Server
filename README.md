# Grave-Site-Server
私はサーバーの中で生き続ける

## 現在のバージョン
- **v0.1.0**（`pyproject.toml`）
- Python 3.11+ を対象

## プロジェクトの目的（北極星）
共有Googleカレンダーへ、故人のメッセージを**終日イベント**として継続配信すること。

## 現在の実装方針
- 入力窓口: ChatGPT Custom GPTs (Actions) / ローカルCLI
- 実行基盤: Cloud Run Service / Cloud Run Jobs
- 保存先: Google Drive（CSV/JSON等）
- 配信先: Google Calendar（終日イベント）

## 主要CLI

### 1) 日記解析CLI（推奨）
`src/diary_cli.py` は `input.txt`（1行1日記）を解析し、`output/` に CSV/JSON を保存します。

```bash
python3 src/diary_cli.py --input input.txt --format json
python3 src/diary_cli.py --input input.txt --format csv --output diary.csv
python3 src/diary_cli.py --input input.txt --format json --date 2026-02-06 --export-drive
python3 src/diary_cli.py --input input.txt --format json --export-calendar --calendar-id your-calendar-id@group.calendar.google.com
```

- `--export-drive` には以下環境変数が必要です。
  - `GOOGLE_SERVICE_ACCOUNT_JSON`
  - `GOOGLE_DRIVE_FOLDER_ID`
- `--export-calendar` には以下のどちらかが必要です。
  - `--calendar-id`
  - 環境変数 `GOOGLE_CALENDAR_ID`

> [!NOTE]
> `python3 src/cli.py` は後方互換のために残っていますが非推奨です。

### 2) プロンプト生成CLI
`src/prompt_cli.py` はテンプレート (`prompts/diary_tagging_v1.txt`) の `{{entry}}` を置換して最終プロンプトを出力します。

```bash
python3 src/prompt_cli.py "今日は少し疲れたけど、散歩して落ち着いた。"
python3 src/prompt_cli.py --prompt-file prompts/diary_tagging_v1.txt "今日は少し疲れたけど、散歩して落ち着いた。"
```

### 3) LLMバッチ解析CLI
```bash
export OPENAI_API_KEY="sk-..."
python3 src/llm_batch.py --provider openai --model gpt-4o-mini --input input.txt --output output/diary_llm_output.csv

export GEMINI_API_KEY="..."
python3 src/llm_batch.py --provider gemini --model gemini-1.5-flash --input input.txt --output output/diary_llm_output.csv
```

### 4) Gemini専用バッチ解析CLI
```bash
export GEMINI_API_KEY="..."
python3 src/gemini_diary_batch.py --input input.txt --output output/diary_gemini_output.csv --model gemini-2.5-flash
```

## Makefile コマンド
```bash
make setup
make run
make test
make lint
make format
```

- `make run` は `python3 src/diary_cli.py --input input.txt --format json` を呼びます。

## Docker / Cloud Run

### Dockerイメージ作成
```bash
docker build -t grave-site-batch:latest .
```

### Cloud Run デプロイ（Makefile経由）
```bash
make deploy-cloudrun \
  CLOUD_RUN_REGION=asia-northeast1 \
  CLOUD_RUN_SERVICE=grave-site-batch \
  GCP_PROJECT_ID=<PROJECT_ID>
```

## 関連ファイル
- OpenAPI: `openapi/gpts_actions.yaml`
- 詳細ガイド: `docs/total_guide_cloudrun_api_diary_gems.md`
- 配信ガイド: `docs/google_cloudrun_drive_gemini.md`
- コントリビューション: `CONTRIBUTING.md`
