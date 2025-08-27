"""
コマンド処理ハンドラー
app.pyから分離されたコマンド処理機能
"""

from typing import List
from utils.ui_helper import ChainlitHelper as ui
from utils.error_handler import ErrorHandler as error_handler
from utils.logger import app_logger

# ハンドラーの遅延インポート用
settings_handler_instance = None
persona_handler_instance = None


class CommandHandler:
    """コマンド処理を統括するクラス"""
    
    def __init__(self):
        """コマンドハンドラーを初期化"""
        self.commands = {
            "/help": self._handle_help,
            "/stats": self._handle_stats,
            "/setkey": self._handle_setkey,
            "/test": self._handle_test,
            "/status": self._handle_status,
            "/settings": self._handle_settings,
            "/tools": self._handle_tools,
            "/persona": self._handle_persona,
            "/personas": self._handle_persona,
            "/model": self._handle_model,
            "/system": self._handle_system,
            "/new": self._handle_new,
            "/clear": self._handle_clear,
            "/kb": self._handle_kb_deprecated,
            "/vs": self._handle_vs,
            "/vector": self._handle_vs,
        }
    
    def _get_settings_handler(self):
        """設定ハンドラーを遅延インポートで取得"""
        global settings_handler_instance
        if settings_handler_instance is None:
            from handlers.settings_handler import SettingsHandler
            settings_handler_instance = SettingsHandler()
        return settings_handler_instance
    
    def _get_persona_handler(self):
        """ペルソナハンドラーを遅延インポートで取得"""
        global persona_handler_instance
        if persona_handler_instance is None:
            from handlers.persona_handler import PersonaHandler
            persona_handler_instance = PersonaHandler()
        return persona_handler_instance
    
    async def handle_command(self, user_input: str):
        """
        コマンドを処理するメインメソッド
        
        Args:
            user_input: ユーザーの入力（コマンド）
        """
        parts = user_input.split(maxsplit=2)
        cmd = parts[0].lower()
        
        app_logger.debug(f"🎮 コマンド処理", command=cmd)
        
        # コマンドハンドラーを取得して実行
        handler = self.commands.get(cmd)
        if handler:
            try:
                await handler(parts)
            except Exception as e:
                await error_handler.handle_unexpected_error(e, f"コマンド処理 ({cmd})")
        else:
            await ui.send_error_message(f"不明なコマンド: {cmd}\n`/help` でコマンド一覧を確認してください。")
    
    async def _handle_help(self, parts: List[str]):
        """ヘルプコマンドの処理"""
        help_content = """
## 🎛️ 利用可能なコマンド

### 基本コマンド
- `/help` - このヘルプを表示
- `/stats` - 使用統計を表示
- `/status` - システム状態を表示
- `/test` - API接続テスト
- `/new` - 新しいチャットを開始
- `/clear` - チャット履歴をクリア

### 設定・管理
- `/setkey <APIキー>` - OpenAI APIキーを設定
- `/settings` - 設定管理画面を表示
- `/tools` - ツール状態を表示

### ペルソナ管理
- `/persona` - ペルソナ一覧を表示
- `/persona <名前>` - ペルソナを切り替え
- `/persona create` - 新しいペルソナを作成
- `/persona edit <名前>` - ペルソナを編集
- `/persona delete <名前>` - ペルソナを削除

### モデル・システム
- `/model <モデル名>` - モデルを切り替え
- `/system <プロンプト>` - システムプロンプトを設定

### ベクトルストア（基本機能）
- `/vs` - ベクトルストア情報表示
        """
        await ui.send_system_message(help_content)
    
    async def _handle_stats(self, parts: List[str]):
        """統計表示コマンドの処理"""
        settings_handler = self._get_settings_handler()
        await settings_handler.show_statistics()
    
    async def _handle_setkey(self, parts: List[str]):
        """APIキー設定コマンドの処理"""
        if len(parts) > 1:
            settings_handler = self._get_settings_handler()
            await settings_handler.set_api_key(parts[1])
        else:
            await ui.send_error_message("APIキーを指定してください。\n例: `/setkey sk-...`")
    
    async def _handle_test(self, parts: List[str]):
        """接続テストコマンドの処理"""
        settings_handler = self._get_settings_handler()
        await settings_handler.test_connection()
    
    async def _handle_status(self, parts: List[str]):
        """ステータス表示コマンドの処理"""
        settings_handler = self._get_settings_handler()
        await settings_handler.show_status()
    
    async def _handle_settings(self, parts: List[str]):
        """設定画面表示コマンドの処理"""
        settings_handler = self._get_settings_handler()
        await settings_handler.show_settings()
    
    async def _handle_tools(self, parts: List[str]):
        """ツール状態表示コマンドの処理"""
        if len(parts) > 1:
            action = parts[1].lower()
            target = parts[2] if len(parts) > 2 else ""
            settings_handler = self._get_settings_handler()
            await settings_handler.handle_tools_command(action, target)
        else:
            settings_handler = self._get_settings_handler()
            await settings_handler.show_tools_status()
    
    async def _handle_persona(self, parts: List[str]):
        """ペルソナ管理コマンドの処理"""
        persona_handler = self._get_persona_handler()
        
        if len(parts) == 1:
            await persona_handler.show_personas()
        elif len(parts) == 2:
            await persona_handler.switch_persona(parts[1])
        else:
            action = parts[1].lower()
            if action == "create":
                await persona_handler.create_persona_interactive()
            elif action == "delete":
                if len(parts) > 2:
                    await persona_handler.delete_persona(parts[2])
                else:
                    await ui.send_error_message("削除するペルソナ名を指定してください。\n例: `/persona delete creative`")
            elif action in ["edit", "update"]:
                if len(parts) > 2:
                    await persona_handler.edit_persona(parts[2])
                else:
                    await ui.send_error_message("編集するペルソナ名を指定してください。\n例: `/persona edit プログラミング専門家`")
            else:
                await ui.send_error_message(f"不明なペルソナアクション: {action}")
    
    async def _handle_model(self, parts: List[str]):
        """モデル変更コマンドの処理"""
        if len(parts) > 1:
            settings_handler = self._get_settings_handler()
            await settings_handler.change_model(parts[1])
        else:
            await ui.send_error_message("モデル名を指定してください。\n例: `/model gpt-4o`")
    
    async def _handle_system(self, parts: List[str]):
        """システムプロンプト設定コマンドの処理"""
        if len(parts) > 1:
            prompt = " ".join(parts[1:])
            settings_handler = self._get_settings_handler()
            await settings_handler.set_system_prompt(prompt)
        else:
            await ui.send_error_message("システムプロンプトを指定してください。\n例: `/system あなたは親切なアシスタントです`")
    
    async def _handle_new(self, parts: List[str]):
        """新しいチャット開始コマンドの処理"""
        settings_handler = self._get_settings_handler()
        await settings_handler.start_new_chat()
    
    async def _handle_clear(self, parts: List[str]):
        """チャット履歴クリアコマンドの処理"""
        ui.set_session("message_history", [])
        ui.set_session("previous_response_id", None)
        await ui.send_success_message("チャット履歴をクリアしました。")
    
    async def _handle_kb_deprecated(self, parts: List[str]):
        """廃止されたKBコマンドの処理"""
        await ui.send_info_message(
            "`/kb`コマンドは廃止されました。\n\n"
            "代わりに以下のコマンドをご利用ください：\n"
            "- `/vs` - ベクトルストア管理\n"
            "- `/vs gui` - GUI管理パネル\n"
            "- `/vs session` - セッション情報\n\n"
            "ファイルをアップロードすると自動的にベクトルストアに追加されます。"
        )
    
    async def _handle_vs(self, parts: List[str]):
        """ベクトルストア管理コマンドの処理"""
        await ui.send_system_message(
            "🔧 ベクトルストア機能は基本実装を使用してください。\n"
            "詳細な管理機能は utils/vector_store_handler.py を参照してください。"
        )


# グローバルインスタンス
command_handler = CommandHandler()