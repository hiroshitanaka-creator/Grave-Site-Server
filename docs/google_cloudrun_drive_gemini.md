# 配信ガイド（Google Drive / Cloud Run / Gemini / Google Calendar）v0.1.0

## 1. 目的
共有Googleカレンダーに、日次メッセージを終日イベントとして残す。

## 2. 現在の推奨フロー
1. `input.txt`（1行1日記）を用意
2. `src/diary_cli.py` または `src/llm_batch.py` で生成
3. 必要に応じて Drive へ保存
4. Calendar へ終日イベント配信

## 3. 実行コマンド

### 3-1. diary_cli
```bash
python3 src/diary_cli.py --input input.txt --format json
python3 src/diary_cli.py --input input.txt --format json --export-drive
python3 src/diary_cli.py --input input.txt --format json --export-calendar --calendar-id your-calendar-id@group.calendar.google.com
```

### 3-2. llm_batch
```bash
export GEMINI_API_KEY="..."
python3 src/llm_batch.py --provider gemini --model gemini-1.5-flash --input input.txt --output output/diary_llm_output.csv
```

### 3-3. gemini_diary_batch
```bash
export GEMINI_API_KEY="..."
python3 src/gemini_diary_batch.py --input input.txt --output output/diary_gemini_output.csv --model gemini-2.5-flash
```

## 4. 必須環境変数
- Gemini利用: `GEMINI_API_KEY`
- OpenAI利用: `OPENAI_API_KEY`
- Drive利用: `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_DRIVE_FOLDER_ID`
- Calendar利用: `GOOGLE_CALENDAR_ID`（または `--calendar-id`）

## 5. Cloud Run デプロイ
```bash
make deploy-cloudrun \
  CLOUD_RUN_REGION=asia-northeast1 \
  CLOUD_RUN_SERVICE=grave-site-batch \
  GCP_PROJECT_ID=<PROJECT_ID>
```

## 6. 補足
- `src/cli.py` は後方互換のため残存（非推奨）
- GPTs Actions 連携は `openapi/gpts_actions.yaml` を参照
