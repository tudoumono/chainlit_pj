"""
Phase 2: 設定管理機能を含むChainlitアプリケーション
- APIキーの設定と保存
- 接続テスト機能
- プロキシ設定
- モデル選択
"""

import chainlit as cl
from dotenv import load_dotenv
import os
from typing import Optional, Dict
import asyncio
from pathlib import Path

# utils/config.pyをインポート
from utils.config import config_manager

# .envファイルの読み込み
load_dotenv()

# アプリケーション設定
APP_NAME = "AI Workspace"
VERSION = "0.2.0 (Phase 2)"


@cl.on_chat_start
async def on_chat_start():
    """
    チャットセッション開始時の処理
    """
    # 設定を読み込み
    settings = config_manager.get_all_settings()
    
    # セッション情報の初期化
    cl.user_session.set("phase", "2")
    cl.user_session.set("app_name", APP_NAME)
    cl.user_session.set("settings", settings)
    
    # ウェルカムメッセージの作成
    api_status = "✅ 設定済み" if settings.get("OPENAI_API_KEY") and settings["OPENAI_API_KEY"] != "your_api_key_here" else "⚠️ 未設定"
    
    welcome_message = f"""
# 🎯 {APP_NAME} へようこそ！

**Version**: {VERSION}

## 📊 現在の状態
- **APIキー**: {api_status}
- **デフォルトモデル**: {settings.get('DEFAULT_MODEL', 'gpt-4o-mini')}
- **プロキシ**: {'設定済み' if settings.get('HTTP_PROXY') else '未設定'}

## 🔧 設定コマンド
以下のコマンドをチャットに入力して設定を変更できます：

- `/setkey [APIキー]` - OpenAI APIキーを設定
- `/setmodel [モデル名]` - デフォルトモデルを設定
- `/setproxy [URL]` - プロキシを設定
- `/test` - API接続テスト
- `/status` - 現在の設定状態を表示
- `/models` - 利用可能なモデル一覧を取得

## 📝 Phase 2の新機能
- ✅ 設定管理機能の実装
- ✅ APIキーの永続保存（.envファイル）
- ✅ 接続テスト機能
- ✅ モデル一覧の取得
- ✅ プロキシ設定のサポート

---
設定が完了したら、メッセージを送信してテストできます。
    """
    
    await cl.Message(content=welcome_message).send()
    
    # APIキーが未設定の場合は警告
    if not settings.get("OPENAI_API_KEY") or settings["OPENAI_API_KEY"] == "your_api_key_here":
        await cl.Message(
            content="⚠️ **APIキーが未設定です**\n`/setkey sk-xxxxx` コマンドで設定してください。",
            author="System"
        ).send()
    
    # 接続テストボタンを追加
    actions = [
        cl.Action(name="test_connection", payload={"value": "test"}, description="接続テスト"),
        cl.Action(name="show_status", payload={"value": "test"}, description="設定状態"),
    ]
    await cl.Message(
        content="🔧 クイックアクション:",
        actions=actions,
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
    
    # Phase 2では接続テストのデモ応答を返す
    response = f"""
📨 メッセージを受信しました:
「{content}」

## 現在の設定状態
- **APIキー**: {settings.get('OPENAI_API_KEY_DISPLAY', '未設定')}
- **モデル**: {settings.get('DEFAULT_MODEL', 'gpt-4o-mini')}

🔄 Phase 2では設定管理機能のテスト中です。
Phase 4以降で実際のAI応答機能を実装予定です。
    """
    
    await cl.Message(content=response).send()


async def handle_command(command: str):
    """
    コマンドを処理
    """
    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    if cmd == "/setkey":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/setkey sk-xxxxxxxxxxxxx`",
                author="System"
            ).send()
            return
        
        # APIキーを設定
        success = config_manager.set_api_key(args)
        if success:
            # セッション設定を更新
            new_settings = config_manager.get_all_settings()
            cl.user_session.set("settings", new_settings)
            
            await cl.Message(
                content="✅ APIキーを設定しました",
                author="System"
            ).send()
            
            # 自動で接続テスト
            await test_connection()
        else:
            await cl.Message(
                content="❌ APIキーの設定に失敗しました",
                author="System"
            ).send()
    
    elif cmd == "/setmodel":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/setmodel gpt-4o-mini`\n利用可能: gpt-4o-mini, gpt-4o, gpt-4-turbo, gpt-3.5-turbo",
                author="System"
            ).send()
            return
        
        # 環境変数を即座に更新
        os.environ["DEFAULT_MODEL"] = args
        success = config_manager.save_config({"DEFAULT_MODEL": args})
        if success:
            # 設定を再読み込みしてセッションを更新
            new_settings = config_manager.get_all_settings()
            cl.user_session.set("settings", new_settings)
            
            await cl.Message(
                content=f"✅ デフォルトモデルを {args} に設定しました",
                author="System"
            ).send()
            
            # 更新後の状態を表示
            await cl.Message(
                content=f"📊 現在のモデル: {new_settings.get('DEFAULT_MODEL', 'gpt-4o-mini')}",
                author="System"
            ).send()
        else:
            await cl.Message(
                content="❌ モデルの設定に失敗しました",
                author="System"
            ).send()
    
    elif cmd == "/setproxy":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/setproxy http://proxy.example.com:8080`",
                author="System"
            ).send()
            return
        
        success = config_manager.set_proxy_settings(http_proxy=args, https_proxy=args)
        if success:
            # 設定を再読み込みしてセッションを更新
            new_settings = config_manager.get_all_settings()
            cl.user_session.set("settings", new_settings)
            
            await cl.Message(
                content=f"✅ プロキシを {args} に設定しました",
                author="System"
            ).send()
        else:
            await cl.Message(
                content="❌ プロキシの設定に失敗しました",
                author="System"
            ).send()
    
    elif cmd == "/test":
        await test_connection()
    
    elif cmd == "/status":
        await show_status()
    
    elif cmd == "/models":
        await list_models()
    
    else:
        await cl.Message(
            content=f"""
❓ 不明なコマンド: {cmd}

利用可能なコマンド:
- `/setkey [APIキー]` - OpenAI APIキーを設定
- `/setmodel [モデル名]` - デフォルトモデルを設定
- `/setproxy [URL]` - プロキシを設定
- `/test` - API接続テスト
- `/status` - 現在の設定状態を表示
- `/models` - 利用可能なモデル一覧を取得
            """,
            author="System"
        ).send()


