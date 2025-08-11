"""
Phase 5 (公式機能版 + 組み込みSQLAlchemyデータレイヤー): Chainlitの履歴管理
- Chainlitに組み込まれているSQLAlchemyDataLayerを使用
- 認証機能による保護
- 自動的な履歴管理
"""

import chainlit as cl
from chainlit.types import ThreadDict
from dotenv import load_dotenv
import os
import auth  # 認証設定をインポート
from typing import Optional, Dict, List
from datetime import datetime
import json

# データレイヤーをインポート（複数の方法を試す）
data_layer_type = None
try:
    # 方法1: Chainlit組み込みのSQLAlchemyDataLayerを使用（推奨）
    import chainlit.data as cl_data
    from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
    
    # SQLiteを使用（簡単なセットアップ）
    # 注: SQLiteには完全な対応がない可能性があるため、インメモリ版にフォールバック
    try:
        cl_data._data_layer = SQLAlchemyDataLayer(
            conninfo="sqlite+aiosqlite:///.chainlit/chainlit.db"
        )
        data_layer_type = "SQLAlchemy (SQLite)"
        print("✅ SQLAlchemyデータレイヤー（SQLite）を使用")
    except Exception as e:
        print(f"⚠️ SQLite接続エラー: {e}")
        # PostgreSQL接続文字列の例（実際に使用する場合は環境変数から読み込む）
        # conninfo = "postgresql+asyncpg://user:password@localhost/dbname"
        raise
        
except (ImportError, Exception) as e:
    print(f"⚠️ SQLAlchemyDataLayerのエラー: {e}")
    try:
        # 方法2: シンプルなインメモリデータレイヤーを使用
        import simple_data_layer
        data_layer_type = "Simple In-Memory"
        print("✅ シンプルなインメモリデータレイヤーを使用")
    except ImportError:
        print("⚠️ データレイヤーが設定されていません")
        print("📝 simple_data_layer.pyを確認してください")

# utils モジュールをインポート（設定管理とAPI呼び出しのみ使用）
from utils.config import config_manager
from utils.response_handler import response_handler

# .envファイルの読み込み
load_dotenv()

# アプリケーション設定
APP_NAME = "AI Workspace"
VERSION = "0.5.4 (Built-in SQLAlchemy)"


