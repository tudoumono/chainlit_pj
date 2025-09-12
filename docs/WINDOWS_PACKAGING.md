# Windows パッケージングガイド（Option B）

本書は、埋め込み Python（`python_dist/`）と Electron を用いた Windows 向け配布物の作成手順をまとめたものです。

重要: Windows 固有の作業は、Windows マシン上でリポジトリをクローンしてから実施してください。

## Quick Steps（再ビルド用）
- PowerShell を管理者不要で実行:
  - `pwsh -ExecutionPolicy Bypass -File scripts/build_python_dist.ps1`
- パッケージ生成（portable EXE + ZIP）:
  - `npm run build:portable`
- 起動失敗時のログ/診断:
  - ログ: `<UserData>/logs`（`main.log`, `chainlit.err.log`, `electron-api.err.log`）
  - 診断: `<UserData>/logs/startup_diagnostics.txt`

## 概要
- Python バックエンドは Electron Main から spawn されます。
- ポートは `.env` で設定可能です（`CHAINLIT_PORT` 既定 8000、`ELECTRON_API_PORT` 既定 8001）。
- ログは `<UserData>/logs` に保存され、UI から閲覧できます。
- 履歴DB（SQLite）と `.env` は「EXEと同じディレクトリ」に作成されます（初回起動時にテンプレをコピーします）。

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
4. `python_dist/` の作成（埋め込み Python・軽量化対応）
   - PowerShell で `scripts/build_python_dist.ps1` を実行
   - スクリプトは以下の最適化を自動実行します:
     - embeddable には `ensurepip/pip` が無いため、公式 `pip.pyz` を使って `pip/setuptools/wheel` を `Lib/site-packages` にブートストラップ
     - pip を `--no-cache-dir --no-compile --prefer-binary --only-binary=:all:` で実行（ビルド時キャッシュ/pycを生成しない）
     - 可能な限り wheel を採用（`--only-binary=:all:`）
     - `pip/setuptools/wheel` 本体および関連 `*.dist-info` を削除（実行時に不要）
     - `tests/`, `testing/`, `__pycache__/`, `*.pyc` を削除
   - `python_dist/` に `python.exe` と必要最小の site-packages が配置されます
5. パッケージ作成（軽量化設定込み）
   - `npm run build:portable`（portable EXE + ZIPを生成）
   - 本プロジェクトの `package.json` は以下を設定済み:
     - `asar: true`（JS リソースを asar で圧縮）
     - `asarUnpack` に `python_dist/**`, `python-backend/**`（Python 実行には展開が必要）
     - `.chainlit` は `config.toml` と `personas/` のみ同梱（SQLite や `vector_stores` は同梱しない）
     - `__pycache__` と `*.pyc` は同梱対象から除外
   - 生成物は `dist/` に出力されます（例: `...portable.exe` / `...-win.zip`）

注意: EXEと同じディレクトリにデータを書き込むため、配置先に書き込み権限が必要です。`Program Files` 直下は避け、ユーザーの書き込み可能なフォルダ（デスクトップ/ドキュメント配下など）でZIPを展開してください。

## 検証項目
- パッケージ実行時に以下を確認:
  - 初回起動で `EXE と同じディレクトリ` に `.env` が生成（未存在の場合）
  - 設定タブが表示され、「チャットを開始」でトップレベルに Chainlit 表示
  - 「ログフォルダを開く」「システムログ」でログが確認できる
  - ヘルスチェックで両サーバー（Chainlit/Electron API）が healthy

## トラブルシュート
- ポート競合 → `.env` のポートを変更して再試行
- 依存不足 → `uv pip install -r requirements.in` を実行して再パッケージ
- OpenAI エラー → API キーと既定モデルを確認
 - Chainlit が pyc を生成してしまう → パッケージでは `PYTHONDONTWRITEBYTECODE=1` を設定済み（Electron から環境変数注入）。
 - 「Failed to start Python servers」 → `<UserData>/logs/startup_diagnostics.txt` と `chainlit.err.log`/`electron-api.err.log` を確認

## 補足: アイコンと署名
- `build/icon.ico` が無い場合は Electron 既定アイコンになります（ログに警告が出ますが問題ありません）。
- Portable/ZIP ではコードサイニングは任意です。必要に応じて `win.cscLink` などの設定を追加してください。
