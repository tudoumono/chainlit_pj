# app.py (カスタムデータレイヤー使用版)

# --- 標準ライブラリのインポート ---
import os
from datetime import datetime
from pathlib import Path

# --- サードパーティライブラリのインポート ---
import chainlit as cl
from chainlit.types import ThreadDict
from dotenv import load_dotenv

# --- ローカルアプリケーションモジュールのインポート ---
import auth
from utils.config import config_manager
from utils.response_handler import response_handler

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ★★★ ここで、完成したカスタムデータレイヤーを読み込みます ★★★
from data_layer import SQLiteDataLayer
import chainlit.data as cl_data

cl_data._data_layer = SQLiteDataLayer()
data_layer_type = "Custom SQLite"
print("✅ カスタムSQLiteデータレイヤーを使用")
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

# .envファイルの読み込み
load_dotenv()

# アプリケーション設定
APP_NAME = "AI Workspace"
VERSION = "0.6.0 (Custom DB Layer)"

# --- on_chat_start 以降のコードは変更ありません ---
# (前のバージョンと同じコードをそのまま使用してください)
@cl.on_chat_start
async def on_chat_start():
    settings = config_manager.get_all_settings()
    cl.user_session.set("settings", settings)
    cl.user_session.set("system_prompt", "")
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    
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

---
**AIと会話を始めましょう！** 何でも質問してください。
    """
    await cl.Message(content=welcome_message).send()
    
    if not settings.get("OPENAI_API_KEY") or settings["OPENAI_API_KEY"] == "your_api_key_here":
        await cl.Message(
            content="⚠️ **APIキーが未設定です**\n`/setkey sk-xxxxx` コマンドで設定してください。",
            author="System"
        ).send()


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    print(f"チャット再開: Thread ID = {thread['id']}")
    settings = config_manager.get_all_settings()
    cl.user_session.set("settings", settings)
    cl.user_session.set("system_prompt", "")
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    
    thread_id = thread.get('id', 'Unknown')
    created_at = thread.get('createdAt', '')
    
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
    content = message.content.strip()
    settings = cl.user_session.get("settings", {})
    
    if content.startswith("/"):
        await handle_command(content)
        return
    
    if not settings.get("OPENAI_API_KEY") or settings["OPENAI_API_KEY"] == "your_api_key_here":
        await cl.Message(
            content="❌ APIキーが設定されていません。`/setkey sk-xxxxx` で設定してください。",
            author="System"
        ).send()
        return
    
    count = cl.user_session.get("message_count", 0) + 1
    cl.user_session.set("message_count", count)
    
    messages = []
    
    system_prompt = cl.user_session.get("system_prompt", "")
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": content})
    
    ai_message = cl.Message(content="")
    await ai_message.send()
    
    full_response = ""
    token_usage = {}
    
    try:
        async for chunk in response_handler.create_chat_completion(
            messages=messages,
            model=settings.get('DEFAULT_MODEL', 'gpt-4o-mini'),
            temperature=0.7,
            stream=True
        ):
            if "error" in chunk:
                error_msg = f"❌ エラー: {chunk['error']}"
                ai_message = cl.Message(content=error_msg)
                await ai_message.send()
                return
            
            if chunk.get("choices"):
                for choice in chunk["choices"]:
                    if "delta" in choice:
                        delta = choice["delta"]
                        if "content" in delta:
                            full_response += delta["content"]
                            await ai_message.stream_token(delta["content"])
            
            if "usage" in chunk:
                token_usage = chunk["usage"]
        
        await ai_message.update()
        
        if token_usage:
            total_tokens = cl.user_session.get("total_tokens", 0) + token_usage.get("total_tokens", 0)
            cl.user_session.set("total_tokens", total_tokens)
    
    except Exception as e:
        error_msg = f"❌ エラーが発生しました: {str(e)}"
        await cl.Message(content=error_msg, author="System").send()
        print(f"Error in on_message: {e}")


async def handle_command(command: str):
    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    if cmd == "/help": await show_help()
    elif cmd == "/model":
        if not args: await cl.Message(content="❌ 使用方法: `/model gpt-4o-mini`", author="System").send()
        else: await change_model(args)
    elif cmd == "/system": await set_system_prompt(args)
    elif cmd == "/stats": await show_statistics()
    elif cmd == "/clear": await start_new_chat()
    elif cmd == "/setkey":
        if not args: await cl.Message(content="❌ 使用方法: `/setkey sk-xxxxxxxxxxxxx`", author="System").send()
        else: await set_api_key(args)
    elif cmd == "/test": await test_connection()
    elif cmd == "/status": await show_status()
    elif cmd == "/debug": await show_debug_info()
    else: await cl.Message(content=f"❓ 不明なコマンド: {cmd}\n\n`/help` で利用可能なコマンドを確認できます。", author="System").send()


async def show_help():
    await cl.Message(content="""
