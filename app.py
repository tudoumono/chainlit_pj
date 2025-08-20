"""
Phase 5 (SQLite永続化版 + Responses API): Chainlitの履歴管理
- SQLiteデータレイヤーを使用して履歴を永続化
- OpenAI Responses API with Tools機能（Web検索、ファイル検索）
- 認証機能による保護
- 自動的な履歴管理（永続的に保存）
- 詳細なデバッグログシステム

============================================================
重要: OpenAI SDKはResponses APIを正式にサポートしています
============================================================

参照ドキュメント:
- OpenAI公式APIリファレンス: https://platform.openai.com/docs/api-reference/responses
- ローカルドキュメント: F:\10_code\AI_Workspace_App_Chainlit\openai_responseAPI_reference\
  - openai responseAPI reference (Text generation).md
  - openai responseAPI reference (Conversation state).md
  - openai responseAPI reference (Streaming API responses).md

このアプリケーションはResponses APIの仕様に完全に準拠して実装されています。
SDKのバージョンや環境によりResponses APIが利用できない場合は、
Chat Completions APIに自動的にフォールバックしますが、
これはSDKがResponses APIをサポートしていないという意味ではありません。
"""

import chainlit as cl
from chainlit.types import ThreadDict
from chainlit.input_widget import Select, Switch, Slider, TextInput
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
from utils.responses_handler import responses_handler
from utils.tools_config import tools_config
from utils.persona_manager import persona_manager  # Phase 6: ペルソナ管理
from utils.vector_store_handler import vector_store_handler  # Phase 7: ベクトルストア
from utils.vector_store_sync import get_sync_manager  # ベクトルストア同期管理
from utils.action_helper import ask_confirmation  # Actionヘルパー

