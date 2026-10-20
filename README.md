# Grave-Site-Server

私はサーバーの中で生き続ける

バージョン **0.2.0**。Python 3.11 / 3.12を検証対象とします。
既存文書の目的は「共有Googleカレンダーへ、故人のメッセージを終日イベントとして継続配信する」ことです。
これは今回確定した運用要件ではありません。対象者・公開範囲・配信開始条件は運用前に決めます。

## 現在できること

- 日記原文をルールベース、または設定したOpenAI / Geminiで解析し、CSV / JSONに保存する。
- 配信用メッセージを永続台帳に登録し、Driveへの書き出しとCalendarへの配信結果を別々に記録する。
- 同じ依頼の再送を照合し、内容の競合を409で返す。訂正は版を増やし、Calendarの同じイベントを更新する。
- 保存済みの未完了記録をジョブで再処理する。配信予定時刻を過ぎた記録だけCalendarへ送る。

SQLite・HTTP API・インストール後のCLIはローカル検証対象です。Google / LLMの実接続、
Firestoreの実環境、Docker / Cloud Runへの登録、継続配信は別の確認段階です。
実施結果は [検証記録](docs/VALIDATION.md)、残件は [RoadMap](RoadMap.md) を参照してください。

## ローカルで試す（外部配信なし）

```bash
make setup PYTHON=python3.12
. .venv/bin/activate
cp .env.example .env
# .env の API_KEY を自分用の十分長いランダム値へ変更する
set -a
. ./.env
set +a
make serve
```

`.env` は自動読み込みしません。信頼するローカル設定だけを読み込みます。
`make setup` はアプリ・開発ツール・Google用の追加依存をインストールします。
依存の定義元は `pyproject.toml`、検証した固定解決結果は `requirements.lock` です。
API_KEY未設定のAPI要求は500、キーなし・不一致は401です。認証を無効にする設定はありません。
`/healthz` は認証不要の生存確認であり、保存先やGoogle接続の正常性を示しません。

別ターミナルで同じ設定を読み込み、合成データを登録します。

```bash
curl --fail-with-body http://127.0.0.1:8080/actions/save-message \
  -H "X-API-Key: $API_KEY" -H 'Content-Type: application/json' \
  --data-binary @examples/message.json
```

`.env.example` は `DRIVE_ENABLED=false` / `CALENDAR_ENABLED=false` のため外部送信しません。
台帳は `data/messages.sqlite3` です。起動ディレクトリが変わる運用では `MESSAGE_DB_PATH` を絶対パスにします。
`recipient` は宛先ラベルであり、メール送信先や閲覧権限ではありません。Calendarの閲覧権限はGoogle側の設定です。

### 応答の読み方・再試行・訂正

`saved:true` / `storage_status:saved` は **台帳保存済み** を意味します。
Drive成功は `drive_status:saved`、Calendar成功は `delivery_status:published` で別に確認します。
`pending` は未実行 / 時刻待ち、`failed` は確認できた失敗、`unknown` は外部での成否を照合する必要がある状態、
`disabled` はその連携を無効にした状態です。`processing:true` なら別の処理がリースを取得しています。
保存後の外部失敗はHTTP 200でも状態フィールドに現れるため、HTTPコードや `saved` だけで配信成功と判断しません。

```bash
# RECORD_ID は保存応答の record_id。値を保存してから以下を実行する
curl --fail-with-body "http://127.0.0.1:8080/messages/$RECORD_ID" -H "X-API-Key: $API_KEY"
curl --fail-with-body -X POST "http://127.0.0.1:8080/messages/$RECORD_ID/retry" -H "X-API-Key: $API_KEY"
# GETした内容を編集し expected_revision を追加した全文JSONを correction.json に保存
curl --fail-with-body -X PUT "http://127.0.0.1:8080/messages/$RECORD_ID" \
  -H "X-API-Key: $API_KEY" -H 'Content-Type: application/json' --data-binary @correction.json
```

`request_id` は呼び出し側で生成・保存し、通信再送時に同じ値を使います。省略すると毎回新規記録です。
同じID・同じ内容は同じ記録、異なる内容は409です。訂正はPUTと `expected_revision` で行います。
PUTは全項目置換です。省略した任意項目は既定値になるため、GET結果を基に編集してください。
詳細・旧APIとの互換性は [データ契約と移行](docs/DATA_AND_RECOVERY.md) に記載しています。

