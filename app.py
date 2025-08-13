"""
Phase 5 (SQLite永続化版): Chainlitの履歴管理
- SQLiteデータレイヤーを使用して履歴を永続化
- 認証機能による保護
- 自動的な履歴管理（永続的に保存）
- 詳細なデバッグログシステム
"""

import chainlit as cl
from chainlit.types import ThreadDict
from dotenv import load_dotenv
import os
import auth  # 認証設定をインポート
from typing import Optional, Dict, List
from datetime import datetime
import json
import uuid  # スレッドID生成用
import chainlit.data as cl_data  # データレイヤーアクセス用

# .envファイルの読み込み
load_dotenv()

# ログシステムをインポート
from utils.logger import app_logger

# データレイヤーをインポート（SQLiteを優先して永続化）
data_layer_type = None

# SQLiteデータレイヤーを優先的に使用（永続化のため）
try:
    # SQLiteデータレイヤーを使用（優先）
    import data_layer
    data_layer_type = "SQLite (Persistent)"
    app_logger.info("✅ SQLiteデータレイヤーを使用")
    app_logger.info("📝 履歴は.chainlit/chainlit.dbに永続化されます")
    print("✅ SQLiteデータレイヤーを使用")
    print("📝 履歴は.chainlit/chainlit.dbに永続化されます")
except Exception as e:
    app_logger.error(f"⚠️ SQLiteデータレイヤーのエラー: {e}")
    print(f"⚠️ SQLiteデータレイヤーのエラー: {e}")
    try:
        # インメモリデータレイヤーをフォールバックとして使用
        import simple_data_layer
        data_layer_type = "Simple In-Memory"
        app_logger.info("✅ シンプルなインメモリデータレイヤーを使用")
        print("✅ シンプルなインメモリデータレイヤーを使用")
        print("📝 注意: 履歴はアプリケーション再起動で消失します")
    except ImportError:
        try:
            # SQLAlchemyDataLayerを試す（PostgreSQL）
            import chainlit.data as cl_data
            from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
            
            # PostgreSQL接続文字列（環境変数から読み込む）
            pg_conninfo = os.getenv("POSTGRES_CONNECTION_STRING")
            if pg_conninfo:
                cl_data._data_layer = SQLAlchemyDataLayer(conninfo=pg_conninfo)
                data_layer_type = "SQLAlchemy (PostgreSQL)"
                app_logger.info("✅ SQLAlchemyDataLayer（PostgreSQL）を使用")
                print("✅ SQLAlchemyDataLayer（PostgreSQL）を使用")
            else:
                app_logger.warning("⚠️ PostgreSQL接続文字列が設定されていません")
                print("⚠️ PostgreSQL接続文字列が設定されていません")
                print("📝 履歴機能を使用するには、data_layerまたは")
                print("   simple_data_layer.pyを確認してください")
        except Exception as e:
            app_logger.error(f"⚠️ SQLAlchemyDataLayerのエラー: {e}")
            print(f"⚠️ SQLAlchemyDataLayerのエラー: {e}")
            print("📝 data_layer.pyまたはsimple_data_layer.pyを使用してください")

# utils モジュールをインポート（設定管理とAPI呼び出しのみ使用）
from utils.config import config_manager
from utils.response_handler import response_handler

