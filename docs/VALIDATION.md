# 再稼働準備の検証記録

実施日: 2026-10-20。基準mainは `ca688ac4c97ee080d800fd0097a6c773c44b9a82`。
変更は `codex/restore-message-delivery-20261020` で実施しました。

## 到達状態

- **A: SQLite構成のコード修正・ローカル検証を完了。** 配信アダプタは模擬外部APIで検証。
  Firestoreアダプタは追加済みだがエミュレータ統合は未実施であり、クラウド構成の準備完了とは断定しない。
- **B: 外部サービス接続検証は未完了。** Google / OpenAI / Gemini / GPTs Actionsの実接続なし。
- **C: 本番での継続稼働確認は未完了。** デプロイ、Scheduler登録、実在の宛先への配信なし。

## 環境と結果

Linux x86_64、Python 3.12.14。開発venvと新規venv、さらにwheel専用の新規venvを使用しました。
パッケージの固定解決結果はrequirements.lockに保存しています。

| 区分 | 実施した検証 | 結果 |
|---|---|---|
| 単体・回帰・ローカル統合・模擬外部接続 | `make test VENV=<開発venv>` | 153 passed / 1 skipped |
| クリーンな開発環境 | `make setup PYTHON=<Python3.12> VENV=<新規venv>` | アプリとdev / google / cloud依存のインストール成功 |
| 同上の回帰検証 | `make test VENV=<新規venv>` | 153 passed / 1 skipped |
| lint | `make lint VENV=<開発venv>` | ruff check成功 |
| 依存整合 | 両開発環境で `python -m pip check` | 不整合なし |
| wheelビルド | `python -m build --wheel` | 0.2.0のwheel生成成功、srcパッケージ・テンプレートを収録 |
| リポジトリ外の実行 | 新規venvへwheelを通常インストールし `python -I scripts/smoke_installed.py` | 日記CLI、プロンプト資源、検索、バッチhelp、console entry points、ジョブ、HTTP起動・保存・再送・401成功 |
| API契約 | 生成OpenAPIとアプリのschemaを完全比較、API正常・異常系 | 成功。X-API-Key必須、422/401/404/409/500、保存/配信状態を確認 |
| 設定の静的確認 | Service / Job / CI / OpenAPIのYAML、examples/message.json、プロンプトコピー一致 | 成功。Google側の設定受理・動作を検証したものではない |
| 変更の整合 | `git diff --check` | 成功 |

pytestはStarlette TestClientのhttpx利用について非推奨警告1件を出します。テスト失敗ではありません。
Python 3.11 / 3.12のGitHub CIも成功しました。ローカル実行環境は3.12です。
CIの結果はPRのChecksも参照してください。実行していない環境をこの表の成功数へ含めていません。

## 必須事項との対応

1. 旧テスト3件の失敗はAPI_KEY必須化後のテスト不整合だった。APIテストへキーと依存差替えを設定し、認証必須を維持した。
2. 同日・異なる宛先/本文は別記録として残り、日付名の上書きを使わないことを確認した。
3. recipient / tags / source / memory_refs / 本文の前後空白を含む保存を確認した。
4. 同じrequest_idの同一入力、相違する入力の409、訂正のexpected_revisionを検証した。
5. Calendar失敗をdelivery_statusへ返し、Drive再アップロードなしで再試行できることを確認した。
6. 同時登録24件、ワーカー競合、リース期限・古いトークン、別プロセスのDB再読込、
   Drive / Calendarの書込み後タイムアウト、外部成功後のcheckpoint失敗を検証した。
7. OpenAIのoutput配列、Geminiのparts・認証ヘッダー、未完了応答・不正JSON・モデル不整合を模擬応答で確認した。
8. OpenAPIと実装を照合した。HTTP 200でも配信失敗があり得る契約を文書化した。
9. 空のvenvへのインストールと、wheelを使ったリポジトリ外のHTTP起動まで確認した。
10. READMEの主要ローカル経路をsmokeで実行した。LLM実要求・クラウドコマンドは対象に含めていない。
11. 台帳のバックアップからID・版・unknown状態を復元し、既存バックアップを上書きしないことを確認した。
12. publish_atのUTC / +09:00境界、dry-run、独立記録の処理継続、処理上限下の失敗記録による飢餓回避を確認した。

