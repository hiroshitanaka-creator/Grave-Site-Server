# Grave-Site-Server 総合説明書（Cloud Run / API接続 / 日記運用 / GPTs Actions）

このドキュメントは、Grave-Site-Serverの北極星に沿って、
**配信要件 -> 実装 -> 運用** の順で全体を整理したガイドです。

---

## 1. 配信要件

### 1-1. 北極星（最上位ゴール）

共有Googleカレンダーへ、故人のメッセージを**終日イベント**として継続配信する。

### 1-2. システム全体像

`Google Drive（記憶ソース） -> Cloud Run/Gemini（生成） -> Google Calendar API（配信）`

### 1-3. 受信体験

- メッセージは通知で消えるのではなく、**予定としてカレンダーに残る**
- 後日検索・見返しが可能
- 共有カレンダー経由で複数人が同じ配信を受け取れる

### 1-4. 解析CLIの役割（下位機能）

- `src/diary_cli.py` / `src/llm_batch.py` / `src/gemini_diary_batch.py` は、
  配信本文を作るための**生成素材づくり**を担う
- 本プロダクトの主機能は「Google Calendarへの配信」

---

## 2. 実装
- Cloud Run への載せ方
- OpenAI / Gemini API のつなぎ方
- 日記をどんな運用で書くとデータ価値が上がるか
- ChatGPT Custom GPTs Actions 連携の作り方
- さらに面白くする拡張アイデア

---

## 0. 重要な方針更新（Gemini Gems -> GPTs Actions）

Gemini Gems から Cloud Run を直接叩く想定ではなく、**ChatGPT Custom GPTs の Actions を入口にする**方針へ更新します。

- 入口: GPTs Actions（OpenAPI）
- 実行: Cloud Run Service（HTTP）
- 保存: Google Drive（Spreadsheet / Document）
- 後段: Google Calendar 終日イベント配信（将来拡張）

### 0-1. まず実装するタスク

1. `openapi/gpts_actions.yaml` を追加し、`POST /actions/save-message` を定義
2. Cloud Run API で `request_id` ベースの冪等化を実装
3. Spreadsheet 追記と Document 追記の両アダプタを実装
4. API Key 認証 + Secret Manager 運用を実装
5. 保存結果を日次ジョブで Calendar 配信へ流す

---

## 1. このリポジトリで何ができるか

### 2-1. このリポジトリの主要コンポーネント

- `src/diary_cli.py`: ローカル解析（ルールベース）→ CSV/JSON出力
- `src/llm_batch.py`: OpenAI/Gemini API を選んで一括解析→ CSV出力
- `src/gemini_diary_batch.py`: Gemini専用の一括解析→ CSV出力
- `src/prompt_cli.py`: テンプレートへ日記本文を差し込んで最終プロンプトを生成
- `src/exporters/drive_exporter.py`: Google Drive へ日次ファイルをアップロード（同名あれば更新）

### 2-2. API接続（OpenAI / Gemini）

#### OpenAI API（`src/llm_batch.py`）

- 環境変数: `OPENAI_API_KEY`
- エンドポイント: `https://api.openai.com/v1/responses`
- 形式: JSON object を要求し `mood_tag/topic_tag/summary` を抽出

```bash
export OPENAI_API_KEY="sk-..."
python3 src/llm_batch.py \
  --provider openai \
  --model gpt-4o-mini \
  --input input.txt \
  --output output/diary_llm_output.csv
```

#### Gemini API（`src/llm_batch.py` / `src/gemini_diary_batch.py`）

- 環境変数: `GEMINI_API_KEY`
- エンドポイント: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- `generationConfig.responseMimeType=application/json` を指定してJSON応答を受ける

```bash
export GEMINI_API_KEY="..."
python3 src/llm_batch.py \
  --provider gemini \
  --model gemini-1.5-flash \
  --input input.txt \
  --output output/diary_llm_output.csv
```

