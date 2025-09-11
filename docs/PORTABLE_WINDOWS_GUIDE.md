---
title: Chainlit AI Workspace — Windows配布手順（Portable版・一枚まとめ）
---

# Chainlit AI Workspace — Windows配布手順（Portable版・一枚まとめ）

対象: Windows 10 / 11（x64） / 非エンジニア配布想定

## 1) 受け取りと展開
- 受け取ったZIP（例: `Chainlit AI Workspace-<version>-windows-x64.zip`）を、書き込み可能なフォルダに展開します。
  - 例: デスクトップ / ドキュメント / ダウンロード配下など
  - 注意: `C:\\Program Files` 直下は不可（書き込み権限が無いため）

## 2) 起動
- 展開フォルダ直下の `Chainlit AI Workspace.exe` をダブルクリック。
- 初回起動時、同じフォルダに以下が自動作成されます:
  - `.env`（設定ファイル）
  - `.chainlit/`（データフォルダ。`chainlit.db` に履歴が保存）

## 3) 初期設定（必須）
- `.env` をテキストエディタで開き、以下を設定します。
  - `OPENAI_API_KEY`：OpenAIのAPIキー
  - `DEFAULT_MODEL`：例 `gpt-4o-mini`
  - 必要に応じてポート等（`CHAINLIT_PORT`, `ELECTRON_API_PORT`）を変更

## 4) 使い方
- 起動後、設定タブからAPIキー等を確認できます。
- チャット履歴は `.chainlit/chainlit.db` に自動保存されます。

## 5) アップデート
- 新しいZIPを同じ場所に展開（上書き）するだけでOK。
- `.env` と `.chainlit/` は残るので、設定・履歴は維持されます。

## 6) トラブルシュート
- SmartScreen 警告が出る: 「詳細情報」→「実行」を選択してください。
- 「書き込みできません」エラー: 別の書き込み可能なフォルダ（デスクトップ等）へ移動してから再実行。
- ポート競合: `.env` の `CHAINLIT_PORT` / `ELECTRON_API_PORT` を変更して再起動。
- 履歴が残らない: フォルダに書き込み権限があるか、`.chainlit/` が作成されているか確認。

## 7) 管理者/配布担当向け（ビルド）
- portable/zip 生成: `npm run build:portable`
- 生成物: `dist/` に portable EXE と ZIP が出力
- 詳細: `docs/WINDOWS_PACKAGING.md` / `docs/WINDOWS_TASKS.md`

（PDF化の方法）このMarkdownをブラウザ拡張や社内ツールでPDF出力するか、同梱のHTML版 `docs/PORTABLE_WINDOWS_GUIDE.html` をブラウザで開いて「印刷→PDF」で保存してください。