単体と模擬外部接続は通常のpytestスイートに混在するため、各区分の成功数を別々には集計していません。
合計件数や成功率だけで実運用可能とは判定しません。

## 未実施と阻害要因

| 項目 | 理由と再開手順 |
|---|---|
| Firestoreエミュレータ | 1件skip。環境にgcloud / emulatorがなくJavaは17。公式のJava21+環境でCONTRIBUTINGの手順を実施する |
| Firestore実環境 | 対象プロジェクト/DB・権限・利用判断未確定。全件走査の費用・容量も実測していない |
| Drive / Calendar | 認証情報とテスト専用の対象・書込み許可を未確認。運用手順の実接続チェックを実施する |
| OpenAI / Gemini | APIキーと利用モデルを未確定。公式形式の解析は模擬確認のみ |
| GPTs Actions | 公開HTTPS入口とCloud Run認証方式の選択が必要。Actionsへの登録・実UIからの呼出しは未実施 |
| Dockerビルド | この環境にDockerなし。wheel導入確認をDocker稼働確認とは扱わない |
| Cloud Run / Scheduler | gcloudなし、対象設定未確定、登録・公開範囲・IAM変更・実配信は承認範囲外 |
| 旧データの実移行 | Drive等の実データ未取得。旧コードから形式を確認し非破壊移行手順を準備した段階 |
| 本番バックアップ/監視 | SQLite模擬復元は確認。本番の復元、アラート通知、長期連続稼働は未確認 |

旧mainの最新Actions run `23101373255` はfailureでした。取得できたjobはstepが空で、
この履歴だけから根本原因を確定できません。認証テスト3件の失敗とCI全体の失敗理由を同一視していません。

## 互換性と残る限界

0.2.0では保存の正本を台帳へ変更し、API応答のstorage_type / record_idの意味も変更しました。
Google IDは別フィールドです。クライアント更新と旧データ移行の詳細はDATA_AND_RECOVERY.mdを参照してください。
旧日記CLIのスナップショット動作とGitOpsは保持しています。旧日記エクスポートへ新APIの保証を拡張して説明しません。
SQLiteは単一永続ホスト向け、Firestoreは全件読込の小規模構成です。
外部APIに対する完全なexactly-once、台帳喪失後の自動復旧、Memory Vaultからの生成、宛先ごとの閲覧制御は保証・実装していません。

## GitHubへの保存とCI

レビュー用 [Draft PR #59](https://github.com/hiroshitanaka-creator/Grave-Site-Server/pull/59) を作成しました。
通常のgit pushは書込み用認証がないため失敗し、接続済みGitHub連携で同じ3コミット分のtreeを保存しました。
各tree SHAをローカルの検証済みtreeと照合し、内容が一致することを確認しています。
コミットの作成者・日時が異なるため、コミットSHAはローカル版と異なります。

- GitHub保存/配信コミット: `2fa1f5bad7c057b9c07390a48937a3f31ea62119`
- 環境/外部APIコミット: `3e2929fecff1cf82a019ed103411fd66d12591a8`
- 実装検証対象HEAD: `e9b01bc23ad127f2ec58e358fc9335ee1e8f515e`
- [GitHub Actions push run 39363342910](https://github.com/hiroshitanaka-creator/Grave-Site-Server/actions/runs/39363342910): **success**
- Python 3.11 / 3.12の両jobで、依存導入、lint、テスト、wheelビルド、リポジトリ外smokeがsuccess。

GitHub CIも外部サービスへの実接続は行いません。Firestore emulatorの未実施は解消していません。
この記録追記は文書のみの変更です。最新コミットのChecksはPRを参照してください。
