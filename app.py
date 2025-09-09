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

# .envファイルの読み込み（DOTENV_PATH優先）
_dotenv_path = os.environ.get("DOTENV_PATH")
if _dotenv_path and os.path.exists(_dotenv_path):
    load_dotenv(_dotenv_path)
else:
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

# グローバルハンドラーインスタンス（遅延初期化用）
persona_handler_instance = None

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


# OAuth認証は現在無効（環境変数未設定のため）
# 必要に応じて.envファイルにOAuth設定を追加してください
# @cl.oauth_callback
# def oauth_callback(provider_id: str, token: str, raw_user_data: Dict[str, str], default_user: cl.User) -> Optional[cl.User]:
#     """OAuth認証コールバック"""
#     app_logger.info("OAuth認証完了", provider=provider_id, user_id=default_user.identifier)
#     return default_user


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


@cl.on_chat_resume
async def on_chat_resume(thread: dict):
    """チャット再開時の処理 - Chainlitが自動的にメッセージと要素を復元"""
    try:
        thread_id = thread.get("id", "unknown")
        app_logger.info("チャット再開", thread_id=thread_id)
        
        # ユーザー情報を取得
        user = cl.user_session.get("user")
        user_id = user.identifier if user else "anonymous"
        
        # セッション情報のみ復元（メッセージはChainlitが自動復元）
        await _restore_session_on_resume(user_id, thread_id, thread)
        
        # 設定UI作成（チャット再開時にも必要）
        await _create_settings_ui()
        
        app_logger.info("✅ セッション復元完了", thread_id=thread_id)
        
    except Exception as e:
        app_logger.error("❌ チャット再開エラー", error=str(e))
        await error_handler.handle_unexpected_error(e, "チャット再開")


async def _restore_session_on_resume(user_id: str, thread_id: str, thread: dict):
    """チャット再開時のセッション復元"""
    try:
        # セッション初期化
        ui.set_session("user_id", user_id)
        ui.set_session("thread_id", thread_id)
        
        # ベクトルストアIDs復元
        await _initialize_vector_stores(user_id, thread)
        
        # デフォルトペルソナ設定
        default_persona = await persona_manager.get_persona("汎用アシスタント")
        if default_persona:
            ui.set_session("active_persona", default_persona)
            ui.set_session("system_prompt", default_persona.get("system_prompt", ""))
        
        # 注意: Chainlitが@cl.on_chat_resumeで自動的に過去のメッセージとエレメントをUIに送信
        # セッション変数の履歴は新しい会話のために初期化
        ui.set_session("message_history", [])
        
        # previous_response_idをスレッドから復元（OpenAI Responses APIの会話継続に必要）
        thread_response_id = thread.get("metadata", {}).get("previous_response_id")
        ui.set_session("previous_response_id", thread_response_id)
        
    except Exception as e:
        app_logger.error("セッション復元エラー", error=str(e))
        raise


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
        
        # 会話履歴の復元または初期化
        await _restore_chat_history(thread_id)
        
        app_logger.info("セッション初期化完了", user_id=user_id, thread_id=thread_id)
        
    except Exception as e:
        app_logger.error("セッション初期化エラー", error=str(e))
        raise


async def _restore_chat_history(thread_id: str):
    """チャット履歴を復元"""
    try:
        # 簡単な方法：Chainlitの内蔵履歴機能を利用
        # データ永続化が有効な場合、Chainlitが自動的に履歴を復元する
        
        # セッション履歴を初期化
        ui.set_session("message_history", [])
        ui.set_session("previous_response_id", None)
        
        app_logger.info("履歴復元処理完了", thread_id=thread_id)
        app_logger.info("注意: Chainlitの自動履歴復元機能に依存")
            
    except Exception as e:
        app_logger.error("履歴復元エラー", error=str(e))
        # エラー時は空の履歴で開始
        ui.set_session("message_history", [])
        ui.set_session("previous_response_id", None)