# アプリケーション設定
APP_NAME = "AI Workspace"
VERSION = "0.9.0 (Phase 7: Vector Store + Knowledge Base)"


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
    cl.user_session.set("previous_response_id", None)
    cl.user_session.set("message_history", [])
    cl.user_session.set("thread_id", thread.get("id"))
    cl.user_session.set("previous_response_id", None)
    cl.user_session.set("message_history", [])
    
    # Phase 6: デフォルトペルソナを初期化
    await persona_manager.initialize_default_personas()
    
    # Phase 7: ベクトルストアの初期化
    cl.user_session.set("uploaded_files", [])
    
    # ユーザー情報を取得
    user = cl.user_session.get("user")
    if user:
        user_id = user.identifier
        
        # 1層目: .envから取得
        company_vs_id = os.getenv("COMPANY_VECTOR_STORE_ID")
        
        # 2層目: データベースから取得
        data_layer_instance = cl_data._data_layer
        personal_vs_id = None
        
        if data_layer_instance and hasattr(data_layer_instance, 'get_user_vector_store_id'):
            personal_vs_id = await data_layer_instance.get_user_vector_store_id(user_id)
        
        # 3層目: 復元したスレッド情報から取得
        session_vs_id = thread.get("vector_store_id")
        
        # セッションにベクトルストアIDを保存
        cl.user_session.set("vector_store_ids", {
            "company": company_vs_id,
            "personal": personal_vs_id,
            "session": session_vs_id
        })
    else:
        cl.user_session.set("vector_store_ids", {})
    
    # ベクトルストアの同期を実行
    sync_manager = get_sync_manager(vector_store_handler)
    await sync_manager.validate_and_clean()
    print("✅ ベクトルストアの同期が完了しました")
    
    # モデルリストを動的に取得
    available_models = config_manager.get_available_models()
    
    # プロキシ設定を取得
    proxy_settings = config_manager.get_proxy_settings()
    
    # 設定ウィジェットを送信（履歴復元時も必要）
    await cl.ChatSettings(
        [
            Select(
                id="Model",
                label="OpenAI - Model",
                values=available_models,
                initial_index=available_models.index(settings.get("DEFAULT_MODEL", "gpt-4o-mini")) if settings.get("DEFAULT_MODEL", "gpt-4o-mini") in available_models else 0,
            ),
            Switch(id="Tools_Enabled", label="Tools機能 - 有効/無効", initial=tools_config.is_enabled()),
            Switch(id="Web_Search", label="Web検索 - 有効/無効", initial=tools_config.is_tool_enabled("web_search")),
            Switch(
                id="File_Search", 
                label="ファイル検索 - 有効/無効", 
                initial=tools_config.is_tool_enabled("file_search"),
                description="有効時は下記ベクトルストアIDで指定したストアの内容を検索します"
            ),
            TextInput(
                id="Vector_Store_IDs",
                label="ベクトルストアID (カンマ区切り)",
                initial=tools_config.get_vector_store_ids_string(),
                placeholder="vs_xxxxx, vs_yyyyy",
                description="使用するベクトルストアのIDをカンマ区切りで入力"
            ),
            Switch(
                id="Proxy_Enabled",
                label="プロキシ - 有効/無効",
                initial=proxy_settings.get("PROXY_ENABLED", False)
            ),
            TextInput(
                id="Proxy_URL",
                label="プロキシURL",
                initial=proxy_settings.get("HTTPS_PROXY", ""),
                placeholder="http://user:pass@host:port",
            ),
            Slider(
                id="Temperature",
                label="OpenAI - Temperature",
                initial=0.7,
                min=0,
                max=2,
                step=0.1,
                description="応答の創造性を制御 (0=決定的, 1=バランス, 2=創造的)"
            ),
            TextInput(
                id="System_Prompt",
                label="システムプロンプト",
                initial="",
                placeholder="AIの振る舞いを定義するプロンプトを入力...",
            ),
        ]
    ).send()
    
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
    for i, step in enumerate(steps):
        step_type = step.get('type')
        step_id = step.get('id')
        created_at = step.get('createdAt')
        
        app_logger.debug(f"ステップ処理 [{i+1}/{len(steps)}]", 
                        step_id=step_id[:8] if step_id else 'None',
                        type=step_type,
                        created_at=created_at,
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
                    'created_at': created_at,
                    'order': i  # 順序を保持
                })
                app_logger.debug(f"📥 ユーザーメッセージを準備 [{i+1}]", preview=user_input[:50])
                print(f"   📥 ユーザーメッセージを準備 [{i+1}]: {user_input[:50]}...")
        
        # アシスタントメッセージの場合
        elif step_type == 'assistant_message':
            assistant_output = step.get('output', '')
            if assistant_output:
                messages_to_display.append({
                    'type': 'assistant',
                    'content': assistant_output,
                    'id': step_id,
                    'created_at': created_at,
                    'order': i  # 順序を保持
                })
                app_logger.debug(f"🤖 アシスタントメッセージを準備 [{i+1}]", preview=assistant_output[:50])
                print(f"   🤖 アシスタントメッセージを準備 [{i+1}]: {assistant_output[:50]}...")
            else:
                app_logger.warning(f"⚠️ アシスタントメッセージの出力が空です [{i+1}]", step_id=step_id[:8])
                print(f"   ⚠️ アシスタントメッセージの出力が空です [{i+1}]: {step_id[:8]}...")
        
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
                    'created_at': created_at,
                    'order': i  # 順序を保持
                })
                app_logger.debug(f"💻 runステップの出力を準備 [{i+1}]", preview=run_output[:50])
                print(f"   💻 runステップの出力を準備 [{i+1}]: {run_output[:50]}...")
            else:
                app_logger.debug(f"ℹ️ runステップをスキップ [{i+1}]", name=step.get('name', 'N/A'))
                print(f"   ℹ️ runステップをスキップ [{i+1}]: {step.get('name', 'N/A')}")
        
        # その他のタイプ
        else:
            # 必要に応じて他のステップタイプも処理
            app_logger.warning(f"⚠️ 未処理のステップタイプ [{i+1}]: {step_type}")
            print(f"   ⚠️ 未処理のステップタイプ [{i+1}]: {step_type}")
            # outputがあれば表示
            other_output = step.get('output', '')
            if other_output:
                messages_to_display.append({
                    'type': 'system',
                    'content': other_output,
                    'id': step_id,
                    'created_at': created_at,
                    'order': i  # 順序を保持
                })
    
    # messages_to_displayをorderでソートしてから表示（念のため）
    messages_to_display.sort(key=lambda x: x.get('order', 0))
    
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
    
    # Phase 6: デフォルトペルソナを初期化
    await persona_manager.initialize_default_personas()
    
    # Phase 7: ベクトルストアの初期化
    cl.user_session.set("uploaded_files", [])
    
    # ユーザー情報を取得
    user = cl.user_session.get("user")
    if user:
        user_id = user.identifier
        
        # 1層目: .envから取得
        company_vs_id = os.getenv("COMPANY_VECTOR_STORE_ID")
        
        # 2層目: データベースから取得（なければ新規作成）
        data_layer_instance = cl_data._data_layer
        personal_vs_id = None
        
        if data_layer_instance and hasattr(data_layer_instance, 'get_user_vector_store_id'):
            personal_vs_id = await data_layer_instance.get_user_vector_store_id(user_id)
            
            if not personal_vs_id:
                # 新規作成
                new_vs_id = await vector_store_handler.create_vector_store(
                    name=f"Personal VS for {user_id}"
                )
                if new_vs_id:
                    await data_layer_instance.set_user_vector_store_id(user_id, new_vs_id)
                    personal_vs_id = new_vs_id
        
        # セッションにベクトルストアIDを保存
        cl.user_session.set("vector_store_ids", {
            "company": company_vs_id,
            "personal": personal_vs_id,
            "session": None  # セッションVSはファイル添付時に作成
        })
    else:
        cl.user_session.set("vector_store_ids", {})
    
    # モデルリストを動的に取得
    available_models = config_manager.get_available_models()
    
    # プロキシ設定を取得
    proxy_settings = config_manager.get_proxy_settings()
    
    # 設定ウィジェットを送信
    await cl.ChatSettings(
        [
            Select(
                id="Model",
                label="OpenAI - Model",
                values=available_models,
                initial_index=available_models.index(settings.get("DEFAULT_MODEL", "gpt-4o-mini")) if settings.get("DEFAULT_MODEL", "gpt-4o-mini") in available_models else 0,
            ),
            Switch(id="Tools_Enabled", label="Tools機能 - 有効/無効", initial=tools_config.is_enabled()),
            Switch(id="Web_Search", label="Web検索 - 有効/無効", initial=tools_config.is_tool_enabled("web_search")),
            Switch(
                id="File_Search", 
                label="ファイル検索 - 有効/無効", 
                initial=tools_config.is_tool_enabled("file_search"),
                description="有効時は下記ベクトルストアIDで指定したストアの内容を検索します"
            ),
            TextInput(
                id="Vector_Store_IDs",
                label="ベクトルストアID (カンマ区切り)",
                initial=tools_config.get_vector_store_ids_string(),
                placeholder="vs_xxxxx, vs_yyyyy",
                description="使用するベクトルストアのIDをカンマ区切りで入力"
            ),

            Switch(
                id="Proxy_Enabled",
                label="プロキシ - 有効/無効",
                initial=proxy_settings.get("PROXY_ENABLED", False)
            ),
            TextInput(
                id="Proxy_URL",
                label="プロキシURL",
                initial=proxy_settings.get("HTTPS_PROXY", ""),
                placeholder="http://user:pass@host:port",
            ),
            Slider(
                id="Temperature",
                label="OpenAI - Temperature",
                initial=0.7,
                min=0,
                max=2,
                step=0.1,
                description="応答の創造性を制御 (0=決定的, 1=バランス, 2=創造的)"
            ),
            TextInput(
                id="System_Prompt",
                label="システムプロンプト",
                initial="",
                placeholder="AIの振る舞いを定義するプロンプトを入力...",
            ),
        ]
    ).send()
    

    
    # ユーザーIDを取得して個人用ベクトルストアを確認
    current_user = cl.user_session.get("user")
    if current_user:
        user_id = current_user.identifier
        # TODO: データベースから既存のVS IDを取得
        # 現在はセッションごとに新規作成
    
    # アクティブなペルソナを取得して設定
    active_persona = await persona_manager.get_active_persona()
    if active_persona:
        cl.user_session.set("active_persona", active_persona)
        cl.user_session.set("system_prompt", active_persona.get("system_prompt", ""))
        
        # モデルを更新
        if active_persona.get("model"):
            settings["DEFAULT_MODEL"] = active_persona.get("model")
            cl.user_session.set("settings", settings)
    
    # 現在のユーザー情報を取得
    current_user = cl.user_session.get("user")
    app_logger.info(f"👤 新しいセッション開始", user=current_user.identifier if current_user else "anonymous")
    print(f"👤 現在のユーザー: {current_user}")
    
    # APIキーの確認
    api_status = "✅ 設定済み" if settings.get("OPENAI_API_KEY") and settings["OPENAI_API_KEY"] != "your_api_key_here" else "⚠️ 未設定"
    
    # Tools機能の状態を取得
    tools_status = "✅ 有効" if tools_config.is_enabled() else "❌ 無効"
    enabled_tools = tools_config.get_enabled_tools() if tools_config.is_enabled() else []
    
    welcome_message = f"""
# 🎯 {APP_NAME} へようこそ！

**Version**: {VERSION}

## 📊 現在の状態
- **APIキー**: {api_status}
- **デフォルトモデル**: {settings.get('DEFAULT_MODEL', 'gpt-4o-mini')}
- **データレイヤー**: {data_layer_type or '未設定'}
- **Tools機能**: {tools_status}
  {f"- 有効なツール: {', '.join(enabled_tools)}" if enabled_tools else ""}

## 🔧 利用可能なコマンド
- `/help` - コマンド一覧とヘルプを表示
- `/stats` - 統計情報を表示
- `/status` - 現在の設定状態を表示
- `/setkey [APIキー]` - OpenAI APIキーを設定
- `/test` - API接続をテスト
- `/tools` - Tools機能の状態を表示
- `/persona` - ペルソナ一覧を表示
- `/persona [名前]` - ペルソナを切り替え
- `/persona create` - 新しいペルソナを作成
- `/persona edit [名前]` - ペルソナを編集
- `/persona delete [名前]` - ペルソナを削除
- `/vs` または `/vector` - ベクトルストア管理
- `/kb` - ナレッジベースの状態表示

💡 **ヒント**: 
- 会話は永続的に保存されます
- 左上の履歴ボタンから過去の会話にアクセスできます
- Tools機能を有効にすると、Web検索やファイル検索が可能になります
- 📄 ファイルを添付すると自動的にベクトルストアに追加され、AIが内容を理解します

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


@cl.on_settings_update
async def on_settings_update(settings):
    """
    設定が更新された時の処理
    """
    app_logger.info(f"🌀 設定更新", settings=settings)
    
    # モデルの更新
    if "Model" in settings:
        model = settings["Model"]
        current_settings = cl.user_session.get("settings", {})
        current_settings["DEFAULT_MODEL"] = model
        cl.user_session.set("settings", current_settings)
        responses_handler.update_model(model)
        await cl.Message(
            content=f"✅ モデルを {model} に変更しました",
            author="System"
        ).send()
    
    # Tools機能全体の更新
    if "Tools_Enabled" in settings:
        if settings["Tools_Enabled"]:
            tools_config.update_enabled(True)
            await cl.Message(content="✅ Tools機能を有効にしました", author="System").send()
        else:
            tools_config.update_enabled(False)
            await cl.Message(content="❌ Tools機能を無効にしました", author="System").send()
    
    # Web検索の更新
    if "Web_Search" in settings:
        if settings["Web_Search"]:
            tools_config.update_tool_status("web_search", True)
            await cl.Message(content="✅ Web検索を有効にしました", author="System").send()
        else:
            tools_config.update_tool_status("web_search", False)
            await cl.Message(content="❌ Web検索を無効にしました", author="System").send()
    
    # ファイル検索の更新
    if "File_Search" in settings:
        if settings["File_Search"]:
            tools_config.update_tool_status("file_search", True)
            await cl.Message(content="✅ ファイル検索を有効にしました", author="System").send()
        else:
            tools_config.update_tool_status("file_search", False)
            await cl.Message(content="❌ ファイル検索を無効にしました", author="System").send()
    
    # ベクトルストアIDの更新
    if "Vector_Store_IDs" in settings:
        vector_store_ids = settings["Vector_Store_IDs"]
        tools_config.update_vector_store_ids(vector_store_ids)
        ids_list = [id.strip() for id in vector_store_ids.split(',') if id.strip()]
        if ids_list:
            await cl.Message(
                content=f"✅ ベクトルストアIDを設定しました: {', '.join(ids_list)}",
                author="System"
            ).send()
        else:
            await cl.Message(
                content="ℹ️ ベクトルストアIDをクリアしました",
                author="System"
            ).send()
    
    # プロキシ設定の更新
    if "Proxy_Enabled" in settings or "Proxy_URL" in settings:
        proxy_enabled = settings.get("Proxy_Enabled", False)
        proxy_url = settings.get("Proxy_URL", "")
        
        # プロキシ設定を保存
        config_manager.set_proxy_settings(
            http_proxy=proxy_url,
            https_proxy=proxy_url,
            proxy_enabled=proxy_enabled
        )
        
        # 環境変数を更新
        if proxy_enabled and proxy_url:
            os.environ["HTTPS_PROXY"] = proxy_url
            os.environ["HTTP_PROXY"] = proxy_url
            await cl.Message(
                content=f"✅ プロキシを有効にしました: {proxy_url}",
                author="System"
            ).send()
        else:
            os.environ.pop("HTTPS_PROXY", None)
            os.environ.pop("HTTP_PROXY", None)
            await cl.Message(
                content="❌ プロキシを無効にしました",
                author="System"
            ).send()
    
    # Temperatureの更新
    if "Temperature" in settings:
        temperature = settings["Temperature"]
        # アクティブなペルソナがある場合はその設定も更新
        active_persona = cl.user_session.get("active_persona")
        if active_persona:
            active_persona["temperature"] = temperature
            cl.user_session.set("active_persona", active_persona)
        await cl.Message(
            content=f"🌡️ Temperatureを {temperature} に変更しました",
            author="System"
        ).send()
    
    # システムプロンプトの更新
    if "System_Prompt" in settings:
        system_prompt = settings["System_Prompt"]
        cl.user_session.set("system_prompt", system_prompt)
        if system_prompt:
            await cl.Message(
                content=f"✅ システムプロンプトを設定しました:\n```\n{system_prompt[:200]}...\n```",
                author="System"
            ).send()
        else:
            await cl.Message(
                content="✅ システムプロンプトをクリアしました",
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
    
    # Phase 7: ファイルアップロード処理
    if message.elements:
        # ファイル処理中のフラグを設定
        processing_msg = await cl.Message(
            content="📤 ファイルをアップロード中です。しばらくお待ちください...",
            author="System"
        ).send()
        
        uploaded_file_ids = []
        for element in message.elements:
            if element.type == "file":
                try:
                    # ファイルを処理
                    file_id = await vector_store_handler.process_uploaded_file(element)
                    if file_id:
                        uploaded_file_ids.append(file_id)
                        
                        # セッションのアップロードファイルリストに追加
                        uploaded_files = cl.user_session.get("uploaded_files", [])
                        uploaded_files.append({
                            "file_id": file_id,
                            "filename": element.name,
                            "timestamp": datetime.now().isoformat()
                        })
                        cl.user_session.set("uploaded_files", uploaded_files)
                        
                        # 処理状況を更新
                        processing_msg.content = f"✅ ファイルをアップロードしました: {element.name}"
                        await processing_msg.update()
                except Exception as e:
                    processing_msg.content = f"❌ ファイルアップロードエラー: {e}"
                    await processing_msg.update()
        
        # アップロードされたファイルをベクトルストアに追加するか確認
        if uploaded_file_ids:
            # ベクトルストアに追加するか確認（ユーザーの応答を待つ）
            res = await cl.AskActionMessage(
                content=f"{len(uploaded_file_ids)}件のファイルをナレッジベースに追加しますか？",
                actions=[
                    cl.Action(name="add_to_kb", value="yes", payload={"action": "yes"}, label="はい"),
                    cl.Action(name="skip", value="no", payload={"action": "no"}, label="いいえ")
                ],
                timeout=60  # 60秒のタイムアウトを設定
            ).send()
            
            # ユーザーの応答を待つ
            if res and res.get("payload", {}).get("action") == "yes":
                # ベクトルストアIDを取得
                vs_ids = cl.user_session.get("vector_store_ids", {})
                session_vs_id = vs_ids.get("session")
                thread_id = cl.user_session.get("thread_id") or cl.context.session.thread_id
                
                # セッション用ベクトルストアが未作成の場合は作成
                if not session_vs_id:
                    session_vs_id = await vector_store_handler.create_vector_store(
                        name=f"Session VS for thread {thread_id[:8] if thread_id else 'unknown'}"
                    )
                    if session_vs_id:
                        # データベースに保存
                        data_layer_instance = cl_data._data_layer
                        if data_layer_instance and hasattr(data_layer_instance, 'update_thread_vector_store'):
                            await data_layer_instance.update_thread_vector_store(thread_id, session_vs_id)
                        
                        vs_ids["session"] = session_vs_id
                        cl.user_session.set("vector_store_ids", vs_ids)
                
                # ファイルをベクトルストアに追加
                if session_vs_id:
                    success = await vector_store_handler.add_files_to_vector_store(session_vs_id, uploaded_file_ids)
                    if success:
                        await cl.Message(
                            content=f"✅ {len(uploaded_file_ids)}個のファイルをナレッジベースに追加しました。",
                            author="System"
                        ).send()
                    else:
                        await cl.Message(
                            content="❌ ファイルのベクトルストアへの追加に失敗しました。",
                            author="System"
                        ).send()
            else:
                await cl.Message(
                    content="ℹ️ ファイルはアップロードされましたが、ナレッジベースには追加されませんでした。",
                    author="System"
                ).send()
        
        # ファイルがアップロードされた場合でも、メッセージがあれば処理を続ける
        if not user_input:
            # アップロード完了メッセージ
            await cl.Message(
                content="✅ ファイルアップロード処理が完了しました。メッセージを入力してください。",
                author="System"
            ).send()
            return
    
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
    
    # メッセージ履歴を管理
    message_history = cl.user_session.get("message_history", [])
    
    # Responses APIを使用してAI応答を生成
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # 履歴を追加（最大10メッセージ）
    messages.extend(message_history[-10:])
    messages.append({"role": "user", "content": user_input})
    
    # Tools機能の状態をログに記録
    tools_enabled = tools_config.is_enabled()
    if tools_enabled:
        enabled_tools = tools_config.get_enabled_tools()
        app_logger.debug(f"🔧 Tools機能有効", tools=enabled_tools)
    
    # AIメッセージを先に作成（ストリーミング用）
    ai_message = cl.Message(content="", author="Assistant")
    await ai_message.send()
    
    response_text = ""
    tool_calls = None
    previous_response_id = cl.user_session.get("previous_response_id")
    
    # ============================================================
    # Responses APIを呼び出し（ストリーミング有効）
    # OpenAI SDKはResponses APIを正式にサポートしています
    # 参照: openai responseAPI reference (Text generation).md
    # 参照: openai responseAPI reference (Conversation state).md
    # ============================================================
    async for chunk in responses_handler.create_response(
        messages=messages,
        model=model,
        stream=True,
        use_tools=tools_enabled,
        previous_response_id=previous_response_id
    ):
        if "error" in chunk:
            app_logger.error(f"API Error: {chunk['error']}")
            # エラーメッセージをより分かりやすく
            error_detail = chunk.get('error', {})
            if isinstance(error_detail, dict):
                error_msg = error_detail.get('message', str(error_detail))
                error_type = error_detail.get('type', 'unknown_error')
                
                # ベクトルストア関連のエラーの場合
                if 'vector_store_ids' in error_msg:
                    ai_message.content = (
                        "❌ ファイル検索エラー\n\n"
                        "📁 ベクトルストアが設定されていません。\n\n"
                        "以下のいずれかをお試しください：\n"
                        "1. `/vs create [名前]` で新しいベクトルストアを作成\n"
                        "2. 設定ウィジェットでベクトルストアIDを設定\n"
                        "3. ファイル検索を一時的に無効化"
                    )
                else:
                    ai_message.content = f"❌ APIエラー: {error_msg}\n\nエラータイプ: {error_type}"
            else:
                ai_message.content = f"❌ エラー: {chunk['error']}"
            await ai_message.update()
            response_text = None
            break
        
        # Responses APIのストリーミングイベント処理
        elif chunk.get("type") == "text_delta":
            # テキストデルタイベント
            if chunk.get("content"):
                response_text += chunk["content"]
                await ai_message.stream_token(chunk["content"])
        
        elif chunk.get("type") == "response_complete":
            # 完了イベント
            if chunk.get("id"):
                cl.user_session.set("previous_response_id", chunk["id"])
            if chunk.get("output_text") and not response_text:
                response_text = chunk["output_text"]
                ai_message.content = response_text
                await ai_message.update()
            break
        
        # Chat Completions APIのフォールバック処理
        elif "choices" in chunk and chunk["choices"]:
            choice = chunk["choices"][0]
            
            # ストリーミングモード（deltaを処理）
            if "delta" in choice:
                delta = choice["delta"]
                
                # テキストコンテンツの処理
                if delta.get("content"):
                    response_text += delta["content"]
                    await ai_message.stream_token(delta["content"])
                
                # finish_reasonがある場合は完了
                if choice.get("finish_reason"):
                    # response_idを保存（会話継続用）
                    if "id" in chunk:
                        cl.user_session.set("previous_response_id", chunk["id"])
                    break
            
            # 非ストリーミングモード（messageを処理）
            elif "message" in choice:
                message_data = choice["message"]
                
                # 通常の応答
                if message_data.get("content"):
                    response_text = message_data["content"]
                    ai_message.content = response_text
                    await ai_message.update()
            
            # ツール呼び出しがある場合
            if message_data.get("tool_calls"):
                tool_calls = message_data["tool_calls"]
                app_logger.debug(f"🔧 ツール呼び出しを検出", count=len(tool_calls))
                
                # ツール呼び出しをUIに表示（設定による）
                if tools_config.get_setting("show_tool_calls", True):
                    for tc in tool_calls:
                        tool_type = tc.get("type")
                        if tool_type == "web_search":
                            query = tc.get("web_search", {}).get("query", "")
                            await cl.Message(
                                content=f"🔍 **Web検索中**: `{query}`",
                                author="System"
                            ).send()
                        elif tool_type == "file_search":
                            await cl.Message(
                                content=f"📁 **ファイル検索中**",
                                author="System"
                            ).send()
                
                # ツールを実行
                tool_results = await responses_handler.handle_tool_calls(tool_calls, messages)
                
                # ツール結果を表示（設定による）
                if tools_config.get_setting("show_tool_results", True):
                    for result in tool_results:
                        await cl.Message(
                            content=f"📊 **ツール結果**:\n```\n{result['content'][:500]}...\n```",
                            author="System"
                        ).send()
                
                # ツール結果をメッセージに追加
                messages.append(message_data)
                messages.extend(tool_results)
                
                # ツール結果を踏まえて再度APIを呼び出し
                final_msg = cl.Message(content="", author="Assistant")
                await final_msg.send()
                
                async for final_chunk in responses_handler.create_response(
                    messages=messages,
                    model=model,
                    stream=True,
                    use_tools=False,  # ツールは一度だけ使用
                    previous_response_id=previous_response_id
                ):
                    # Responses APIイベント
                    if final_chunk.get("type") == "text_delta":
                        if final_chunk.get("content"):
                            response_text += final_chunk["content"]
                            await final_msg.stream_token(final_chunk["content"])
                    
                    elif final_chunk.get("type") == "response_complete":
                        if final_chunk.get("output_text") and not response_text:
                            response_text = final_chunk["output_text"]
                            final_msg.content = response_text
                            await final_msg.update()
                        break
                    
                    # Chat Completions APIフォールバック
                    elif "choices" in final_chunk and final_chunk["choices"]:
                        final_choice = final_chunk["choices"][0]
                        
                        # ストリーミングモード
                        if "delta" in final_choice:
                            delta = final_choice["delta"]
                            if delta.get("content"):
                                response_text += delta["content"]
                                await final_msg.stream_token(delta["content"])
                            
                            if final_choice.get("finish_reason"):
                                break
                        
                        # 非ストリーミングモード
                        elif "message" in final_choice:
                            final_message = final_choice["message"]
                            if final_message.get("content"):
                                response_text = final_message["content"]
                                final_msg.content = response_text
                                await final_msg.update()
                            break
            
            # response_idを保存（会話継続用）
            if "id" in chunk:
                cl.user_session.set("previous_response_id", chunk["id"])
            
            break
    
    if response_text:
        # ストリーミング完了時の処理
        await ai_message.update()  # ストリーミング完了を通知
        
        # メッセージ履歴を更新
        message_history.append({"role": "user", "content": user_input})
        message_history.append({"role": "assistant", "content": response_text})
        
        # 履歴を20メッセージに制限
        if len(message_history) > 20:
            message_history = message_history[-20:]
        
        cl.user_session.set("message_history", message_history)
        
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
        # response_textがnullの場合は、すでにエラーメッセージが表示されているはず
        app_logger.error(f"AI応答生成失敗", user_input=user_input[:100])
        # ai_messageにエラーが設定されていない場合のみ設定
        if not ai_message.content or ai_message.content == "":
            ai_message.content = "❌ AI応答の生成に失敗しました。"
            await ai_message.update()


async def handle_command(user_input: str):
    """コマンドを処理"""
    parts = user_input.split(maxsplit=2)
    cmd = parts[0].lower()
    
    app_logger.debug(f"🎮 コマンド処理", command=cmd)
    
    if cmd == "/help":
        await show_help()
    elif cmd == "/stats":
        await show_statistics()
    elif cmd == "/setkey":
        if len(parts) > 1:
            await set_api_key(parts[1])
        else:
            await cl.Message(
                content="❌ APIキーを指定してください。\n例: `/setkey sk-...`",
                author="System"
            ).send()
    elif cmd == "/test":
        await test_connection()
    elif cmd == "/status":
        await show_status()
    elif cmd == "/settings":
        await show_settings()
    elif cmd == "/tools":
        await show_tools_status()
    elif cmd == "/persona" or cmd == "/personas":
        if len(parts) == 1:
            await show_personas()
        elif len(parts) == 2:
            await switch_persona(parts[1])
        else:
            action = parts[1].lower()
            if action == "create":
                await create_persona_interactive()
            elif action == "delete":
                if len(parts) > 2:
                    await delete_persona(parts[2])
                else:
                    await cl.Message(
                        content="❌ 削除するペルソナ名を指定してください。\n例: `/persona delete creative`",
                        author="System"
                    ).send()
            elif action == "edit" or action == "update":
                if len(parts) > 2:
                    await edit_persona(parts[2])
                else:
                    await cl.Message(
                        content="❌ 編集するペルソナ名を指定してください。\n例: `/persona edit プログラミング専門家`",
                        author="System"
                    ).send()
            else:
                await switch_persona(parts[1])
    elif cmd == "/kb" or cmd == "/knowledge":
        if len(parts) == 1:
            await show_knowledge_base()
        elif len(parts) > 1:
            action = parts[1].lower()
            if action == "clear":
                await clear_knowledge_base()
            elif action == "list":
                await show_knowledge_base()
            else:
                await cl.Message(
                    content="❌ 不明なコマンド\n使い方: `/kb` - 状態表示, `/kb clear` - クリア",
                    author="System"
                ).send()
    elif cmd == "/vs" or cmd == "/vector":
        if len(parts) == 1:
            await show_vector_stores()
        else:
            action = parts[1].lower()
            if action == "create":
                if len(parts) > 2:
                    await create_vector_store(parts[2])
                else:
                    await create_vector_store("Personal Knowledge Base")
            elif action == "list":
                await show_vector_stores()
            elif action == "info":
                if len(parts) > 2:
                    await show_vector_store_info(parts[2])
                else:
                    await cl.Message(
                        content="❌ ベクトルストアIDを指定してください。\n例: `/vs info vs_xxxxx`",
                        author="System"
                    ).send()
            elif action == "delete":
                if len(parts) > 2:
                    await delete_vector_store(parts[2])
                else:
                    await cl.Message(
                        content="❌ 削除するベクトルストアIDを指定してください。\n例: `/vs delete vs_xxxxx`",
                        author="System"
                    ).send()
            elif action == "files":
                if len(parts) > 2:
                    await show_vector_store_files(parts[2])
                else:
                    await cl.Message(
                        content="❌ ベクトルストアIDを指定してください。\n例: `/vs files vs_xxxxx`",
                        author="System"
                    ).send()
            elif action == "use":
                if len(parts) > 2:
                    await set_personal_vector_store(parts[2])
                else:
                    await cl.Message(
                        content="❌ 使用するベクトルストアIDを指定してください。\n例: `/vs use vs_xxxxx`",
                        author="System"
                    ).send()
            elif action == "sync":
                await sync_vector_stores()
            elif action == "rename":
                if len(parts) > 2:
                    # IDと新しい名前を分割
                    rename_parts = user_input[len("/vs rename"):].strip().split(maxsplit=1)
                    if len(rename_parts) == 2:
                        await rename_vector_store(rename_parts[0], rename_parts[1])
                    else:
                        await cl.Message(
                            content="❌ ベクトルストアIDと新しい名前を指定してください。\n例: `/vs rename vs_xxxxx 新しい名前`",
                            author="System"
                        ).send()
                else:
                    await cl.Message(
                        content="❌ ベクトルストアIDと新しい名前を指定してください。\n例: `/vs rename vs_xxxxx 新しい名前`",
                        author="System"
                    ).send()
            else:
                await cl.Message(
                    content="❌ 不明なアクション: " + action + "\n使用可能: create, sync, list, info, delete, files, use, rename",
                    author="System"
                ).send()
    else:
        await cl.Message(
            content=f"❌ 不明なコマンド: {cmd}\n`/help` でコマンド一覧を確認してください。",
            author="System"
        ).send()


async def handle_file_upload(elements):
    """ファイルアップロードを処理"""
    # ファイルを抽出
    files = [element for element in elements if isinstance(element, cl.File)]
    
    if not files:
        return
    
    # 個人ベクトルストアが設定されているか確認
    personal_vs_id = cl.user_session.get("personal_vs_id") or vector_store_handler.personal_vs_id
    
    if not personal_vs_id:
        # ベクトルストアがない場合は作成
        await cl.Message(
            content="📁 ベクトルストアがないため、新しく作成します...",
            author="System"
        ).send()
        
        personal_vs_id = await vector_store_handler.create_vector_store("Personal Knowledge Base")
        
        if personal_vs_id:
            cl.user_session.set("personal_vs_id", personal_vs_id)
            vector_store_handler.personal_vs_id = personal_vs_id
        else:
            await cl.Message(
                content="❌ ベクトルストアの作成に失敗しました。",
                author="System"
            ).send()
            return
    
    # ファイルをアップロード
    await cl.Message(
        content=f"🔄 {len(files)}個のファイルをアップロード中...",
        author="System"
    ).send()
    
    successful_ids, failed_files = await vector_store_handler.process_uploaded_files(files)
    
    # 結果を表示
    if successful_ids:
        # ベクトルストアに追加
        success = await vector_store_handler.add_files_to_vector_store(personal_vs_id, successful_ids)
        
        if success:
            message = f"✅ {len(successful_ids)}個のファイルをベクトルストアに追加しました\n\n"
            message += "📁 ベクトルストアID: `" + personal_vs_id + "`\n\n"
            message += "ファイルの内容に関する質問に答えられるようになりました。"
            
            if failed_files:
                message += "\n\n⚠️ 失敗したファイル:\n"
                for failed in failed_files:
                    message += f"- {failed}\n"
            
            await cl.Message(content=message, author="System").send()
        else:
            await cl.Message(
                content="❌ ファイルのベクトルストアへの追加に失敗しました。",
                author="System"
            ).send()
    else:
        message = "❌ すべてのファイルのアップロードに失敗しました\n\n"
        if failed_files:
            message += "失敗したファイル:\n"
            for failed in failed_files:
                message += f"- {failed}\n"
        await cl.Message(content=message, author="System").send()


async def show_help():
    """ヘルプメッセージを表示"""
    help_message = """
