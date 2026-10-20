# Google連携・外部受付・定期運用

この文書は2026-10-20時点のコードと公式資料に基づく設定手順です。
設定例の作成、クラウドへの登録、実接続、継続配信の成功は別の到達状態です。
ここにある登録・IAM・公開範囲変更・配信コマンドは本作業では実行していません。

## 設定一覧

| 変数 | 必要な場面・意味 |
|---|---|
| API_KEY | API必須。Secret Managerまたはローカル環境で注入する共有秘密値。未設定はfail closed |
| MESSAGE_STORE | sqlite（ローカル既定）/ firestore。Cloud Runはfirestore必須 |
| MESSAGE_DB_PATH | SQLiteファイル。既定data/messages.sqlite3。永続ローカルディスクの絶対パス推奨 |
| GOOGLE_CLOUD_PROJECT | FirestoreのプロジェクトID |
| FIRESTORE_DATABASE / FIRESTORE_COLLECTION | 既定(default) / grave_messages。ServiceとJobで一致させる |
| GOOGLE_APPLICATION_CREDENTIALS | FirestoreのADCでローカル認証ファイルを選ぶ場合。Cloud Runは実行SAのADCを使える |
| DRIVE_ENABLED / CALENDAR_ENABLED | true / falseのみ。コード既定true、配布例はfalse。対象と権限確認後に明示して有効化 |
| GOOGLE_AUTH_MODE | service_account（既定）/ oauth / adc。Drive・Calendarの共通方式 |
| GOOGLE_SERVICE_ACCOUNT_JSON | service_account時の秘密鍵JSONのパス |
| GOOGLE_OAUTH_TOKEN_JSON | oauth時のauthorized_user形式JSONのパス。refresh_token等が必要 |
| GOOGLE_DRIVE_FOLDER_ID | Drive書込み先。My Driveか共有ドライブかはIDだけで決めない |
| GOOGLE_CALENDAR_ID | Calendarの既定値。メッセージ入力calendar_idを優先し、台帳へ固定 |
| OPENAI_API_KEY / OPENAI_MODEL | OpenAIバッチ用。モデルは明示設定。保存API / delivery jobはLLMを呼ばない |
| GEMINI_API_KEY / GEMINI_MODEL | Geminiバッチ用。同上 |

API_KEY、OAuthトークン、サービスアカウントJSONをgit / イメージ / プロンプト / ログへ含めません。
Firestore認証はADCで、GOOGLE_AUTH_MODEとは独立です。Google連携の依存は `[google]`、Firestoreは `[cloud]`。
APIとJobは同じ台帳・保存フォルダを使います。途中でDriveフォルダを変えると既存ID照合が競合するので、変更は移行として扱います。

## DriveとCalendarの認証分岐

### 共有ドライブを使う場合

サービスアカウントは所有者になれずストレージ割当がないため、My Driveへ新規ファイルを作る構成を前提にしません。
共有ドライブと対象フォルダへ必要な書込み権限を付けた主体を用意し、
`GOOGLE_AUTH_MODE=service_account` と秘密鍵ファイルのパスを設定します。
利用可能な鍵レスADC主体にDriveのスコープ・共有権限がある場合はadcも選べます。
Cloud Runの実行SAを指定しただけでDriveスコープが揃うとは限らないため、読み書き検証が必要です。

### 個人のMy Driveを使う場合

対象ユーザーのOAuth認可を使い、`GOOGLE_AUTH_MODE=oauth`、`GOOGLE_OAUTH_TOKEN_JSON` を設定します。
OAuthクライアントと同意画面、テストユーザー/公開状態、offline accessによるrefresh_tokenの取得が必要です。
認可フロー自体をこのサーバが提供するわけではありません。GoogleのPython認可フローなどで取得した
`authorized_user` JSONをSecret Managerまたは制限したローカルファイルへ保存します。
アクセストークンは必要時にrefreshされますが、同意失効・OAuthアプリのテスト状態等によるrefresh_token失効は運用で復旧します。

この実装のDriveスコープは `https://www.googleapis.com/auth/drive.file` です。
対象フォルダはそのアプリが作ったもの、またはそのOAuthアプリに明示的に許可されたものを使います。
ブラウザで作った任意フォルダのIDを渡すだけでは権限が足りないことがあります。
Google Pickerによる既存フォルダ選択画面は未実装です。既存フォルダの利用権限がない場合は、
同じOAuthクライアントで作成したテストフォルダを用いるか、認可手順を先に整備します。Drive全体スコープへ黙って広げません。

### Calendar共通

