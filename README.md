# -Grave-Site-Server
私はサーバーの中で生き続ける

## 100文字日記 → 感情/トピック自動タグ化テンプレ（概要）

**目的**: 100文字以内の日記をGPTに解析させ、感情タグ・トピックタグ・要約を生成してCSV/Excel/JSON/Notionへ保存しやすい形に整形する。

詳細なプロンプト定義・変更履歴は `prompts/` 配下を参照してください。

- プロンプト本体: `prompts/diary_tagging_v1.txt`
- 変更履歴: `prompts/CHANGELOG.md`

## CLI（用途別）

### 1) プロンプト生成CLI

`src/prompt_cli.py` は `--prompt-file` で指定したテンプレートを読み込み、`{{entry}}` を日記本文に置換して最終プロンプトを出力します。

```bash
python3 src/prompt_cli.py "今日は少し疲れたけど、散歩して落ち着いた。"
python3 src/prompt_cli.py --prompt-file prompts/diary_tagging_v1.txt "今日は少し疲れたけど、散歩して落ち着いた。"
```

標準入力にも対応しています。

```bash
echo "今日は少し疲れたけど、散歩して落ち着いた。" | python3 src/prompt_cli.py --prompt-file prompts/diary_tagging_v1.txt
```

> [!NOTE]
> 旧コマンド `python3 cli.py ...` は後方互換のため利用可能ですが、**非推奨**です。

### 2) 日記解析CLI

`src/diary_cli.py` は `input.txt`（1行1日記）を読み取り、`src/diary_processor.py` の解析ロジックでタグ生成・要約生成を行って `output/` へ保存します。

```bash
python3 src/diary_cli.py --input input.txt --format json
python3 src/diary_cli.py --input input.txt --format csv --output diary.csv
```

- `input.txt` は1行1日記の形式で用意してください。
- 生成ファイルは `output/` に保存されます。

> [!NOTE]
> 旧コマンド `python3 src/cli.py ...` は後方互換のため利用可能ですが、**非推奨**です。


### 3) OpenAIバッチ解析CLI（複数日記 → CSV）

`src/openai_diary_batch.py` は `OPENAI_API_KEY` を使って1行1日記を順番にOpenAIへ送り、CSVを出力します。

```bash
export OPENAI_API_KEY="sk-..."
python3 src/openai_diary_batch.py --input input.txt --output output/diary_openai_output.csv --model gpt-4o-mini
```

- 入力は1行1日記です。
- `--date` で `date` 列の固定値を指定できます。
- OpenAI API未設定時はエラーで終了します。

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

### すぐ渡せるもの（実在ファイルベース）

- [x] GPT用プロンプトテンプレ
- [x] CSV / Excel用ヘッダー付きフォーマット
- [x] Pythonスクリプト：複数日記 → OpenAI API → CSV出力
- [x] RAG用Embeddingsスクリプト：日記 → ベクトル → 検索可能DB
- [ ] ChatGPT / MyGPTで「今日の100文字」記入Bot化テンプレ
