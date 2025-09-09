# フォルダ構成（Option B; Electron Main が埋め込みPythonを直接起動）

本構成は exe 配布を前提に、Electron 側（デスクトップ）と Chainlit 側（Python）を明確に分離しつつ、共通の .env を参照する。

## 概要
- デスクトップ（Electron）: `electron/`, `renderer/`, `package.json`, `build/`
- バックエンド（Python / Chainlit）: `app.py`, `handlers/`, `utils/`, `electron_api.py`, `.chainlit/`（設定・DB）
- 共有設定: ルート `.env`（開発時）/ ユーザーデータ配下 `.env`（配布時）

## 物理構成（現行）
```
root/
├─ electron/            # Electron Main / Preload
├─ renderer/            # Renderer(UI)
├─ app.py               # Chainlit entry
├─ electron_api.py      # FastAPI (Electron API)
├─ handlers/, utils/    # Python modules
├─ .chainlit/           # Chainlit config/SQLite/personas/vector_stores
├─ .env, .env.example   # 環境変数（開発用はルート）
└─ package.json, build/ # Electronビルド構成
```

## 配布時の参照先
- `.env`: 初回起動時に `<userData>/.env` を作成（存在しない場合は `resources/.env` または `resources/.env.example` からコピー）。以降は同ファイルを Electron / Python 双方で参照。
- `CHAINLIT_CONFIG_PATH`: `<resources>/.chainlit/config.toml` を指すように Electron Main から環境変数で指定（起動時に設定）。

## 開発時の参照先
- `.env`: リポジトリ直下の `.env`
- `CHAINLIT_CONFIG_PATH`: 省略可（`.chainlit/config.toml` を自動参照）

## 実装メモ
- Electron Main で `.env` を `<userData>` に用意するロジックを実装済（electron/main.js 内 `ensureUserEnvFile()`）。
- electron-builder で `.env.example` を `resources` に同梱済（package.json の build.files を更新）。
- IPC で `get-system-info` から `dotenvPath` を返却（UI表示や診断用）。

## 将来のディレクトリ再編（任意）
- `desktop/` 以下に `electron/` と `renderer/` を移動
- `backend/` 以下に Python モジュールを移動
- スクリプト/インポート/ビルド設定の参照パスを順次更新

現段階では互換性優先のため物理移動は行わず、配布時の参照先と .env 運用を統一した。
