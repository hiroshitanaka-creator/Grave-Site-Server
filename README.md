# -Grave-Site-Server
私はサーバーの中で生き続ける

## 100文字日記 → 感情/トピック自動タグ化テンプレ（概要）

**目的**: 100文字以内の日記をGPTに解析させ、感情タグ・トピックタグ・要約を生成してCSV/Excel/JSON/Notionへ保存しやすい形に整形する。

詳細なプロンプト定義・変更履歴は `prompts/` 配下を参照してください。

- プロンプト本体: `prompts/diary_tagging_v1.txt`
- 変更履歴: `prompts/CHANGELOG.md`

## CLI（--prompt-file対応）

`cli.py` は `--prompt-file` で指定したテンプレートを読み込み、`{{entry}}` を日記本文に置換して最終プロンプトを出力します。

```bash
python3 cli.py "今日は少し疲れたけど、散歩して落ち着いた。"
python3 cli.py --prompt-file prompts/diary_tagging_v1.txt "今日は少し疲れたけど、散歩して落ち着いた。"
```

標準入力にも対応しています。

```bash
echo "今日は少し疲れたけど、散歩して落ち着いた。" | python3 cli.py --prompt-file prompts/diary_tagging_v1.txt
```