認証主体がテストCalendarのイベントを書けることを確認します。スコープは
`https://www.googleapis.com/auth/calendar.events` です。OAuthでは両サービスに必要なスコープを事前に認可します。
サービスアカウントを使う場合はCalendar自体をその主体へ適切に共有します。
共有先・閲覧範囲はアプリが変更しません。recipientの値からメール・招待・権限設定を作ることもありません。
本番の対象者へ送らず、合成本文とテスト専用Calendarで確認します。

## ローカル定期起動

同じ永続ディスク・同じ環境設定で、任意のスケジューラから `grave-deliver --limit 100` を起動します。
例としてcronでは以下のように作業場所と環境を固定します。/srv/graveの設定ファイルは管理者だけが編集できるようにします。

```cron
*/5 * * * * cd /srv/grave && /bin/sh -c 'set -a; . ./.env; set +a; exec .venv/bin/grave-deliver --limit 100' >> /srv/grave/job.log 2>&1
```

ジョブの5分間隔は例であり今回確定した運用要件ではありません。並行起動は台帳リースで抑制します。
`date` はCalendarの終日日付、`publish_at` はオフセット付きの最早掲載時刻です。
Schedulerのタイムゾーンは起動時間にのみ影響し、保存済みpublish_atはUTC比較です。
未来日付だけを指定しても未来まで公開を待つことにはなりません。

## Docker、Cloud Run ServiceとJob

ServiceはHTTP受付、Jobは保存済み記録を1回走査するバッチです。同じイメージを異なる入口で使います。
データの永続性はFirestoreへ置き、Cloud Runのローカルディスクへ台帳を置きません。
DockerfileのPython3.12-slimタグはOSパッチで変わるため、本番登録時は完成イメージdigestを記録します。

既存のArtifact Registryと承認されたプロジェクトがある場合の手順です。未作成のDB / Registry / Secret等の作成は費用・権限を確認して別に実施します。

```bash
# PROJECT_ID / REGION / REPOSITORY は承認された既存の値を指定する
IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/grave-site:restore-20261020"
docker build -t "$IMAGE_URI" .
gcloud auth configure-docker "$REGION-docker.pkg.dev"
docker push "$IMAGE_URI"
```

登録前に `deploy/cloudrun-service.yaml` と `deploy/cloudrun-job.yaml` を作業コピーへ複製し、
すべてのREPLACE_*、完成イメージdigest、secretの固定version、実行SA、Google認証方式、テスト対象を設定します。
共有のFirestore DBは事前にNative modeで準備します。Firestoreへの必要なデータアクセス権、
対象secretへのアクセス権だけを実行SAへ付けます。正確なIAMは既存構成と組織ポリシーを確認して決定します。
テンプレートは配信false、Serviceのingressはinternalです。

```bash
# 承認・設定レビュー後にのみ登録する
make deploy-cloudrun GCP_PROJECT_ID="$PROJECT_ID" CLOUD_RUN_REGION="$REGION" SERVICE_CONFIG=/path/to/reviewed-service.yaml
gcloud run jobs replace /path/to/reviewed-job.yaml --project "$PROJECT_ID" --region "$REGION"
# まずdry-runの実行結果を確認する
gcloud run jobs execute grave-site-delivery --project "$PROJECT_ID" --region "$REGION" --args=--dry-run --wait
```

IAM invoker必須はYAMLだけで既存IAMから復元できるとは限りません。既存Serviceを更新する場合は、
登録前後にIAM policyとinvoker IAM checkの有効状態を確認します。
テンプレートには公開化設定を含めていません。Jobの実行権限はHTTP API_KEYとは別です。

## GPTs Actionsとの接続条件

`X-API-Key` はアプリ層の認証です。Cloud Run IAMのGoogle IDトークンとは別物です。
internal ingressかつIAM必須のServiceへ、GPTs ActionsがAPIキーだけで直接アクセスすることはできません。
次のどちらかを明示的に選択します。どちらも本作業では登録していません。

1. **直接の外部受付:** Cloud Run ingressをallにし、invoker IAM checkを無効化して、アプリのAPI_KEYを必須にする。
   公開範囲を変更するため承認が必要です。API_KEY共有者は全メッセージへアクセスできることも確認します。
2. **IAMを維持する外部ゲートウェイ:** 公開HTTPSゲートウェイで受付し、アプリのX-API-Keyを転送しつつ、
   Google IDトークンでCloud Runを呼び出す。ゲートウェイSAのrun.invokerと到達可能なingressが必要です。
   API Gateway等の製品選定・別料金・設定・統合検証が必要で、このリポジトリに登録済みのゲートウェイはありません。

直接方式を選択して承認した場合の変更コマンド例です。

```bash
gcloud run services update grave-site-api --project "$PROJECT_ID" --region "$REGION" \
  --ingress=all --no-invoker-iam-check
```