# 📚 コマンド一覧

## 基本コマンド
- `/help` - このヘルプを表示
- `/stats` - 現在のセッションの統計を表示
- `/status` - 設定状態を表示

## 設定コマンド
- `/setkey [APIキー]` - OpenAI APIキーを設定
- `/test` - API接続をテスト

💡 **ヒント**: モデル変更、システムプロンプト設定、Temperature調整は画面右上の設定パネルから行えます。

## Tools機能
- `/tools` - Tools機能の現在の設定を表示
- **設定の変更は画面右上の設定パネルから行ってください**

## ペルソナ管理
- `/persona` - ペルソナ一覧を表示
- `/persona [名前]` - ペルソナを切り替え
- `/persona create` - 新しいペルソナを作成
- `/persona edit [名前]` - ペルソナを編集（モデル/Temperature/プロンプト等）
- `/persona delete [名前]` - カスタムペルソナを削除

## ベクトルストア管理
- `/vs` または `/vector` - ベクトルストア一覧を表示
- `/vs sync` - ベクトルストアを同期
- `/vs create [名前]` - 新しいベクトルストアを作成
- `/vs info [ID]` - 詳細情報を表示
- `/vs files [ID]` - ファイル一覧を表示
- `/vs use [ID]` - ベクトルストアを使用
- `/vs rename [ID] [新しい名前]` - ベクトルストアの名前を変更
- `/vs delete [ID]` - ベクトルストアを削除

