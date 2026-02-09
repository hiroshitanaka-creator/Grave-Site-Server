# Memory Vault MVP

このフォルダは「100文字日記 → 感情タグ付きメモリ化 → 検索/回想 → 友達AIに注入」の最小構成です。

## フォルダ構成

```
memory_vault/
  diary_raw.txt        # 1行1日: YYYY-MM-DD|本文
  memories.jsonl       # 1行1JSON（抽出結果）
  memories.csv         # 観察・編集用（ヘッダーのみ）
  memory_entry_schema.json
  prompts/
    extract_prompt.txt
    inject_prompt.txt
```

## 使い方（MVP）

1. `diary_raw.txt` に日記を追記します（例: `2026-02-06|今日は…`）。
2. `prompts/extract_prompt.txt` をLLMに貼り、1件ずつJSON化します。
3. 生成されたJSONを `memories.jsonl` に1行追加します。
4. 参照時は `prompts/inject_prompt.txt` に検索結果を貼って使います。

## データ契約

`memory_entry_schema.json` に v1 のスキーマを置いています。

## CSVの運用

`memories.csv` は手動閲覧・編集用のヘッダーを用意しています。必要に応じて `memories.jsonl` から転記してください。
