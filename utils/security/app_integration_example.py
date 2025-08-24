"""
セキュリティ実装の統合例
app.pyで使用するための実装サンプル
"""

import chainlit as cl
from typing import Optional, List, Dict


async def get_current_user_id() -> str:
    """
    現在のユーザーIDを取得
    
    Returns:
        ユーザーID
    """
    # Chainlitのユーザーセッションから取得
    user = cl.user_session.get("user")
    
    if user:
        # 認証済みユーザー
        return user.identifier
    else:
        # 未認証ユーザー（セッションIDを使用）
        session_id = cl.user_session.get("session_id")
        return f"anon_{session_id[:8]}" if session_id else "anonymous"


async def create_personal_vector_store_secure(name: str = None, category: str = None) -> Optional[str]:
    """
    セキュアな個人用ベクトルストアを作成
    
    Args:
        name: ベクトルストア名（省略時は自動生成）
        category: カテゴリ
    
    Returns:
        作成されたベクトルストアID
    """
    from utils.vector_store_handler import vector_store_handler
    from utils.security.vector_store_security import security_manager, access_logger
    
    # 現在のユーザーIDを取得
    user_id = await get_current_user_id()
    
    # 名前が指定されていない場合は自動生成
    if not name:
        from datetime import datetime
        name = f"Personal KB - {user_id} - {datetime.now().strftime('%Y%m%d_%H%M')}"
    
    # メタデータを作成
    metadata = security_manager.create_secure_metadata(
        user_id=user_id,
        category=category or "general",
        api_key=vector_store_handler.api_key
    )
    
    try:
        # ベクトルストアを作成
        vector_store = await vector_store_handler.async_client.beta.vector_stores.create(
            name=name,
            metadata=metadata
        )
        
        vs_id = vector_store.id
        
        # セッションに保存
        cl.user_session.set("personal_vs_id", vs_id)
        vector_store_handler.personal_vs_id = vs_id
        
        # 成功ログ
        access_logger.log_access(
            user_id=user_id,
            vector_store_id=vs_id,
            action="create",
            success=True
        )
        
        await cl.Message(
            content=f"""✅ セキュアな個人用ベクトルストアを作成しました

🆔 **ID**: `{vs_id}`
📁 **名前**: {name}
🏷️ **カテゴリ**: {category or 'general'}
👤 **所有者**: {user_id}
🔐 **アクセスレベル**: プライベート

このベクトルストアはあなた専用です。他のユーザーはアクセスできません。""",
            author="System"
        ).send()
        
        return vs_id
        
    except Exception as e:
        # エラーログ
        access_logger.log_access(
            user_id=user_id,
            vector_store_id="N/A",
            action="create",
            success=False,
            reason=str(e)
        )
        
        await cl.Message(
            content=f"❌ ベクトルストア作成エラー: {e}",
            author="System"
        ).send()
        
        return None


