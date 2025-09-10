# ADR-0002: 単一ウィンドウ方式 + トップレベルでChainlitを表示

- 日付: 2025-09-10
- ステータス: 採用（設計合意）

## 背景

Electron内でChainlitをiframe表示すると、最近のCookie/SameSite/第三者Cookie制限により、認証が不安定（401）になりやすい。非エンジニア向けに分かりやすい導線も求められる。

## 決定

単一ウィンドウ方式を採用し、Chainlitはウィンドウ本体でトップレベル表示（BrowserWindow.loadURL）する。設定画面（自前UI）とチャット（Chainlit）の切替は同一ウィンドウで行う。

## 目的

- 認証安定化（第一者Cookie）
- 導線の簡素化（単一ウィンドウ内の切替）
- iframe依存の低減（CSP/フラグ調整の最小化）

## 実装方針（概要）

- 起動: 子プロセス（Chainlit 8000 / Electron API 8001）をspawn→ヘルス待ち→設定画面をloadFile
- チャットへ: IPC `open-chat` で loadURL(`http://localhost:<CHAINLIT_PORT>`) に遷移
- 設定へ: IPC `return-to-settings` で設定画面に戻す（loadFile）。必要に応じてサーバ維持/停止を選択
- 終了: `before-quit`/`window-all-closed`で子プロセスの確実停止（SIGTERM、二重化）

## 影響

- iframe前提のCSPやCookie緩和は基本不要化（将来のCSP強化が容易）
- 設定とチャットの同時表示は不可（切替UXで解決）。必要なら別ウィンドウ方式は別ADRで検討
- ログ運用、.env、Windows配布（埋め込みPython）は現行方針を踏襲

## 検証観点（Phase 1）

- 起動→設定画面→「チャットを開始」→Electron内でログイン成功
- 「設定に戻る」で復帰
- 終了で8000/8001が解放
- Log/ に main/childログが出力

## 代替案

- 別ウィンドウ方式（管理UIとチャットを分離）
- 同一オリジン配信（rendererをローカルHTTPで提供しiframeでも第一者化）

