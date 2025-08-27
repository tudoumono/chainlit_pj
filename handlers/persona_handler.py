"""
ペルソナ管理ハンドラー
app.pyから分離されたペルソナ管理機能
"""

import chainlit as cl
from utils.ui_helper import ChainlitHelper as ui
from utils.error_handler import ErrorHandler as error_handler
from utils.persona_manager import persona_manager


class PersonaHandler:
    """ペルソナ管理を統括するクラス"""
    
    async def show_personas(self):
        """ペルソナ一覧を表示"""
        try:
            personas = await persona_manager.get_all_personas()
            active_persona = ui.get_session("active_persona")
            
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
            
            await ui.send_system_message(message)
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "ペルソナ一覧表示")
    
    async def switch_persona(self, persona_name: str):
        """ペルソナを切り替え"""
        try:
            personas = await persona_manager.get_all_personas()
            
            # ペルソナ名の完全一致または部分一致で検索
            target_persona = None
            for persona in personas:
                if persona.get("name") == persona_name or persona_name in persona.get("name", ""):
                    target_persona = persona
                    break
            
            if not target_persona:
                await ui.send_error_message(f"ペルソナ '{persona_name}' が見つかりません。\n`/persona` で一覧を確認してください。")
                return
            
            # ペルソナを有効化
            ui.set_session("active_persona", target_persona)
            
            # 設定をChainlitの設定に反映
            await self._apply_persona_settings(target_persona)
            
            await ui.send_success_message(f"ペルソナを '{target_persona.get('name')}' に切り替えました。\n"
                                        f"🤖 Model: {target_persona.get('model', 'gpt-4o-mini')}\n"
                                        f"🌡️ Temperature: {target_persona.get('temperature', 0.7)}")
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "ペルソナ切り替え")
    
    async def create_persona_interactive(self):
        """インタラクティブなペルソナ作成"""
        try:
            # アクションボタンでペルソナ作成フォームを送信
            actions = [
                cl.Action(name="create_persona_form", value="start", label="📝 ペルソナ作成フォーム")
            ]
            
            await cl.Message(
                content="# 🎭 新しいペルソナを作成\n\n以下のボタンを押してペルソナ作成フォームを開始してください。",
                author="System",
                actions=actions
            ).send()
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "ペルソナ作成開始")
    
    async def delete_persona(self, persona_name: str):
        """ペルソナを削除"""
        try:
            # デフォルトペルソナの削除を防止
            if persona_name in ["汎用アシスタント", "プログラミング専門家", "創作アシスタント"]:
                await ui.send_error_message(f"デフォルトペルソナ '{persona_name}' は削除できません。")
                return
            
            personas = await persona_manager.get_all_personas()
            target_persona = None
            
            for persona in personas:
                if persona.get("name") == persona_name:
                    target_persona = persona
                    break
            
            if not target_persona:
                await ui.send_error_message(f"ペルソナ '{persona_name}' が見つかりません。")
                return
            
            # 確認ダイアログ
            confirmation = await ui.ask_confirmation(f"ペルソナ '{persona_name}' を削除しますか？")
            
            if not confirmation:
                await ui.send_info_message("削除をキャンセルしました。")
                return
            
            # ペルソナ削除
            success = await persona_manager.delete_persona(persona_name)
            
            if success:
                # アクティブなペルソナが削除された場合はデフォルトに戻す
                active_persona = ui.get_session("active_persona")
                if active_persona and active_persona.get("name") == persona_name:
                    default_persona = await persona_manager.get_persona("汎用アシスタント")
                    ui.set_session("active_persona", default_persona)
                    await self._apply_persona_settings(default_persona)
                
                await ui.send_success_message(f"ペルソナ '{persona_name}' を削除しました。")
            else:
                await ui.send_error_message(f"ペルソナ '{persona_name}' の削除に失敗しました。")
                
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "ペルソナ削除")
    
    async def edit_persona(self, persona_name: str):
        """ペルソナを編集"""
        try:
            personas = await persona_manager.get_all_personas()
            target_persona = None
            
            for persona in personas:
                if persona.get("name") == persona_name:
                    target_persona = persona
                    break
            
            if not target_persona:
                await ui.send_error_message(f"ペルソナ '{persona_name}' が見つかりません。")
                return
            
            # ペルソナ情報を表示
            message = f"# 🎭 ペルソナ編集: {persona_name}\n\n"
            message += f"**現在の設定:**\n"
            message += f"- 🤖 Model: {target_persona.get('model', 'gpt-4o-mini')}\n"
            message += f"- 🌡️ Temperature: {target_persona.get('temperature', 0.7)}\n"
            message += f"- 📝 Description: {target_persona.get('description', 'No description')}\n"
            message += f"- 💬 System Prompt: {target_persona.get('system_prompt', '')[:100]}...\n\n"
            
            message += "**編集するには新しいペルソナを作成し、古いものを削除してください。**\n"
            message += "💡 `/persona create` でペルソナ作成\n"
            message += f"💡 `/persona delete {persona_name}` で現在のものを削除"
            
            await ui.send_system_message(message)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "ペルソナ編集")
    
    async def _apply_persona_settings(self, persona: dict):
        """ペルソナの設定をセッションに適用"""
        try:
            # システムプロンプトを設定
            ui.set_session("system_prompt", persona.get("system_prompt", ""))
            
            # モデル設定を保存（Chainlitの設定システムと連携）
            ui.set_session("selected_model", persona.get("model", "gpt-4o-mini"))
            ui.set_session("temperature", persona.get("temperature", 0.7))
            ui.set_session("max_tokens", persona.get("max_tokens"))
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "ペルソナ設定適用", show_to_user=False)


# グローバルインスタンス
persona_handler = PersonaHandler()