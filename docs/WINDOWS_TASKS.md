# Windows専用 作業リストと手順

Windows 環境でのみ実施する必要がある作業をリストアップし、手順を記載します。

## 1) `python_dist/` の作成（Windows）
- 管理者権限は不要です。PowerShell を開き、以下を実行します:
  - `pwsh -ExecutionPolicy Bypass -File ./scripts/build_python_dist.ps1`
- スクリプトの内容（自動化されます）
  - Python 埋め込み ZIP（3.10+）をダウンロードし `python_dist/` に展開
  - `pythonXX._pth` を編集して `import site` を有効化
  - embeddable には `ensurepip/pip` が無いため、公式 `pip.pyz` を取得して `Lib/site-packages` に `pip/setuptools/wheel` をブートストラップ
  - その後、最小依存（chainlit, fastapi, uvicorn, openai, python-dotenv, tenacity など）をインストール
    - pip は `--no-cache-dir --no-compile --prefer-binary --only-binary=:all:` で実行
    - インストール後に `pip/setuptools/wheel`, `tests/`, `testing/`, `__pycache__/`, `*.pyc` を削除（容量削減）

## 2) electron-builder でパッケージ（Windows / portable 配布）
- `npm run build:portable`
- 生成物は `dist/` に出力されます（portable EXE と ZIP）
- `.chainlit` は `config.toml` と `personas/` のみ同梱（SQLite/ベクトルDBは実行時に生成/クラウド）
- 実行時のデータ（`.env`, `.chainlit/chainlit.db`）は「EXEと同じディレクトリ」に作成されます。
  - 配置先に書き込み権限が必要です。
  - `Program Files` 直下など、管理者権限が必要なフォルダは避けてください。

## 3) パッケージのスモークテスト
- アプリを起動
- `.env` に設定したポート（`CHAINLIT_PORT`, `ELECTRON_API_PORT`）でアクセスできること
- `<UserData>/logs` にログが出力され、UI → 設定 → システムログ で表示できること
  - 失敗時は `startup_diagnostics.txt`（同フォルダ）に診断情報が出力されます

## 5) CI（GitHub Actions）について
- 本リポジトリの Windows ビルドは「手動実行（workflow_dispatch）」のみ有効です。push で自動実行されません。
- 必要に応じて Actions の “Windows Build” を手動実行してください。

## 4) オプション: コードサイニング
- electron-builder の署名設定（社内検証では必須ではありません）
- 必要に応じて証明書/シークレットを GitHub Actions またはローカル環境に設定
