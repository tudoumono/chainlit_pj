# AI Workspace - Chainlit公式機能版

多機能AIワークスペースアプリケーション - Chainlitの公式データ永続化機能を使用

## ✨ 特徴

- 🔐 **認証システム** - ユーザー名/パスワードによる保護
- 📚 **自動履歴管理** - Chainlit組み込みの履歴機能
- 🤖 **OpenAI統合** - GPT-4oなど各種モデルに対応
- 💬 **ストリーミング応答** - リアルタイムでAIの応答を表示
- 🎨 **シンプルなUI** - 使いやすいインターフェース

## 📋 必要要件

- Python 3.8以上
- OpenAI APIキー

## 🚀 クイックスタート

### 1. インストール

```bash
# リポジトリをクローン
git clone [repository-url]
cd AI_Workspace_App_Chainlit

# 依存関係をインストール
pip install -r requirements.in
```

### 2. 環境設定

`.env` ファイルを作成して設定：

```env
# OpenAI API設定
OPENAI_API_KEY=sk-your-api-key-here

# 認証設定
CHAINLIT_AUTH_TYPE="credentials"
CHAINLIT_AUTH_SECRET="your-password-here"

# デフォルトモデル
DEFAULT_MODEL=gpt-4o-mini
```

### 3. 起動

```bash
# Pythonスクリプトで起動
python run.py

# または直接Chainlitで起動
chainlit run app.py
```

### 4. ログイン

ブラウザで `http://localhost:8000` を開き、ログイン：

- **ユーザー名**: `admin`
- **パスワード**: `.env`で設定した値（デフォルト: `admin123`）

## 💡 使い方

### 基本的な会話

1. メッセージを入力して送信
2. AIからの応答を待つ
3. 会話は自動的に保存される

### 履歴機能

- **履歴を見る**: 左上の履歴ボタンをクリック
- **過去の会話を再開**: 履歴リストから選択

### コマンド

| コマンド | 説明 | 例 |
|---------|------|-----|
| `/help` | ヘルプを表示 | `/help` |
| `/model` | モデルを変更 | `/model gpt-4o` |
| `/system` | システムプロンプトを設定 | `/system あなたは親切なアシスタントです` |
| `/stats` | 統計情報を表示 | `/stats` |
| `/clear` | 新しい会話を開始 | `/clear` |
| `/setkey` | APIキーを設定 | `/setkey sk-xxxxx` |
| `/test` | 接続テスト | `/test` |
| `/status` | 現在の設定を表示 | `/status` |

## 📁 プロジェクト構造

```
AI_Workspace_App_Chainlit/
├── app.py              # メインアプリケーション
├── auth.py             # 認証設定
├── run.py              # 起動スクリプト
├── .env                # 環境変数
├── .chainlit/
│   ├── config.toml     # Chainlit設定
│   └── data/          # 履歴データ（自動生成）
├── utils/
│   ├── config.py       # 設定管理
│   └── response_handler.py  # OpenAI API処理
└── requirements.in     # 依存関係
```

## 🔧 設定のカスタマイズ

### パスワードの変更

`.env` ファイルを編集：

```env
CHAINLIT_AUTH_SECRET="new-password-here"
```

### 認証を無効にする

認証が不要な場合、`.env` から以下を削除：

```env
# CHAINLIT_AUTH_TYPE="credentials"
# CHAINLIT_AUTH_SECRET="admin123"
```

### モデルの変更

`.env` ファイルでデフォルトモデルを設定：

```env
DEFAULT_MODEL=gpt-4o
```

または会話中にコマンドで変更：

```
/model gpt-3.5-turbo
```

## 🐛 トラブルシューティング

### ログインできない

1. `.env` ファイルのパスワードを確認
2. ユーザー名は `admin` を使用
3. ブラウザのキャッシュをクリア

### 履歴が表示されない

1. `.chainlit/config.toml` で設定を確認
2. ブラウザをリロード
3. 新しい会話を開始してテスト

### APIエラー

1. OpenAI APIキーを確認
2. `/test` コマンドで接続テスト
3. `/setkey` コマンドでAPIキーを再設定

## 📚 ドキュメント

- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - 移行ガイド
- [Chainlit公式ドキュメント](https://docs.chainlit.io)
- [OpenAI APIドキュメント](https://platform.openai.com/docs)

## 🔄 バージョン履歴

- **v0.5.2** - Chainlit公式機能版
  - 公式の履歴管理機能を採用
  - 認証システムの実装
  - コードの大幅な簡略化

- **v0.5.1** - Phase 5改善版
  - セッション管理の修正
  - サイドバー機能の追加

- **v0.5.0** - Phase 5初期版
  - カスタムセッション管理
  - SQLiteデータベース使用

## 📝 ライセンス

MIT License

## 🤝 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。

## 📧 サポート

問題が発生した場合は、GitHubのissueセクションで報告してください。
