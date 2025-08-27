"""
多機能AIワークスペースアプリケーション - リファクタリング版
Modular Handler Architectureによる保守性向上
"""

import chainlit as cl
from chainlit.types import ThreadDict
from chainlit.input_widget import Select, Switch, Slider, TextInput
from dotenv import load_dotenv
import os
import auth
from typing import Optional, Dict, List
from datetime import datetime
import json
import uuid
import chainlit.data as cl_data

# .envファイルの読み込み
load_dotenv()

# コアシステム
from utils.logger import app_logger
from utils.ui_helper import ChainlitHelper as ui
from utils.error_handler import ErrorHandler as error_handler
from utils.config import config_manager
from utils.responses_handler import responses_handler
from utils.tools_config import tools_config
from utils.persona_manager import persona_manager
from utils.vector_store_handler import vector_store_handler

# ハンドラー
from handlers.command_handler import command_handler
from handlers.persona_handler import persona_handler
from handlers.settings_handler import settings_handler
from handlers.vector_store_commands import vector_store_commands

# WebSocket接続モニター（オプション）
try:
    from utils.connection_handler import connection_monitor, handle_websocket_error
    app_logger.info("[SUCCESS] WebSocket接続モニターを初期化")
except ImportError as e:
    app_logger.warning(f"[WARNING] WebSocket接続モニターをスキップ: {e}")
    connection_monitor = None

# データレイヤー初期化
data_layer_type = None
data_layer_instance = None

try:
    import data_layer
    data_layer_instance = cl_data._data_layer  
    data_layer_type = "SQLite (Persistent)"
    app_logger.info("[SUCCESS] SQLiteデータレイヤーを使用")
except Exception as e:
    app_logger.warning(f"SQLiteデータレイヤーエラー: {e}")
    try:
        import simple_data_layer
        data_layer_type = "Simple In-Memory" 
        app_logger.info("[SUCCESS] シンプルデータレイヤーを使用")
    except ImportError:
        app_logger.error("データレイヤーの初期化に失敗")


@cl.oauth_callback
def oauth_callback(provider_id: str, token: str, raw_user_data: Dict[str, str], default_user: cl.User) -> Optional[cl.User]:
    """OAuth認証コールバック"""
    app_logger.info("OAuth認証完了", provider=provider_id, user_id=default_user.identifier)
    return default_user


@cl.on_chat_start
async def chat_start():
    """チャット開始時の初期化処理"""
    try:
        app_logger.info("🚀 チャット開始")
        
        # ユーザー情報を取得
        user = cl.user_session.get("user")
        user_id = user.identifier if user else "anonymous"
        
        # セッション初期化
        await _initialize_session(user_id)
        
        # 設定UI作成
        await _create_settings_ui()
        
        # ウェルカムメッセージ
        await _show_welcome_message()
        
        app_logger.info("✅ チャット開始完了", user_id=user_id)
        
    except Exception as e:
        app_logger.error("❌ チャット開始エラー", error=str(e))
        await error_handler.handle_unexpected_error(e, "チャット開始")


async def _initialize_session(user_id: str):
    """セッション初期化"""
    try:
        # 基本セッション設定
        ui.set_session("message_history", [])
        ui.set_session("settings", {"DEFAULT_MODEL": "gpt-4o-mini"})
        ui.set_session("user_id", user_id)
        
        # スレッド情報を初期化
        thread = cl.user_session.get("thread", {})
        thread_id = thread.get("id") or str(uuid.uuid4())
        ui.set_session("thread_id", thread_id)
        
        # ベクトルストアIDs初期化（3層構造）
        await _initialize_vector_stores(user_id, thread)
        
        # デフォルトペルソナ設定
        default_persona = await persona_manager.get_persona("汎用アシスタント")
        if default_persona:
            ui.set_session("active_persona", default_persona)
            ui.set_session("system_prompt", default_persona.get("system_prompt", ""))
        
        # APIクライアント初期化
        responses_handler.reset_conversation()
        
        app_logger.info("セッション初期化完了", user_id=user_id, thread_id=thread_id)
        
    except Exception as e:
        app_logger.error("セッション初期化エラー", error=str(e))
        raise