async def _initialize_vector_stores(user_id: str, thread: dict):
    """ベクトルストア3層構造初期化"""
    try:
        # Company層（環境変数から）
        company_vs_id = os.getenv("COMPANY_VECTOR_STORE_ID")
        
        # Personal層（データレイヤーから取得または作成）
        personal_vs_id = None
        if data_layer_instance and hasattr(data_layer_instance, 'get_user_vector_store_id'):
            personal_vs_id = await data_layer_instance.get_user_vector_store_id(user_id)
        
        # Chat層（チャット専用ベクトルストア）- ファイルアップロード時に作成
        thread_id = ui.get_session("thread_id")
        chat_vs_id = thread.get("vector_store_id")
        
        # Note: チャット専用ベクトルストアはファイルアップロード時に自動作成されます
        
        # セッションに保存
        vs_ids = {
            "company": company_vs_id,
            "personal": personal_vs_id,
            "chat": chat_vs_id  # sessionからchatに名称変更
        }
        
        ui.set_session("vector_store_ids", vs_ids)
        ui.set_session("company_vs_id", company_vs_id)
        ui.set_session("personal_vs_id", personal_vs_id)
        ui.set_session("chat_vs_id", chat_vs_id)  # sessionからchatに名称変更
        
        app_logger.debug("ベクトルストア初期化", **{k: v[:8] + "..." if v else None for k, v in vs_ids.items()})
        
    except Exception as e:
        app_logger.error("ベクトルストア初期化エラー", error=str(e))
        # 失敗時は空の構造を設定
        ui.set_session("vector_store_ids", {})
        ui.set_session("company_vs_id", None)
        ui.set_session("personal_vs_id", None)
        ui.set_session("chat_vs_id", None)


