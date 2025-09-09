# ADR-0001: Electron起動方式の選定（埋め込みPythonをElectron Mainから直接spawn）

- 日付: 2025-09-09
- ステータス: 提案 → 採用
- 対象: デスクトップ配布（exe化）時の起動方式

## 背景（Context）
本プロジェクトは非エンジニアへの配布（exe化）を前提とし、アプリ起動時に下記2つのPythonプロセスを立ち上げる必要がある。
- Chainlit サーバー（ポート 8000）
- Electron API（FastAPI、ポート 8001）

現状は Electron Main から `integrated_run.py` を spawn し、その中で両サーバーを起動している。
将来的に配布物へ埋め込みPython（スタンドアロン版）を同梱する方針であり、起動・終了・ログ・環境変数の管理を一元化したい。

## 選択肢（Options）

- A: これまで通り Python の統合起動スクリプト（`integrated_run.py`）を Main から spawn し、その中で Chainlit と Electron API を並行起動する。
- B: Electron の `main.js` が埋め込みPython（配布物に同梱）を直接 `spawn` し、Chainlit と Electron API を個別に起動・監視・終了する。

## 決定（Decision）
選択肢 B を採用する。Electron の Main プロセスが、開発時は `uv` を用い、配布時は同梱の埋め込みPythonを用いて、Chainlit と Electron API を直接起動する。

## 理由（Rationale）
- 依存の明確化と配布容易性: 配布時に `uv` 等の外部依存を排除し、同梱の埋め込みPythonと site-packages のみで完結させられる。
- 運用の一元化: 起動・停止・再起動・ヘルスチェック・ログ出力の流れを Electron Main で統一管理できる。
- エラーハンドリングの簡素化: `ipcMain.handle` と Renderer 側の待機（ヘルスチェック）を直結し、ユーザー通知までの経路を最短化できる。
- 将来の拡張容易性: 起動順制御、リトライ、環境変数の切替、OS別分岐（PATH区切り文字等）を Main 側で集約。

## 選択肢Aを選ばない理由
- 二重管理の複雑化: Main と `integrated_run.py` の双方に起動ロジックが分散し、障害時の切り分けや再起動制御が複雑。
- 配布時の外部依存が残る: `uv` 等の実行環境が必要になる可能性があり、非エンジニア配布に不向き。
- ログ/設定の責務が曖昧: どの層で `.env` やログディレクトリ、`CHAINLIT_CONFIG_PATH` を最終決定するかが不明瞭になりやすい。

## 実装概要（Implementation Outline）
- Electron `main.js`
  - IPC: `start-chainlit`, `start-electron-api`, `stop-*`（冪等）を追加。
  - 開発時（dev）:
    - Chainlit: `uv run chainlit run app.py --host 127.0.0.1 --port 8000`
    - API: `uv run python electron_api.py`
  - 配布時（packaged）:
    - 埋め込みPython（例: `resources/python_dist/python(.exe)`）を `spawn`。
    - Chainlit: `PY_EMBED -m chainlit run app.py --host 127.0.0.1 --port 8000`
    - API: `PY_EMBED electron_api.py`
  - 環境変数:
    - `PYTHONHOME`, `PYTHONPATH`, `PATH`（`path.delimiter` を使用）
    - `CHAINLIT_CONFIG_PATH`（`<resources>/.chainlit/config.toml`）
    - `EXE_DIR`, `CHAT_LOG_DIR`, `CONSOLE_LOG_DIR`（`app.getPath('userData')` 等）
  - 終了処理: `before-quit` で `SIGTERM` を送信し、子プロセスを安全に停止。
- `preload.js`: `electronAPI.app.startChainlit()` / `startElectronAPI()` を `contextBridge` で公開。
- Renderer: 初期化時に `start-*` を呼び、既存のヘルスチェック（HTTP 200）で待機 → UI を表示。

## 影響（Consequences）
- 良い点
  - 配布一体化（exe + 埋め込みPython）の整合性が高まる。
  - ログ/設定/ポート監視の責務が明確化。
  - 起動・停止のUXをElectron側で最適化可能。
- 留意点
  - `electron-builder` の `extraResources` に `python_dist`（埋め込みPython + site-packages）が必須。
  - Windows/Mac/Linux でのパス差異（`path.delimiter`、`.exe` 有無）に対応。
  - `.env` コピーは「必要な場合のみ」。優先は `CHAINLIT_CONFIG_PATH`。

## マイグレーション計画（Migration Plan）
1. ドキュメント整備（本ADR、ガイド、README反映）。
2. Electron `main.js` に `start-*` IPC を追加（コード変更）。
3. `preload.js` と Renderer 初期化で `start-*` を呼ぶように更新。
4. `electron-builder` で `python_dist` を同梱（OS別バイナリと必要パッケージ）。
5. スモークテスト（dev と packaged の両方）を実施。
6. 旧 `integrated_run.py` への依存を段階的に縮小・撤去（最終段）。

## テスト（Testing）
- dev: `npm run dev` → 起動後、`/api/health` と Chainlit ルートの疎通確認。
- packaged: ビルド成果物で起動し、Chainlit/Electron API 双方のヘルスチェックと終了処理を確認。

## セキュリティ
- CSPの強化（`unsafe-inline` 排除、接続先の最小化）を段階的に実施。
- `payload` は常に dict（Chainlit Action仕様の遵守）。
- 秘密情報は `.env`/環境変数で管理し、リポジトリにコミットしない。

