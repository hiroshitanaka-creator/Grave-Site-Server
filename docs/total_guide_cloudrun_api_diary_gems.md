# Grave-Site-Server 総合説明書（Cloud Run / API接続 / 日記運用 / Gemini Gems）

このドキュメントは、以下を1つにまとめた実運用向けガイドです。

- Cloud Run への載せ方
- OpenAI / Gemini API のつなぎ方
- 日記をどんな運用で書くとデータ価値が上がるか
- Gemini Gems（カスタムGemini）用プロンプトの作り方
- さらに面白くする拡張アイデア

---

## 1. このリポジトリで何ができるか

主な用途は「短い日記を定期的に構造化して蓄積すること」です。

- `src/diary_cli.py`: ローカル解析（ルールベース）→ CSV/JSON出力
- `src/llm_batch.py`: OpenAI/Gemini API を選んで一括解析→ CSV出力
- `src/gemini_diary_batch.py`: Gemini専用の一括解析→ CSV出力
- `src/prompt_cli.py`: `prompts/diary_tagging_v1.txt` の `{{entry}}` に日記本文を差し込んで最終プロンプトを生成
- `src/exporters/drive_exporter.py`: Google Drive へ日次ファイルをアップロード（同名あれば更新）

推奨の最小フロー:
1. `input.txt` に1行1日記で追記
2. `llm_batch.py` or `gemini_diary_batch.py` でタグ付け
3. `output/*.csv` を保存（必要なら Drive へ）

---

## 2. API接続の全体像（OpenAI / Gemini）

### 2-1. OpenAI API（`src/llm_batch.py`）

- 環境変数: `OPENAI_API_KEY`
- エンドポイント: `https://api.openai.com/v1/responses`
- 形式: JSON object を要求して `mood_tag/topic_tag/summary` を取り出す

実行例:

```bash
export OPENAI_API_KEY="sk-..."
python3 src/llm_batch.py \
  --provider openai \
  --model gpt-4o-mini \
  --input input.txt \
  --output output/diary_llm_output.csv
```

### 2-2. Gemini API（`src/llm_batch.py` または `src/gemini_diary_batch.py`）

- 環境変数: `GEMINI_API_KEY`
- エンドポイント: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- `generationConfig.responseMimeType=application/json` を指定してJSON応答を受ける

実行例（共通CLI）:

```bash
export GEMINI_API_KEY="..."
python3 src/llm_batch.py \
  --provider gemini \
  --model gemini-1.5-flash \
  --input input.txt \
  --output output/diary_llm_output.csv
```

実行例（Gemini専用CLI）:

```bash
export GEMINI_API_KEY="..."
python3 src/gemini_diary_batch.py \
  --input input.txt \
  --output output/diary_gemini_output.csv \
  --model gemini-2.5-flash
```

### 2-3. つまずきやすいポイント

- APIキー未設定: 各CLIは明示エラーで終了
- モデル名ミス: 404/400系エラーになりやすい
- JSON崩れ: 応答が厳密JSONでないとパース失敗（再試行制御の追加余地あり）
- 文字数・行数増加: APIコストが増えるため、1日あたり上限件数を決めると安全

---

## 3. Cloud Run への載せ方（実務向け）

### 3-1. 最小構成

- `Dockerfile` でコンテナ化
- `deploy/cloudrun-service.yaml` でサービス定義
- Secret Manager で `GEMINI_API_KEY` / `OPENAI_API_KEY` / Drive系鍵を注入

`deploy/cloudrun-service.yaml` の基本方針:

- `timeoutSeconds: 300`
- `containerConcurrency: 1`（バッチ処理向け）
- `minScale: 0`, `maxScale: 2`（コストを抑えやすい）

### 3-2. どの実行形態を選ぶべきか

- 毎日定時で十分: **Cloud Run Jobs + Cloud Scheduler**
- APIとして都度叩く: **Cloud Run Service（HTTP）**

日記のバッチ運用なら Jobs が管理しやすいです。

### 3-3. 運用で最低限入れるべきもの

1. Budget アラート（例: 50/90/100%）
2. 実行ログに `date`, `input_count`, `success_count`, `error_count` を出す
3. API失敗時の再実行ルール（1〜3回）
4. 出力保存先を `output/` + Drive で二重化

---

## 4. Google Drive 連携

