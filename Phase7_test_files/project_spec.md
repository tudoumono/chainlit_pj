# AI Workspace プロジェクト仕様書

## 概要
AI Workspaceは、OpenAI APIを活用した多機能AIアシスタントアプリケーションです。

## 主要機能

### 1. チャット機能
- リアルタイムストリーミング応答
- 会話履歴の永続化
- セッション管理

### 2. ペルソナ管理
- 複数のAIペルソナを定義
- 用途別の最適化
- カスタムシステムプロンプト

### 3. ベクトルストア（ナレッジベース）
- ファイルアップロード機能
- 文書の埋め込み処理
- セマンティック検索

## 技術スタック
- Python 3.11
- Chainlit
- OpenAI API
- SQLite

## アーキテクチャ

### データレイヤー
- SQLiteによる永続化
- 非同期処理対応
- トランザクション管理

### APIレイヤー
- OpenAI Responses API
- Embeddings API
- Vector Store API

### UIレイヤー
- Chainlit フレームワーク
- リアルタイムメッセージング
- ファイルアップロード対応

## 今後の展開
- Phase 8: 3階層ベクトルストア
- Phase 9: マルチモーダル入力
- Phase 10: Agents SDK
