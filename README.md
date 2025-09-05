# Policy Game API (Backend)

## Quickstart

- Create/activate venv (example):
  - `python3 -m venv .venv && source .venv/bin/activate`
- Install deps:
  - `pip install -r requirements.txt`
- Run dev server:
  - `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
- Health check:
  - `curl -iS http://127.0.0.1:8000/health`
 - Simple UI:
   - Open `http://127.0.0.1:8000/ui/` in your browser
- Start a session:
  - `curl -iS -X POST http://127.0.0.1:8000/v1/state/start`
- Next event (replace SESSION):
  - `curl -iS "http://127.0.0.1:8000/v1/events/next?session_id=SESSION"`

## レビューと修正点（2025-09）
- 設定の統一: `app/core/config.py` の `ALPHA/BETA/TOPK/TAU` を `Settings` フィールド化。`settings.ALPHA` 等で取得できるよう修正。
- CORS対応: `app/main.py` に `CORSMiddleware` を追加し、`.env` の `CORS_ORIGINS`（カンマ区切り）を反映。
- 予算割当の上書き整合性: `POST /v1/allocate` は同一イベントに対する再割当時、差分（delta）のみ残額に反映するよう修正。過剰時は 422 を返却。
- 予算推定の入力検証: `PredictRequest` のベクトル長チェックを `Field(min_length=1)` に修正（Pydantic v2に合わせる）。
- 年度遷移: `POST /v1/state/next_year` を追加。年度の未提示イベントが残っている場合や最終年度では 409 を返す。

### 年度遷移の使い方
- 次イベントを取り切ると `/v1/events/next` は 409 を返すため、その後に次を呼ぶ:
  - `curl -iS -X POST http://127.0.0.1:8000/v1/state/next_year -H 'Content-Type: application/json' -d '{"session_id":"SESSION"}'`

## 既知の制約 / 今後のTODO
- 状態参照API: 現在状態を返す `GET /v1/state/me` は未実装（提案: 年/残額/スケジュール残/割当概要を返却）。
- 年度境界の初期化: 現在は年度遷移時に残額のみリセット。イベントごとの割当/スコア/予測のリセット方針は設計要（年度単位でクリア or 永続）。
- イベントカタログ: 現状はダミーID。実データの導入と `/v1/events/{id}` でメタ返却を追加予定。
- 永続化: セッションはメモリ保持。将来Redis/DBに置換する抽象化が必要。
- 予算推定のデータ依存: `data/embeddings.npz` および `events.parquet|csv` が未配置だと推定不可（500）。

## Notes
- Budget prediction `/v1/budget/predict` requires data files under `data/`:
  - If `adm_game.parquet` exists: uses column `embedding_sum` as embeddings (single `X1`), and tries `当初予算`/`歳出予算現額` for targets/metadata.
  - Otherwise falls back to `embeddings.npz` with arrays `X1`, `X2` (optional), `y_init`, `y_final` (optional), and metadata DataFrame from `events.parquet|selected_game.csv|events.csv`.
- Game events catalog is read from `data/selected_game.csv` and used to schedule yearly events and to return event metadata from `/v1/events/next`.
- Simple UI is available at `/ui/` for manual testing (predict, session/events).
 - UI renders human-friendly results: 推定当初予算/推定現額/推定増減率 and a Top-K table (rank, 類似度, 重み, 事業名, 当初予算, 現額).

### Prediction API
- Request: `POST /v1/budget/predict`
  - Body: `{ "query_text": string }` → サーバ側で埋め込みして推定
- Notes:
  - Server-side embedding provider is configurable:
    - `EMBEDDING_PROVIDER=dummy` (default): ダミー埋め込み（トークン毎の安定ランダム）
    - `EMBEDDING_PROVIDER=openai`: OpenAI Embeddings API を使用（`OPENAI_API_KEY` 必須、`OPENAI_EMBEDDING_MODEL` 既定は `text-embedding-3-large`）
  - OpenAI で推論する場合、学習データ（`adm_game.parquet` の `embedding_sum`）も同一モデルで作成した埋め込みである必要があります（次元一致が必須）。
  - Prediction uses only `X1` embeddings with cosine similarity and no linear combination.
  - `TOPK` and `TAU` in `app/core/config.py` control neighbor count and softmax temperature.

### Configure OpenAI Embeddings (optional)
- Install deps: already in `requirements.txt` (`openai`)
- Set env vars (e.g. `.env`):
  - `EMBEDDING_PROVIDER=openai`
  - `OPENAI_API_KEY=sk-...`
  - `OPENAI_EMBEDDING_MODEL=text-embedding-3-large` (default 3072 dims)
  - `OPENAI_BASE_URL=...` (Azureや互換エンドポイント利用時のみ)
- Config is in `app/core/config.py`. You can override via `.env`.
