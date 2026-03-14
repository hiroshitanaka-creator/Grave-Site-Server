# Grave-Site-Server
私はサーバーの中で生き続ける

## 現在のバージョン
- **v0.1.0**（`pyproject.toml`）
- Python 3.11+ を対象

## プロジェクトの目的（北極星）
共有Googleカレンダーへ、故人のメッセージを**終日イベント**として継続配信すること。

## 開発進捗

| フェーズ | 内容 | 状態 |
|---|---|---|
| Phase 1 | 基盤整備（CLI / 入出力の安定化） | ✅ 完了 |
| Phase 2 | 外部連携の信頼性向上（Drive / Calendar / LLM） | ✅ 完了 |
| Phase 3 | 運用自動化（Cloud Run / Workflow / GitOps） | ✅ 完了 |
| Phase 4 | 品質向上と拡張（Embedding / OpenAPI / Docs） | ✅ 完了 |

詳細は [RoadMap.md](./RoadMap.md) を参照してください。

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
  - 環境変数 `GOOGLE_CALENDAR_ID`（`--calendar-id` が優先）

> [!NOTE]
> `python3 src/cli.py` は後方互換のために残っていますが非推奨です。

出力スキーマ（CSV/JSON共通）は次で固定です。

- キー順/列順: `date`, `entry`, `mood_tag`, `topic_tag`, `summary`
- `date`: `YYYY-MM-DD` のみを有効値として扱い、それ以外は空文字
- 欠損値: 空文字で補完
- 余分なキー: 出力時に無視

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

- LLMが返した壊れた行は隔離（quarantine）し、全体処理は継続します。

### 4) Gemini専用バッチ解析CLI
```bash
export GEMINI_API_KEY="..."
python3 src/gemini_diary_batch.py --input input.txt --output output/diary_gemini_output.csv --model gemini-2.5-flash
```

### 5) EmbeddingパイプラインCLI
```bash
python3 src/embedding/cli.py --input output/diary_llm_output.csv --output output/vectors.json
```

- ベクトル次元・保存形式・再生成手順は `src/embedding/` 配下で固定。

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

## 運用

### 定期実行ワークフロー
`src/workflows/scheduled_diary_pipeline.py` が Cloud Run Jobs から呼び出され、再実行安全性（冪等性）を確保しています。

### GitOps方針
- `src/gitops/` に変更承認・ロールバック・監査ログの最小ルールを実装。
- PRタイトルには `P{phase}-T{task}` 形式のタスクIDを含めてください（例: `feat(P2-T2): add retry policy`）。

### 環境変数一覧

| 変数名 | 用途 | 必須 |
|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Drive/Calendar認証 | Drive・Calendar利用時 |
| `GOOGLE_DRIVE_FOLDER_ID` | Drive保存先フォルダ | `--export-drive` 時 |
| `GOOGLE_CALENDAR_ID` | カレンダーID（デフォルト） | `--export-calendar` 時 |
| `OPENAI_API_KEY` | OpenAI LLM利用時 | LLMバッチ利用時 |
| `GEMINI_API_KEY` | Gemini LLM利用時 | Geminiバッチ利用時 |

## 関連ファイル
- OpenAPI: `openapi/gpts_actions.yaml`
- ロードマップ: `RoadMap.md`
- 詳細ガイド: `docs/total_guide_cloudrun_api_diary_gems.md`
- 配信ガイド: `docs/google_cloudrun_drive_gemini.md`
- コントリビューション: `CONTRIBUTING.md`
