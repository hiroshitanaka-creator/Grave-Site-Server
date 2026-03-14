# Grave-Site-Server 総合説明書（v0.1.0）

このドキュメントは、現在の実装（v0.1.0）に合わせて
**配信要件 → 実装構成 → 運用** を整理したものです。

## 1. 配信要件

### 1-1. 北極星
共有Googleカレンダーへ、故人のメッセージを**終日イベント**として継続配信する。

### 1-2. 全体構成
`Google Drive（記憶ソース） -> Cloud Run（処理） -> Google Calendar API（配信）`

### 1-3. 解析CLIの位置づけ
- `src/diary_cli.py`: ルールベース解析（CSV/JSON出力）
- `src/llm_batch.py`: OpenAI / Gemini 切り替え一括解析
- `src/gemini_diary_batch.py`: Gemini専用一括解析
- `src/prompt_cli.py`: プロンプトテンプレ差し込み

これらは配信本文を作るための下位機能です。

## 2. 実装構成

### 2-1. ローカルCLI
```bash
python3 src/diary_cli.py --input input.txt --format json
python3 src/diary_cli.py --input input.txt --format csv --output diary.csv
```

### 2-2. 外部連携
- Drive出力: `--export-drive`
  - 必須: `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_DRIVE_FOLDER_ID`
- Calendar配信: `--export-calendar`
  - 必須: `--calendar-id` または `GOOGLE_CALENDAR_ID`

### 2-3. LLMバッチ
```bash
export OPENAI_API_KEY="sk-..."
python3 src/llm_batch.py --provider openai --model gpt-4o-mini --input input.txt --output output/diary_llm_output.csv

export GEMINI_API_KEY="..."
python3 src/llm_batch.py --provider gemini --model gemini-1.5-flash --input input.txt --output output/diary_llm_output.csv
```

## 3. Cloud Run

### 3-1. Docker
```bash
docker build -t grave-site-batch:latest .
```

### 3-2. デプロイ
```bash
make deploy-cloudrun \
  CLOUD_RUN_REGION=asia-northeast1 \
  CLOUD_RUN_SERVICE=grave-site-batch \
  GCP_PROJECT_ID=<PROJECT_ID>
```

## 4. API連携方針
- OpenAPI定義: `openapi/gpts_actions.yaml`
- 入口: ChatGPT Custom GPTs Actions
- 実行: Cloud Run API
- 保存: Drive（Spreadsheet / Document）

## 5. 運用チェックリスト
- `input.txt` は1行1件を維持
- 日次で `mood_tag` / `topic_tag` の偏りを確認
- 失敗ログを残し再実行可能な運用にする