```bash
export GEMINI_API_KEY="..."
python3 src/gemini_diary_batch.py \
  --input input.txt \
  --output output/diary_gemini_output.csv \
  --model gemini-2.5-flash
```

### 2-3. Cloud Run 実装方針

- `Dockerfile` でコンテナ化
- `deploy/cloudrun-service.yaml` でサービス定義
- Secret Manager で `GEMINI_API_KEY` / `OPENAI_API_KEY` / Drive系鍵を注入
- 日次バッチ用途は **Cloud Run Jobs + Cloud Scheduler** を優先

### 2-4. Google Drive / Google Calendar 連携

- Drive: 生成ログや素材CSVの保存先として利用
- Calendar: 最終配信チャネルとして終日イベントを作成
- 1日の処理単位を固定し、同一日付で追跡できる命名・ID設計にする

---

## 3. 運用

### 3-1. Cloudコストと実行制御

1. Budget アラート（例: 50/90/100%）
2. Job最小リソース実行（CPU 1 / 256Mi〜512Mi）
3. `minScale: 0` を基本にアイドル課金を抑制
4. API失敗時の再実行ルール（1〜3回）を定義
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

## 6. ChatGPT Custom GPTs Actions 向けAPI設計

Custom GPTs から Cloud Run を Action 呼び出しするために、OpenAPI と保存APIの責務を固定します。

### 6-1. OpenAPI 最小テンプレ（短縮版）

```yaml
openapi: 3.1.0
info:
  title: Grave Site Actions API
  version: 1.0.0
paths:
  /actions/save-message:
    post:
      operationId: saveMessage
      requestBody:
        required: true
      responses:
        '200':
          description: Saved
```

### 6-2. GPTs Actions設計の実務ポイント

- Action request/response schema を先に固定する
- Cloud Run 側で `request_id` 冪等化を必須化する
- 認証は API Key から始め、運用でローテーションする
- 失敗時フォーマット（`{"error":"..."}`）を統一する

### 6-3. 既存CLIに接続するコツ

- `src/diary_cli.py` の出力フォーマットに合わせて保存列を定義する
- `src/exporters/drive_exporter.py` の責務分離を再利用し、Action API から保存処理を呼ぶ

---

## 7. 何か付け加えると面白くなる案

### 案A: 「感情ヒートマップ」

- 週/月単位で `mood_tag` を集計して可視化
- 変化点にコメントを自動生成

### 案B: 「リカバリ提案エンジン」

- `negative` が連続したら、過去に効いた行動（散歩/早寝など）を提案
- 提案の実行率も記録して改善

### 3-2. ログと突合（event_id）

- Scheduler実行ごとに `event_id` を発行
- 解析ログ / Driveアップロード / Calendar配信 / 通知に同一 `event_id` を付与
- 後から「どの配信がどの生成結果か」を追跡可能にする

### 3-3. 日記データの品質運用

- `input.txt` は1行1件を維持
- 「事実 / 感情 / 次の一歩」を短文で残し、生成品質を安定化
- `mood_tag` と `topic_tag` の偏りを週次レビュー

### 3-4. Gemini Gems（カスタムGemini）運用

- 出力スキーマを先に固定（CSV列互換）
- 禁止事項（余計な前置き・Markdownなど）を明示
- 失敗時フォーマット（`{"error":"..."}`）を定義

### 3-5. 30日ロードマップ

1. Day 1-3: `input.txt` 運用開始（1日1行）
2. Day 4-7: `llm_batch.py` でCSV蓄積
3. Week 2: Drive連携を有効化
4. Week 3: Cloud Run Job + Scheduler 化
5. Week 4: Google Calendar APIで終日イベント配信を定常化

---

## 4. 参考ファイル

- `README.md`
- `docs/google_cloudrun_drive_gemini.md`
- `src/llm_batch.py`
- `src/gemini_diary_batch.py`
- `src/diary_cli.py`
- `prompts/chatgpt_100char_bot_template.md`
- `prompts/diary_tagging_v1.txt`