async def _initialize_vector_stores(user_id: str, thread: dict):
    """ベクトルストア3層構造初期化"""
    try:
        # Company層（環境変数から）
        company_vs_id = os.getenv("COMPANY_VECTOR_STORE_ID")
        
        # Personal層（データレイヤーから取得または作成）
        personal_vs_id = None
        if data_layer_instance and hasattr(data_layer_instance, 'get_user_vector_store_id'):
            personal_vs_id = await data_layer_instance.get_user_vector_store_id(user_id)
        
        # Session層（スレッドから）
        session_vs_id = thread.get("vector_store_id")
        
        # セッションに保存
        vs_ids = {
            "company": company_vs_id,
            "personal": personal_vs_id,
            "session": session_vs_id
        }
        
        ui.set_session("vector_store_ids", vs_ids)
        ui.set_session("company_vs_id", company_vs_id)
        ui.set_session("personal_vs_id", personal_vs_id)
        ui.set_session("session_vs_id", session_vs_id)
        
        app_logger.debug("ベクトルストア初期化", **{k: v[:8] + "..." if v else None for k, v in vs_ids.items()})
        
    except Exception as e:
        app_logger.error("ベクトルストア初期化エラー", error=str(e))
        # 失敗時は空の構造を設定
        ui.set_session("vector_store_ids", {})
        ui.set_session("company_vs_id", None)
        ui.set_session("personal_vs_id", None)
        ui.set_session("session_vs_id", None)


async def _create_settings_ui():
    """設定UIを作成"""
    try:
        # チャット設定UI
        await cl.ChatSettings([
            Select(
                id="model",
                label="🤖 Model",
                values=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
                initial_index=1,
            ),
            Slider(
                id="temperature",
                label="🌡️ Temperature",
                initial=0.7,
                min=0.0,
                max=2.0,
                step=0.1,
            ),
            Switch(
                id="stream",
                label="🔄 Stream",
                initial=True,
            ),
            TextInput(
                id="company_vs_id",
                label="🏢 Company Vector Store ID",
                initial=os.getenv("COMPANY_VECTOR_STORE_ID", ""),
                placeholder="vs_xxxxx",
            ),
            TextInput(
                id="personal_vs_id", 
                label="👤 Personal Vector Store ID",
                initial=ui.get_session("vector_store_ids", {}).get("personal", ""),
                placeholder="vs_yyyyy",
            )
        ]).send()
        
    except Exception as e:
        app_logger.error("設定UI作成エラー", error=str(e))


async def _show_welcome_message():
    """ウェルカムメッセージ表示"""
    try:
        active_persona = ui.get_session("active_persona")
        model = ui.get_session("settings", {}).get("DEFAULT_MODEL", "gpt-4o-mini")
        
        message = "# 🎉 多機能AIワークスペースへようこそ！\n\n"
        
        if active_persona:
            message += f"🎭 **アクティブペルソナ**: {active_persona.get('name', 'Unknown')}\n"
        
        message += f"🤖 **使用モデル**: {model}\n"
        message += f"📊 **データレイヤー**: {data_layer_type}\n\n"
        
        message += "## 💡 主な機能\n"
        message += "- 🎭 **ペルソナ管理**: `/persona` で切り替え\n"
        message += "- 🔧 **設定管理**: `/settings` で各種設定\n"
        message += "- 🗂️ **ベクトルストア**: ファイルアップロードで自動追加\n"
        message += "- 📊 **統計情報**: `/stats` で使用状況確認\n\n"
        
        message += "**コマンドヘルプ**: `/help` で全コマンド表示"
        
        await ui.send_system_message(message)
        
    except Exception as e:
        app_logger.error("ウェルカムメッセージエラー", error=str(e))


@cl.on_settings_update
async def settings_update(settings):
    """設定更新時の処理"""
    try:
        app_logger.info("設定更新", settings=settings)
        
        # セッション設定を更新
        current_settings = ui.get_session("settings", {})
        current_settings.update(settings)
        ui.set_session("settings", current_settings)
        
        # モデル変更
        if "model" in settings:
            responses_handler.update_model(settings["model"])
        
        # ベクトルストア設定更新
        if "company_vs_id" in settings or "personal_vs_id" in settings:
            vs_ids = ui.get_session("vector_store_ids", {})
            if "company_vs_id" in settings:
                vs_ids["company"] = settings["company_vs_id"]
                ui.set_session("company_vs_id", settings["company_vs_id"])
            if "personal_vs_id" in settings:
                vs_ids["personal"] = settings["personal_vs_id"]
                ui.set_session("personal_vs_id", settings["personal_vs_id"])
            ui.set_session("vector_store_ids", vs_ids)
        
        await ui.send_success_message("設定を更新しました")
        
    except Exception as e:
        await error_handler.handle_unexpected_error(e, "設定更新")


@cl.on_message  
async def message_handler(message: cl.Message):
    """メッセージ処理のメインハンドラー"""
    try:
        user_input = message.content.strip()
        app_logger.info("メッセージ受信", content_length=len(user_input))
        
        # コマンド処理
        if user_input.startswith("/"):
            await command_handler.handle_command(user_input)
            return
        
        # 通常の会話処理
        await _process_conversation(user_input)
        
    except Exception as e:
        await error_handler.handle_unexpected_error(e, "メッセージ処理")