@cl.action_callback("test_connection")
async def test_connection_callback(action: cl.Action):
    """接続テストボタンのコールバック"""
    await test_connection()


@cl.action_callback("show_status")
async def show_status_callback(action: cl.Action):
    """設定状態表示ボタンのコールバック"""
    await show_status()


async def test_connection():
    """API接続テストを実行"""
    # ローディングメッセージ
    msg = cl.Message(content="🔄 接続テスト中...", author="System")
    await msg.send()
    
    # 接続テスト実行
    success, message, models = await config_manager.test_connection()
    
    if success:
        models_text = "\n".join([f"  - {model}" for model in (models[:5] if models else [])])
        result_message = f"""
✅ **接続テスト成功！**

{message}

**利用可能なモデル（上位5個）:**
{models_text}

詳細なモデル一覧は `/models` コマンドで確認できます。
        """
    else:
        result_message = f"""
❌ **接続テスト失敗**

{message}

**確認事項:**
1. APIキーが正しく入力されているか
2. プロキシ設定が必要な環境かどうか
3. OpenAI APIの利用制限に達していないか
        """
    
    # 結果を更新
    msg.content = result_message
    await msg.update()


async def show_status():
    """現在の設定状態を表示"""
    settings = config_manager.get_all_settings()
    
    status_message = f"""
## 📊 現在の設定状態

**基本設定:**
- **APIキー**: {settings.get('OPENAI_API_KEY_DISPLAY', '未設定')}
- **デフォルトモデル**: {settings.get('DEFAULT_MODEL', 'gpt-4o-mini')}
- **データベース**: {settings.get('DB_PATH', 'chat_history.db')}

**ネットワーク設定:**
- **HTTPプロキシ**: {settings.get('HTTP_PROXY', '未設定')}
- **HTTPSプロキシ**: {settings.get('HTTPS_PROXY', '未設定')}

**ベクトルストア設定:**
- **社内VS ID**: {settings.get('COMPANY_VECTOR_STORE_ID', '未設定')}
- **個人VS ID**: {settings.get('PERSONAL_VECTOR_STORE_ID', '未設定')}

**サーバー設定:**
- **ホスト**: {settings.get('CHAINLIT_HOST', '0.0.0.0')}
- **ポート**: {settings.get('CHAINLIT_PORT', '8000')}
    """
    
    await cl.Message(content=status_message, author="System").send()


async def list_models():
    """利用可能なモデル一覧を取得"""
    msg = cl.Message(content="🔄 モデル一覧を取得中...", author="System")
    await msg.send()
    
    success, message, models = await config_manager.test_connection()
    
    if success and models:
        models_text = "\n".join([f"{i+1}. {model}" for i, model in enumerate(models)])
        result_message = f"""
## 📋 利用可能なGPTモデル

{models_text}

**推奨モデル:**
- `gpt-4o-mini` - 高速で低コスト
- `gpt-4o` - 最新の高性能モデル
- `gpt-4-turbo` - バランス型

モデルを変更するには: `/setmodel [モデル名]`
        """
    else:
        result_message = "❌ モデル一覧の取得に失敗しました。APIキーと接続を確認してください。"
    
    msg.content = result_message
    await msg.update()


if __name__ == "__main__":
    # デバッグ情報の出力
    print(f"Starting {APP_NAME} {VERSION}")
    print(f"Python Path: {os.sys.executable}")
    print(f"Working Directory: {os.getcwd()}")
    
    # 設定の確認
    current_settings = config_manager.get_all_settings()
    print(f"API Key: {current_settings.get('OPENAI_API_KEY_DISPLAY', 'Not set')}")
    print(f"Default Model: {current_settings.get('DEFAULT_MODEL', 'Not set')}")