async def _create_settings_ui():
    """設定UIを作成"""
    try:
        # 現在の設定値を取得
        settings = config_manager.get_all_settings()
        proxy_settings = config_manager.get_proxy_settings()
        available_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
        current_settings = ui.get_session("settings", {})
        vector_store_ids = ui.get_session("vector_store_ids", {})
        
        # 詳細な設定UI（元の完全版）
        await cl.ChatSettings([
            Select(
                id="Model",
                label="OpenAI - Model",
                values=available_models,
                initial_index=available_models.index(current_settings.get("Model", settings.get("DEFAULT_MODEL", "gpt-4o-mini"))) if current_settings.get("Model", settings.get("DEFAULT_MODEL", "gpt-4o-mini")) in available_models else 0,
            ),
            Switch(id="Tools_Enabled", label="Tools機能 - 有効/無効", initial=tools_config.is_enabled()),
            Switch(id="Web_Search", label="Web検索 - 有効/無効", initial=tools_config.is_tool_enabled("web_search")),
            Switch(
                id="File_Search", 
                label="ファイル検索 - 有効/無効", 
                initial=tools_config.is_tool_enabled("file_search"),
                description="有効時は下記ベクトルストアで指定したストアの内容を検索します"
            ),
            # ベクトルストア3層設定
            Switch(
                id="VS_Layer_Company",
                label="ベクトル層1: 会社全体 - 有効/無効",
                initial=tools_config.is_layer_enabled("company"),
                description="会社全体で共有するナレッジベース"
            ),
            TextInput(
                id="VS_ID_Company",
                label="会社全体ベクトルストアID",
                initial=vector_store_ids.get("company", os.getenv("COMPANY_VECTOR_STORE_ID", "")),
                placeholder="vs_xxxxx",
                description="会社全体で使用するベクトルストアのID"
            ),
            Switch(
                id="VS_Layer_Personal",
                label="ベクトル層2: 個人ユーザー - 有効/無効",
                initial=tools_config.is_layer_enabled("personal"),
                description="個人ユーザー専用のナレッジベース"
            ),
            TextInput(
                id="VS_ID_Personal",
                label="個人ベクトルストアID",
                initial=vector_store_ids.get("personal", ""),
                placeholder="vs_yyyyy",
                description="個人専用のベクトルストアのID"
            ),
            Switch(
                id="VS_Layer_Thread",
                label="ベクトル層3: チャット単位 - 有効/無効",
                initial=tools_config.is_layer_enabled("thread"),
                description="このチャット専用のナレッジベース（自動作成）"
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
                initial=ui.get_session("temperature", 0.7),
                min=0,
                max=2,
                step=0.1,
                description="応答の創造性を制御 (0=決定的, 1=バランス, 2=創造的)"
            ),
            TextInput(
                id="System_Prompt",
                label="システムプロンプト",
                initial=ui.get_session("system_prompt", ""),
                placeholder="AIの振る舞いを定義するプロンプトを入力...",
            ),
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
        
        # アクションボタンを作成
        actions = [
            cl.Action(
                name="create_persona_form",
                payload={"action": "create_persona"},
                label="🎭 新しいペルソナ作成",
                icon="user-plus"
            ),
            cl.Action(
                name="analytics_dashboard", 
                payload={"action": "show_analytics"},
                label="📊 統計ダッシュボード",
                icon="bar-chart"
            ),
            cl.Action(
                name="search_workspace",
                payload={"action": "search", "query": ""},
                label="🔍 ワークスペース検索",
                icon="search"
            )
        ]
        
        await cl.Message(content=message, actions=actions).send()
        
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
        
        # 1. モデル変更処理
        if "Model" in settings:
            responses_handler.update_model(settings["Model"])
            app_logger.info("モデル変更", model=settings["Model"])
        
        # 2. Tools設定更新
        if "Tools_Enabled" in settings:
            tools_config.update_enabled(settings["Tools_Enabled"])
        if "Web_Search" in settings:
            tools_config.update_tool_status("web_search", settings["Web_Search"])
        if "File_Search" in settings:
            tools_config.update_tool_status("file_search", settings["File_Search"])
        
        # 3. ベクトルストア3層設定更新
        vs_ids = ui.get_session("vector_store_ids", {})
        
        # 会社全体層
        if "VS_Layer_Company" in settings:
            tools_config.set_layer_enabled("company", settings["VS_Layer_Company"])
        if "VS_ID_Company" in settings:
            company_id = settings["VS_ID_Company"].strip() if settings["VS_ID_Company"] else ""
            vs_ids["company"] = company_id
            ui.set_session("company_vs_id", company_id)
            # 注意: 会社全体のベクトルストアIDは.envファイルから読み取り専用
            
        # 個人ユーザー層
        if "VS_Layer_Personal" in settings:
            tools_config.set_layer_enabled("personal", settings["VS_Layer_Personal"])
        if "VS_ID_Personal" in settings:
            personal_id = settings["VS_ID_Personal"].strip() if settings["VS_ID_Personal"] else ""
            vs_ids["personal"] = personal_id
            ui.set_session("personal_vs_id", personal_id)
            
        # チャット単位層
        if "VS_Layer_Thread" in settings:
            tools_config.set_layer_enabled("thread", settings["VS_Layer_Thread"])
        
        ui.set_session("vector_store_ids", vs_ids)
        
        # 4. プロキシ設定更新
        if "Proxy_Enabled" in settings or "Proxy_URL" in settings:
            proxy_enabled = settings.get("Proxy_Enabled", False)
            proxy_url = settings.get("Proxy_URL", "")
            if proxy_enabled and proxy_url:
                config_manager.set_proxy_settings(
                    http_proxy=proxy_url,
                    https_proxy=proxy_url,
                    proxy_enabled=proxy_enabled
                )
                app_logger.info("プロキシ設定更新", enabled=proxy_enabled, url=proxy_url)
        
        # 5. Temperature設定更新
        if "Temperature" in settings:
            ui.set_session("temperature", settings["Temperature"])
            app_logger.info("Temperature更新", temperature=settings["Temperature"])
        
        # 6. システムプロンプト更新
        if "System_Prompt" in settings:
            system_prompt = settings["System_Prompt"]
            ui.set_session("system_prompt", system_prompt)
            prompt_length = len(system_prompt) if system_prompt else 0
            app_logger.info("システムプロンプト更新", prompt_length=prompt_length)
        
        await ui.send_success_message("🔧 設定を更新しました")
        
    except Exception as e:
        await error_handler.handle_unexpected_error(e, "設定更新")


@cl.on_message  
async def message_handler(message: cl.Message):
    """メッセージ処理のメインハンドラー"""
    try:
        user_input = message.content.strip()
        app_logger.info("メッセージ受信", content_length=len(user_input))
        
        # ファイルアップロード処理（メッセージに添付されている場合）
        # 公式ドキュメント準拠: message.elementsでファイル存在をチェック
        if message.elements:
            await handle_file_upload(message)
            
            # Chainlit公式パターン: ファイルのみアップロードの場合は会話処理をスキップ
            # 空メッセージまたは非常に短いメッセージの場合
            if not user_input or len(user_input.strip()) <= 2:
                app_logger.info("ファイルのみのアップロード", 
                              content_length=len(user_input), 
                              files_count=len(message.elements))
                return
        
        # コマンド処理
        if user_input.startswith("/"):
            await command_handler.handle_command(user_input)
            return
        
        # 通常の会話処理
        if user_input:  # 空でない場合のみ会話処理を実行
            await _process_conversation(user_input)
        
    except Exception as e:
        await error_handler.handle_unexpected_error(e, "メッセージ処理")


async def _process_conversation(user_input: str):
    """通常の会話処理"""
    try:
        # Chainlitのネイティブなメッセージコンテキストを使用
        message_history = cl.chat_context.to_openai()
        system_prompt = ui.get_session("system_prompt", "")
        settings = ui.get_session("settings", {})
        
        # ツール設定を準備
        vector_store_ids = ui.get_session("vector_store_ids", {})
        if vector_store_ids:
            # ベクトルストアIDを文字列として渡す
            vs_id_string = ",".join([v for v in vector_store_ids.values() if v])
            tools_config.update_vector_store_ids(vs_id_string)
        tools = tools_config.get_enabled_tools()
        
        # レスポンス生成（Responses API使用）
        loading_msg = await ui.show_loading_message("回答を生成中...")
        
        # セッションから最新設定を取得
        current_model = settings.get("Model", settings.get("DEFAULT_MODEL", "gpt-4o-mini"))
        current_temperature = ui.get_session("temperature", settings.get("Temperature", 0.7))
        current_system_prompt = ui.get_session("system_prompt", system_prompt)
        
        # OpenAI Responses API用に履歴を処理
        # - systemメッセージは除外（instructionsで別途送信）
        # - assistantメッセージも除外（OpenAIが管理）
        user_messages = [msg for msg in message_history if msg.get("role") == "user"]
        
        # ストリーミングレスポンス処理（Chainlitの標準パターン）
        # 会話継続のためのprevious_response_idを取得
        previous_response_id = ui.get_session("previous_response_id")
        
        response_generator = responses_handler.create_response(
            messages=user_messages,  # ユーザーメッセージのみ渡す
            model=current_model,
            temperature=current_temperature,
            use_tools=True,  # Tools機能を有効化
            stream=settings.get("stream", True),
            previous_response_id=previous_response_id,  # 会話継続のためのID
            instructions=current_system_prompt  # システムプロンプトをinstructionsで渡す
        )
        
        # ローディングメッセージを削除
        if loading_msg:
            await loading_msg.remove()
        
        # Chainlitの標準的なストリーミングメッセージを作成
        msg = cl.Message(content="")
        
        assistant_message = ""
        try:
            async for chunk in response_generator:
                if chunk and chunk.get("content"):
                    chunk_content = chunk.get("content", "")
                    assistant_message += chunk_content
                    # Chainlitの標準ストリーミング方式
                    await msg.stream_token(chunk_content)
                
                # レスポンスIDを保存（会話の継続性）
                if chunk and chunk.get("response_id"):
                    response_id = chunk["response_id"]
                    ui.set_session("previous_response_id", response_id)
                    
                    # データベースのスレッドテーブルに永続化（将来の使用のため）
                    try:
                        thread_id = ui.get_session("thread_id")
                        if thread_id and data_layer_instance:
                            # Note: 現在はprevious_response_idの保存機能は未実装
                            # 必要に応じてdata_layerに追加のメソッドを実装
                            pass
                    except Exception as meta_error:
                        app_logger.debug(f"スレッド情報更新エラー: {meta_error}")
            
            # ストリーミング完了 - メッセージを確定・記録
            await msg.send()
                
            # 注意: cl.chat_contextが自動的に履歴を管理するため、手動更新は不要
                
        except Exception as e:
            # エラー時は通常のメッセージとして送信
            await cl.Message(content=f"❌ エラー: {str(e)}").send()
        
        app_logger.info("会話処理完了")
        
    except Exception as e:
        await error_handler.handle_unexpected_error(e, "会話処理")


async def handle_file_upload(message: cl.Message):
    """メッセージに添付されたファイルの処理（Chainlit公式ドキュメント準拠）"""
    try:
        # 公式ドキュメント準拠: elements存在チェック
        if not message.elements:
            await ui.send_info_message("📎 ファイルが添付されていません")
            return
        
        app_logger.info("ファイル処理開始", count=len(message.elements))
        
        # ベクトルストア管理の処理
        from utils.vector_store_handler import vector_store_handler
        
        success_count = 0
        failed_files = []
        
        for element in message.elements:
            # 公式ドキュメント準拠: mime属性とpath属性の確認
            if hasattr(element, 'mime') and hasattr(element, 'path') and hasattr(element, 'name'):
                try:
                    app_logger.debug(f"処理中のファイル: {element.name} ({element.mime})")
                    
                    # ファイル保存とベクトルストア追加
                    saved_path = await vector_store_handler.save_uploaded_file(element)
                    if saved_path:
                        success_count += 1
                        app_logger.info("ファイル保存完了", name=element.name, path=saved_path, mime=element.mime)
                    else:
                        failed_files.append(element.name)
                        
                except Exception as e:
                    failed_files.append(element.name)
                    app_logger.error("ファイル処理エラー", name=element.name, error=str(e))
            else:
                app_logger.warning("無効なファイル要素", element=str(element))
                failed_files.append(getattr(element, 'name', 'Unknown'))
        
        # 結果通知（公式ドキュメント準拠の詳細フィードバック）
        if success_count > 0:
            await ui.send_success_message(
                f"📁 {success_count}個のファイルを正常にアップロードし、ベクトルストアに追加しました。"
            )
            
        if failed_files:
            await ui.send_warning_message(
                f"⚠️ {len(failed_files)}個のファイルの処理に失敗しました: {', '.join(failed_files[:3])}"
                + ("..." if len(failed_files) > 3 else "")
            )
            
        if success_count == 0 and not failed_files:
            await ui.send_info_message("ファイルが検出されましたが、処理対象のファイルがありませんでした。")
            
    except Exception as e:
        await error_handler.handle_unexpected_error(e, "ファイル処理")


@cl.action_callback("create_persona_form")
async def create_persona_action(action: cl.Action):
    """ペルソナ作成アクション"""
    try:
        app_logger.info("ペルソナ作成アクション実行")
        persona_handler = persona_handler_instance or _get_persona_handler()
        await persona_handler.create_persona_interactive()
        await action.remove()
    except Exception as e:
        await error_handler.handle_unexpected_error(e, "ペルソナ作成アクション")

@cl.action_callback("analytics_dashboard")
async def analytics_dashboard_action(action: cl.Action):
    """統計ダッシュボードアクション"""
    try:
        app_logger.info("統計ダッシュボードアクション実行")
        from handlers.analytics_handler import AnalyticsHandler
        analytics_handler = AnalyticsHandler()
        user_id = ui.get_session("user_id")
        await analytics_handler.show_usage_dashboard(user_id)
        await action.remove()
    except Exception as e:
        await error_handler.handle_unexpected_error(e, "統計ダッシュボードアクション")

@cl.action_callback("search_workspace")  
async def search_workspace_action(action: cl.Action):
    """ワークスペース検索アクション"""
    try:
        app_logger.info("検索アクション実行")
        search_query = action.payload.get("query", "")
        if search_query:
            from handlers.search_handler import SearchHandler
            search_handler = SearchHandler()
            user_id = ui.get_session("user_id")
            await search_handler.search_all(search_query, user_id)
        else:
            await ui.send_info_message("検索クエリを指定してください。")
        await action.remove()
    except Exception as e:
        await error_handler.handle_unexpected_error(e, "検索アクション")

def _get_persona_handler():
    """ペルソナハンドラー取得（グローバル変数対応）"""
    global persona_handler_instance
    if persona_handler_instance is None:
        from handlers.persona_handler import PersonaHandler
        persona_handler_instance = PersonaHandler()
    return persona_handler_instance


# 重複していた古い@cl.on_chat_resumeを削除済み


@cl.on_chat_end
async def chat_end():
    """チャット終了時の処理"""
    try:
        app_logger.info("チャット終了")
        
        # セッションベクトルストアのクリーンアップ
        await vector_store_commands.cleanup_session_resources()
        
        # WebSocket接続の監視を停止
        if connection_monitor and hasattr(connection_monitor, 'stop_monitoring'):
            connection_monitor.stop_monitoring()
        elif connection_monitor:
            app_logger.debug("ConnectionMonitorのstop_monitoring メソッドが利用できません")
            
        app_logger.info("チャット終了処理完了")
        
    except Exception as e:
        app_logger.error("チャット終了エラー", error=str(e))


if __name__ == "__main__":
    app_logger.info("🚀 多機能AIワークスペースアプリケーション開始")
    print("🚀 多機能AIワークスペースアプリケーション開始")
    print(f"📊 データレイヤー: {data_layer_type}")
