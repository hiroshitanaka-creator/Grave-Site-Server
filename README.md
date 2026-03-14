# -Grave-Site-Server
私はサーバーの中で生き続ける

## Grave-Site-Serverの目的（北極星）

**最上位ゴール**: 共有Googleカレンダーへ、故人のメッセージを**終日イベント**として配信し続けること。

### システム構成（文章化）

`Google Drive（記憶ソース） -> Cloud Run/Gemini（生成） -> Google Calendar API（配信）`

### 受信体験

本プロジェクトの配信は、一般的な通知メッセージとは異なり、**カレンダー予定として残る**ことを重視します。
通知が流れて消えるのではなく、受信者の予定表に「その日のメッセージ」が残り、あとから見返せる体験を提供します。

### 解析CLIの位置づけ（下位機能）

`src/diary_cli.py` と `src/llm_batch.py` は、配信そのものではなく、
**配信メッセージの生成素材（タグ・要約・構造化テキスト）を作るための下位機能**として扱います。

詳細なプロンプト定義・変更履歴は `prompts/` 配下を参照してください。

- プロンプト本体: `prompts/diary_tagging_v1.txt`
- 変更履歴: `prompts/CHANGELOG.md`
- MyGPT用テンプレ: `prompts/chatgpt_100char_bot_template.md`


## GitOps運用ポリシー（Gemini提案 / GitOps実行）

本リポジトリでは、LLM（Gemini含む）は**変更提案データのみ**を生成し、実際の `push` / PR作成はサービスアカウント権限を持つバックエンドの GitOps サービスが実行します。

- LLMの責務: 変更対象ファイル・コミットメッセージ・PR情報の提案
- GitOpsサービスの責務: ブランチ作成、コミット/Push、PR作成、監査ログ出力
- 実装: `src/gitops/service.py`（検証＋監査）と `src/gitops/backends.py`（`git`/`gh` 実行）
- 保護ルール:
  - 対象ディレクトリ制限（例: `src/`, `README.md`）
  - コミットメッセージ規約（Conventional Commits）
  - 必須レビュー（最低1 reviewer）

この責務分離により、LLMに直接書き込み権限を付与せず、統制された変更運用を行います。

## CLI（用途別）

### 1) プロンプト生成CLI

`src/prompt_cli.py` は `--prompt-file` で指定したテンプレートを読み込み、`{{entry}}` を日記本文に置換して最終プロンプトを出力します。

```bash
python3 src/prompt_cli.py "今日は少し疲れたけど、散歩して落ち着いた。"
python3 src/prompt_cli.py --prompt-file prompts/diary_tagging_v1.txt "今日は少し疲れたけど、散歩して落ち着いた。"
```

標準入力にも対応しています。

```bash
echo "今日は少し疲れたけど、散歩して落ち着いた。" | python3 src/prompt_cli.py --prompt-file prompts/diary_tagging_v1.txt
```

> [!NOTE]
> 旧コマンド `python3 cli.py ...` は後方互換のため利用可能ですが、**非推奨**です。

### 2) 日記解析CLI（生成素材づくりの下位機能）

`src/diary_cli.py` は `input.txt`（1行1日記）を読み取り、`src/diary_processor.py` の解析ロジックでタグ生成・要約生成を行って `output/` へ保存します。

```bash
python3 src/diary_cli.py --input input.txt --format json
python3 src/diary_cli.py --input input.txt --format csv --output diary.csv
python3 src/diary_cli.py --input input.txt --format json --date 2026-02-06 --export-drive
```

- `input.txt` は1行1日記の形式で用意してください。
- 生成ファイルは `output/` に保存され、未指定時の命名規則は `diary_YYYY-MM-DD.<format>` です。
- `--export-drive` 指定時はローカル保存後にGoogle Driveへ送信します。
- Drive上に同名（例: `diary_2026-02-06.csv`）がある場合は、同一ファイルIDに対して**上書き更新**します。

#### Google Drive エクスポート初期セットアップ

1. Google Cloud Console でプロジェクトを作成し、**Google Drive API** を有効化する。
2. サービスアカウントを作成し、JSONキーをダウンロードする。
3. アップロード先のDriveフォルダを作成し、サービスアカウントのメールアドレスへ編集権限で共有する。
4. フォルダURLからフォルダIDを取得する（`https://drive.google.com/drive/folders/<FOLDER_ID>`）。
5. 以下の環境変数を設定する。

```bash
export GOOGLE_SERVICE_ACCOUNT_JSON="/path/to/service-account.json"
export GOOGLE_DRIVE_FOLDER_ID="xxxxxxxxxxxxxxxxx"
```

未設定時は `src/diary_cli.py --export-drive` 実行時に明示的なエラーを表示して終了します。

> [!NOTE]
> 旧コマンド `python3 src/cli.py ...` は後方互換のため利用可能ですが、**非推奨**です。


### 3) LLMバッチ解析CLI（生成素材づくりの下位機能）

`src/llm_batch.py` は `--provider` で LLM プロバイダを切り替え、1行1日記を順番に解析してCSVを出力します。

