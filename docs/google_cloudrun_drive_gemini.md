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

> 補足: GoogleAI Proのサブスクと、Gemini APIの課金・無料枠は分かれているため、Google Cloud側の予算アラート設定が安全です。

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

1. GCPで **Billing budget** を `USD 10` に設定（50/90/100%通知）
2. Cloud Runは **Job** として最小リソースで実行
   - CPU: 1
   - Memory: 256Mi 〜 512Mi
   - 実行時間を短くする（バッチのみ）
3. Cloud Schedulerで1日1回実行
4. 予算超過前に通知し、必要ならSchedulerを自動停止（運用スクリプト化）

### 3-2. Google Driveへ毎日日記ログを記録

推奨構成:

- Cloud Run Jobで日記生成/解析
- 出力CSVをGoogle Drive APIで指定フォルダへアップロード
- ファイル名を `diary-YYYY-MM-DD.csv` にして日次管理

必要準備:

1. Drive API有効化
2. サービスアカウント作成
3. 共有ドライブ or マイドライブの対象フォルダをサービスアカウントに共有
4. Cloud Run Jobにサービスアカウントを割り当て

### 3-3. 「Geminiからpushできるか？」への回答

- Gemini自体が直接 `git push` するわけではなく、
  **Geminiを呼ぶ実行環境（Cloud Run / CI / ローカルCLI）** がpushを実行します。
- つまり「Geminiが提案→ジョブがコミット/プッシュ」は可能です。
- セキュリティ上、リポジトリへの書き込み権限は最小化し、ブランチ保護を併用してください。

### 3-4. スケジュール通知とGemini連携のズレ対策

「Scheduler通知メッセージ」と「Gemini処理結果」がずれる問題には、
**Pub/SubをハブにしてイベントIDを共通化** するのが安定です。

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