async def show_my_vector_stores():
    """現在のユーザーがアクセス可能なベクトルストア一覧を表示"""
    from utils.vector_store_handler import vector_store_handler
    from utils.security.vector_store_security import security_manager
    from datetime import datetime
    
    # 現在のユーザーIDを取得
    user_id = await get_current_user_id()
    
    try:
        # 全てのベクトルストアを取得
        all_stores = await vector_store_handler.async_client.beta.vector_stores.list()
        
        my_stores = []
        shared_stores = []
        
        for vs in all_stores.data:
            try:
                # 詳細情報を取得
                vs_detail = await vector_store_handler.async_client.beta.vector_stores.retrieve(vs.id)
                metadata = getattr(vs_detail, 'metadata', {}) or {}
                
                # アクセス権限をチェック
                if security_manager.can_access(metadata, user_id, vector_store_handler.api_key, "read"):
                    store_info = {
                        "id": vs_detail.id,
                        "name": vs_detail.name,
                        "file_count": vs_detail.file_counts.total if hasattr(vs_detail.file_counts, 'total') else 0,
                        "created_at": vs_detail.created_at,
                        "category": metadata.get("category", "general"),
                        "access_level": metadata.get("access_level", "unknown")
                    }
                    
                    # 所有者かどうかで分類
                    if metadata.get("user_id") == user_id:
                        my_stores.append(store_info)
                    else:
                        shared_stores.append(store_info)
                        
            except Exception as e:
                print(f"⚠️ ベクトルストア {vs.id} の取得エラー: {e}")
                continue
        
        # メッセージを構築
        message = f"# 📁 ベクトルストア一覧\n\n"
        message += f"👤 **ユーザー**: {user_id}\n\n"
        
        # 自分のベクトルストア
        if my_stores:
            message += "## 🔐 マイベクトルストア\n\n"
            for store in my_stores:
                message += f"### {store['name']}\n"
                message += f"- 🆔 ID: `{store['id']}`\n"
                message += f"- 📄 ファイル数: {store['file_count']}\n"
                message += f"- 🏷️ カテゴリ: {store['category']}\n"
                message += f"- 🔓 アクセス: {store['access_level']}\n"
                message += f"- 📅 作成日: {datetime.fromtimestamp(store['created_at']).strftime('%Y-%m-%d %H:%M')}\n\n"
        else:
            message += "## 🔐 マイベクトルストア\n\n"
            message += "*作成されたベクトルストアがありません*\n\n"
        
        # 共有されているベクトルストア
        if shared_stores:
            message += "## 🤝 共有ベクトルストア\n\n"
            for store in shared_stores:
                message += f"### {store['name']}\n"
                message += f"- 🆔 ID: `{store['id']}`\n"
                message += f"- 📄 ファイル数: {store['file_count']}\n"
                message += f"- 🏷️ カテゴリ: {store['category']}\n"
                message += f"- 📅 作成日: {datetime.fromtimestamp(store['created_at']).strftime('%Y-%m-%d %H:%M')}\n\n"
        
        # コマンドヘルプ
        message += "\n## 💡 コマンド\n"
        message += "- `/vs create [名前] [カテゴリ]` - 新規作成\n"
        message += "- `/vs delete [ID]` - 削除（自分のもののみ）\n"
        message += "- `/vs share [ID] [team|public]` - 共有設定\n"
        message += "- `/vs category [ID] [新カテゴリ]` - カテゴリ変更"
        
        await cl.Message(content=message, author="System").send()
        
    except Exception as e:
        await cl.Message(
            content=f"❌ ベクトルストア一覧取得エラー: {e}",
            author="System"
        ).send()


async def delete_my_vector_store(vs_id: str):
    """自分のベクトルストアを削除（他人のものは削除不可）"""
    from utils.vector_store_handler import vector_store_handler
    from utils.security.vector_store_security import security_manager, access_logger
    
    # 現在のユーザーIDを取得
    user_id = await get_current_user_id()
    
    try:
        # ベクトルストアの詳細を取得
        vs_detail = await vector_store_handler.async_client.beta.vector_stores.retrieve(vs_id)
        metadata = getattr(vs_detail, 'metadata', {}) or {}
        
        # 削除権限をチェック
        if not security_manager.can_access(metadata, user_id, vector_store_handler.api_key, "delete"):
            # アクセス拒否ログ
            access_logger.log_access(
                user_id=user_id,
                vector_store_id=vs_id,
                action="delete",
                success=False,
                reason="Access denied"
            )
            
            await cl.Message(
                content=f"""❌ **削除権限がありません**

ベクトルストア `{vs_id}` は他のユーザーが作成したものです。
削除できるのは所有者のみです。

所有者: {metadata.get('user_id', '不明')}
あなた: {user_id}""",
                author="System"
            ).send()
            return False
        
        # 削除実行
        await vector_store_handler.async_client.beta.vector_stores.delete(vs_id)
        
        # 成功ログ
        access_logger.log_access(
            user_id=user_id,
            vector_store_id=vs_id,
            action="delete",
            success=True
        )
        
        await cl.Message(
            content=f"✅ ベクトルストア `{vs_id}` を削除しました",
            author="System"
        ).send()
        
        return True
        
    except Exception as e:
        # エラーログ
        access_logger.log_access(
            user_id=user_id,
            vector_store_id=vs_id,
            action="delete",
            success=False,
            reason=str(e)
        )
        
        await cl.Message(
            content=f"❌ 削除エラー: {e}",
            author="System"
        ).send()
        
        return False


