# フロントエンド（Next.js・任意）

本リポジトリの FastAPI バックエンドと連携する、任意利用の React/Next.js UI です。簡易UI（`/ui/`）だけでも動作しますが、よりリッチな表示や開発体験が必要な場合git にご利用ください。

## 前提条件
- Node.js 18+
- バックエンドが `http://127.0.0.1:8000` で起動済み
- バックエンドの CORS に `http://localhost:3000` を含める（`.env` の `CORS_ORIGINS`）

## セットアップ

```
cd frontend
npm install
npm run dev
```

ブラウザで `http://localhost:3000` を開きます。

## 主な機能
- テキストから当初予算を推定し、見やすく表示
- 類似事業カードを相対スコアバー付きで表示
- バックエンド API と連携して事業メタ・予測結果を取得

## 参照API
- `POST /v1/budget/predict`
- `GET /v1/events/ids`
- `GET /v1/events/meta?budget_id=...`

## 備考
- プロダクション用途では環境変数や API ベースURLの切替を `.env.local` などで管理してください。
- バックエンドの簡易UI（`/ui/`）は依然として利用可能です。まずはバックエンドのみで確認し、必要に応じて本UIを起動してください。