## 💡 ヒント
- 会話履歴は自動的に保存されます
- 左上の履歴ボタンから過去の会話にアクセスできます
- Tools機能を有効にすると、AIが必要に応じてWeb検索やファイル検索を実行します
"""
    await cl.Message(content=help_message, author="System").send()


async def show_tools_status():
    """Tools機能の状態を表示"""
    status = "✅ 有効" if tools_config.is_enabled() else "❌ 無効"
    enabled_tools = tools_config.get_enabled_tools()
    
    tools_message = f"""
# 🔧 Tools機能の設定

## 全体の状態
- **Tools機能**: {status}

## 個別ツールの状態
- **Web検索**: {"✅ 有効 (web_search)" if tools_config.is_tool_enabled("web_search") else "❌ 無効 (web_search)"}
- **ファイル検索**: {"✅ 有効 (file_search)" if tools_config.is_tool_enabled("file_search") else "❌ 無効 (file_search)"}
- **コードインタープリター**: {"✅ 有効 (code_interpreter)" if tools_config.is_tool_enabled("code_interpreter") else "❌ 無効 (code_interpreter)"}
- **カスタム関数**: {"✅ 有効 (custom_functions)" if tools_config.is_tool_enabled("custom_functions") else "❌ 無効 (custom_functions)"}

