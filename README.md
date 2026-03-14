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

### 自動記録 → データ保存の流れ

1. 手元で日記を書く（Notepad / Obsidian / VS Code など）
2. バッチでGPTに投げる or 日記Bot化する
3. 出力をCSV or JSONに変換
4. 保存先を選ぶ

- Google Sheet（クラウド）
- Local CSV（RAG用に埋め込み化も可能）
- Firestore / Supabase（構造化DB）
- Notionページ（感情日記として回覧可）

### 将来拡張のアイデア

- summaryだけ抽出してvector embedding化
- RAGで「去年の今日の気持ち」を呼び出し
- 記憶ありAIとの連携で自己対話補助

### すぐ渡せるもの

- [x] GPT用プロンプトテンプレ
- [x] CSV / Excel用ヘッダー付きフォーマット
- [ ] Pythonスクリプト：複数日記 → OpenAI API → CSV出力
- [x] RAG用Embeddingsスクリプト：日記 → ベクトル → 検索可能DB
- [ ] ChatGPT / MyGPTで「今日の100文字」記入Bot化テンプレ

## CLI実行例

```bash
python src/cli.py --input input.txt --format json
python src/cli.py --input input.txt --format csv --output diary.csv
```

- `input.txt` は1行1日記の形式で用意してください。
- 生成ファイルは `output/` に保存されます。
