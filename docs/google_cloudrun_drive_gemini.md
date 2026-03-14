# GoogleAI Pro + Gemini運用 / Cloud Run / Google Drive日記ログ設計

## 1. Gemini運用（このリポジトリ）

- 追加CLI: `src/gemini_diary_batch.py`
- 必須環境変数: `GEMINI_API_KEY`
- 例:
  ```bash
  export GEMINI_API_KEY="AIza..."
  python3 src/gemini_diary_batch.py --input input.txt --output output/diary_gemini_output.csv --model gemini-2.5-flash
  ```

> 補足: GoogleAI Proのサブスクと、Gemini APIの課金・無料枠は分かれているため、Google Cloud側の予算アラート設定が安全です。

## 2. Cloud Runを毎月10ドル無料枠に寄せて使う

1. GCPで **Billing budget** を `USD 10` に設定（50/90/100%通知）
2. Cloud Runは **Job** として最小リソースで実行
   - CPU: 1
   - Memory: 256Mi 〜 512Mi
   - 実行時間を短くする（バッチのみ）
3. Cloud Schedulerで1日1回実行
4. 予算超過前に通知し、必要ならSchedulerを自動停止（運用スクリプト化）

## 3. Google Driveへ毎日日記ログを記録

推奨構成:

- Cloud Run Jobで日記生成/解析
- 出力CSVをGoogle Drive APIで指定フォルダへアップロード
- ファイル名を `diary-YYYY-MM-DD.csv` にして日次管理

必要準備:

1. Drive API有効化
2. サービスアカウント作成
3. 共有ドライブ or マイドライブの対象フォルダをサービスアカウントに共有
4. Cloud Run Jobにサービスアカウントを割り当て

## 4. 「Geminiからpushできるか？」への回答

- Gemini自体が直接 `git push` するわけではなく、
  **Geminiを呼ぶ実行環境（Cloud Run / CI / ローカルCLI）** がpushを実行します。
- つまり「Geminiが提案→ジョブがコミット/プッシュ」は可能です。
- セキュリティ上、リポジトリへの書き込み権限は最小化し、ブランチ保護を併用してください。

## 5. スケジュール通知とGemini連携のズレ対策

「Scheduler通知メッセージ」と「Gemini処理結果」がずれる問題には、
**Pub/SubをハブにしてイベントIDを共通化** するのが安定です。

### パターン

1. Cloud Scheduler → Pub/Sub(topic: `daily-diary-trigger`)
2. Cloud Run JobがPub/Subメッセージの `event_id` を受け取って実行
3. Gemini解析結果とDriveアップロード結果に同じ `event_id` を付けてログ保存
4. 通知（Slack/Gmail/LINE等）も同じ `event_id` で送信

こうすると、通知と解析結果を後から確実に突合できます。

## 6. 最小実装ロードマップ

1. ローカルで `src/gemini_diary_batch.py` を利用開始
2. Cloud Run Job化（Docker化 + env `GEMINI_API_KEY`）
3. Cloud Scheduler日次実行
4. Drive APIアップロード追加
5. Pub/Sub `event_id` 連携で通知と結果を一致
