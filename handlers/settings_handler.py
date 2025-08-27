"""
設定管理ハンドラー
app.pyから分離された設定管理機能
"""

import chainlit as cl
from typing import Dict, List, Optional
from utils.ui_helper import ChainlitHelper as ui
from utils.error_handler import ErrorHandler as error_handler
from utils.logger import app_logger
from utils.config import config_manager
from utils.responses_handler import responses_handler


class SettingsHandler:
    """設定管理を統括するクラス"""
    
    async def show_settings(self):
        """設定画面を表示"""
        try:
            settings = ui.get_session("settings", {})
            active_persona = ui.get_session("active_persona")
            
            # 基本設定
            message = "# ⚙️ システム設定\n\n"
            
            # API設定
            message += "## 🔑 API設定\n"
            api_key = settings.get("OPENAI_API_KEY", "未設定")
            masked_key = f"{api_key[:10]}...{api_key[-4:]}" if api_key != "未設定" and len(api_key) > 14 else api_key
            message += f"- OpenAI API Key: `{masked_key}`\n\n"
            
            # モデル設定
            message += "## 🤖 モデル設定\n"
            current_model = settings.get("DEFAULT_MODEL", "gpt-4o-mini")
            message += f"- 現在のモデル: **{current_model}**\n"
            message += f"- 利用可能なモデル: gpt-4o, gpt-4o-mini, gpt-4-turbo\n\n"
            
            # ペルソナ設定
            message += "## 🎭 ペルソナ設定\n"
            if active_persona:
                message += f"- アクティブなペルソナ: **{active_persona.get('name', 'Unknown')}**\n"
                message += f"- 説明: {active_persona.get('description', 'No description')}\n"
                message += f"- モデル: {active_persona.get('model', 'gpt-4o-mini')}\n"
                message += f"- Temperature: {active_persona.get('temperature', 0.7)}\n"
            else:
                message += "- アクティブなペルソナ: なし\n"
            message += "\n"
            
            # システムプロンプト
            system_prompt = ui.get_session("system_prompt", "")
            message += "## 💬 システムプロンプト\n"
            if system_prompt:
                preview = system_prompt[:100] + "..." if len(system_prompt) > 100 else system_prompt
                message += f"```\n{preview}\n```\n\n"
            else:
                message += "設定されていません\n\n"
            
            # 操作ガイド
            message += "## 📖 操作コマンド\n"
            message += "- `/setkey <APIキー>` - APIキーを設定\n"
            message += "- `/model <モデル名>` - モデルを変更\n"
            message += "- `/system <プロンプト>` - システムプロンプトを設定\n"
            message += "- `/persona <名前>` - ペルソナを切り替え\n"
            message += "- `/test` - API接続テスト\n"
            message += "- `/stats` - 使用統計を表示\n"
            message += "- `/status` - システム状態を表示\n"
            
            await ui.send_system_message(message)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "設定画面表示")
    
    async def set_api_key(self, api_key: str):
        """APIキーを設定"""
        try:
            if not api_key or len(api_key) < 20:
                await ui.send_error_message("無効なAPIキーです。正しいOpenAI APIキーを入力してください。")
                return
            
            app_logger.info("APIキー設定開始")
            
            settings = ui.get_session("settings", {})
            settings["OPENAI_API_KEY"] = api_key
            ui.set_session("settings", settings)
            
            # responses_handlerにAPIキーを設定
            responses_handler.update_api_key(api_key)
            
            app_logger.info("APIキー設定成功")
            
            await ui.send_success_message("APIキーを設定しました")
            await self.test_connection()
            
        except Exception as e:
            await error_handler.handle_api_error(e, "APIキー設定")
    
    async def test_connection(self):
        """API接続テスト"""
        try:
            loading_msg = await ui.show_loading_message("接続テスト中...")
            
            success, message, models = await config_manager.test_connection()
            
            if success:
                test_success, test_message = await config_manager.test_simple_completion()
                result = f"✅ 接続成功！\n{test_message if test_success else '応答テスト失敗'}"
                app_logger.info("API接続テスト成功")
            else:
                result = f"❌ 接続失敗: {message}"
                app_logger.error("API接続テスト失敗", error=message)
            
            await ui.update_loading_message(loading_msg, result)
            
        except Exception as e:
            await error_handler.handle_api_error(e, "接続テスト")
    
    async def show_status(self):
        """システム状態を表示"""
        try:
            settings = ui.get_session("settings", {})
            message_history = ui.get_session("message_history", [])
            active_persona = ui.get_session("active_persona")
            
            message = "# 📊 システム状態\n\n"
            
            # 接続状態
            message += "## 🔗 接続状態\n"
            api_key = settings.get("OPENAI_API_KEY")
            if api_key:
                message += "- OpenAI API: ✅ 設定済み\n"
            else:
                message += "- OpenAI API: ❌ 未設定\n"
            
            # セッション情報
            message += "\n## 💬 セッション情報\n"
            message += f"- メッセージ履歴: {len(message_history)}件\n"
            message += f"- ユーザーID: {ui.get_user_id()}\n"
            message += f"- スレッドID: {ui.get_thread_id() or 'なし'}\n"
            
            # アクティブ設定
            message += "\n## ⚙️ アクティブ設定\n"
            message += f"- モデル: {settings.get('DEFAULT_MODEL', 'gpt-4o-mini')}\n"
            if active_persona:
                message += f"- ペルソナ: {active_persona.get('name', 'Unknown')}\n"
            else:
                message += "- ペルソナ: なし\n"
            
            # システムリソース
            message += "\n## 💾 システムリソース\n"
            message += f"- Python Version: 3.x\n"
            message += f"- Chainlit Version: 最新\n"
            
            await ui.send_system_message(message)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "システム状態表示")
    
    async def show_statistics(self):
        """使用統計を表示"""
        try:
            settings = ui.get_session("settings", {})
            message_history = ui.get_session("message_history", [])
            
            message = "# 📈 使用統計\n\n"
            
            # 会話統計
            message += "## 💬 会話統計\n"
            message += f"- 総メッセージ数: {len(message_history)}\n"
            
            user_messages = len([msg for msg in message_history if msg.get("role") == "user"])
            assistant_messages = len([msg for msg in message_history if msg.get("role") == "assistant"])
            
            message += f"- ユーザーメッセージ: {user_messages}\n"
            message += f"- アシスタントメッセージ: {assistant_messages}\n"
            
            # モデル使用統計
            message += "\n## 🤖 モデル使用\n"
            current_model = settings.get("DEFAULT_MODEL", "gpt-4o-mini")
            message += f"- 現在のモデル: {current_model}\n"
            
            # セッション統計
            message += "\n## 📊 セッション統計\n"
            message += f"- ユーザーID: {ui.get_user_id()}\n"
            message += f"- セッション開始時刻: 現在のセッション\n"
            
            await ui.send_system_message(message)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "使用統計表示")
    
    async def change_model(self, model: str):
        """モデルを変更"""
        try:
            available_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
            
            if model not in available_models:
                await ui.send_error_message(
                    f"不明なモデル: {model}\n"
                    f"利用可能なモデル: {', '.join(available_models)}"
                )
                return
            
            # 設定を更新
            settings = ui.get_session("settings", {})
            settings["DEFAULT_MODEL"] = model
            ui.set_session("settings", settings)
            
            # responses_handlerのモデルも更新
            responses_handler.update_model(model)
            
            app_logger.info("モデル変更", model=model)
            
            await ui.send_success_message(f"モデルを '{model}' に変更しました")
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "モデル変更")
    
    async def set_system_prompt(self, prompt: str):
        """システムプロンプトを設定"""
        try:
            if not prompt.strip():
                await ui.send_error_message("システムプロンプトが空です。")
                return
            
            ui.set_session("system_prompt", prompt)
            
            app_logger.info("システムプロンプト設定")
            
            # プレビューを表示
            preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
            
            await ui.send_success_message(
                f"システムプロンプトを設定しました\n\n"
                f"**設定内容:**\n```\n{preview}\n```"
            )
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "システムプロンプト設定")
    
    async def start_new_chat(self):
        """新しいチャットを開始"""
        try:
            # セッション履歴をクリア
            ui.set_session("message_history", [])
            ui.set_session("previous_response_id", None)
            
            # responses_handlerもリセット
            responses_handler.reset_conversation()
            
            app_logger.info("新しいチャット開始")
            
            await ui.send_success_message(
                "新しいチャットを開始しました\n"
                "会話履歴がクリアされ、新鮮な状態でお話しできます！"
            )
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "新しいチャット開始")
    
    async def show_tools_status(self):
        """ツール状態を表示"""
        try:
            message = "# 🛠️ ツール状態\n\n"
            
            # コアツール
            message += "## 🎯 コアツール\n"
            message += "- ✅ UI Helper - UI操作支援\n"
            message += "- ✅ Error Handler - エラー処理統一\n"
            message += "- ✅ Logger - ログ管理\n"
            message += "- ✅ Config Manager - 設定管理\n"
            message += "- ✅ Persona Manager - ペルソナ管理\n"
            
            # ハンドラー
            message += "\n## 📁 ハンドラー\n"
            message += "- ✅ Command Handler - コマンド処理\n"
            message += "- ✅ Persona Handler - ペルソナ管理\n"
            message += "- ✅ Settings Handler - 設定管理\n"
            message += "- ✅ Responses Handler - API応答処理\n"
            
            # ベクトルストア
            message += "\n## 🗂️ ベクトルストア\n"
            message += "- ✅ Vector Store Handler - 基本機能\n"
            message += "- 📝 3層構造 (Company/Personal/Session)\n"
            
            await ui.send_system_message(message)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "ツール状態表示")
    
    async def handle_tools_command(self, action: str, target: str):
        """ツール関連コマンドの処理"""
        try:
            if action == "status":
                await self.show_tools_status()
            elif action == "info":
                await ui.send_info_message(
                    "ツール機能:\n"
                    "- `/tools` - ツール状態表示\n"
                    "- `/tools status` - 詳細状態表示"
                )
            else:
                await ui.send_error_message(f"不明なツールアクション: {action}")
                
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "ツールコマンド処理")


# グローバルインスタンス
settings_handler = SettingsHandler()