`src/diary_cli.py --export-drive` でローカル出力後にDriveへアップロードできます。

必要な環境変数:

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_DRIVE_FOLDER_ID`

セットアップ:

1. Google Drive API を有効化
2. サービスアカウントを作成しJSONキー取得
3. 対象フォルダをサービスアカウントに共有（編集者）
4. フォルダIDを設定

同名ファイルがある場合は更新されるため、日次の固定ファイル名運用（`diary_YYYY-MM-DD.csv`）と相性が良いです。

---

## 5. 日記の書き方ガイド（データ価値を上げる）

### 5-1. 1エントリの推奨テンプレ

「事実 / 感情 / 次の一歩」を1〜2文で書くと、タグ精度が上がります。

例:

- 事実: 今日やったこと
- 感情: その時の気分
- 次の一歩: 明日やる小さな行動

### 5-2. 1日1行の型（`input.txt` 想定）

- 1行目: 今日の要点（最大100〜140文字）
- 改行して次の日記（1行1件）

解析しやすいコツ:

- 固有名詞を適度に残す（会議名/場所など）
- 感情語を1つ入れる（焦り、安堵、達成感など）
- 抽象語だけで終えない（「頑張った」だけで終えない）

### 5-3. 週次で見返す観点

- `mood_tag` の偏り（negativeが連続していないか）
- `topic_tag` の偏り（仕事だけに寄っていないか）
- `summary` から行動パターンを抽出

---

## 6. Gemini Gems（カスタムGemini）向けプロンプト設計

`prompts/chatgpt_100char_bot_template.md` をベースに、Gemini Gems向けには次の調整が有効です。

### 6-1. システム指示テンプレ（短縮版）

```text
あなたは「100文字日記コーチ」です。
ユーザーの入力を解析し、必ず次のキーでJSONを返してください:
- date (YYYY-MM-DD)
- mood_tag (1〜2語)
- topic_tag (カンマ区切り)
- summary (日本語30文字以内)
- advice (日本語40文字以内)

制約:
- 入力が100文字超なら先頭100文字を解析対象にする
- 不確実な内容を断定しない
- 医療/法律/投資は一般的助言に留める
- JSON以外の文を出力しない
```

### 6-2. Gems設計の実務ポイント

- 出力スキーマを先に固定（CSV列に合わせる）
- 禁止事項を明示（余計な前置き禁止、Markdown禁止など）
- 文字数上限をキーごとに指定
- 失敗時フォーマット（`{"error":"..."}`）を決める

### 6-3. 既存CLIに接続するコツ

- `mood_tag/topic_tag/summary` 互換を優先
- `advice` や `emotion_tags` など拡張列は別CSVに出すか、後段でマージ

---

## 7. 何か付け加えると面白くなる案

### 案A: 「感情ヒートマップ」

- 週/月単位で `mood_tag` を集計して可視化
- 変化点にコメントを自動生成

### 案B: 「リカバリ提案エンジン」

- `negative` が連続したら、過去に効いた行動（散歩/早寝など）を提案
- 提案の実行率も記録して改善

### 案C: 「イベントID連携」

- Scheduler実行ごとに `event_id` を発行
- 解析ログ/Driveアップロード/通知すべてに付与
- 後から「この通知はどの実行か」を追跡可能

### 案D: 「埋め込み検索」

- `src/embedding/` の仕組みを使って過去日記をベクトル化
- 「似た気分だった日」を検索して、再現性のある行動を抽出

### 案E: 「週報自動生成」

- 1週間分の `summary` から、
  - よかったこと3件
  - しんどかったこと3件
  - 来週の重点1件
  を自動作成

---

## 8. 30日ロードマップ（最短で価値を出す）

1. Day 1-3: `input.txt` 運用開始（1日1行）
2. Day 4-7: `llm_batch.py` でCSV蓄積
3. Week 2: Drive連携を有効化
4. Week 3: Cloud Run Job + Scheduler 化
5. Week 4: 感情ヒートマップ or 週報自動生成を追加

---

## 9. 参考ファイル

- `README.md`
- `docs/google_cloudrun_drive_gemini.md`
- `src/llm_batch.py`
- `src/gemini_diary_batch.py`
- `src/diary_cli.py`
- `prompts/chatgpt_100char_bot_template.md`
- `prompts/diary_tagging_v1.txt`