```bash
export OPENAI_API_KEY="sk-..."
python3 src/llm_batch.py --provider openai --model gpt-4o-mini --input input.txt --output output/diary_llm_output.csv

export GEMINI_API_KEY="..."
python3 src/llm_batch.py --provider gemini --model gemini-1.5-flash --input input.txt --output output/diary_llm_output.csv
```

- 入力は1行1日記です。
- `--date` で `date` 列の固定値を指定できます。
- OpenAI 利用時は `OPENAI_API_KEY`、Gemini 利用時は `GEMINI_API_KEY` が必要です。



### 4) Geminiバッチ解析CLI（複数日記 → CSV）

`src/gemini_diary_batch.py` は `GEMINI_API_KEY` を使って1行1日記を順番にGeminiへ送り、CSVを出力します。

```bash
export GEMINI_API_KEY="AIza..."
python3 src/gemini_diary_batch.py --input input.txt --output output/diary_gemini_output.csv --model gemini-2.5-flash
```

- 入力は1行1日記です。
- `--date` で `date` 列の固定値を指定できます。
- Gemini API未設定時はエラーで終了します。
- GoogleAI Pro加入者でも API キー課金は別管理なので、Google Cloud Billing 側で上限設定を推奨します。

### 自動記録 → データ保存の流れ

1. 手元で日記を書く（Notepad / Obsidian / VS Code など）
2. バッチでGPTに投げる or 日記Bot化する
3. 出力をCSV or JSONに変換
4. 保存先を選ぶ

- Google Sheet（クラウド）
- Local CSV（RAG用に埋め込み化も可能）
- Firestore / Supabase（構造化DB）
- Notionページ（感情日記として回覧可）

### 将来拡張のアイデア

- summaryだけ抽出してvector embedding化
- RAGで「去年の今日の気持ち」を呼び出し
- 記憶ありAIとの連携で自己対話補助

### すぐ渡せるもの（実在ファイルベース）

- [x] GPT用プロンプトテンプレ
- [x] CSV / Excel用ヘッダー付きフォーマット
- [x] Pythonスクリプト：複数日記 → OpenAI API → CSV出力
- [x] RAG用Embeddingsスクリプト：日記 → ベクトル → 検索可能DB
- [x] ChatGPT / MyGPTで「今日の100文字」記入Bot化テンプレ（`prompts/chatgpt_100char_bot_template.md`）


## Docker / Cloud Run（CLIバッチ最小構成）

### Dockerイメージ作成

`Dockerfile` は CLIバッチ（`src/openai_diary_batch.py`）を実行するための最小構成です。

```bash
docker build -t grave-site-batch:latest .
```

実行例：

```bash
docker run --rm \
  -e OPENAI_API_KEY="sk-..." \
  -v "$PWD/input.txt:/app/input.txt:ro" \
  grave-site-batch:latest \
  --input /app/input.txt --output /app/output.csv --model gpt-4o-mini
```

### Cloud Run サービスデプロイ

`deploy/cloudrun-service.yaml` には無料枠寄りの設定（`minInstances: 0`、小さめの `maxInstances`、`timeoutSeconds`、`cpu/memory`）を明示しています。

```bash
gcloud run services replace deploy/cloudrun-service.yaml --region asia-northeast1 --project <PROJECT_ID>
```

`Makefile` の `deploy-cloudrun` でも、必須引数（リージョン、サービス名、プロジェクト）を変数化してデプロイできます。

```bash
make deploy-cloudrun \
  CLOUD_RUN_REGION=asia-northeast1 \
  CLOUD_RUN_SERVICE=grave-site-batch \
  GCP_PROJECT_ID=<PROJECT_ID>
```

### 日次ジョブ用途（Cloud Run Jobs）

毎日1回などのバッチ実行が目的なら、Cloud Run Jobs のほうが適しています。

```bash
gcloud run jobs create grave-site-daily \
  --image asia-northeast1-docker.pkg.dev/<PROJECT_ID>/grave-site/grave-site-batch:latest \
  --region asia-northeast1 \
  --project <PROJECT_ID> \
  --tasks 1 \
  --max-retries 1 \
  --task-timeout 10m \
  --cpu 1 \
  --memory 512Mi \
  --set-env-vars OPENAI_API_KEY=sk-... \
  --args=--input,/app/input.txt,--output,/app/output.csv,--model,gpt-4o-mini

# 手動実行
gcloud run jobs execute grave-site-daily --region asia-northeast1 --project <PROJECT_ID>
```

### 無料枠運用の注意

- **リージョン選択**: 料金と無料枠の対象はリージョンで異なるため、利用前に対象リージョンを確認してください。
- **アイドル時0**: 常時起動コストを避けるため `minInstances=0` を維持します。
- **ログ保持期間**: Cloud Logging の保持期間・課金条件を確認し、不要ログはフィルタや除外で削減してください。
- **予算アラート設定**: Cloud Billing で予算とアラート通知を必ず設定し、想定外の従量課金を早期検知します。

## 総合説明書

Cloud Run / API接続 / 日記運用 / Gemini Gems までをまとめたガイドは以下を参照してください。

- `docs/total_guide_cloudrun_api_diary_gems.md`
