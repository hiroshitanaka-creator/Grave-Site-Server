# -Grave-Site-Server
私はサーバーの中で生き続ける

## 100文字日記 → 感情/トピック自動タグ化テンプレ

**目的**: 100文字以内の日記をGPTに解析させ、感情タグ・トピックタグ・要約を生成してCSV/Excel/JSON/Notionへ保存しやすい形に整形する。

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

### すぐ渡せるもの

- [x] GPT用プロンプトテンプレ
- [x] CSV / Excel用ヘッダー付きフォーマット
- [ ] Pythonスクリプト：複数日記 → OpenAI API → CSV出力
- [ ] RAG用Embeddingsスクリプト：日記 → ベクトル → 検索可能DB
- [ ] ChatGPT / MyGPTで「今日の100文字」記入Bot化テンプレ