# アプリケーション設定
APP_NAME = "AI Workspace"
VERSION = "0.6.1 (SQLite Persistent + Logging)"


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """
    履歴からチャットを復元する際の処理
    過去のメッセージを画面に再表示する
    """
    app_logger.info(f"📂 on_chat_resumeが呼ばれました", 
                   thread_id=thread.get('id', 'None')[:8],
                   thread_name=thread.get('name', 'None'),
                   steps_count=len(thread.get('steps', [])))
    
    print(f"📂 on_chat_resumeが呼ばれました")
    print(f"   Thread ID: {thread.get('id', 'None')}")
    print(f"   Thread Name: {thread.get('name', 'None')}")
    print(f"   Steps count: {len(thread.get('steps', []))}")
    
    # 設定を読み込み
    settings = config_manager.get_all_settings()
    cl.user_session.set("settings", settings)
    cl.user_session.set("system_prompt", "")
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    cl.user_session.set("thread_id", thread.get("id"))
    
    # 復元通知メッセージ
    await cl.Message(
        content=f"📂 過去の会話を復元中: {thread.get('name', 'Untitled')}...",
        author="System"
    ).send()
    
    # ステップから過去のメッセージを再構築して表示
    steps = thread.get('steps', [])
    app_logger.debug(f"復元するステップ数: {len(steps)}")
    print(f"   復元するステップ数: {len(steps)}")
    
    # メッセージを順番に復元
    message_count = 0
    messages_to_display = []  # 表示するメッセージを一時保存
    
    # ステップを処理してメッセージを抽出
    for step in steps:
        step_type = step.get('type')
        step_id = step.get('id')
        created_at = step.get('createdAt')
        
        app_logger.debug(f"ステップ処理", 
                        step_id=step_id[:8] if step_id else 'None',
                        type=step_type,
                        has_input=bool(step.get('input')),
                        has_output=bool(step.get('output')))
        
        # ユーザーメッセージの場合
        if step_type == 'user_message':
            user_input = step.get('input', '')
            if user_input:
                messages_to_display.append({
                    'type': 'user',
                    'content': user_input,
                    'id': step_id,
                    'created_at': created_at
                })
                app_logger.debug(f"📥 ユーザーメッセージを準備", preview=user_input[:50])
                print(f"   📥 ユーザーメッセージを準備: {user_input[:50]}...")
        
        # アシスタントメッセージの場合
        elif step_type == 'assistant_message':
            assistant_output = step.get('output', '')
            if assistant_output:
                messages_to_display.append({
                    'type': 'assistant',
                    'content': assistant_output,
                    'id': step_id,
                    'created_at': created_at
                })
                app_logger.debug(f"🤖 アシスタントメッセージを準備", preview=assistant_output[:50])
                print(f"   🤖 アシスタントメッセージを準備: {assistant_output[:50]}...")
            else:
                app_logger.warning(f"⚠️ アシスタントメッセージの出力が空です", step_id=step_id[:8])
                print(f"   ⚠️ アシスタントメッセージの出力が空です: {step_id[:8]}...")
        
        # runタイプはシステム的なものなのでスキップ
        elif step_type == 'run':
            # runステップにもoutputがある場合がある
            run_output = step.get('output', '')
            if run_output and not run_output.startswith('{'):  # JSONでない場合
                # システムメッセージとして表示
                messages_to_display.append({
                    'type': 'system',
                    'content': run_output,
                    'id': step_id,
                    'created_at': created_at
                })
                app_logger.debug(f"💻 runステップの出力を準備", preview=run_output[:50])
                print(f"   💻 runステップの出力を準備: {run_output[:50]}...")
            else:
                app_logger.debug(f"ℹ️ runステップをスキップ", name=step.get('name', 'N/A'))
                print(f"   ℹ️ runステップをスキップ: {step.get('name', 'N/A')}")
        
        # その他のタイプ
        else:
            # 必要に応じて他のステップタイプも処理
            app_logger.warning(f"⚠️ 未処理のステップタイプ: {step_type}")
            print(f"   ⚠️ 未処理のステップタイプ: {step_type}")
            # outputがあれば表示
            other_output = step.get('output', '')
            if other_output:
                messages_to_display.append({
                    'type': 'system',
                    'content': other_output,
                    'id': step_id,
                    'created_at': created_at
                })
    
    # メッセージを順番に表示
    for msg in messages_to_display:
        if msg['type'] == 'user':
            # ユーザーメッセージを表示
            user_msg = cl.Message(
                content=msg['content'],
                author="User",
                type="user_message"
            )
            user_msg.id = msg['id']  # 元のIDを保持
            await user_msg.send()
            message_count += 1
        elif msg['type'] == 'assistant':
            # アシスタントメッセージを表示
            assistant_msg = cl.Message(
                content=msg['content'],
                author="Assistant"
            )
            assistant_msg.id = msg['id']  # 元のIDを保持
            await assistant_msg.send()
            message_count += 1
        elif msg['type'] == 'system':
            # システムメッセージを表示
            system_msg = cl.Message(
                content=msg['content'],
                author="System"
            )
            system_msg.id = msg['id']  # 元のIDを保持
            await system_msg.send()
            message_count += 1
    
    # 復元完了メッセージ
    await cl.Message(
        content=f"✅ 復元完了: {message_count}件のメッセージを表示しました",
        author="System"
    ).send()
    
    # セッション変数を更新
    cl.user_session.set("message_count", message_count)
    
    app_logger.history_restored(thread.get('id', 'unknown'), message_count)
    print(f"   ✅ 復元完了: {message_count}件のメッセージ")


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
    
    # 現在のユーザー情報を取得
    current_user = cl.user_session.get("user")
    app_logger.info(f"👤 新しいセッション開始", user=current_user.identifier if current_user else "anonymous")
    print(f"👤 現在のユーザー: {current_user}")
    
    # Chainlitが生成するスレッドIDを使用
    # メッセージが送信される際にChainlitがスレッドIDを自動生成するため、
    # ここではスレッド作成を遅延させる
    
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