# 📚 コマンドヘルプ
/model [モデル名], /system [プロンプト], /stats, /status, /debug, /setkey [APIキー], /test, /clear
""", author="System").send()

async def show_debug_info():
    data_layer_status, data_layer_class = "❌ 未設定", "N/A"
    if hasattr(cl_data, '_data_layer') and cl_data._data_layer:
        data_layer_class = type(cl_data._data_layer).__name__
        data_layer_status = f"✅ 有効 ({data_layer_class})"
    
    db_path = Path(".chainlit/chainlit.db")
    db_exists = "✅ 存在" if db_path.exists() else "❌ 存在しない"
    db_size = f"{db_path.stat().st_size / 1024:.2f} KB" if db_path.exists() else "N/A"
    auth_type = os.getenv("CHAINLIT_AUTH_TYPE", "未設定")
    
    await cl.Message(content=f"""
# 🔍 デバッグ情報
- **データレイヤー状態**: {data_layer_status}
- **データベースファイル**: {db_exists} ({db_size})
- **認証タイプ**: {auth_type}
""", author="System").send()

async def change_model(model: str):
    settings = cl.user_session.get("settings", {})
    settings["DEFAULT_MODEL"] = model
    cl.user_session.set("settings", settings)
    await cl.Message(content=f"✅ モデルを {model} に変更しました", author="System").send()

async def set_system_prompt(prompt: str):
    cl.user_session.set("system_prompt", prompt)
    msg = f"✅ システムプロンプトを設定しました:\n```\n{prompt}\n```" if prompt else "✅ システムプロンプトをクリアしました"
    await cl.Message(content=msg, author="System").send()

async def show_statistics():
    message_count = cl.user_session.get("message_count", 0)
    total_tokens = cl.user_session.get("total_tokens", 0)
    await cl.Message(content=f"""
# 📊 現在のセッションの統計
- **メッセージ数**: {message_count}
- **使用トークン**: {total_tokens:,}
""", author="System").send()

async def start_new_chat():
    await cl.Message(content="✅ 新しい会話を開始しました", author="System").send()
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    cl.user_session.set("system_prompt", "")

async def set_api_key(api_key: str):
    if config_manager.set_api_key(api_key):
        new_settings = config_manager.get_all_settings()
        cl.user_session.set("settings", new_settings)
        response_handler.update_api_key(api_key)
        await cl.Message(content="✅ APIキーを設定しました", author="System").send()
        await test_connection()

async def test_connection():
    await cl.Message(content="🔄 接続テスト中...", author="System").send()
    success, message, _ = await config_manager.test_connection()
    result = f"✅ 接続成功！" if success else f"❌ 接続失敗: {message}"
    await cl.Message(content=result, author="System").send()

async def show_status():
    settings = config_manager.get_all_settings()
    await cl.Message(content=f"""
## 📊 現在の設定
- **APIキー**: {settings.get('OPENAI_API_KEY_DISPLAY', '未設定')}
- **モデル**: {cl.user_session.get('settings', {}).get('DEFAULT_MODEL', 'gpt-4o-mini')}
""", author="System").send()