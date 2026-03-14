# -Grave-Site-Server
私はサーバーの中で生き続ける

## 100文字日記 → 感情/トピック自動タグ化テンプレ

**目的**: 100文字以内の日記をGPTに解析させ、感情タグ・トピックタグ・要約を生成してCSV/Excel/JSON/Notionへ保存しやすい形に整形する。

## MVPで提供する機能

### 1. 入力形式

- **1件入力**: 1行の日記テキストを直接入力。
- **複数件入力**: 複数行の日記を一括処理（1行=1件）。
- **受け付けるファイル形式**:
  - `.txt`（改行区切り）
  - `.csv`（`entry`列必須。任意で`date`列）
  - `.json`（`[{"entry":"...","date":"YYYY-MM-DD"}]` 形式）

### 2. 出力形式（CSV/JSONの項目定義）

- **CSV出力**: UTF-8、ヘッダー付き。
- **JSON出力**: 配列形式。
- **共通スキーマ**:
  - `date` (string): `YYYY-MM-DD`。入力にない場合は実行日を補完。
  - `entry` (string): 元の日記本文。
  - `mood_tag` (string): 感情タグ（1〜2語）。
  - `topic_tag` (string): トピックタグ（1〜2語、カンマ区切り可）。
  - `summary` (string): 30文字以内を目安にした要約。

### 3. 実行形態

- **MVPはCLI実行**を前提とする。
- バッチ処理で複数件をまとめて実行し、CSV/JSONを生成する。
- **将来のAPI化**（HTTPエンドポイント提供）はPhase 2以降で実施予定。

### 5. 成功条件

- 100件の日記を一括処理できる。
- 出力件数が入力件数と一致し、欠損レコードがない。
- 各レコードで `entry / mood_tag / topic_tag / summary` が空欄にならない。
- 生成結果をCSVとJSONの両形式で保存できる。

## 今回はやらない機能（非スコープ）

### 4. 非スコープ

- Web UI / モバイルUIの提供。
- ユーザー認証・認可（ログイン、権限管理）。
- ベクトル検索・RAG連携（Phase後半で実施）。
- 高度な分析ダッシュボード（時系列可視化、感情推移グラフ）。
- 外部SaaSへの自動書き込み（Notion/Sheetsへの本番連携）。

### 想定入力量（1行日記）

```
今日は会社で上司に怒られた。納得いかないけど、成長のチャンスと捉える。
```

### 出力テンプレ（CSVに格納しやすい構造）

| date       | entry                               | mood_tag           | topic_tag           | summary            |
| ---------- | ----------------------------------- | ------------------ | ------------------- | ------------------ |
| 2026-02-06 | 今日は会社で上司に怒られた。納得いかないけど、成長のチャンスと捉える。 | frustration→growth | workplace, feedback | 上司とのやり取りから成長の視点を得た |

### GPT用プロンプトテンプレ

```plaintext
あなたは、100文字以内の日記文を解析し、「感情タグ（Mood）」「トピックタグ（Topic）」「要約（Summary）」を生成するシステムです。

# 出力形式（CSV形式）:
- date: 現在日付（YYYY-MM-DD）
- entry: 元の日記文（そのまま）
- mood_tag: 感情（例: happiness / frustration / neutral / hope / loneliness）など1〜2語
- topic_tag: 内容的なトピック（例: work, relationship, memory, routine, idea）など1〜2語
- summary: 日記の意味内容を1文で要約（30文字以内）

# 出力例（日本語）:

Input:
今日は会社で上司に怒られた。納得いかないけど、成長のチャンスと捉える。

Output:
date: 2026-02-06  
entry: 今日は会社で上司に怒られた。納得いかないけど、成長のチャンスと捉える。  
mood_tag: frustration→growth  
topic_tag: workplace, feedback  
summary: 上司とのやり取りから成長の視点を得た

次のInputに進んでください：
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

### すぐ渡せるもの（実ファイル連動）

| 項目 | 状態 | 実ファイル |
| --- | --- | --- |
| GPT用プロンプトテンプレ | ✅ 完了 | `README.md` |
| CSV / Excel用ヘッダー付きフォーマット | ✅ 完了 | `README.md` |
| Pythonプロジェクト定義（`pyproject.toml`） | ✅ 完了 | `pyproject.toml` |
| 開発用コマンド（`make run/test/lint`） | ✅ 完了 | `Makefile` |
| 開発時除外設定（`.gitignore`） | ✅ 完了 | `.gitignore` |
| 貢献ガイド（環境構築・実行・テスト・コミット規約） | ✅ 完了 | `CONTRIBUTING.md` |
| Pythonスクリプト：複数日記 → OpenAI API → CSV出力 | ⏳ 未着手 | （未作成） |
| RAG用Embeddingsスクリプト：日記 → ベクトル → 検索可能DB | ⏳ 未着手 | （未作成） |
| ChatGPT / MyGPTで「今日の100文字」記入Bot化テンプレ | ⏳ 未着手 | （未作成） |
