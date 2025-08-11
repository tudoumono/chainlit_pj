"""
Phase 5 (公式機能版): Chainlitの組み込み機能を使用した履歴管理
- Chainlitの公式データ永続化機能を使用
- 認証機能による保護
- 自動的な履歴管理
"""

import chainlit as cl
from chainlit.types import ThreadDict
from dotenv import load_dotenv
import os
import auth  # 認証設定をインポート
import data_layer  # カスタムデータレイヤーをインポート
from typing import Optional, Dict, List
from datetime import datetime
import json

# utils モジュールをインポート（設定管理とAPI呼び出しのみ使用）
from utils.config import config_manager
from utils.response_handler import response_handler

# .envファイルの読み込み
load_dotenv()

# アプリケーション設定
APP_NAME = "AI Workspace"
VERSION = "0.5.2 (Official Features)"


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

## 🔧 利用可能なコマンド
- `/help` - コマンド一覧とヘルプを表示
- `/model [モデル名]` - 使用するモデルを変更
- `/system [プロンプト]` - システムプロンプトを設定
- `/stats` - 統計情報を表示
- `/clear` - 新しい会話を開始
- `/setkey [APIキー]` - OpenAI APIキーを設定

💡 **ヒント**: 会話は自動で保存され、左上の履歴ボタンからいつでも再開できます！

## 📝 Phase 5 公式機能版の特徴
- ✅ **Chainlit組み込みの履歴管理**
- ✅ **認証による保護**
- ✅ **自動的なセッション保存**
- ✅ **UIからの履歴アクセス**

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
    
    else:
        await cl.Message(
            content=f"❓ 不明なコマンド: {cmd}\n\n`/help` で利用可能なコマンドを確認できます。",
            author="System"
        ).send()


async def show_help():
    """コマンドヘルプを表示"""
    help_message = """
# 📚 コマンドヘルプ (公式機能版)

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
- **使用例**: `/stats`

### `/status`
- **説明**: 現在の設定状態を表示
- **使用例**: `/status`

## 🔧 システム設定

### `/setkey [APIキー]`
- **説明**: OpenAI APIキーを設定
- **使用例**: `/setkey sk-xxxxxxxxxxxxx`

### `/test`
- **説明**: API接続をテスト
- **使用例**: `/test`

### `/clear`
- **説明**: 新しい会話を開始
- **使用例**: `/clear`

## 💡 履歴管理について

**Chainlitの公式機能を使用しています：**
- 会話は自動的に保存されます
- 左上の履歴ボタンから過去の会話にアクセスできます
- 認証により、あなたの会話は保護されています

**メリット：**
- 手動でのセッション管理が不要
- UIから簡単に履歴にアクセス
- 安定した動作と高速なパフォーマンス
"""
    
    await cl.Message(content=help_message, author="System").send()


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

💡 **ヒント**: 履歴は自動で保存されています。左上のボタンから過去の会話にアクセスできます。
"""
    
    await cl.Message(content=stats_message, author="System").send()


async def start_new_chat():
    """新しいチャットを開始"""
    # Chainlitが自動で新しいスレッドを作成
    await cl.Message(
        content="""
✅ 新しい会話を開始しました

前の会話は自動的に保存されています。
左上の履歴ボタンからいつでもアクセスできます。
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
"""
    
    await cl.Message(content=status_message, author="System").send()


if __name__ == "__main__":
    print(f"Starting {APP_NAME} {VERSION}")
    print(f"Working Directory: {os.getcwd()}")
    print("=" * 50)
    print("📌 Chainlit公式機能を使用した履歴管理")
    print("📌 ログイン情報:")
    print("   - ユーザー名: admin")
    print("   - パスワード: admin123 (または.envで設定した値)")
    print("=" * 50)
    
    current_settings = config_manager.get_all_settings()
    print(f"API Key: {current_settings.get('OPENAI_API_KEY_DISPLAY', 'Not set')}")
    print(f"Default Model: {current_settings.get('DEFAULT_MODEL', 'Not set')}")