@cl.on_chat_start
async def on_chat_start():
    """
    新しいチャットセッション開始時の処理
    """
    # 設定を読み込み
    settings = config_manager.get_all_settings()
    cl.user_session.set("settings", settings)
    cl.user_session.set("system_prompt", "")
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    
    # APIキーの確認
    api_status = "✅ 設定済み" if settings.get("OPENAI_API_KEY") and settings["OPENAI_API_KEY"] != "your_api_key_here" else "⚠️ 未設定"
    
    welcome_message = f"""
# 🎯 {APP_NAME} へようこそ！

**Version**: {VERSION}

## 📊 現在の状態
- **APIキー**: {api_status}
- **デフォルトモデル**: {settings.get('DEFAULT_MODEL', 'gpt-4o-mini')}
- **データレイヤー**: {data_layer_type or '未設定'}

## 🔧 利用可能なコマンド
- `/help` - コマンド一覧とヘルプを表示
- `/model [モデル名]` - 使用するモデルを変更
- `/system [プロンプト]` - システムプロンプトを設定
- `/stats` - 統計情報を表示
- `/clear` - 新しい会話を開始
- `/setkey [APIキー]` - OpenAI APIキーを設定
- `/debug` - デバッグ情報を表示

💡 **ヒント**: 
- 会話は自動で保存されます
- 左上の履歴ボタンから過去の会話にアクセスできます
- データレイヤーが設定されていない場合、履歴は保存されません

## 📝 データレイヤーの状態
- **タイプ**: {data_layer_type or '❌ 未設定'}
- **永続化**: {"✅ 有効" if data_layer_type and "Memory" not in data_layer_type else "⚠️ インメモリ（再起動で消失）"}
- **認証**: {"✅ 有効" if os.getenv("CHAINLIT_AUTH_TYPE") == "credentials" else "❌ 無効"}

---
**AIと会話を始めましょう！** 何でも質問してください。
    """
    
    await cl.Message(content=welcome_message).send()
    
    # APIキーが未設定の場合は警告
    if not settings.get("OPENAI_API_KEY") or settings["OPENAI_API_KEY"] == "your_api_key_here":
        await cl.Message(
            content="⚠️ **APIキーが未設定です**\n`/setkey sk-xxxxx` コマンドで設定してください。",
            author="System"
        ).send()


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """
    ユーザーが履歴からチャットを再開した際に呼び出される
    """
    print(f"チャット再開: Thread ID = {thread['id']}")
    
    # 設定を復元
    settings = config_manager.get_all_settings()
    cl.user_session.set("settings", settings)
    cl.user_session.set("system_prompt", "")
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    
    # スレッドの情報を取得
    thread_id = thread.get('id', 'Unknown')
    created_at = thread.get('createdAt', '')
    
    # 再開メッセージ
    await cl.Message(
        content=f"""
✅ 以前の会話を再開しました

**Thread ID**: `{thread_id[:8]}...`
**作成日時**: {created_at}

会話を続けてください。
        """,
        author="System"
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    ユーザーメッセージ受信時の処理
    """
    content = message.content.strip()
    settings = cl.user_session.get("settings", {})
    
    # コマンド処理
    if content.startswith("/"):
        await handle_command(content)
        return
    
    # APIキーの確認
    if not settings.get("OPENAI_API_KEY") or settings["OPENAI_API_KEY"] == "your_api_key_here":
        await cl.Message(
            content="❌ APIキーが設定されていません。`/setkey sk-xxxxx` で設定してください。",
            author="System"
        ).send()
        return
    
    # メッセージカウントを更新
    count = cl.user_session.get("message_count", 0) + 1
    cl.user_session.set("message_count", count)
    
    # メッセージ履歴を構築（Chainlitが自動で管理）
    messages = []
    
    # システムプロンプトがあれば追加
    system_prompt = cl.user_session.get("system_prompt", "")
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # 現在のメッセージを追加
    messages.append({"role": "user", "content": content})
    
    # AIレスポンスメッセージを作成
    ai_message = cl.Message(content="")
    await ai_message.send()
    
    # ストリーミング応答を処理
    full_response = ""
    token_usage = {}
    
    try:
        # OpenAI APIを呼び出し
        async for chunk in response_handler.create_chat_completion(
            messages=messages,
            model=settings.get('DEFAULT_MODEL', 'gpt-4o-mini'),
            temperature=0.7,
            stream=True
        ):
            # エラーチェック
            if "error" in chunk:
                error_msg = f"❌ エラー: {chunk['error']}"
                ai_message = cl.Message(content=error_msg)
                await ai_message.send()
                return
            
            # ストリーミングコンテンツを処理
            if chunk.get("choices"):
                for choice in chunk["choices"]:
                    if "delta" in choice:
                        delta = choice["delta"]
                        if "content" in delta:
                            full_response += delta["content"]
                            await ai_message.stream_token(delta["content"])
            
            # トークン使用量を更新
            if "usage" in chunk:
                token_usage = chunk["usage"]
        
        # ストリーミング完了
        await ai_message.update()
        
        # トークン使用量を更新
        if token_usage:
            total_tokens = cl.user_session.get("total_tokens", 0) + token_usage.get("total_tokens", 0)
            cl.user_session.set("total_tokens", total_tokens)
    
    except Exception as e:
        error_msg = f"❌ エラーが発生しました: {str(e)}"
        await cl.Message(content=error_msg, author="System").send()
        print(f"Error in on_message: {e}")


async def handle_command(command: str):
    """
    コマンドを処理
    """
    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    if cmd == "/help":
        await show_help()
    
    elif cmd == "/model":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/model gpt-4o-mini`",
                author="System"
            ).send()
            return
        await change_model(args)
    
    elif cmd == "/system":
        await set_system_prompt(args)
    
    elif cmd == "/stats":
        await show_statistics()
    
    elif cmd == "/clear":
        await start_new_chat()
    
    elif cmd == "/setkey":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/setkey sk-xxxxxxxxxxxxx`",
                author="System"
            ).send()
            return
        await set_api_key(args)
    
    elif cmd == "/test":
        await test_connection()
    
    elif cmd == "/status":
        await show_status()
    
    elif cmd == "/debug":
        await show_debug_info()
    
    else:
        await cl.Message(
            content=f"❓ 不明なコマンド: {cmd}\n\n`/help` で利用可能なコマンドを確認できます。",
            author="System"
        ).send()


async def show_help():
    """コマンドヘルプを表示"""
    help_message = """
# 📚 コマンドヘルプ (組み込みSQLAlchemy版)

## 🤖 AI設定コマンド

### `/model [モデル名]`
- **説明**: 使用するモデルを変更
- **使用例**: `/model gpt-4o`

### `/system [プロンプト]`
- **説明**: システムプロンプトを設定
- **使用例**: `/system プログラミングの専門家として`

## 📊 情報表示

### `/stats`
- **説明**: 現在のセッションの統計情報を表示

### `/status`
- **説明**: 現在の設定状態を表示

### `/debug`
- **説明**: デバッグ情報を表示（データレイヤーの状態など）

## 🔧 システム設定

### `/setkey [APIキー]`
- **説明**: OpenAI APIキーを設定

### `/test`
- **説明**: API接続をテスト

### `/clear`
- **説明**: 新しい会話を開始

## 💡 履歴管理について

**データレイヤーの状態により動作が異なります：**

- **SQLAlchemyDataLayer**: 永続化あり、履歴保存
- **インメモリ**: 再起動で履歴が消失
- **未設定**: 履歴機能が無効

**現在の状態を確認**: `/debug` コマンドを使用
"""
    
    await cl.Message(content=help_message, author="System").send()


async def show_debug_info():
    """デバッグ情報を表示"""
    import chainlit.data as cl_data
    import os
    from pathlib import Path
    
    # データレイヤーの状態を確認
    data_layer_status = "❓ 不明"
    data_layer_class = "N/A"
    if hasattr(cl_data, '_data_layer'):
        if cl_data._data_layer is not None:
            data_layer_class = type(cl_data._data_layer).__name__
            data_layer_status = f"✅ 有効 ({data_layer_class})"
        else:
            data_layer_status = "❌ None"
    else:
        data_layer_status = "❌ 未設定"
    
    # データベースファイルの存在確認
    db_path = Path(".chainlit/chainlit.db")
    db_exists = "✅ 存在" if db_path.exists() else "❌ 存在しない"
    db_size = f"{db_path.stat().st_size / 1024:.2f} KB" if db_path.exists() else "N/A"
    
    # 認証の状態
    auth_type = os.getenv("CHAINLIT_AUTH_TYPE", "未設定")
    auth_enabled = "✅ 有効" if auth_type == "credentials" else "❌ 無効"
    
    # Chainlit設定を確認
    try:
        import chainlit.config as cl_config
        data_persistence = cl_config.features.data_persistence if hasattr(cl_config.features, 'data_persistence') else '不明'
        show_history = cl_config.ui.show_history if hasattr(cl_config.ui, 'show_history') else '不明'
    except:
        data_persistence = '確認できません'
        show_history = '確認できません'
    
    debug_message = f"""
# 🔍 デバッグ情報

## データレイヤー
- **状態**: {data_layer_status}
- **クラス**: {data_layer_class}
- **グローバル変数**: {data_layer_type or '未設定'}
- **データベースファイル**: {db_exists}
- **データベースサイズ**: {db_size}
- **パス**: `.chainlit/chainlit.db`

## 認証
- **タイプ**: {auth_type}
- **状態**: {auth_enabled}

## Chainlit設定
- **データ永続化**: {data_persistence}
- **履歴UI**: {show_history}

## 環境
- **Python**: {os.sys.version.split()[0]}
- **Chainlit**: {cl.__version__ if hasattr(cl, '__version__') else '不明'}
- **作業ディレクトリ**: {os.getcwd()}

## トラブルシューティング

### 履歴が表示されない場合：

1. **データレイヤーが未設定の場合**：
   - 組み込みのSQLAlchemyDataLayerはSQLite対応が不完全な可能性があります
   - PostgreSQLを使用するか、インメモリ版を使用してください

2. **認証が無効の場合**：
   - 履歴UIは認証とセットで動作します
   - `.env`で認証を有効にしてください

3. **ブラウザの問題**：
   - キャッシュをクリア（Ctrl+F5）
   - シークレットモードで開く
   - 別のブラウザで試す

4. **PostgreSQLを使用する場合**：
   ```python
   # app.pyを編集して接続文字列を変更
   conninfo="postgresql+asyncpg://user:password@localhost/dbname"
   ```

5. **完全に動作させるには**：
   - PostgreSQLデータベースをセットアップ
   - または、インメモリ版で一時的に使用
"""
    
    await cl.Message(content=debug_message, author="System").send()


async def change_model(model: str):
    """モデルを変更"""
    settings = cl.user_session.get("settings", {})
    settings["DEFAULT_MODEL"] = model
    cl.user_session.set("settings", settings)
    
    await cl.Message(
        content=f"✅ モデルを {model} に変更しました",
        author="System"
    ).send()


async def set_system_prompt(prompt: str):
    """システムプロンプトを設定"""
    cl.user_session.set("system_prompt", prompt)
    
    if prompt:
        await cl.Message(
            content=f"✅ システムプロンプトを設定しました:\n```\n{prompt}\n```",
            author="System"
        ).send()
    else:
        await cl.Message(
            content="✅ システムプロンプトをクリアしました",
            author="System"
        ).send()


async def show_statistics():
    """統計情報を表示"""
    message_count = cl.user_session.get("message_count", 0)
    total_tokens = cl.user_session.get("total_tokens", 0)
    model = cl.user_session.get("settings", {}).get("DEFAULT_MODEL", "gpt-4o-mini")
    
    stats_message = f"""
# 📊 現在のセッションの統計

- **メッセージ数**: {message_count}
- **使用トークン**: {total_tokens:,}
- **使用モデル**: {model}
- **システムプロンプト**: {"設定済み" if cl.user_session.get("system_prompt") else "未設定"}
- **データレイヤー**: {data_layer_type or '未設定'}

💡 **ヒント**: 
- データレイヤーが設定されている場合、履歴は自動保存されます
- `/debug` でより詳細な情報を確認できます
"""
    
    await cl.Message(content=stats_message, author="System").send()


async def start_new_chat():
    """新しいチャットを開始"""
    # Chainlitが自動で新しいスレッドを作成
    await cl.Message(
        content=f"""
✅ 新しい会話を開始しました

{"前の会話は自動的に保存されています。" if data_layer_type else "⚠️ データレイヤーが未設定のため、履歴は保存されません。"}
{"左上の履歴ボタンからいつでもアクセスできます。" if data_layer_type else ""}
        """,
        author="System"
    ).send()
    
    # セッション変数をリセット
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    cl.user_session.set("system_prompt", "")


async def set_api_key(api_key: str):
    """APIキーを設定"""
    success = config_manager.set_api_key(api_key)
    if success:
        new_settings = config_manager.get_all_settings()
        cl.user_session.set("settings", new_settings)
        response_handler.update_api_key(api_key)
        
        await cl.Message(
            content="✅ APIキーを設定しました",
            author="System"
        ).send()
        
        await test_connection()


async def test_connection():
    """API接続テスト"""
    msg = cl.Message(content="🔄 接続テスト中...")
    await msg.send()
    
    success, message, models = await config_manager.test_connection()
    
    if success:
        test_success, test_message = await config_manager.test_simple_completion()
        result = f"✅ 接続成功！\n{test_message if test_success else '応答テスト失敗'}"
    else:
        result = f"❌ 接続失敗: {message}"
    
    await cl.Message(content=result, author="System").send()


async def show_status():
    """設定状態を表示"""
    settings = config_manager.get_all_settings()
    
    status_message = f"""
## 📊 現在の設定

- **APIキー**: {settings.get('OPENAI_API_KEY_DISPLAY', '未設定')}
- **モデル**: {cl.user_session.get('settings', {}).get('DEFAULT_MODEL', 'gpt-4o-mini')}
- **メッセージ数**: {cl.user_session.get("message_count", 0)}
- **トークン使用量**: {cl.user_session.get("total_tokens", 0):,}
- **システムプロンプト**: {"設定済み" if cl.user_session.get("system_prompt") else "未設定"}
- **データレイヤー**: {data_layer_type or '未設定'}
"""
    
    await cl.Message(content=status_message, author="System").send()


if __name__ == "__main__":
    print(f"Starting {APP_NAME} {VERSION}")
    print(f"Working Directory: {os.getcwd()}")
    print("=" * 50)
    print("📌 Chainlit組み込みSQLAlchemyDataLayerを使用")
    print("📌 ログイン情報:")
    print("   - ユーザー名: admin")
    print("   - パスワード: admin123 (または.envで設定した値)")
    print("=" * 50)
    print("📌 データレイヤーの状態:")
    print(f"   - タイプ: {data_layer_type or '未設定'}")
    if not data_layer_type:
        print("   ⚠️ データレイヤーが設定されていません")
        print("   📝 履歴機能が動作しない可能性があります")
    print("=" * 50)
    
    current_settings = config_manager.get_all_settings()
    print(f"API Key: {current_settings.get('OPENAI_API_KEY_DISPLAY', 'Not set')}")
    print(f"Default Model: {current_settings.get('DEFAULT_MODEL', 'Not set')}")
