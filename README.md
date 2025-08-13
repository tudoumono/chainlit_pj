# AI Workspace - Phase 5完了版

Chainlitを使用した多機能AIワークスペースアプリケーション

## 🌟 概要

OpenAI APIを活用したプロフェッショナル向けのAIチャットアプリケーションです。

### 主な特徴

- 🗣️ **リアルタイムAI対話** - GPT-4.1対応
- 💾 **完全な永続化** - SQLiteで履歴が消えない
- 🔍 **強力な検索機能** - 過去の会話を素早く発見
- 🏷️ **タグ管理** - 整理された情報管理
- 📊 **統計機能** - 使用状況の可視化
- 🔄 **セッション管理** - 複数の会話を効率的に管理

## 📦 実装状況

| Phase | タイトル | 状態 |
|-------|---------|------|
| Phase 1 | 基本環境構築 | ✅ 完了 |
| Phase 2 | 設定管理機能 | ✅ 完了 |
| Phase 3 | データベース基盤 | ✅ 完了 |
| Phase 4 | 基本的なチャット機能 | ✅ 完了 |
| Phase 5 | セッション永続化の強化 | ✅ 完了 |
| Phase 6-12 | 高度な機能 | ⏳ 今後実装 |

## 🚀 クイックスタート

### 1. 依存関係のインストール

```bash
# pipを使用
pip install -r requirements.txt

# またはuvを使用
uv pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example`をコピーして`.env`を作成し、必要な情報を設定：

```bash
cp .env.example .env
```

`.env`ファイルを編集：
```env
# OpenAI API設定
OPENAI_API_KEY=your_api_key_here
DEFAULT_MODEL=gpt-4.1-2025-04-14

# 認証設定
CHAINLIT_AUTH_TYPE=credentials
CHAINLIT_AUTH_SECRET=admin123
```

### 3. アプリケーションの起動

```bash
# Pythonスクリプトで起動
python run.py

# または直接Chainlitで起動
chainlit run app.py
```

### 4. ログイン

ブラウザで http://localhost:8000 を開き、以下でログイン：
- **ユーザー名**: admin
- **パスワード**: admin123

## 🛠️ 機能一覧

### コマンド

| コマンド | 説明 |
|---------|------|
| `/help` | ヘルプ表示 |
| `/status` | 現在の設定状態 |
| `/model [name]` | モデル変更 |
| `/system [prompt]` | システムプロンプト設定 |
| `/clear` | 新しいセッション開始 |
| `/stats` | 統計情報表示 |

## 🔧 技術スタック

- **フレームワーク**: Chainlit
- **言語モデル**: OpenAI GPT-4.1
- **データベース**: SQLite
- **認証**: Chainlit Authentication
- **言語**: Python 3.11+

## 📂 ファイル構造

```
AI_Workspace_App_Chainlit/
├── app.py                 # メインアプリケーション (v0.7.0)
├── run.py                 # 起動スクリプト
├── auth.py                # 認証ハンドラー
├── data_layer.py          # SQLiteデータレイヤー
├── utils/                 # ユーティリティモジュール
│   ├── config.py          # 設定管理
│   ├── session_handler.py # セッション管理
│   ├── response_handler.py # API通信
│   ├── responses_handler.py # Responses API対応
│   ├── tools_config.py    # Tools設定
│   └── logger.py          # ログシステム
├── .chainlit/              # Chainlit設定
│   ├── config.toml        # Chainlit設定
│   ├── chainlit.db        # SQLiteデータベース
│   └── tools_config.json  # Tools設定
├── .env                   # 環境変数
└── requirements.txt       # 依存関係
```

## 📝 ライセンス

MIT

## 👥 貢献

プルリクエストやイシューの報告を歓迎します！

## 🔄 更新履歴

- **v0.7.0** - Responses API + Tools機能対応
- **v0.6.1** - SQLite永続化実装
- **v0.5.0** - セッション管理強化
- **v0.4.0** - 基本的なチャット機能
- **v0.3.0** - データベース基盤
- **v0.2.0** - 設定管理機能
- **v0.1.0** - 初期リリース