💡 **ヒント**: 
- 会話は永続的に保存されます
- 左上の履歴ボタンから過去の会話にアクセスできます
- アプリを再起動しても履歴は保持されます

## 📝 データレイヤーの状態
- **タイプ**: {data_layer_type or '❌ 未設定'}
- **永続化**: {"✅ SQLiteに永続化" if data_layer_type == "SQLite (Persistent)" else "✅ PostgreSQLに永続化" if data_layer_type == "SQLAlchemy (PostgreSQL)" else "⚠️ インメモリ（再起動で消失）" if data_layer_type == "Simple In-Memory" else "❌ なし"}
- **認証**: {"✅ 有効" if os.getenv("CHAINLIT_AUTH_TYPE") == "credentials" else "❌ 無効"}

---
**AIと会話を始めましょう！** 何でも質問してください。
    """
    
    await cl.Message(content=welcome_message).send()
    
    # APIキーが未設定の場合は警告
    if not settings.get("OPENAI_API_KEY") or settings["OPENAI_API_KEY"] == "your_api_key_here":
        await cl.Message(
            content="⚠️ **APIキーが設定されていません**\n\n`/setkey [あなたのAPIキー]` コマンドで設定してください。",
            author="System"
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    ユーザーメッセージの処理
    コマンドの処理とAI応答の生成・保存
    """
    # メッセージを受信
    user_input = message.content
    current_user = cl.user_session.get("user")
    user_id = current_user.identifier if current_user else "anonymous"
    
    app_logger.message_received(user_input, user_id)
    app_logger.debug(f"📥 メッセージ受信", 
                     user=user_id,
                     length=len(user_input),
                     thread_id=cl.context.session.thread_id[:8] if hasattr(cl.context.session, 'thread_id') else 'None')
    
    # メッセージカウントを増加
    message_count = cl.user_session.get("message_count", 0) + 1
    cl.user_session.set("message_count", message_count)
    
    # コマンド処理
    if user_input.startswith("/"):
        await handle_command(user_input)
        return
    
    # AI応答の生成
    settings = cl.user_session.get("settings", {})
    api_key = settings.get("OPENAI_API_KEY")
    
    if not api_key or api_key == "your_api_key_here":
        await cl.Message(
            content="⚠️ APIキーが設定されていません。\n`/setkey [APIキー]` でAPIキーを設定してください。",
            author="System"
        ).send()
        return
    
    # システムプロンプト
    system_prompt = cl.user_session.get("system_prompt", "")
    model = settings.get("DEFAULT_MODEL", "gpt-4o-mini")
    
    app_logger.debug(f"🤖 AI応答生成開始", model=model, has_system_prompt=bool(system_prompt))
    
    # レスポンスハンドラーを使用してAI応答を生成
    response_text = await response_handler.get_response(
        user_input,
        system_prompt=system_prompt,
        model=model
    )
    
    if response_text:
        # AI応答を送信
        ai_message = cl.Message(content=response_text, author="Assistant")
        await ai_message.send()
        
        # AI応答をログに記録
        app_logger.ai_response(response_text, model)
        app_logger.debug(f"🤖 AI応答送信完了", 
                        length=len(response_text),
                        message_id=ai_message.id[:8] if ai_message.id else 'None')
        
        # トークン使用量を更新（簡易計算）
        total_tokens = cl.user_session.get("total_tokens", 0)
        estimated_tokens = len(user_input.split()) + len(response_text.split())
        total_tokens += estimated_tokens * 2  # 概算
        cl.user_session.set("total_tokens", total_tokens)
        
        app_logger.debug(f"📊 トークン使用量更新", 
                        estimated_tokens=estimated_tokens,
                        total_tokens=total_tokens)
    else:
        error_msg = "❌ AI応答の生成に失敗しました。"
        await cl.Message(content=error_msg, author="System").send()
        app_logger.error(f"AI応答生成失敗", user_input=user_input[:100])