async def _process_conversation(user_input: str):
    """通常の会話処理"""
    try:
        # セッションから必要な情報を取得
        message_history = ui.get_session("message_history", [])
        system_prompt = ui.get_session("system_prompt", "")
        settings = ui.get_session("settings", {})
        
        # ユーザーメッセージを履歴に追加
        user_message = {"role": "user", "content": user_input}
        message_history.append(user_message)
        ui.set_session("message_history", message_history)
        
        # ツール設定を準備
        tools_config.set_vector_store_ids(ui.get_session("vector_store_ids", {}))
        tools = tools_config.get_tools_for_request()
        
        # レスポンス生成（Responses API使用）
        loading_msg = await ui.show_loading_message("回答を生成中...")
        
        response_data = await responses_handler.create_response(
            messages=message_history,
            system_prompt=system_prompt,
            model=settings.get("DEFAULT_MODEL", "gpt-4o-mini"),
            temperature=settings.get("temperature", 0.7),
            tools=tools,
            stream=settings.get("stream", True)
        )
        
        if response_data.get("success"):
            assistant_message = response_data.get("content", "応答の取得に失敗しました")
            
            # アシスタントメッセージを履歴に追加
            message_history.append({"role": "assistant", "content": assistant_message})
            ui.set_session("message_history", message_history)
            
            # レスポンスIDを保存（会話の継続性）
            if response_data.get("response_id"):
                ui.set_session("previous_response_id", response_data["response_id"])
            
            await ui.update_loading_message(loading_msg, assistant_message)
            
        else:
            error_message = response_data.get("error", "不明なエラーが発生しました")
            await ui.update_loading_message(loading_msg, f"❌ エラー: {error_message}")
        
        app_logger.info("会話処理完了", history_length=len(message_history))
        
    except Exception as e:
        await error_handler.handle_unexpected_error(e, "会話処理")


@cl.on_file_upload
async def file_upload(files: List[cl.File]):
    """ファイルアップロード処理"""
    try:
        if not files:
            return
        
        app_logger.info("ファイルアップロード開始", count=len(files))
        
        # ベクトルストアハンドラーに処理を委譲
        await vector_store_commands.process_file_upload(files)
        
    except Exception as e:
        await error_handler.handle_file_error(e, "ファイルアップロード")


@cl.on_action
async def action_handler(action: cl.Action):
    """アクション処理"""
    try:
        action_name = action.name
        app_logger.info("アクション実行", name=action_name)
        
        if action_name == "create_persona_form":
            await persona_handler.create_persona_interactive()
        else:
            await ui.send_error_message(f"不明なアクション: {action_name}")
            
    except Exception as e:
        await error_handler.handle_unexpected_error(e, "アクション処理")


@cl.on_chat_resume
async def chat_resume(thread: ThreadDict):
    """チャット再開時の処理"""
    try:
        app_logger.info("チャット再開", thread_id=thread["id"])
        
        user = cl.user_session.get("user")
        user_id = user.identifier if user else "anonymous"
        
        # セッション復元
        await _restore_session_from_thread(thread, user_id)
        
        await ui.send_info_message("チャットを再開しました")
        
    except Exception as e:
        await error_handler.handle_unexpected_error(e, "チャット再開")


async def _restore_session_from_thread(thread: ThreadDict, user_id: str):
    """スレッドからセッションを復元"""
    try:
        # 基本セッション情報
        ui.set_session("thread_id", thread["id"])
        ui.set_session("user_id", user_id)
        
        # メッセージ履歴の復元（データレイヤーから）
        if data_layer_instance:
            try:
                elements = await data_layer_instance.get_thread_elements(thread["id"])
                messages = []
                for element in elements:
                    if hasattr(element, 'content'):
                        role = "user" if element.type == "user_message" else "assistant"
                        messages.append({"role": role, "content": element.content})
                ui.set_session("message_history", messages)
            except Exception as e:
                app_logger.warning("履歴復元エラー", error=str(e))
                ui.set_session("message_history", [])
        
        # ベクトルストア情報復元
        await _initialize_vector_stores(user_id, thread)
        
        app_logger.info("セッション復元完了", thread_id=thread["id"])
        
    except Exception as e:
        app_logger.error("セッション復元エラー", error=str(e))


@cl.on_chat_end
async def chat_end():
    """チャット終了時の処理"""
    try:
        app_logger.info("チャット終了")
        
        # セッションベクトルストアのクリーンアップ
        await vector_store_commands.cleanup_session_resources()
        
        # WebSocket接続の監視を停止
        if connection_monitor:
            connection_monitor.stop_monitoring()
            
        app_logger.info("チャット終了処理完了")
        
    except Exception as e:
        app_logger.error("チャット終了エラー", error=str(e))


if __name__ == "__main__":
    app_logger.info("🚀 多機能AIワークスペースアプリケーション開始")
    print("🚀 多機能AIワークスペースアプリケーション開始")
    print(f"📊 データレイヤー: {data_layer_type}")