# ChatGPT GPTs Actions + Cloud Run + Google Drive 保存設計

## 1. 方針転換（重要）

本プロジェクトは、Gemini Gems から Cloud Run を直接接続する案ではなく、**ChatGPT の Custom GPTs Actions から Cloud Run API を呼ぶ**構成を採用します。

- フロント: ChatGPT Custom GPTs
- 連携方式: GPTs Actions (OpenAPI)
- 実行: Cloud Run Service (HTTP)
- 保存: Google Drive API（Spreadsheet / Document）

## 2. なぜこの構成が良いか

1. GPTs Actions は「会話→API実行」の導線が作りやすい
2. Cloud Run 側で認証・監査・冪等化を一元管理できる
3. 保存先を Spreadsheet / Document で使い分けできる
4. 後段で Google Calendar 配信へ接続しやすい

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

```json
{
  "saved": true,
  "storage_type": "spreadsheet",
  "record_id": "row-1024"
}
```

### Task B: Drive保存アダプタを分離実装

- `spreadsheet_writer.py`:
  - 1行1メッセージで append
  - 列: `created_at, recipient, date, message, tags, source, request_id`
- `document_writer.py`:
  - 日付見出しごとに本文追記
  - 追記結果の `document_revision_id` を返す

### Task C: GPTs Actions 用 OpenAPI を追加

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
