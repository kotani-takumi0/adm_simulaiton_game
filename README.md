# Policy Game（FastAPI + 簡易UI）

予算推定（当初予算の推定と類似事業の提示）と、年度進行型の簡易シミュレーションを提供する FastAPI アプリです。`/ui/` にシンプルな検証用フロントエンドを同梱しています。

## 概要

- バックエンド: FastAPI（`app/`）
- データ: `data/adm_game.parquet`（推奨）または `data/selected_game.csv` など
- 簡易UI: 静的ファイル（`web/`）を `/ui/` で配信
- オプションUI: `frontend/` に Next.js 実装（任意）

## 必要要件

- Python 3.10+（推奨）
- pip / venv
- データファイル（後述）

## セットアップ

1) 仮想環境と依存関係

- `python3 -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements.txt`

2) 環境変数（任意、`.env` を利用可）

- `CORS_ORIGINS`: 例 `http://localhost:3000`
- `GAME_YEARS` / `GAME_EVENTS_PER_YEAR` / `GAME_BUDGET_PER_YEAR`: ゲーム設定
- `TOPK` / `TAU` / `ALPHA` / `BETA`: 予測ハイパーパラメータ
- `EMBEDDING_PROVIDER`: `dummy`（既定）/ `openai`
- `OPENAI_API_KEY` / `OPENAI_EMBEDDING_MODEL` / `OPENAI_BASE_URL`: OpenAI埋め込み利用時

3) データ配置（最低いずれか）

- 推奨: `data/adm_game.parquet`
  - 必須列: `embedding_sum`（埋め込み 1D ベクトルの配列/JSON 文字列）
  - あると良い列: `予算事業ID`, `事業名`, `現状・課題`, `事業の概要`, `当初予算`, `歳出予算現額`, `事業概要URL`
- 代替: `data/embeddings.npz`（`X1`, `y_init` 必須, `X2`/`y_final` 任意）とメタデータ（`events.parquet` または `selected_game.csv` または `events.csv`）

## 起動

- `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
- ヘルスチェック: `curl -iS http://127.0.0.1:8000/health`
- UI: ブラウザで `http://127.0.0.1:8000/`（`/ui/` にリダイレクト）

## 簡易UIの使い方（/ui/）

- ゲーム開始 → 今月の事業を取得 → 「事業の概要」を入力して予測 → 「この事業に割当」で年度残額を更新
- 「今月の事業の当初予算を確認」は、当月イベントの実データを表示します（割当後に解放）
- 年度内のイベントが尽きると、次年度ボタンが表示されます

## API 一覧（抜粋）

- `GET /health`: 稼働確認
- `POST /v1/state/start`: セッション開始（初年度のイベントIDを採番）
- `GET /v1/state/me?session_id=...`: 現在状態を取得
- `POST /v1/state/next_year` body: `{"session_id": "..."}`: 次年度へ遷移（残イベントがある場合は 409）
- `GET /v1/events/next?session_id=...`: 当年の未提示イベントを1件取り出し（尽きたら 409）
- `GET /v1/events/meta?budget_id=...`: 任意IDのメタ情報（名称/課題/当初予算など）
- `GET /v1/events/ids`: 参照可能な全イベントID（文字列）
- `GET /v1/events/overview`: 既定イベントの概要（最初の1件）
- `GET /v1/events/meta_by_name?name=...`: 事業名からメタを取得
- `POST /v1/budget/predict` body: `{ "query_text": string }`: 当初予算の推定 + 類似 Top-K
- `GET /v1/budget/model_info`: 埋め込み次元・件数・TopK/Tau 等
- `POST /v1/allocate` body: `{ session_id, event_id, allocated_budget }`: 予算割当（同一IDは上書き、差分だけ残額反映）

### 予算推定の仕組み（概要）

- コサイン類似度で近傍 Top-K を抽出し、温度付きソフトマックス重みで当初予算の対数加重平均を推定
- 既定では `adm_game.parquet` の `embedding_sum` を `X1` として使用
- 埋め込み提供元は `EMBEDDING_PROVIDER` で切替（`dummy`/`openai`）。OpenAI を使う場合はデータの埋め込み次元一致が必須

## よくあるトラブル

- 500: `prediction failed: ...` → `data/adm_game.parquet` の `embedding_sum` 形式/次元不一致、またはデータ未配置
- 409（`/v1/events/next`）: 当年のイベントを出し切り → `/v1/state/next_year` を呼ぶ
- 409（`/v1/state/next_year`）: まだ当年のイベントが残っている
- CORS ブロック: `.env` の `CORS_ORIGINS` にフロントのオリジンを追加
- `/` が 404 → 修正済み。`/` は `/ui/` にリダイレクト、`/favicon.ico` は 204 を返却

## 開発メモ

- セッションはプロセスメモリ保持（`app/api/v1/state.py` の `_SESSIONS`）。本番用途では外部ストア（Redis/DB）への置換を推奨
- 事業メタは `data/selected_game.csv` と `data/adm_game.parquet` をマージ（`予算事業ID` をキーに正規化）
- コード構成
  - 予測: `app/services/predictor.py`
  - データロード: `app/services/datastore.py`
  - イベントメタ: `app/services/events_catalog.py`
  - API: `app/api/v1/*`
  - 設定: `app/core/config.py`

## サンプルコマンド

- セッション開始: `curl -sS -X POST http://127.0.0.1:8000/v1/state/start | jq` 
- 次イベント取得: `curl -sS "http://127.0.0.1:8000/v1/events/next?session_id=SESSION" | jq`
- 予算推定: `curl -sS -H 'Content-Type: application/json' -d '{"query_text":"学校のICT化を推進する"}' http://127.0.0.1:8000/v1/budget/predict | jq`
- 割当: `curl -sS -H 'Content-Type: application/json' -d '{"session_id":"SESSION","event_id":"ID","allocated_budget":5000000000}' http://127.0.0.1:8000/v1/allocate | jq`
