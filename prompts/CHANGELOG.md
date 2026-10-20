# prompts CHANGELOG

## 2026-03-14
- `diary_tagging_v1.txt` を新規作成。
- READMEにあったGPT用プロンプトテンプレを `prompts/diary_tagging_v1.txt` へ移植。
- 出力制約（文字数・タグ数・日本語出力）をテンプレ内で明示。

## 2026-10-20
- 機械処理をmood_tag / topic_tag / summaryの3項目、日本語要約30文字以内へ統一。
- date / entryは呼び出し側が保持する契約を明記。
- wheel同梱のsrc/resourcesを正本とし、promptsの互換コピーを同期。
- 表示用MyGPTテンプレートの語彙・長さ・保存列を対応させ、無断の原文切り詰めを廃止。
