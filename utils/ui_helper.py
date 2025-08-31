"""
Chainlit UI処理の共通ヘルパー
重複するUI処理パターンを統一化
"""

import chainlit as cl
from typing import Dict, List, Optional, Any


class ChainlitHelper:
    """Chainlit UI操作の共通処理クラス"""
    
    @staticmethod
    async def send_system_message(content: str):
        """システムメッセージを送信"""
        await cl.Message(content=content, author="System").send()
    
    @staticmethod
    async def send_success_message(content: str):
        """成功メッセージを送信"""
        await cl.Message(content=f"✅ {content}", author="System").send()
    
    @staticmethod
    async def send_error_message(content: str):
        """エラーメッセージを送信"""
        await cl.Message(content=f"❌ {content}", author="System").send()
    
    @staticmethod
    async def send_warning_message(content: str):
        """警告メッセージを送信"""
        await cl.Message(content=f"⚠️ {content}", author="System").send()
    
    @staticmethod
    async def send_info_message(content: str):
        """情報メッセージを送信"""
        await cl.Message(content=f"ℹ️ {content}", author="System").send()
    
    @staticmethod
    def get_session(key: str, default=None):
        """セッション値を取得"""
        return cl.user_session.get(key, default)
    
    @staticmethod  
    def set_session(key: str, value):
        """セッション値を設定"""
        cl.user_session.set(key, value)
    
    @staticmethod
    def get_user_id() -> str:
        """現在のユーザーIDを取得"""
        user = cl.user_session.get("user")
        if user and hasattr(user, 'identifier'):
            return user.identifier
        return "anonymous"
    
    @staticmethod
    def get_thread_id() -> Optional[str]:
        """現在のスレッドIDを取得"""
        return cl.user_session.get("thread_id")
    
    @staticmethod
    async def ask_confirmation(message: str) -> bool:
        """確認ダイアログを表示"""
        from utils.action_helper import ask_confirmation
        return await ask_confirmation(message)
    
    @staticmethod
    def format_file_size(size: int) -> str:
        """ファイルサイズを人間が読みやすい形式でフォーマット"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"
    
    @staticmethod
    def format_model_list(models: List[str]) -> str:
        """モデルリストを表示用にフォーマット"""
        return "\n".join([f"• {model}" for model in models])
    
    @staticmethod
    def format_vector_store_info(vs_info: Dict) -> str:
        """ベクトルストア情報を表示用にフォーマット"""
        lines = [
            f"🗂️ **{vs_info.get('name', 'Unknown')}**",
            f"📊 ID: `{vs_info.get('id', 'N/A')}`",
            f"📈 ファイル数: {vs_info.get('file_counts', {}).get('total', 0)}",
            f"📅 作成日: {vs_info.get('created_at', 'Unknown')}"
        ]
        return "\n".join(lines)
    
    @staticmethod
    async def show_loading_message(message: str = "処理中...") -> cl.Message:
        """ローディングメッセージを表示して返す"""
        loading_msg = cl.Message(content=f"⏳ {message}", author="System")
        await loading_msg.send()
        return loading_msg
    
    @staticmethod
    async def update_loading_message(loading_msg: cl.Message, new_content: str):
        """ローディングメッセージを更新"""
        loading_msg.content = new_content
        await loading_msg.update()


# 短縮形のエイリアス
ui = ChainlitHelper