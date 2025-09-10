# Windows パッケージングガイド（Option B）

本書は、埋め込み Python（`python_dist/`）と Electron を用いた Windows 向け配布物の作成手順をまとめたものです。

重要: Windows 固有の作業は、Windows マシン上でリポジトリをクローンしてから実施してください。

## 概要
- Python バックエンドは Electron Main から spawn されます。
- ポートは `.env` で設定可能です（`CHAINLIT_PORT` 既定 8000、`ELECTRON_API_PORT` 既定 8001）。
- ログは `<UserData>/logs` に保存され、UI から閲覧できます。

## 前提条件（Windows）
- Node.js 18 以上（x64）
- Python 3.10 以上（開発用）。配布では埋め込みパッケージを使用
- Git、7-Zip または PowerShell（アーカイブ展開用）

## 手順
1. リポジトリの取得
   - `git clone <your repo>`
   - `cd chainlit_pj`
2. 依存関係のインストール（開発）
   - `npm i`
   - `uv pip install -r requirements.in`（または `pip install -r requirements.in`）
3. `.env` の準備
   - `.env.example` を `.env` にコピー
   - `OPENAI_API_KEY`、`CHAINLIT_AUTH_SECRET`、`DEFAULT_MODEL` を設定
   - 必要に応じて `CHAINLIT_PORT`、`ELECTRON_API_PORT` も調整
4. `python_dist/` の作成（埋め込み Python）
   - PowerShell で `scripts/build_python_dist.ps1` を実行
   - `python_dist/` に `python.exe` と必要な site-packages が配置されます
5. パッケージ作成
   - `npm run build:win`（electron-builder）
   - 生成物は `dist/` に出力されます

## 検証項目
- パッケージ実行時に以下を確認:
  - 初回起動で `<UserData>/.env` が生成（未存在の場合）
  - 設定タブが表示され、「チャットを開始」でトップレベルに Chainlit 表示
  - 「ログフォルダを開く」「システムログ」でログが確認できる
  - ヘルスチェックで両サーバー（Chainlit/Electron API）が healthy

## トラブルシュート
- ポート競合 → `.env` のポートを変更して再試行
- 依存不足 → `uv pip install -r requirements.in` を実行して再パッケージ
- OpenAI エラー → API キーと既定モデルを確認
