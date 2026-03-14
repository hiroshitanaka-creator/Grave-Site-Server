# Grave-Site-Server 配信ガイド（Google Drive / Cloud Run / Gemini / Google Calendar）

## 1. 配信要件（北極星）

### 1-1. 最上位ゴール

共有Googleカレンダーへ、故人メッセージを**終日イベント**として配信することを最優先要件とします。

### 1-2. システム構成（文章化）

`Google Drive（記憶ソース） -> Cloud Run/Gemini（生成） -> Google Calendar API（配信）`

### 1-3. 受信体験要件

- 通知で一瞬表示して終わるのではなく、**カレンダー予定として残る**こと
- 日付単位で後から見返せること
- 家族や関係者が共有カレンダーを通じて同じ情報を受け取れること

---

## 2. 実装

### 2-1. 生成レイヤー（Cloud Run + Gemini）

- 追加CLI: `src/gemini_diary_batch.py`
- 必須環境変数: `GEMINI_API_KEY`
- 実行例:
  ```bash
  export GEMINI_API_KEY="AIza..."
  python3 src/gemini_diary_batch.py --input input.txt --output output/diary_gemini_output.csv --model gemini-2.5-flash
  ```
# ChatGPT GPTs Actions + Cloud Run + Google Drive 保存設計

## 1. 方針転換（重要）

本プロジェクトは、Gemini Gems から Cloud Run を直接接続する案ではなく、**ChatGPT の Custom GPTs Actions から Cloud Run API を呼ぶ**構成を採用します。

- フロント: ChatGPT Custom GPTs
- 連携方式: GPTs Actions (OpenAPI)
- 実行: Cloud Run Service (HTTP)
- 保存: Google Drive API（Spreadsheet / Document）

### 2-2. 配信レイヤー（Google Calendar API）

- Cloud Run Job で生成したメッセージを Google Calendar API に渡し、終日イベントとして登録
- イベント本文にメッセージ、必要に応じてタグや生成時刻を含める
- 共有カレンダーIDを固定し、配信先を一元化

### 2-3. 解析CLIの位置づけ

- `src/diary_cli.py` と `src/llm_batch.py` は、配信メッセージを作るための**生成素材づくり（下位機能）**
- 本システムの主機能は「カレンダー配信」であり、解析CLIは前処理として利用

---

## 3. 運用

### 3-1. Cloud Runを毎月10ドル無料枠に寄せて使う
## 2. なぜこの構成が良いか

1. GPTs Actions は「会話→API実行」の導線が作りやすい
2. Cloud Run 側で認証・監査・冪等化を一元管理できる
3. 保存先を Spreadsheet / Document で使い分けできる
4. 後段で Google Calendar 配信へ接続しやすい

### 3-2. Google Driveへ毎日日記ログを記録
## 3. 実装タスク（優先順）

### Task A: Cloud Run Action API を追加

- エンドポイント: `POST /actions/save-message`
- リクエスト例:

```json
{
  "request_id": "2026-02-06-user123-001",
  "recipient": "child-a",
  "message": "ヤッホー！そっちは暑い？",
  "date": "2026-08-10",
  "tags": ["summer", "memory"],
  "source": "gpts"
}
```

- レスポンス例:

### 3-3. 「Geminiからpushできるか？」への回答
```json
{
  "saved": true,
  "storage_type": "spreadsheet",
  "record_id": "row-1024"
}
```

### Task B: Drive保存アダプタを分離実装

### 3-4. スケジュール通知とGemini連携のズレ対策
- `spreadsheet_writer.py`:
  - 1行1メッセージで append
  - 列: `created_at, recipient, date, message, tags, source, request_id`
- `document_writer.py`:
  - 日付見出しごとに本文追記
  - 追記結果の `document_revision_id` を返す

### Task C: GPTs Actions 用 OpenAPI を追加

1. Cloud Scheduler → Pub/Sub(topic: `daily-diary-trigger`)
2. Cloud Run JobがPub/Subメッセージの `event_id` を受け取って実行
3. Gemini解析結果とDriveアップロード結果に同じ `event_id` を付けてログ保存
4. 通知（Slack/Gmail/LINE等）も同じ `event_id` で送信

### 3-5. 最小実装ロードマップ

1. ローカルで `src/gemini_diary_batch.py` を利用開始
2. Cloud Run Job化（Docker化 + env `GEMINI_API_KEY`）
3. Cloud Scheduler日次実行
4. Drive APIアップロード追加
5. Google Calendar API で終日イベント配信を本線化
6. Pub/Sub `event_id` 連携で通知と結果を一致
- 新規: `openapi/gpts_actions.yaml`
- 必須定義:
  - `POST /actions/save-message`
  - request/response schema
  - 認証ヘッダ（API Key）

### Task D: 認証と運用保護

- 最小: `X-API-Key` 固定キー
- 推奨: Secret Manager + ローテーション
- 監査ログ: `request_id`, `status`, `latency_ms`, `drive_target`

### Task E: 失敗耐性

- 冪等化キー: `request_id`
- Drive API 失敗時:
  - 429/5xx は指数バックオフ
  - 最終失敗は dead-letter（再処理キュー）へ

## 4. Cloud Run デプロイ要点

- Cloud Run は Service（HTTP）として運用
- 環境変数例:
  - `GOOGLE_SERVICE_ACCOUNT_JSON`
  - `GOOGLE_DRIVE_FOLDER_ID`
  - `GOOGLE_SPREADSHEET_ID`
  - `GOOGLE_DOCUMENT_ID`
  - `GPTS_ACTION_API_KEY`
- 予算アラート:
  - 50 / 90 / 100%

## 5. 次フェーズ（配信）

保存済みメッセージを日次で読み出し、Google Calendar の終日イベントへ配信する Job を追加する。

- 入力: Spreadsheet / Document
- 出力: 共有カレンダーへの `events.insert`
- 冪等化: `recipient + date + message_hash`
