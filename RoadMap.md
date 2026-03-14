# RoadMap

このドキュメントは、`grave-site-server` を段階的に改善するための実行計画です。  
各フェーズにタスク番号（`P{phase}-T{task}`）を付与しています。

## Phase 1: 基盤整備（CLI / 入出力の安定化）

- **P1-T1: CLI導線の統一**
  - `src/diary_cli.py` を主導線として明示し、`src/cli.py` は後方互換の位置づけを文書化。
  - ✅ 完了日: 2026-03-14 / status: done
- **P1-T2: 入力バリデーション共通化**
  - 空行・不正日付・異常文字列の扱いを統一。
  - ✅ 完了日: 2026-03-14 / status: done
- **P1-T3: JSON/CSV出力スキーマ固定**
  - キー名、日付フォーマット、欠損値のルールを定義。
  - ✅ 完了日: 2026-03-14 / status: done
- **P1-T4: エラーメッセージ標準化**
  - CLI間で同じ失敗理由には同じ文言を採用。
  - ✅ 完了日: 2026-03-14 / status: done

**完了条件 (DoD)**
- CLI関連の主要テストがグリーン。
- READMEのCLI例と実装挙動が一致。

---

## Phase 2: 外部連携の信頼性向上（Drive / Calendar / LLM）

- **P2-T1: 認証・環境変数チェック強化**
  - 必須環境変数不足時の終了コードとエラー内容を統一。
  - ✅ 完了日: 2026-03-14 / status: done
- **P2-T2: Exporterの再試行戦略導入**
  - 一時的失敗（ネットワーク・API制限）に対するリトライ方針を追加。
  - ✅ 完了日: 2026-03-14 / status: done
- **P2-T3: Calendar ID解決ルール統一**
  - `--calendar-id` と `GOOGLE_CALENDAR_ID` の優先順位をコード/READMEで一致。
  - ✅ 完了日: 2026-03-14 / status: done
- **P2-T4: LLMバッチ結果のスキーマ検証**
  - 壊れた行を隔離しつつ全体処理を継続。
  - ✅ 完了日: 2026-03-14 / status: done

**完了条件 (DoD)**
- Exporter/Batchの失敗系テストを追加しグリーン。
- ドキュメントに環境変数と復旧手順を明記。

---

## Phase 3: 運用自動化（Cloud Run / Workflow / GitOps）

- **P3-T1: Cloud Run実行導線の整理**
  - `Dockerfile` / `deploy/cloudrun-service.yaml` / `Makefile` の手順を統一。
  - ✅ 完了日: 2026-03-14 / status: done
- **P3-T2: 定期実行ワークフロー整備**
  - `scheduled_diary_pipeline` の再実行安全性を確認。
  - ✅ 完了日: 2026-03-14 / status: done
- **P3-T3: GitOps方針の明文化**
  - 変更承認、ロールバック、監査ログの最小ルールを定義。
  - ✅ 完了日: 2026-03-14 / status: done
- **P3-T4: 監視項目の定義**
  - 成功率、処理件数、APIエラー率の観測指標を導入。
  - ✅ 完了日: 2026-03-14 / status: done

**完了条件 (DoD)**
- デプロイ手順がドキュメントだけで再現可能。
- 最低限の運用Runbookが存在。

---

## Phase 4: 品質向上と拡張（Embedding / OpenAPI / Docs）

- **P4-T1: テストレイヤーの明確化**
  - 単体・統合・ワークフロー・goldenの更新ルールを明文化。
  - ✅ 完了日: 2026-03-14 / status: done
- **P4-T2: Embeddingパイプライン改善**
  - ベクトル次元・保存形式・再生成手順を固定。
  - ✅ 完了日: 2026-03-14 / status: done
- **P4-T3: OpenAPI契約の強化**
  - `openapi/gpts_actions.yaml` と実装差分の検出を自動化。
  - ✅ 完了日: 2026-03-14 / status: done
- **P4-T4: ドキュメント統合更新**
  - README / CONTRIBUTING / docs を運用実態に合わせて更新。
  - ✅ 完了日: 2026-03-14 / status: done

**完了条件 (DoD)**
- CIで主要テスト + OpenAPI整合チェックが通過。
- 新規参加者がドキュメントのみでセットアップ可能。

---

## 優先度と着手順

1. **最優先:** Phase 1（利用者に直結するCLI品質）
2. **次点:** Phase 2（外部API依存部分の障害耐性）
3. **中期:** Phase 3（運用の再現性・自動化）
4. **継続:** Phase 4（品質と拡張性の底上げ）

## タスク管理ルール（運用提案）

- タスクIDは `P{phase}-T{task}` を必須化。
- PRタイトルに対象タスクIDを含める（例: `feat(P2-T2): add retry policy for drive exporter`）。
- 1PRあたり原則1〜2タスクに限定してレビュー容易性を確保。
- 完了時は DoD チェック結果をPR本文に記載。