async def share_my_vector_store(vs_id: str, access_level: str = "team"):
    """自分のベクトルストアの共有設定を変更"""
    from utils.vector_store_handler import vector_store_handler
    from utils.security.vector_store_security import security_manager, access_logger
    
    # 現在のユーザーIDを取得
    user_id = await get_current_user_id()
    
    # アクセスレベルの検証
    valid_levels = ["private", "team", "public"]
    if access_level not in valid_levels:
        await cl.Message(
            content=f"❌ 無効なアクセスレベル: {access_level}\n有効な値: {', '.join(valid_levels)}",
            author="System"
        ).send()
        return False
    
    try:
        # 現在のベクトルストアを取得
        vs_detail = await vector_store_handler.async_client.beta.vector_stores.retrieve(vs_id)
        current_metadata = getattr(vs_detail, 'metadata', {}) or {}
        
        # 更新権限をチェック
        if not security_manager.can_access(current_metadata, user_id, vector_store_handler.api_key, "write"):
            await cl.Message(
                content=f"❌ このベクトルストアの共有設定を変更する権限がありません",
                author="System"
            ).send()
            return False
        
        # メタデータを更新
        new_metadata = {**current_metadata}
        new_metadata["access_level"] = access_level
        new_metadata["updated_at"] = datetime.now().isoformat()
        new_metadata["updated_by"] = user_id
        
        # ベクトルストアを更新
        await vector_store_handler.async_client.beta.vector_stores.update(
            vector_store_id=vs_id,
            metadata=new_metadata
        )
        
        # 成功ログ
        access_logger.log_access(
            user_id=user_id,
            vector_store_id=vs_id,
            action="update",
            success=True,
            reason=f"Changed access_level to {access_level}"
        )
        
        # アクセスレベルの説明
        level_descriptions = {
            "private": "あなただけがアクセス可能",
            "team": "同じプロジェクトメンバーがアクセス可能",
            "public": "全員が読み取り可能"
        }
        
        await cl.Message(
            content=f"""✅ 共有設定を変更しました

🆔 **ベクトルストア**: `{vs_id}`
🔐 **新しいアクセスレベル**: {access_level}
📝 **説明**: {level_descriptions[access_level]}""",
            author="System"
        ).send()
        
        return True
        
    except Exception as e:
        await cl.Message(
            content=f"❌ 共有設定変更エラー: {e}",
            author="System"
        ).send()
        return False


# セキュリティチェック用のデコレータ
def require_ownership(action: str = "access"):
    """
    所有権を要求するデコレータ
    
    Args:
        action: アクション名（read, write, delete）
    """
    def decorator(func):
        async def wrapper(vs_id: str, *args, **kwargs):
            from utils.vector_store_handler import vector_store_handler
            from utils.security.vector_store_security import security_manager
            
            user_id = await get_current_user_id()
            
            # ベクトルストアの詳細を取得
            vs_detail = await vector_store_handler.async_client.beta.vector_stores.retrieve(vs_id)
            metadata = getattr(vs_detail, 'metadata', {}) or {}
            
            # アクセス権限をチェック
            if not security_manager.can_access(metadata, user_id, vector_store_handler.api_key, action):
                await cl.Message(
                    content=f"❌ {action}権限がありません",
                    author="System"
                ).send()
                return None
            
            # 元の関数を実行
            return await func(vs_id, *args, **kwargs)
        
        return wrapper
    return decorator
