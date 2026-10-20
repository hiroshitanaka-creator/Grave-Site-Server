# 統合ガイドの入口

旧ガイドはAPI・日記CLI・試作ワークフローを同じ稼働経路として説明していたため、
2026-10-20に以下へ整理しました。古いデプロイ例やモデル名はgit履歴で参照できます。

1. [README: インストール、API、CLI、定期処理](../README.md)
2. [Google認証・Cloud Run・GPTs Actions・Scheduler](google_cloudrun_drive_gemini.md)
3. [データ契約・移行・バックアップ・障害復旧](DATA_AND_RECOVERY.md)
4. [実施した検証と未実施の範囲](VALIDATION.md)
5. [ブランチと既存PRの整理案](REPOSITORY_CLEANUP.md)

旧日記CLIはCSV / JSONのスナップショット、新メッセージAPIは永続台帳と版別Drive保存です。
`scheduled_diary_pipeline` のInMemory / NoOp実装は参照用であり、本番配信の入口ではありません。