async def handle_command(user_input: str):
    """コマンドを処理"""
    parts = user_input.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    app_logger.debug(f"🎮 コマンド処理", command=cmd, args=args[:50] if args else None)
    
    if cmd == "/help":
        await show_help()
    elif cmd == "/model":
        if args:
            await change_model(args)
        else:
            await cl.Message(
                content="❌ モデル名を指定してください。\n例: `/model gpt-4o`",
                author="System"
            ).send()
    elif cmd == "/system":
        await set_system_prompt(args)
    elif cmd == "/stats":
        await show_statistics()
    elif cmd == "/clear":
        await start_new_chat()
    elif cmd == "/setkey":
        if args:
            await set_api_key(args)
        else:
            await cl.Message(
                content="❌ APIキーを指定してください。\n例: `/setkey sk-...`",
                author="System"
            ).send()
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
    help_message = f"""
# 📚 コマンドヘルプ (永続化版)

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

## 🔧 システム設定

### `/setkey [APIキー]`
- **説明**: OpenAI APIキーを設定

### `/test`
- **説明**: API接続をテスト

### `/clear`
- **説明**: 新しい会話を開始

## 💡 履歴管理について

**現在{"SQLiteデータレイヤー" if data_layer_type == "SQLite (Persistent)" else "のデータレイヤー"}を使用中：**
- ✅ 履歴UIが表示されます
- {"✅ 履歴はSQLiteに永続的に保存されます" if data_layer_type == "SQLite (Persistent)" else "✅ セッション中は履歴が保持されます"}
- {"✅ アプリ再起動後も履歴が保持されます" if data_layer_type == "SQLite (Persistent)" else "⚠️ アプリ再起動で履歴が消失します"}

**履歴の保存場所：**
- {".chainlit/chainlit.db" if data_layer_type == "SQLite (Persistent)" else "メモリ内（一時的）"}
"""
    
    await cl.Message(content=help_message, author="System").send()


async def change_model(model: str):
    """モデルを変更"""
    settings = cl.user_session.get("settings", {})
    settings["DEFAULT_MODEL"] = model
    cl.user_session.set("settings", settings)
    
    app_logger.info(f"モデル変更", model=model)
    
    await cl.Message(
        content=f"✅ モデルを {model} に変更しました",
        author="System"
    ).send()


async def set_system_prompt(prompt: str):
    """システムプロンプトを設定"""
    cl.user_session.set("system_prompt", prompt)
    
    app_logger.info(f"システムプロンプト設定", length=len(prompt))
    
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

💡 **ヒント**: {"SQLiteデータレイヤーを使用中。履歴は永続的に保存されます。" if data_layer_type == "SQLite (Persistent)" else "インメモリデータレイヤーを使用中。履歴はアプリ再起動で消失します。"}
"""
    
    await cl.Message(content=stats_message, author="System").send()


async def start_new_chat():
    """新しいチャットを開始"""
    # Chainlitが自動で新しいスレッドを作成するため、
    # ここではセッション変数のリセットのみを行う
    
    app_logger.info("新しいチャット開始")
    
    await cl.Message(
        content=f"""
✅ 新しい会話を開始しました

{"前の会話はSQLiteに永続的に保存されています。" if data_layer_type == "SQLite (Persistent)" else "前の会話はセッション中のみ保存されています。"}
左上の履歴ボタンから過去の会話にアクセスできます。
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
        
        app_logger.info("APIキー設定成功")
        
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
        app_logger.info("API接続テスト成功")
    else:
        result = f"❌ 接続失敗: {message}"
        app_logger.error(f"API接続テスト失敗", error=message)
    
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
    app_logger.info(f"Starting {APP_NAME} {VERSION}")
    app_logger.info(f"Working Directory: {os.getcwd()}")
    
    print(f"Starting {APP_NAME} {VERSION}")
    print(f"Working Directory: {os.getcwd()}")
    print("=" * 50)
    print("📌 データレイヤーの状態:")
    print(f"   - タイプ: {data_layer_type or '未設定'}")
    if data_layer_type == "SQLite (Persistent)":
        print("   ✅ SQLite: 履歴は永続的に保存されます")
        print("   📂 保存場所: .chainlit/chainlit.db")
    elif data_layer_type == "Simple In-Memory":
        print("   ⚠️ インメモリ: 履歴はアプリ再起動で消失します")
    elif not data_layer_type:
        print("   ❌ データレイヤーが設定されていません")
        print("   📝 履歴機能が動作しません")
    print("=" * 50)
    print("📌 ログイン情報:")
    print("   - ユーザー名: admin")
    print("   - パスワード: admin123 (または.envで設定した値)")
    print("=" * 50)
    
    current_settings = config_manager.get_all_settings()
    print(f"API Key: {current_settings.get('OPENAI_API_KEY_DISPLAY', 'Not set')}")
    print(f"Default Model: {current_settings.get('DEFAULT_MODEL', 'Not set')}")
    
    app_logger.info("アプリケーション起動完了")