## 設定
- **ツール選択**: {tools_config.get_setting("tool_choice", "auto")}
- **並列実行**: {"✅ 有効" if tools_config.get_setting("parallel_tool_calls", True) else "❌ 無効"}
- **最大ツール数/呼び出し**: {tools_config.get_setting("max_tools_per_call", 5)}
- **Web検索最大結果数**: {tools_config.get_setting("web_search_max_results", 5)}
- **ファイル検索最大チャンク数**: {tools_config.get_setting("file_search_max_chunks", 20)}
- **ツール呼び出し表示**: {"✅ 有効" if tools_config.get_setting("show_tool_calls", True) else "❌ 無効"}
- **ツール結果表示**: {"✅ 有効" if tools_config.get_setting("show_tool_results", True) else "❌ 無効"}

## 設定の変更方法
- **画面右上の設定パネルから各ツールの有効/無効を切り替えてください**
- コマンドによる個別設定は廃止されました
"""
    
    await cl.Message(content=tools_message, author="System").send()


async def handle_tools_command(action: str, target: str):
    """Tools機能のコマンドを処理"""
    if action == "enable":
        if target == "all":
            tools_config.config["enabled"] = True
            for tool_name in tools_config.config.get("tools", {}):
                tools_config.update_tool_status(tool_name, True)
            await cl.Message(
                content="✅ すべてのツールを有効化しました",
                author="System"
            ).send()
        elif target in tools_config.config.get("tools", {}):
            tools_config.config["enabled"] = True
            tools_config.update_tool_status(target, True)
            await cl.Message(
                content=f"✅ {target}を有効化しました",
                author="System"
            ).send()
        else:
            await cl.Message(
                content=f"❌ 不明なツール: {target}",
                author="System"
            ).send()
    
    elif action == "disable":
        if target == "all":
            tools_config.config["enabled"] = False
            await cl.Message(
                content="✅ すべてのツールを無効化しました",
                author="System"
            ).send()
        elif target in tools_config.config.get("tools", {}):
            tools_config.update_tool_status(target, False)
            await cl.Message(
                content=f"✅ {target}を無効化しました",
                author="System"
            ).send()
        else:
            await cl.Message(
                content=f"❌ 不明なツール: {target}",
                author="System"
            ).send()
    
    else:
        await cl.Message(
            content=f"❌ 不明なアクション: {action}",
            author="System"
            ).send()


async def change_model(model: str):
    """モデルを変更"""
    valid_models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    
    if model not in valid_models:
        await cl.Message(
            content=f"❌ 無効なモデル名です。\n利用可能: {', '.join(valid_models)}",
            author="System"
        ).send()
        return
    
    settings = cl.user_session.get("settings", {})
    settings["DEFAULT_MODEL"] = model
    cl.user_session.set("settings", settings)
    
    config_manager.update_setting("DEFAULT_MODEL", model)
    responses_handler.update_model(model)
    
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
- **Tools機能**: {"有効" if tools_config.is_enabled() else "無効"}
  - **有効なツール**: {', '.join(tools_config.get_enabled_tools()) if tools_config.get_enabled_tools() else "なし"}

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
    cl.user_session.set("previous_response_id", None)
    cl.user_session.set("message_history", [])


async def set_api_key(api_key: str):
    """APIキーを設定"""
    success = config_manager.set_api_key(api_key)
    if success:
        new_settings = config_manager.get_all_settings()
        cl.user_session.set("settings", new_settings)
        responses_handler.update_api_key(api_key)
        
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


async def show_personas():
    """ペルソナ一覧を表示"""
    personas = await persona_manager.get_all_personas()
    active_persona = cl.user_session.get("active_persona")
    
    message = "# 🎭 ペルソナ一覧\n\n"
    
    for persona in personas:
        is_active = active_persona and persona.get("name") == active_persona.get("name")
        status = "✅ [アクティブ]" if is_active else ""
        
        message += f"## {persona.get('name')} {status}\n"
        message += f"{persona.get('description', 'No description')}\n"
        message += f"- 🤖 Model: {persona.get('model', 'gpt-4o-mini')}\n"
        message += f"- 🌡️ Temperature: {persona.get('temperature', 0.7)}\n"
        
        if persona.get('tags'):
            message += f"- 🏷️ Tags: {', '.join(persona.get('tags', []))}\n"
        message += "\n"
    
    message += "\n💡 **使い方**: `/persona [ペルソナ名]` で切り替え\n"
    message += "💡 **新規作成**: `/persona create` で新しいペルソナを作成\n"
    message += "💡 **削除**: `/persona delete [ペルソナ名]` で削除"
    
    await cl.Message(content=message, author="System").send()


async def switch_persona(persona_name: str):
    """ペルソナを切り替え"""
    personas = await persona_manager.get_all_personas()
    
    # 名前でペルソナを検索
    target_persona = None
    for persona in personas:
        if persona.get("name").lower() == persona_name.lower():
            target_persona = persona
            break
    
    if target_persona:
        # アクティブに設定
        if hasattr(persona_manager, 'set_active_persona'):
            await persona_manager.set_active_persona(target_persona.get("id", target_persona.get("name")))
        
        # セッションを更新
        cl.user_session.set("active_persona", target_persona)
        cl.user_session.set("system_prompt", target_persona.get("system_prompt", ""))
        
        # モデルを更新
        settings = cl.user_session.get("settings", {})
        if target_persona.get("model"):
            settings["DEFAULT_MODEL"] = target_persona.get("model")
            cl.user_session.set("settings", settings)
            
            # responses_handlerのモデルも更新
            responses_handler.update_model(target_persona.get("model"))
        
        # 表示
        info = persona_manager.format_persona_info(target_persona)
        await cl.Message(
            content=f"✅ ペルソナを切り替えました\n\n{info}",
            author="System"
        ).send()
    else:
        await cl.Message(
            content=f"❌ ペルソナ '{persona_name}' が見つかりません。`/persona` で一覧を確認してください。",
            author="System"
        ).send()


async def create_persona_interactive():
    """インタラクティブにペルソナを作成"""
    # 名前を入力
    res = await cl.AskUserMessage(
        content="🎭 新しいペルソナの**名前**を入力してください:",
        timeout=60
    ).send()
    
    if not res:
        await cl.Message(content="❌ キャンセルされました", author="System").send()
        return
    
    name = res["output"]
    
    # 説明を入力
    res = await cl.AskUserMessage(
        content="📝 ペルソナの**説明**を入力してください:",
        timeout=60
    ).send()
    
    if not res:
        await cl.Message(content="❌ キャンセルされました", author="System").send()
        return
    
    description = res["output"]
    
    # システムプロンプトを入力
    res = await cl.AskUserMessage(
        content="🤖 **システムプロンプト**を入力してください (AIの振る舞いを定義):",
        timeout=120
    ).send()
    
    if not res:
        await cl.Message(content="❌ キャンセルされました", author="System").send()
        return
    
    system_prompt = res["output"]
    
    # モデルを選択
    models_list = "\n".join([f"- {model}" for model in persona_manager.AVAILABLE_MODELS])
    res = await cl.AskUserMessage(
        content=f"🤖 使用する**モデル**を選択してください:\n{models_list}\n\n(デフォルト: gpt-4o-mini)",
        timeout=60
    ).send()
    
    model = "gpt-4o-mini"
    if res:
        input_model = res["output"].strip()
        if input_model in persona_manager.AVAILABLE_MODELS:
            model = input_model
    
    # Temperatureを入力
    res = await cl.AskUserMessage(
        content="🌡️ **Temperature** (0.0-2.0, デフォルト: 0.7)\n低い値=より一貫性がある、高い値=より創造的:",
        timeout=60
    ).send()
    
    temperature = 0.7
    if res:
        try:
            temp_value = float(res["output"])
            if 0.0 <= temp_value <= 2.0:
                temperature = temp_value
        except ValueError:
            pass
    
    # タグを入力
    res = await cl.AskUserMessage(
        content="🏷️ **タグ** (カンマ区切り、例: technical, creative, business):",
        timeout=60
    ).send()
    
    tags = []
    if res:
        tags = [tag.strip() for tag in res["output"].split(",") if tag.strip()]
    
    # ペルソナを作成
    persona_data = {
        "name": name,
        "description": description,
        "system_prompt": system_prompt,
        "model": model,
        "temperature": temperature,
        "tags": tags
    }
    
    persona_id = await persona_manager.create_persona(persona_data)
    
    # 確認メッセージ
    info = persona_manager.format_persona_info(persona_data)
    await cl.Message(
        content=f"✅ ペルソナを作成しました\n\n{info}\n\n`/persona {name}` で切り替えできます。",
        author="System"
    ).send()


async def delete_persona(persona_name: str):
    """ペルソナを削除"""
    personas = await persona_manager.get_all_personas()
    
    # 名前でペルソナを検索
    target_persona = None
    for persona in personas:
        if persona.get("name").lower() == persona_name.lower():
            target_persona = persona
            break
    
    if target_persona:
        # デフォルトペルソナは削除できない
        if target_persona.get("name") in ["汎用アシスタント", "プログラミング専門家", "ビジネスアナリスト", "クリエイティブライター", "学習サポーター"]:
            await cl.Message(
                content="❌ デフォルトペルソナは削除できません。",
                author="System"
            ).send()
            return
        
        # 削除実行
        success = await persona_manager.delete_persona(target_persona.get("id", target_persona.get("name")))
        
        if success:
            await cl.Message(
                content=f"✅ ペルソナ '{persona_name}' を削除しました。",
                author="System"
            ).send()
        else:
            await cl.Message(
                content=f"❌ ペルソナ '{persona_name}' の削除に失敗しました。",
                author="System"
            ).send()
    else:
        await cl.Message(
            content=f"❌ ペルソナ '{persona_name}' が見つかりません。",
            author="System"
        ).send()


async def edit_persona(persona_name: str):
    """既存のペルソナを編集"""
    personas = await persona_manager.get_all_personas()
    
    # 名前でペルソナを検索
    target_persona = None
    for persona in personas:
        if persona.get("name").lower() == persona_name.lower():
            target_persona = persona
            break
    
    if not target_persona:
        await cl.Message(
            content=f"❌ ペルソナ '{persona_name}' が見つかりません。`/persona` で一覧を確認してください。",
            author="System"
        ).send()
        return
    
    # 現在の設定を表示
    current_info = persona_manager.format_persona_info(target_persona)
    await cl.Message(
        content=f"📝 現在の設定:\n\n{current_info}\n\n編集する項目を選択してください。",
        author="System"
    ).send()
    
    # 編集する項目を選択
    res = await cl.AskActionMessage(
        content="どの項目を編集しますか？",
        actions=[
            cl.Action(name="edit_model", payload={"type": "model"}, label="🤖 モデル"),
            cl.Action(name="edit_temp", payload={"type": "temperature"}, label="🌡️ Temperature"),
            cl.Action(name="edit_prompt", payload={"type": "system_prompt"}, label="📝 システムプロンプト"),
            cl.Action(name="edit_desc", payload={"type": "description"}, label="📄 説明"),
            cl.Action(name="cancel", payload={"type": "cancel"}, label="❌ キャンセル")
        ],
        timeout=60
    ).send()
    
    if not res or res.get("payload", {}).get("type") == "cancel":
        await cl.Message(content="❌ 編集をキャンセルしました", author="System").send()
        return
    
    edit_type = res.get("payload", {}).get("type")
    updates = {}
    
    if edit_type == "model":
        # モデルを選択
        models_list = "\n".join([f"- {model}" for model in persona_manager.AVAILABLE_MODELS])
        res = await cl.AskUserMessage(
            content=f"🤖 新しい**モデル**を選択してください:\n{models_list}\n\n現在: {target_persona.get('model', 'gpt-4o-mini')}",
            timeout=60
        ).send()
        
        if res:
            input_model = res["output"].strip()
            if input_model in persona_manager.AVAILABLE_MODELS:
                updates["model"] = input_model
            else:
                await cl.Message(
                    content=f"❌ 無効なモデル名です。利用可能なモデルから選択してください。",
                    author="System"
                ).send()
                return
    
    elif edit_type == "temperature":
        # Temperatureを入力
        res = await cl.AskUserMessage(
            content=f"🌡️ 新しい**Temperature** (0.0-2.0)を入力してください:\n現在: {target_persona.get('temperature', 0.7)}",
            timeout=60
        ).send()
        
        if res:
            try:
                temp_value = float(res["output"])
                if 0.0 <= temp_value <= 2.0:
                    updates["temperature"] = temp_value
                else:
                    await cl.Message(
                        content="❌ Temperatureは0.0から2.0の範囲で入力してください。",
                        author="System"
                    ).send()
                    return
            except ValueError:
                await cl.Message(
                    content="❌ 無効な数値です。",
                    author="System"
                ).send()
                return
    
    elif edit_type == "system_prompt":
        # システムプロンプトを入力
        res = await cl.AskUserMessage(
            content=f"📝 新しい**システムプロンプト**を入力してください:\n\n現在の設定:\n{target_persona.get('system_prompt', '')[:200]}...",
            timeout=120
        ).send()
        
        if res:
            updates["system_prompt"] = res["output"]
    
    elif edit_type == "description":
        # 説明を入力
        res = await cl.AskUserMessage(
            content=f"📄 新しい**説明**を入力してください:\n現在: {target_persona.get('description', '')}",
            timeout=60
        ).send()
        
        if res:
            updates["description"] = res["output"]
    
    # 更新を実行
    if updates:
        success = await persona_manager.update_persona(
            target_persona.get("id", target_persona.get("name")),
            updates
        )
        
        if success:
            # 更新後のペルソナを取得
            updated_persona = await persona_manager.get_persona(
                target_persona.get("id", target_persona.get("name"))
            )
            
            # 現在アクティブなペルソナの場合は再設定
            active_persona = cl.user_session.get("active_persona")
            if active_persona and active_persona.get("name") == target_persona.get("name"):
                cl.user_session.set("active_persona", updated_persona)
                
                # モデルが変更された場合
                if "model" in updates:
                    settings = cl.user_session.get("settings", {})
                    settings["DEFAULT_MODEL"] = updates["model"]
                    cl.user_session.set("settings", settings)
                    responses_handler.update_model(updates["model"])
                
                # システムプロンプトが変更された場合
                if "system_prompt" in updates:
                    cl.user_session.set("system_prompt", updates["system_prompt"])
            
            # 確認メッセージ
            updated_info = persona_manager.format_persona_info(updated_persona) if updated_persona else "更新されました"
            await cl.Message(
                content=f"✅ ペルソナ '{persona_name}' を更新しました\n\n{updated_info}",
                author="System"
            ).send()
        else:
            await cl.Message(
                content=f"❌ ペルソナの更新に失敗しました。",
                author="System"
            ).send()


async def sync_vector_stores():
    """ベクトルストアを同期"""
    await cl.Message(
        content="🔄 ベクトルストアを同期中...",
        author="System"
    ).send()
    
    sync_manager = get_sync_manager(vector_store_handler)
    result = await sync_manager.sync_all()
    
    message = "🌐 **ベクトルストア同期結果**\n\n"
    
    if result["synced"]:
        message += f"✅ 同期: {len(result['synced'])}件\n"
        for vs_id in result["synced"]:
            message += f"  - `{vs_id}`\n"
    
    if result["removed_from_local"]:
        message += f"\n🗑️ ローカルから削除: {len(result['removed_from_local'])}件\n"
        for vs_id in result["removed_from_local"]:
            message += f"  - `{vs_id}`\n"
    
    if result["removed_from_config"]:
        message += f"\n🗑️ 設定から削除: {len(result['removed_from_config'])}件\n"
        for vs_id in result["removed_from_config"]:
            message += f"  - `{vs_id}`\n"
    
    if result["errors"]:
        message += f"\n❌ エラー: {len(result['errors'])}件\n"
        for error in result["errors"]:
            message += f"  - {error}\n"
    
    if not any([result["synced"], result["removed_from_local"], result["removed_from_config"], result["errors"]]):
        message += "✔️ すべて同期済みです"
    
    await cl.Message(content=message, author="System").send()


async def show_vector_stores():
    """ベクトルストア一覧を表示"""
    vector_stores = await vector_store_handler.list_vector_stores()
    
    if not vector_stores:
        await cl.Message(
            content="📁 ベクトルストアがありません。\n\n`/vs create [名前]` で作成できます。",
            author="System"
        ).send()
        return
    
    message = "# 📁 ベクトルストア一覧\n\n"
    
    # 現在使用中のVSを確認
    personal_vs_id = cl.user_session.get("personal_vs_id") or vector_store_handler.personal_vs_id
    
    for vs in vector_stores:
        is_active = vs.get("id") == personal_vs_id
        status = "✅ [使用中]" if is_active else ""
        
        message += f"## {vs.get('name', 'Unnamed')} {status}\n"
        message += f"🆔 ID: `{vs.get('id')}`\n"
        message += f"📄 ファイル数: {vs.get('file_counts', {}).get('total', 0)}\n"
        message += f"✅ ステータス: {vs.get('status', 'unknown')}\n"
        message += f"📅 作成日: {datetime.fromtimestamp(vs.get('created_at', 0)).strftime('%Y-%m-%d %H:%M')}\n\n"
    
    message += "\n💡 **コマンド**:\n"
    message += "- `/vs create [名前]` - 新しいベクトルストアを作成\n"
    message += "- `/vs info [ID]` - 詳細情報を表示\n"
    message += "- `/vs files [ID]` - ファイル一覧を表示\n"
    message += "- `/vs use [ID]` - ベクトルストアを使用\n"
    message += "- `/vs rename [ID] [新しい名前]` - ベクトルストアの名前を変更\n"
    message += "- `/vs delete [ID]` - ベクトルストアを削除"
    
    await cl.Message(content=message, author="System").send()


async def create_vector_store(name: str = "Personal Knowledge Base"):
    """ベクトルストアを作成"""
    msg = cl.Message(content=f"🔄 ベクトルストア '{name}' を作成中...", author="System")
    await msg.send()
    
    vs_id = await vector_store_handler.create_vector_store(name)
    
    if vs_id:
        # セッションに保存
        cl.user_session.set("personal_vs_id", vs_id)
        vector_store_handler.personal_vs_id = vs_id
        
        await cl.Message(
            content=f"✅ ベクトルストアを作成しました\n\n🆔 ID: `{vs_id}`\n📁 名前: {name}\n\nファイルをアップロードして知識ベースを構築できます。",
            author="System"
        ).send()
    else:
        await cl.Message(
            content="❌ ベクトルストアの作成に失敗しました。APIキーを確認してください。",
            author="System"
        ).send()


async def show_vector_store_info(vs_id: str):
    """ベクトルストアの詳細情報を表示"""
    vs_info = await vector_store_handler.get_vector_store_info(vs_id)
    
    if vs_info:
        message = f"# 📁 ベクトルストア詳細\n\n"
        message += vector_store_handler.format_vector_store_info(vs_info)
        await cl.Message(content=message, author="System").send()
    else:
        await cl.Message(
            content=f"❌ ベクトルストア `{vs_id}` が見つかりません。",
            author="System"
        ).send()


async def delete_vector_store(vs_id: str):
    """ベクトルストアを削除"""
    # 確認メッセージ
    res = await cl.AskUserMessage(
        content=f"⚠️ ベクトルストア `{vs_id}` を削除しますか？\nこの操作は元に戻せません。(yes/no)",
        timeout=30
    ).send()
    
    if res and res["output"].lower() in ["yes", "y", "はい"]:
        success = await vector_store_handler.delete_vector_store(vs_id)
        
        if success:
            # 現在使用中のVSだった場合はクリア
            if cl.user_session.get("personal_vs_id") == vs_id:
                cl.user_session.set("personal_vs_id", None)
                vector_store_handler.personal_vs_id = None
            
            await cl.Message(
                content=f"✅ ベクトルストア `{vs_id}` を削除しました。",
                author="System"
            ).send()
        else:
            await cl.Message(
                content=f"❌ ベクトルストア `{vs_id}` の削除に失敗しました。",
                author="System"
            ).send()
    else:
        await cl.Message(
            content="❌ 削除をキャンセルしました。",
            author="System"
        ).send()


async def show_vector_store_files(vs_id: str):
    """ベクトルストア内のファイル一覧を表示"""
    files = await vector_store_handler.list_vector_store_files(vs_id)
    
    if files:
        message = f"# 📄 ベクトルストアのファイル\n\n"
        message += f"🆔 ベクトルストアID: `{vs_id}`\n\n"
        message += "## ファイル一覧\n"
        message += vector_store_handler.format_file_list(files)
        await cl.Message(content=message, author="System").send()
    else:
        await cl.Message(
            content=f"📁 ベクトルストア `{vs_id}` にファイルがありません。",
            author="System"
        ).send()


async def rename_vector_store(vs_id: str, new_name: str):
    """ベクトルストアの名前を変更"""
    # ベクトルストアが存在するか確認
    vs_info = await vector_store_handler.get_vector_store_info(vs_id)
    
    if vs_info:
        # 名前を変更
        success = await vector_store_handler.rename_vector_store(vs_id, new_name)
        
        if success:
            await cl.Message(
                content=f"✅ ベクトルストアの名前を変更しました\n\n🆔 ID: `{vs_id}`\n📁 新しい名前: {new_name}",
                author="System"
            ).send()
        else:
            await cl.Message(
                content=f"❌ ベクトルストアの名前変更に失敗しました。",
                author="System"
            ).send()
    else:
        await cl.Message(
            content=f"❌ ベクトルストア `{vs_id}` が見つかりません。",
            author="System"
        ).send()


async def set_personal_vector_store(vs_id: str):
    """個人ベクトルストアを設定"""
    # ベクトルストアが存在するか確認
    vs_info = await vector_store_handler.get_vector_store_info(vs_id)
    
    if vs_info:
        cl.user_session.set("personal_vs_id", vs_id)
        vector_store_handler.personal_vs_id = vs_id
        
        await cl.Message(
            content=f"✅ ベクトルストアを設定しました\n\n{vector_store_handler.format_vector_store_info(vs_info)}",
            author="System"
        ).send()
    else:
        await cl.Message(
            content=f"❌ ベクトルストア `{vs_id}` が見つかりません。",
            author="System"
        ).send()


async def add_files_to_knowledge_base(file_ids: List[str]):
    """ファイルをナレッジベースに追加"""
    try:
        # 現在のユーザーを取得
        current_user = cl.user_session.get("user")
        user_id = current_user.identifier if current_user else "anonymous"
        
        # 個人用ベクトルストアを取得または作成
        vector_stores = cl.user_session.get("vector_stores", {})
        
        if "personal" not in vector_stores:
            # 個人用ベクトルストアを作成
            vs_id = await vector_store_handler.create_personal_vector_store(user_id)
            if vs_id:
                vector_stores["personal"] = vs_id
                cl.user_session.set("vector_stores", vector_stores)
        
        # ベクトルストアにファイルを追加
        vs_id = vector_stores.get("personal")
        if vs_id:
            for file_id in file_ids:
                success = await vector_store_handler.add_file_to_vector_store(vs_id, file_id)
                if success:
                    app_logger.info(f"ファイルをベクトルストアに追加: {file_id}")
            
            await cl.Message(
                content=f"✅ {len(file_ids)}件のファイルをナレッジベースに追加しました\n\n今後の会話でこれらのファイルの内容を参照できます。",
                author="System"
            ).send()
        else:
            await cl.Message(
                content="❌ ベクトルストアの作成に失敗しました",
                author="System"
            ).send()
            
    except Exception as e:
        app_logger.error(f"ナレッジベースへのファイル追加エラー: {e}")
        await cl.Message(
            content=f"❌ ナレッジベースへのファイル追加エラー: {e}",
            author="System"
        ).send()


async def show_knowledge_base():
    """ナレッジベースの状態を表示"""
    vector_stores = cl.user_session.get("vector_stores", {})
    uploaded_files = cl.user_session.get("uploaded_files", [])
    
    message = "# 📚 ナレッジベース\n\n"
    
    # ベクトルストア情報
    message += "## ベクトルストア\n"
    if vector_stores:
        for store_type, store_id in vector_stores.items():
            message += f"- **{store_type}**: `{store_id[:8]}...`\n"
    else:
        message += "*ベクトルストアが作成されていません*\n"
    
    message += "\n## アップロードされたファイル\n"
    if uploaded_files:
        for file_info in uploaded_files:
            message += f"- 📄 {file_info['filename']} (ID: `{file_info['file_id'][:8]}...`)\n"
    else:
        message += "*ファイルがアップロードされていません*\n"
    
    message += "\n## 使い方\n"
    message += "1. ファイルをドラッグ&ドロップまたはクリップボードアイコンからアップロード\n"
    message += "2. ファイルは自動的に処理され、ナレッジベースに追加されます\n"
    message += "3. AIはアップロードされたファイルの内容を参照して回答します\n\n"
    
    message += "💡 **サポートされるファイル形式**: "
    message += "TXT, MD, PDF, DOC, DOCX, CSV, JSON, XML, HTML, Python, JavaScriptなど"
    
    await cl.Message(content=message, author="System").send()


async def clear_knowledge_base():
    """ナレッジベースをクリア"""
    # ヘルパー関数を使用したシンプルな確認
    if await ask_confirmation(
        "⚠️ ナレッジベースのすべてのファイルを削除します。よろしいですか？",
        yes_label="はい、削除します",
        no_label="キャンセル"
    ):
        try:
            # ベクトルストアを削除
            vector_stores = cl.user_session.get("vector_stores", {})
            
            for store_type, store_id in vector_stores.items():
                if store_type == "personal":
                    success = await vector_store_handler.delete_vector_store(store_id)
                    if success:
                        app_logger.info(f"ベクトルストア削除: {store_id}")
            
            # セッション情報をクリア
            cl.user_session.set("vector_stores", {})
            cl.user_session.set("uploaded_files", [])
            
            await cl.Message(
                content="✅ ナレッジベースをクリアしました",
                author="System"
            ).send()
            
        except Exception as e:
            app_logger.error(f"ナレッジベースクリアエラー: {e}")
            await cl.Message(
                content=f"❌ クリアエラー: {e}",
                author="System"
            ).send()
    else:
        await cl.Message(
            content="キャンセルされました",
            author="System"
        ).send()


async def show_settings():
    """設定画面を表示（トグル式）"""
    settings = config_manager.get_all_settings()
    
    # 現在の設定状態を取得
    proxy_enabled = os.getenv("PROXY_ENABLED", "false").lower() == "true"
    http_proxy = os.getenv("HTTP_PROXY", "")
    https_proxy = os.getenv("HTTPS_PROXY", "")
    
    # Toolsの状態を取得
    tools_status = tools_config.get_tools_status()
    
    # メッセージを構築
    message = "# ⚙️ 設定\n\n"
    
    # プロキシ設定
    message += "## 🌐 プロキシ設定\n"
    message += f"**状態**: {'\u2705 有効' if proxy_enabled else '\u274c 無効'}\n"
    if proxy_enabled:
        message += f"**HTTP Proxy**: {http_proxy or '未設定'}\n"
        message += f"**HTTPS Proxy**: {https_proxy or '未設定'}\n"
    message += "\n"
    
    # Tools設定
    message += "## 🔧 Tools機能\n"
    message += f"**全体**: {'\u2705 有効' if tools_config.is_enabled() else '\u274c 無効'}\n"
    if tools_config.is_enabled():
        for tool_name, enabled in tools_status.items():
            status_icon = '\u2705' if enabled else '\u274c'
            message += f"- **{tool_name}**: {status_icon}\n"
    
    # ベクトルストアIDの表示
    vector_store_ids = tools_config.get_vector_store_ids_string()
    if vector_store_ids:
        message += f"\n**参照ベクトルストア**: {vector_store_ids}\n"
    message += "\n"
    
    # アクションボタン
    actions = [
        cl.Action(name="toggle_proxy", payload={"action": "proxy"}, label="🌐 プロキシトグル"),
        cl.Action(name="set_proxy_url", payload={"action": "proxy_url"}, label="🔗 プロキシURL設定"),
        cl.Action(name="toggle_tools", payload={"action": "tools"}, label="🔧 Tools全体トグル"),
        cl.Action(name="toggle_web_search", payload={"action": "web_search"}, label="🔍 Web検索トグル"),
        cl.Action(name="toggle_file_search", payload={"action": "file_search"}, label="📄 ファイル検索トグル"),
    ]
    
    res = await cl.AskActionMessage(
        content=message + "\n下のボタンから設定を変更できます:",
        actions=actions
    ).send()
    
    if res:
        await handle_settings_action(res)


async def handle_settings_action(action_response):
    """設定アクションを処理"""
    action = action_response.get("payload", {}).get("action")
    
    if action == "proxy":
        # プロキシの有効/無効をトグル
        current = os.getenv("PROXY_ENABLED", "false").lower() == "true"
        new_value = "false" if current else "true"
        
        # .envファイルを更新
        config_manager.update_env_value("PROXY_ENABLED", new_value)
        os.environ["PROXY_ENABLED"] = new_value
        
        # クライアントを再初期化
        vector_store_handler._init_clients()
        responses_handler._init_clients()
        
        status = "有効" if new_value == "true" else "無効"
        await cl.Message(
            content=f"✅ プロキシを{status}にしました",
            author="System"
        ).send()
        
    elif action == "proxy_url":
        # プロキシURLを設定
        res = await cl.AskUserMessage(
            content="HTTPプロキシURLを入力してください (例: http://proxy.example.com:8080):",
            timeout=60
        ).send()
        
        if res:
            http_proxy = res["output"].strip()
            
            # HTTPSプロキシも設定
            res2 = await cl.AskUserMessage(
                content="HTTPSプロキシURLを入力してください (同じ場合はEnter, 例: http://proxy.example.com:8080):",
                timeout=60
            ).send()
            
            https_proxy = res2["output"].strip() if res2 else http_proxy
            
            # .envファイルを更新
            config_manager.update_env_value("HTTP_PROXY", http_proxy)
            config_manager.update_env_value("HTTPS_PROXY", https_proxy)
            os.environ["HTTP_PROXY"] = http_proxy
            os.environ["HTTPS_PROXY"] = https_proxy
            
            # クライアントを再初期化
            vector_store_handler._init_clients()
            responses_handler._init_clients()
            
            await cl.Message(
                content=f"✅ プロキシURLを設定しました\nHTTP: {http_proxy}\nHTTPS: {https_proxy}",
                author="System"
            ).send()
    
    elif action == "tools":
        # Tools全体をトグル
        if tools_config.is_enabled():
            tools_config.disable_all_tools()
            await cl.Message(content="❌ Tools機能を無効にしました", author="System").send()
        else:
            tools_config.enable_all_tools()
            await cl.Message(content="✅ Tools機能を有効にしました", author="System").send()
    
    elif action == "web_search":
        # Web検索をトグル
        if tools_config.is_tool_enabled("web_search_preview"):
            tools_config.disable_tool("web_search_preview")
            await cl.Message(content="❌ Web検索を無効にしました", author="System").send()
        else:
            tools_config.enable_tool("web_search_preview")
            await cl.Message(content="✅ Web検索を有効にしました", author="System").send()
    
    elif action == "file_search":
        # ファイル検索をトグル
        if tools_config.is_tool_enabled("file_search"):
            tools_config.disable_tool("file_search")
            await cl.Message(content="❌ ファイル検索を無効にしました", author="System").send()
        else:
            tools_config.enable_tool("file_search")
            await cl.Message(content="✅ ファイル検索を有効にしました", author="System").send()
    
    # 設定画面を再表示
    await show_settings()


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
- **Tools機能**: {"有効" if tools_config.is_enabled() else "無効"}
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
    print("📌 Tools機能の状態:")
    print(f"   - 全体: {'有効' if tools_config.is_enabled() else '無効'}")
    if tools_config.is_enabled():
        enabled_tools = tools_config.get_enabled_tools()
        print(f"   - 有効なツール: {', '.join(enabled_tools) if enabled_tools else 'なし'}")
    print("=" * 50)
    print("📌 ログイン情報:")
    print("   - ユーザー名: admin")
    print("   - パスワード: admin123 (または.envで設定した値)")
    print("=" * 50)
    
    current_settings = config_manager.get_all_settings()
    print(f"API Key: {current_settings.get('OPENAI_API_KEY_DISPLAY', 'Not set')}")
    print(f"Default Model: {current_settings.get('DEFAULT_MODEL', 'Not set')}")
    
    app_logger.info("アプリケーション起動完了")
