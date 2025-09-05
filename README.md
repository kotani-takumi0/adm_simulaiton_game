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
  - `embeddings.npz` with arrays `X1`, `X2` (optional), `y_init`, `y_final` (optional)
  - `events.parquet` or `events.csv` for metadata
- Config is in `app/core/config.py`. You can override via `.env`.
