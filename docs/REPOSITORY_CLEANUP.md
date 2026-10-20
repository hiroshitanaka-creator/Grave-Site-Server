# ブランチ・既存PRの整理候補

調査日: 2026-10-20。基準main: `ca688ac4c97ee080d800fd0097a6c773c44b9a82`。
最終mainコミットは2026-03-15、管理ファイル75、リモートブランチ57（HEAD別名を除く）、
mainへ取り込み済みの作業ブランチ54を再確認しました。作業開始時の既存未完了PRは#2 / #8です。
今回の作業ブランチを追加した後の総数はこの基準から増えます。
適用されるAGENTS.mdはリポジトリと親ディレクトリにありませんでした。

未反映変更のない元チェックアウトから隔離worktreeを作り、既存ブランチは書き換えていません。
作業ブランチは `codex/restore-message-delivery-20261020` です。
既存PRのクローズ・リモートブランチ削除・mainへのマージは行っていません。

## 未統合PR

| PR | 確認した差分 | 提案・判断材料 |
|---|---|---|
| [#8](https://github.com/hiroshitanaka-creator/Grave-Site-Server/pull/8) | head `54ef815a9b02c3f99b32359207d4f5ceb1a4cd71`。Embeddingディレクトリのmainとの差はCLIの正の整数検証で、main側に追加されている。関連機能は別ブランチで取り込み済み | mainと同じ機能の再統合は不要。所有者が確認後、重複としてクローズする候補。未統合という理由だけで現在の機能へ戻さない |
| [#2](https://github.com/hiroshitanaka-creator/Grave-Site-Server/pull/2) | head `8d318adf76bbdb91aa13ed8991d22a9e7a7f3c32`。Memory Vaultのスキーマ、抽出/注入プロンプト、CSVヘッダ等が固有資産 | 実行機能としての統合は保留し、設計資料として保持する案。自動マージも削除もしない |

#2は `id=date` を前提とするため、同日複数記録へそのまま採用できません。
`mood.primary/secondary`（joy等18種）、valence/arousal/intensity、topics、people、places、actions、
signals、privacy、embedding_textを持ち、現行の日記mood_tag / topic_tagとは別契約です。
要約30文字制限は共通ですが、変換仕様・識別子・原文保持・privacyの配信制御が必要です。
注入プロンプトの「Memoryを事実として扱う」という前提も、出典・訂正・生成誤りの扱いを決めてから見直します。
新APIのmemory_refsを付けただけでは、このMemory Vaultや検索・生成へ接続したことにはなりません。
採用するなら独立したPRでスキーマ変換、識別子衝突、権限、出典と生成結果の評価を行います。
参考資料化なら独立した文書ディレクトリへ保存し、未実装表示を付けてから旧PRの扱いを決めます。

## 取り込み済みブランチ54本

下表はtipが基準mainの祖先であることをgitで確認した削除候補です。日付が古いという推測ではありません。
削除前に再fetchし、SHAが一致すること、新コミット・参照中のPR・運用依存がないことを再確認してください。
承認後も一括削除前に一覧を保存します。復元には表のSHAから同名ブランチを再作成できますが、
リモートでそのオブジェクトが将来残るとは保証しないため、必要なら手元のgit bundle等を保持します。
この文書の作成自体は削除承認を意味しません。

| ブランチ（origin/を省略） | 確認したtip SHA |
|---|---|
| `claude/update-readme-progress-jGRa3` | `0f7f37351f586fbb45585e9da13e5a2bb2867456` |
| `codex/add-calendar-export-option-to-diary_cli` | `e3c814a189041c27405e81b06f3e7fe60c0b9430` |
| `codex/add-calendar_exporter.py-for-calendar-handling` | `d0d190daa57197e48afb6ce49396ac9583ed86f5` |
| `codex/add-cli-entry-point-implementation` | `951b8375057a4f364532afa684dbafb6b670d572` |
| `codex/add-dockerfile-and-.dockerignore-for-cli` | `8b058a04ef9f83b750a347da5bdc21524d4a829f` |
| `codex/add-gitops-service-layer-functions` | `409f5d4091c509ef62e72e7e3b73544660b11ccb` |
| `codex/add-project-setup-files-and-update-readme` | `0e027ccdbcf7fea18a68feb73ed63189ec7780ed` |
| `codex/add-tests-for-japanese-diary-functionality` | `98ebdb18cebd01f0ee786c2e4d00393aaff8ba19` |
| `codex/add-unit-tests-for-cli-and-embedding` | `2a2a720e7f6ec69e127616255b3f07161dc819d9` |
| `codex/create-comprehensive-documentation-for-repository` | `3e9b0800d4560d4194f09fcd6d70b7106128bea8` |
| `codex/create-diary_tagging_v1.txt-and-update-readme` | `7556f4d7e1ad24911580069d13278a80ebdd7fd3` |
| `codex/create-src/embedding-and-implement-features-9t2kjy` | `aea2e0efff0b4f5ac5f1e03e049c68d01dd61846` |
| `codex/create-task-plan-for-repository` | `a720164b96414c0f616dd37975977036b1d4ad41` |
| `codex/enable-gemini-operation-and-cloudrun-usage` | `6af3697846376556ca414a9729a1a579f67e8ddf` |
| `codex/expand-scheduled-diary-pipeline-for-delivery` | `471e1f36d9228907c457391fc0e9b346aec6143c` |
| `codex/fix-api-authentication-bypass-issue` | `17ef3f5e54d9df45a2c3b59f325b6e31cbf2125c` |
| `codex/fix-cloud-run-deployment-vulnerability` | `328221a411bd9b588f3aeccc2c4ab194c52e292e` |
| `codex/fix-option-injection-vulnerability-in-git-cli-backend` | `c901c048e16f14f527a1bc6180ba26099b09959d` |
| `codex/implement-daily-csv/json-uploader-to-drive` | `47bbf0d0d3aecef3565718d9f1b95f6e6a42f69e` |
| `codex/implement-scheduled-diary-pipeline` | `3e75b53784887d22ac4ba953a49223375b43a6da` |
| `codex/proceed-to-next-task` | `91cfd912d7497cbbcfc4a7ed3e76ec4c24eef271` |
| `codex/proceed-to-next-task-3sn143` | `9a55ac8681334b6c12cbcaa9508345e955b697a9` |
| `codex/proceed-to-next-task-5of4bt` | `3f4d630ee8fe2ba3902886f39637e6ce288a09de` |
| `codex/proceed-to-next-task-6y6e43` | `68934df1f01096792f968ad724afbdd279cb725e` |
| `codex/proceed-to-next-task-apyfg9` | `50350196fc39840dc0a9976672dc38048b122c16` |
| `codex/proceed-to-next-task-cw4o7z` | `545872eebcbee0872973201f18a23e26ca7d7f88` |
| `codex/proceed-to-next-task-lyzaxb` | `7faaf0a3eb18b40d9cec3c69de51ac424dfd6793` |
| `codex/proceed-to-next-task-mlotim` | `3ce369572c57cd30f4afdd89cafe11549c527ba4` |
| `codex/proceed-to-next-task-ozxnum` | `ae844c06c074587459b9e21e07cf284bf4ff076e` |
| `codex/proceed-to-next-task-q3us90` | `9676efab209b49c2f2cde073b6f7ad3370bda231` |
| `codex/proceed-to-next-task-ycj004` | `e62829eeb51fc2189720d1c9b90c479154a2ae0d` |
| `codex/proceed-to-the-next-task` | `5e584776aadf7ef1dc2e52677baef6ccfdf8519f` |
| `codex/proceed-to-the-next-task-07m3j3` | `9ecfc72ec14d37f829f96c5421654db0ad700698` |
| `codex/proceed-to-the-next-task-3wwmma` | `27542db194a3da93dc95c6600db44f3411a6d691` |
| `codex/proceed-to-the-next-task-8ghpcd` | `104f590c6f2ea4ea46b0dff8379e7576d56a59ce` |
| `codex/proceed-to-the-next-task-aibdx7` | `4e154e799423fb73fa681dbafff7206dcbfb9e59` |
| `codex/proceed-to-the-next-task-cduu2t` | `f4bb0f64ff55a9b88e245edd7558bff6a77067b2` |
| `codex/proceed-to-the-next-task-h5cigo` | `b59af4ec3b48d454e33e422dbe971e2d85a2c372` |
| `codex/proceed-to-the-next-task-impsyt` | `998f676429d2cc266a8e1d02c5b34544092fa54c` |
| `codex/proceed-to-the-next-task-ko5yy6` | `c6e6113c6999805b087b907ca2dfcc98ae323d9c` |
| `codex/proceed-to-the-next-task-nu1fh0` | `dde802a2e3de1c4984b44c462f471189f02e812a` |
| `codex/proceed-to-the-next-task-ogbkz4` | `2e75ba7421832b277f886efcb480666a07517525` |
| `codex/proceed-to-the-next-task-ogum7t` | `44d9074e07e850be6d57392a00b7cd5912140e49` |
| `codex/proceed-to-the-next-task-r1j40j` | `8a0a2702ab02efd30d52c1f84396e174339fec40` |
| `codex/proceed-to-the-next-task-rfzcp6` | `c413df6b959b662aed81c9eb82a38a9e81634d78` |
| `codex/proceed-to-the-next-task-smw40l` | `d07642575344f0d1184127bc0d59444e397d682b` |
| `codex/proceed-to-the-next-task-uqehb4` | `067bc0aba90b7188f5c074732d58a454012f6938` |
| `codex/refactor-clients-and-add-cli-options` | `e2f956f851e9a912ce7adfdc3ee376b76ac74ec6` |
| `codex/refactor-diary-processing-and-cli-structure` | `5346c5796c2fe5466b968d34cfe879942fd24112` |
| `codex/update-documentation-to-current-version` | `f4683c554b7d8ef5c07deb0e6e2e3cce8fafa5e7` |
| `codex/update-readme-checklist-and-roadmap` | `dc2f9b9a8d831813e23fe62f8f43c4169f17b420` |
| `codex/update-readme.md-for-grave-site-server` | `29999c7b64521af5eee93f81c1f87fb9a61c2da8` |
| `codex/update-readme.md-with-mvp-features` | `b4bad9bdcdfbc236a858f56aab0740fe5c906e10` |
| `codex/update-repository-goals-and-functionality` | `5e2f674a8aa4c8d2e15af256bfd930ec3b03fee7` |