その後、生成 `openapi/gpts_actions.yaml` のservers.urlを確定したHTTPS URLへ変更してGPTs Actionsへ登録します。
認証設定はAPI Keyのカスタムヘッダー `X-API-Key` とし、サーバのAPI_KEYと一致させます。
キーはGPTの指示文やOpenAPI本文へ埋め込みません。Actionsでカスタムヘッダーを利用できるかも実UIで確認します。
GPTの指示には、再送時のrequest_id再利用、保存と配信状態の説明、409時は確認してPUTで訂正することを記載します。
GET / PUT / retryも含め、他のクライアントから同じ契約を使えます。
直接方式の戻し方はingress=internalと `--invoker-iam-check` を再設定し、以前のIAMを確認することです。
これらは公開範囲/IAMの変更なので、今回の実装エージェントは実行しません。

## Cloud SchedulerからJobを起動する

Serviceに定期処理スレッドを常駐させません。Jobを作成してdry-run確認後、承認された起動用SAへ
対象Jobだけの実行権限を用意します。Cloud Schedulerはrun.googleapis.comのAPIへOAuthトークンでPOSTします。
以下は5分間隔・Asia/Tokyoの例で、予定頻度や時間帯は運用判断で変更します。

```bash
gcloud scheduler jobs create http grave-site-delivery \
  --project "$PROJECT_ID" --location "$REGION" \
  --schedule='*/5 * * * *' --time-zone=Asia/Tokyo \
  --uri="https://run.googleapis.com/v2/projects/$PROJECT_ID/locations/$REGION/jobs/grave-site-delivery:run" \
  --http-method=POST --headers=Content-Type=application/json --message-body='{}' \
  --oauth-service-account-email="$SCHEDULER_SERVICE_ACCOUNT"
```

実配信を開始する前にService / Jobの対象・権限・DRIVE_ENABLED / CALENDAR_ENABLEDをレビューします。
Schedulerの受付成功はJobの処理成功ではありません。Job実行の終了状態と台帳の状態を確認してください。
停止時はSchedulerをpauseし、稼働中のJobとAPI受付を停止してからバックアップ / 復旧を行います。

## 実接続チェック（未実施）

1. 認証主体、テストフォルダとCalendarの読み書き権限、Firestoreの接続を確認する。
2. 合成メッセージを登録し、recipient / message / date / tags / source / memory_refsをDrive JSONで照合する。
3. 同じ依頼を再送し、同じDrive ID / Calendar IDで件数が増えないことを確認する。
4. PUT訂正で旧Drive版が残り、Calendarの同じIDの本文が変わることを確認する。
5. テスト環境で失敗・再起動・リース期限・応答喪失を再現し、unknownから固定IDで復旧することを確認する。
6. 未来publish_atと日本時間境界を確認し、Scheduler受付・Job終了・台帳成功を別々に記録する。
7. API_KEYなし/不正は拒否され、GPTs Actionsからも正しい認証だけでアクセスできることを確認する。
8. バックアップから隔離復元し、固定ID・件数・Google側の差異を照合する。

## 公式資料（2026-10-20照合）

- [Calendar: Events insertと指定IDの制約](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert)
- [Drive: pre-generated IDと再試行](https://developers.google.com/workspace/drive/api/guides/manage-uploads)
- [共有ドライブとサービスアカウントの所有制限](https://developers.google.com/workspace/drive/api/guides/about-shareddrives)
- [Drive OAuthスコープ](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
- [OAuth認可のPython例](https://developers.google.com/identity/protocols/oauth2/web-server#python)
- [Firestoreトランザクション](https://docs.cloud.google.com/firestore/native/docs/manage-data/transactions)
- [Firestoreエミュレータ](https://docs.cloud.google.com/firestore/native/docs/emulator)
- [Cloud Run公開範囲とIAM check](https://docs.cloud.google.com/run/docs/authenticating/public)
- [Cloud Runのサービス間認証](https://docs.cloud.google.com/run/docs/authenticating/service-to-service)
- [API GatewayとCloud Run](https://docs.cloud.google.com/api-gateway/docs/get-started-cloud-run)
- [Cloud Run定期Job](https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule)
- [GPTs Actions認証](https://developers.openai.com/api/docs/actions/authentication)
- [OpenAIのテキスト応答](https://developers.openai.com/api/docs/guides/text)
- [Geminiモデルの提供終了情報](https://ai.google.dev/gemini-api/docs/deprecations)

Geminiの旧1.5モデルを現行の起動例から除きました。2.5系列にも既存アカウント等の提供条件があるため、
単に新しそうな名前へ置き換えず、利用時点の提供状況と自分のアカウントで検証します。
