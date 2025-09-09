# Repository Guidelines

## プロジェクト構成とモジュール
- Chainlit本体: `app.py`。機能は`handlers/`に分割、共通処理は`utils/`に配置。
- データと設定: `.chainlit/`（SQLite、personas、vector_stores、config）。
- デスクトップ連携: `electron/`（メイン）と`renderer/`（UI）。Electron用APIは`electron_api.py`（FastAPI/8001）。
- ドキュメントは`docs/`、検証用スクリプトは`test_scripts/`。
- 機能追加は適切なハンドラーへ。`app.py`は薄く、単一責任を徹底。

## ビルド・テスト・開発コマンド
- 依存関係: `uv pip install -r requirements.in`（または`pip install -r requirements.in`）。
- Chainlitのみ起動: `uv run chainlit run app.py --host 127.0.0.1 --port 8000`（または`python run.py`）。
- 統合開発（Electron含む）: `npm i && npm run dev`（モックモードは廃止。常に本物のAPIを使用）。
- Electronビルド: `npm run build:win|mac|linux`。
- Electron APIのみ: `uv run python electron_api.py`（ポート8001）。

## コーディング規約と命名
- Python 3.10+。Blackで整形（100桁）: `uv run black .`。
- RuffでLint: `uv run ruff check .`。MyPyで型チェック: `uv run mypy .`。
- インデント4スペース。関数・ファイルは`snake_case`、クラスは`CamelCase`。
- ハンドラーの責務を厳密化（例: コマンド→`handlers/command_handler.py`、ペルソナ→`handlers/persona_handler.py`）。
- OpenAIはResponses APIのみを使用（Chat Completionsは非使用）。UI/エラー/ログは`utils/`を優先。

## テスト方針
- 単体テストはpytest（`tests/`に`test_*.py`）: `uv run pytest -q`。
- UI/統合チェック: `python test_scripts/run_comprehensive_tests.py`（8000で起動中が前提）。
- PRには最小限のテスト計画と再現手順を含め、テストは対象モジュールの近くに配置。

## コミット/PRガイドライン
- Conventional Commitsを推奨: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`（例: `feat(handlers): add stats route`）。
- PRに含めるもの: 概要/背景、関連Issue、UI変更のスクショ、検証コマンド。
- 変更は最小限に保ち、仕様変更時はドキュメント/設定サンプルも更新。

## セキュリティと設定
- `.env.example`をコピーして`.env`を作成し、`OPENAI_API_KEY`/`CHAINLIT_AUTH_SECRET`/`DEFAULT_MODEL`を設定。
- 秘密情報や`.chainlit/chainlit.db`をコミットしない。Chainlit Actionの`payload`は必ずdict。

## エージェント作業指針
- パッチは最小限・スコープ内で。公開APIの改名は正当な理由なしに行わない。
- 新規ロジックは適切なhandler/utilに配置し、関連ドキュメントも更新。

## MCP連携（Codex向け）
- 参考設定: `/root/.claude.json` の本プロジェクトエントリにMCPサーバー定義はありません（空）。本リポジトリではChainlit側でMCPを有効化済み（`.chainlit/config.toml`）。
- 許可実行ファイル: `[features.mcp.stdio].allowed_executables = ["npx", "uvx"]`。
- 例: Filesystemサーバー起動（stdio）
  - `scripts/start_mcp_filesystem.sh` を実行（`npx @modelcontextprotocol/server-filesystem --root .` を起動）。
  - 起動後、Chainlit UIのMCP機能から利用可能。
- SSE/HTTPサーバーを使う場合は各MCPサーバーの起動方法に従い、`[features.mcp.sse]`/`[features.mcp.streamable-http]`の有効化を活用。