## CLI

```bash
. .venv/bin/activate
printf '%s\n' '今日は読書をして楽しかった。' > input.txt
grave-diary --input input.txt --format json --output diary.json
grave-diary --input input.txt --format csv --output diary.csv
grave-prompt '今日は散歩をした。'
grave-embedding index --input output/diary.json --output output/vectors.db
grave-embedding search --query '読書' --store output/vectors.db
```

`grave-diary` の相対出力名は `output/` 配下になります。`make run` は日付名の日記JSONを出力します。
日記の解析出力は `date, entry, mood_tag, topic_tag, summary` です。
日記原文の `entry` と配信用の `message` は別のデータで、自動的には変換・配信しません。
検索は文字3-gramのハッシュ特徴とコサイン類似度です。学習済みEmbeddingや意味検索ではなく、表記揺れ・言い換えに限界があります。

LLMを使う場合は、利用可能なモデルを公式モデル一覧で確認し、キーとモデル名を環境変数に設定します。
モデルの提供状況はアカウントにも依存するため既定モデルを固定していません。

```bash
grave-llm --provider openai --model "$OPENAI_MODEL" --input input.txt --output output/diary_llm.csv
grave-llm --provider gemini --model "$GEMINI_MODEL" --input input.txt --output output/diary_gemini.csv
grave-gemini --model "$GEMINI_MODEL" --input input.txt --output output/diary_gemini.csv
```

`OPENAI_API_KEY` / `GEMINI_API_KEY` がそれぞれ必要です。無効出力は原文と理由を隔離JSONLへ保存し、
ほかの行を処理した後に終了コード1を返します。CSVと隔離JSONLは日記を含むため公開しないでください。
OpenAIの生HTTP応答は `output[].content[].text`、Geminiは候補のテキストを検証して取り出します。
プロバイダ名と明らかに異なるモデル名は拒否しますが、存在・権限・提供中かどうかは実APIでの確認が必要です。

`python -m src.diary_cli`、`python -m src.llm_batch`、`python -m src.embedding.cli` も利用できます。
旧 `python src/cli.py` / `src/diary_cli.py` / `src/gemini_diary_batch.py` は互換用に保持しています。
Embeddingは直接ファイル実行せず `-m` または `grave-embedding` を使います。
旧日記CLIの `--export-drive` は日付単位スナップショット、`--export-calendar` は本文由来IDの従来方式です。
配信メッセージの台帳・訂正・復旧保証は新しいAPI / `grave-deliver` の経路に適用されます。
日記CLIで同日の別記録を蓄積したい場合は個別の出力名を指定してください。

## 定期処理

```bash
grave-deliver --enqueue examples/message.json --dry-run
grave-deliver --enqueue examples/message.json
grave-deliver --dry-run
grave-deliver --limit 100
```

`--enqueue` は保存だけ、通常実行は未完了記録の処理です。外部連携フラグがtrueなら実送信します。
`publish_at` はオフセット付き日時で指定し、UTCに正規化します。省略時は即時Calendar登録です。
`date` はイベントの終日日付であり、送信開始時刻ではありません。終了日は翌日（排他的）です。
`memory_refs` は出典参照を保持するだけで、自動検索・LLM生成は行いません。
旧 `scheduled_diary_pipeline.py` はメモリ内の参照実装で、実運用ジョブは `src.workflows.delivery_job` です。

## 設定・運用・検証

- [Google認証、Cloud Run Service / Job、GPTs Actions、定期起動](docs/google_cloudrun_drive_gemini.md)
- [データ契約、バックアップ、旧データ移行、障害復旧、ロールバック](docs/DATA_AND_RECOVERY.md)
- [検証結果と未確認事項](docs/VALIDATION.md)
- [ブランチ・既存PRの整理候補](docs/REPOSITORY_CLEANUP.md)
- [開発手順](CONTRIBUTING.md)、[設定一覧](.env.example)、[生成OpenAPI](openapi/gpts_actions.yaml)

```bash
make test
make lint
make build
make schema
```

テスト・lintツールが未導入なら失敗します。構文チェックへの代替や検証スキップを成功扱いしません。
`src/gitops/` は既存のGit変更管理モジュールとして保持し、メッセージ配信からは呼び出しません。
