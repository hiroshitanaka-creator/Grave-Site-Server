# 再稼働準備の進捗

- 基準main: `ca688ac4c97ee080d800fd0097a6c773c44b9a82`（2026-10-20再fetchでも変更なし）。
- ブランチ: `codex/restore-message-delivery-20261020`。
- GitHub実装コミット: `2fa1f5b`（保存・配信）、`3e2929f`（環境・外部API）。
- 検証対象HEAD: `e9b01bc23ad127f2ec58e358fc9335ee1e8f515e`。以降は検証記録の文書更新。
- レビュー用Draft PR: [#59](https://github.com/hiroshitanaka-creator/Grave-Site-Server/pull/59)。
- GitHub CI: push run `39363342910` はPython 3.11 / 3.12とも成功。
- 適用AGENTS.md: リポジトリと親ディレクトリに存在せず。
- A: SQLite経路の修正・ローカル検証を完了。Firestoreのエミュレータ検証は未実施。
- B: 外部実接続は未実施。Google環境・認証・テスト対象とLLMモデルの確定が必要。
- C: 本番継続稼働は未実施。デプロイ・公開範囲/IAM変更・実配信は未実行。

## 完了

台帳の永続化、入力保持、依頼キー競合、版管理、Drive版別保存、Calendar固定ID/ETag照合、
状態の分離、再試行、定期処理入口、SQLiteバックアップ、LLM解析共通化、依存/CLI/wheel、
OpenAPI契約、README/運用手順、既存ブランチ/PR整理案。
検証は153成功・Firestore1skip、lintとクリーン導入・リポジトリ外HTTP smoke成功。
最新の結果と制約は [VALIDATION.md](VALIDATION.md) を参照。

## 次の実行位置

1. PRの差分とCIを確認する。mainへのマージは今回実施しない。
2. Firestore構成を採用する場合はJava21+のローカルemulator検証を先に行う。
3. Drive種別・Google認証・テストCalendar・外部受付方式を確定する。
4. Google接続・復旧のチェックリストを合成データで実施する。
5. 承認された範囲だけクラウドへ登録し、実行記録をA/B/C別に更新する。

リモートブランチ削除と既存PRクローズは提案のみ。自動再開・継続監視の仕組みは登録していない。
