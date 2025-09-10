# Windows 配布パッケージング手順（Option B）

この手順は Windows 配布（.exe）専用です。Electron Main が埋め込みPythonを直接 spawn し、Chainlit(8000) と Electron API(8001) を起動します。

## 前提
- Node.js/NPM が導入済み
- Electron Builder が devDependencies に含まれている（package.json 済）
- Python ランタイムと必要パッケージを同梱（`python_dist/`）

## フォルダ構成（抜粋）
```
project_root/
├─ electron/
├─ renderer/
├─ app.py, electron_api.py, handlers/, utils/, .chainlit/
├─ python_dist/                 # 同梱する埋め込みPython
│  ├─ python.exe
│  ├─ python3.dll 等（Python配布物に同梱）
│  └─ Lib\site-packages\       # 依存パッケージ（Chainlit, FastAPI, Uvicorn, OpenAI等）
├─ .env.example                 # 初期テンプレート（リソースに同梱）
└─ package.json
```

推奨 site-packages（例）
- chainlit
- fastapi
- uvicorn
- pydantic
- openai（Responses API）
- httpx / aiohttp（必要に応じて）
- python-dotenv（DOTENV_PATHの読取りに使う場合）

## Electron Main の動作（Windows）
- 埋め込みPythonパス: `resources/python_dist/python.exe`
- 環境変数（spawn時）
  - `PYTHONHOME`: `resources/python_dist`
  - `PYTHONPATH`: `resources/python_dist/Lib/site-packages`
  - `PATH`: `PYTHONHOME;既存PATH`
  - `CHAINLIT_CONFIG_PATH`: `resources/.chainlit/config.toml`
  - `DOTENV_PATH`: `<userData>/.env`（初回起動時に自動作成）

## .env の扱い
- 初回起動時に Electron が `<userData>/.env` を生成
  - 優先して `resources/.env.example` をコピー（存在しない場合はビルトインのサンプルテンプレートを生成）
- 以降はユーザーが `<userData>/.env` を編集して設定を変更

## ビルド
```bash
# 依存インストール
npm i

# Windows用パッケージを作成
npm run build:win
```

出力物
- `dist/Chainlit AI Workspace-<version>-windows-x64.exe`（NSIS）
- `dist/Chainlit AI Workspace-<version>-windows-x64.portable.exe`（Portable）

## テスト項目
- 起動後に Chainlit(8000) と Electron API(8001) が起動し、UIが表示されること
- `<userData>/.env` が生成され、編集が反映されること
- ログはアプリのワーキングフォルダ直下の `Log/` に出力されること（なければ自動作成）
- 終了時に子プロセス（Chainlit/Electron API）が確実に終了すること
- ログ、CSP等のセキュリティ設定が意図通りであること

## トラブルシュート
- ポート競合: 8000/8001 を占有するプロセスがないか確認
- 埋め込みPythonに依存が不足: `Lib\site-packages` の内容を再確認
- 環境変数: `CHAINLIT_CONFIG_PATH` と `DOTENV_PATH` が正しく設定されているか確認
