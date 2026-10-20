# 開発手順

Python 3.11 / 3.12、GNU Makeを検証対象とします。依存定義は `pyproject.toml` にまとめ、
実行用の中核、Google連携の `google`、Firestoreの `cloud`、開発用の `dev` を分離しています。
`requirements.lock` は2026-10-20にPython 3.12で解決した固定バージョンのconstraintsです。
ハッシュによる供給元検証やOSイメージの固定までは含みません。

```bash
make setup PYTHON=python3.12
make lint
make test
make build
make schema
git diff -- openapi/gpts_actions.yaml
```

`make setup` で作った `.venv` を全Makeターゲットで使います。
別環境の場合は `make test VENV=/absolute/path/to/venv` のように指定します。
`make format` はコードを書き換えるため、関連する差分だけを確認して採用してください。
依存更新時はクリーンなvenvでextrasを含めて解決し、constraintsを更新して以下のwheel検証も行います。

## インストール後の検証

```bash
python3.12 -m venv /tmp/grave-wheel-test
/tmp/grave-wheel-test/bin/python -m pip install -c requirements.lock dist/grave_site_server-0.2.0-py3-none-any.whl
/tmp/grave-wheel-test/bin/python -I scripts/smoke_installed.py
```

smokeは一時ディレクトリへ移動して日記CLI、同梱テンプレート、検索、バッチのhelp、ジョブ、
HTTPサーバ起動、保存・再送・401を確認します。Google連携は無効で、実サービスには送信しません。
Google / Firestore運用には `.[google,cloud]` が必要です。Dockerfileはこの組合せをインストールします。
`src` パッケージ名は既存import互換のため保持しました。wheel内にも同じ名前で収録します。

## テストの区分

- 単体・回帰: 解析、CLI、特徴検索、既存GitOps。
- ローカル統合: SQLiteトランザクション、スレッド並行実行、別プロセス再読込、API契約、wheel smoke。
- 模擬外部接続: Drive / Calendar書込み直後のタイムアウト、ETag競合、状態保存失敗、OpenAI / Gemini公式応答形式。
- Firestoreエミュレータ: ローカル専用の明示設定時のみ実行。本番接続として扱わない。
- 実接続: 管理者が認証・テスト対象を指定し、実送信を認めた環境で別に実施する。

Firestoreを変更した場合はJava 21+とGoogle Cloud CLIを用意し、別ターミナルで以下を実行します。

```bash
gcloud emulators firestore start --host-port=127.0.0.1:8085
FIRESTORE_EMULATOR_HOST=127.0.0.1:8085 .venv/bin/python -m pytest -m firestore
```

`demo-grave-site` のランダムなテストcollectionを使用します。エミュレータは実際のIAM・制限・性能を再現しません。
未設定ならskipであり、Firestore検証成功の根拠にはできません。

APIのモデル・経路を変更したら `make schema` でOpenAPIを再生成し、正常・異常系と認証の契約を検証します。
単に文字列が存在するだけの検証には戻しません。プロンプトの正本は `src/resources/diary_tagging_v1.txt` で、
`prompts/` の互換コピーも同期します。機械解析は3項目、日本語要約30文字以内です。

変更理由、互換性、データへの影響、実行コマンド、未実施の検証をPRへ記載してください。
過去の `P{phase}-T{task}` は追跡用に使用できますが、フェーズ完了の根拠にはしません。
リモートブランチ削除、既存PRのクローズ、マージ、実配信、デプロイは今回の検証手順に含めません。
