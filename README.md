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

### すぐ渡せるもの（実在ファイルベース）

- [x] GPT用プロンプトテンプレ（`prompts/diary_tagging_v1.txt`）
- [x] プロンプト組み立てCLI（`cli.py`）
- [x] 日記一括処理CLI（`src/cli.py` / JSON・CSV出力）
- [x] RAG用Embeddings CLI（`src/embedding/*`）
- [ ] OpenAI API連携の本番版バッチ（現在はローカルルールベース実装）
- [ ] ChatGPT / MyGPT向け「今日の100文字」記入Botテンプレ

## CLI実行例

```bash
python3 src/cli.py --input input.txt --format json
python3 src/cli.py --input input.txt --format csv --output diary.csv
```

- `input.txt` は1行1日記の形式で用意してください。
- 生成ファイルは `output/` に保存されます。

## ロードマップ（優先度順）

### 現在のMVP範囲

1. **日記の一括変換（JSON/CSV）を安定運用する**  
   入口: `python3 src/cli.py --input input.txt --format json`
2. **プロンプトテンプレを使って手作業運用しやすくする**  
   入口: `python3 cli.py --prompt-file prompts/diary_tagging_v1.txt "..."`
3. **ローカルEmbedding検索で「過去メモ参照」を可能にする**  
   入口: `python3 -m src.embedding.cli index ...` / `python3 -m src.embedding.cli search ...`

### 次スプリント範囲

1. **`src/cli.py` のタグ付けを設定可能化（辞書外出し・重み調整）**  
   対象モジュール: `src/cli.py`
2. **EmbeddingパイプラインのI/Oバリエーション追加（JSONLなど）**  
   対象モジュール: `src/embedding/io_utils.py`, `src/embedding/pipeline.py`
3. **CLI間の接続を簡略化する統合コマンド追加**  
   入口候補: `python3 src/cli.py ...` → `python3 -m src.embedding.cli index ...` を1コマンド化
4. **自動テストをMVP運用フローへ拡張**  
   入口: `pytest`, 対象モジュール: `tests/test_diary_processor.py`, `src/embedding/*`

## 開発時の実行・テスト手順（CONTRIBUTINGと整合）

- セットアップ: `make setup`
- 実行（サンプル入力を処理）: `make run`
- 構文チェック: `make test`
- Lint（ruff導入時のみ）: `make lint`
