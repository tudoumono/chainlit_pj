"""
Chainlit認証設定
基本認証（ユーザー名/パスワード）を実装
"""

from typing import Optional
import chainlit as cl
from chainlit.user import User


@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> Optional[User]:
    """
    認証コールバック関数
    ユーザー名とパスワードを検証して、認証されたユーザーを返す
    """
    import os
    from dotenv import load_dotenv
    
    # .envファイルから設定を読み込み
    load_dotenv()
    
    # 環境変数からパスワードを取得
    auth_secret = os.getenv("CHAINLIT_AUTH_SECRET", "admin123")
    
    # シンプルな認証（本番環境ではより安全な方法を使用してください）
    # デフォルト: ユーザー名 "admin" とパスワードは環境変数から
    if username == "admin" and password == auth_secret:
        return User(
            identifier=username,
            metadata={
                "role": "admin",
                "provider": "credentials"
            }
        )
    
    # 認証失敗
    return None
