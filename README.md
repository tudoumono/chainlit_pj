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
- 📁 **ベクトルストア管理** - ナレッジベースの構築と管理
- 🎭 **ペルソナ機能** - カスタマイズ可能なAIアシスタント

## 📦 実装状況

| Phase | タイトル | 状態 |
|-------|---------|------|
| Phase 1 | 基本環境構築 | ✅ 完了 |
| Phase 2 | 設定管理機能 | ✅ 完了 |
| Phase 3 | データベース基盤 | ✅ 完了 |
| Phase 4 | 基本的なチャット機能 | ✅ 完了 |
| Phase 5 | セッション永続化の強化 | ✅ 完了 |
| Phase 6 | ペルソナ管理 | ✅ 完了 |
| Phase 7 | ベクトルストア | ✅ 完了 |
| Phase 8-12 | 高度な機能 | ⏳ 今後実装 |

## ⚠️ 重要な注意事項

### OpenAI beta.vector_stores APIの廃止について

**2025年8月20日現在、OpenAIの`beta.vector_stores` APIは廃止予定（deprecated）です。**

- 参考: [GitHub Issue #2451](https://github.com/openai/openai-python/issues/2451)
- 参考: [公式移行ガイド](https://platform.openai.com/docs/guides/migrate-to-responses)

#### 対応状況
- ✅ 現在のコードには**フォールバック処理が実装済み**
- ✅ APIエラー時は自動的にローカルJSON管理に切り替わる
- ✅ 完全ローカル管理版（`vector_store_handler_v2.py`）も作成済み

詳細は[ベクトルストアAPI移行ガイド](docs/VECTOR_STORE_MIGRATION.md)を参照してください。

### Chainlit Action APIについて

**ChainlitのAction APIでは、`payload`パラメータは必ず辞書型（dict）である必要があります。**

```python
# ❌ 間違い
cl.Action(name="action", payload="yes", label="はい")  # エラー

# ✅ 正しい
cl.Action(name="action", payload={"action": "yes"}, label="はい")
```

詳細は[Chainlit Action APIガイド](docs/CHAINLIT_ACTION_GUIDE.md)を参照してください。

ヘルパー関数を使用することを推奨します：
```python
from utils.action_helper import ask_confirmation, ask_choice

# 確認ダイアログ
if await ask_confirmation("削除してもよろしいですか？"):
    # 削除処理
    pass
```

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

### ベクトルストア管理

#### 設定ウィジェット
- **ベクトルストアID**: 使用するベクトルストアのIDをカンマ区切りで入力
  - 例: `vs_xxxxx, vs_yyyyy`
  - AIが指定されたベクトルストアの内容を参照して回答します

#### ベクトルストアコマンド
| コマンド | 説明 |
|---------|------|
| `/vs` または `/vector` | ベクトルストア一覧を表示 |
| `/vs create [名前]` | 新しいベクトルストアを作成 |
| `/vs list` | ベクトルストア一覧を表示 |
| `/vs info [ID]` | 詳細情報を表示 |
| `/vs files [ID]` | ファイル一覧を表示 |
| `/vs use [ID]` | ベクトルストアを使用 |
| `/vs rename [ID] [新しい名前]` | ベクトルストアの名前を変更 |
| `/vs delete [ID]` | ベクトルストアを削除 |

#### ファイルアップロード
- ファイルをドラッグ&ドロップまたはクリップボタンから選択
- アップロードされたファイルはOpenAIに保存されます
- ベクトルストアに追加してAIが内容を参照できるようにするには、コマンドで操作してください

### コマンド

| コマンド | 説明 |
|---------|------|
| `/help` | ヘルプ表示 |
| `/stats` | 統計情報表示 |
| `/status` | 現在の設定状態 |
| `/setkey [APIキー]` | OpenAI APIキーを設定 |
| `/test` | API接続をテスト |
| `/tools` | Tools機能の状態表示 |
| `/persona` | ペルソナ管理 |
| `/persona create` | 新しいペルソナを作成 |
| `/kb` | ナレッジベース状態表示 |

💡 **ヒント**: モデル変更、システムプロンプト、Temperature調整などの設定は画面右上の設定パネルから行えます。

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
│   ├── persona_manager.py # ペルソナ管理
│   ├── vector_store_handler.py # ベクトルストア管理
│   ├── action_helper.py   # Actionヘルパー
│   └── logger.py          # ログシステム
├── .chainlit/              # Chainlit設定
│   ├── config.toml        # Chainlit設定
│   ├── chainlit.db        # SQLiteデータベース
│   ├── tools_config.json  # Tools設定
│   ├── personas.json      # ペルソナデータ
│   └── vector_stores/     # ベクトルストア管理
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
