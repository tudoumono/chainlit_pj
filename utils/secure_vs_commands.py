"""
app.py統合用のセキュアなベクトルストアコマンド
所有者のもののみ表示、他人のVSはID指定で使用可能
"""

import chainlit as cl
from typing import Optional, List
from datetime import datetime


async def get_current_user_id() -> str:
    """現在のユーザーIDを取得"""
    user = cl.user_session.get("user")
    if user:
        return user.identifier
    else:
        # 未認証ユーザーはセッションIDを使用
        session_id = cl.user_session.get("session_id", "unknown")
        return f"anon_{session_id[:8]}"


async def handle_vs_command_secure(message_content: str):
    """
    セキュアな/vsコマンドの処理
    
    Args:
        message_content: メッセージ内容
    """
    from utils.vector_store_handler import vector_store_handler
    from utils.secure_vector_store_manager import secure_vs_manager, initialize_secure_manager
    
    # セキュアマネージャーを初期化（まだの場合）
    if secure_vs_manager is None:
        initialize_secure_manager(vector_store_handler)
    
    # 現在のユーザーIDを取得
    user_id = await get_current_user_id()
    
    # コマンドをパース
    parts = message_content.split()
    
    # /vs または /vs list - 自分のVSのみ表示
    if len(parts) == 1 or (len(parts) == 2 and parts[1] == "list"):
        await show_my_vector_stores_only(user_id)
    
    # /vs create [名前] [カテゴリ] - 新規作成
    elif len(parts) >= 2 and parts[1] == "create":
        name = parts[2] if len(parts) > 2 else None
        category = parts[3] if len(parts) > 3 else None
        await create_secure_vector_store(user_id, name, category)
    
    # /vs delete [ID] - 削除（所有者のみ）
    elif len(parts) >= 3 and parts[1] == "delete":
        vs_id = parts[2]
        await delete_secure_vector_store(vs_id, user_id)
    
    # /vs rename [ID] [新しい名前] - 名前変更（所有者のみ）
    elif len(parts) >= 4 and parts[1] == "rename":
        vs_id = parts[2]
        new_name = " ".join(parts[3:])
        await rename_secure_vector_store(vs_id, user_id, new_name)
    
    # /vs use [ID] - 使用設定（他人のVSもIDで使用可能）
    elif len(parts) >= 3 and parts[1] == "use":
        vs_id = parts[2]
        await use_vector_store_by_id(vs_id, user_id)
    
    # /vs info [ID] - 詳細情報（読み取り可能なもののみ）
    elif len(parts) >= 3 and parts[1] == "info":
        vs_id = parts[2]
        await show_vector_store_info_secure(vs_id, user_id)
    
    # /vs files [ID] - ファイル一覧（読み取り可能なもののみ）
    elif len(parts) >= 3 and parts[1] == "files":
        vs_id = parts[2]
        await show_vector_store_files_secure(vs_id, user_id)
    
    # ヘルプ
    else:
        await show_vs_help()


async def show_my_vector_stores_only(user_id: str):
    """自分が所有するベクトルストアのみ表示"""
    from utils.secure_vector_store_manager import secure_vs_manager
    
    my_stores = await secure_vs_manager.list_my_vector_stores(user_id)
    
    if not my_stores:
        message = """# 📁 マイベクトルストア

ベクトルストアがまだ作成されていません。

## 作成方法
`/vs create [名前] [カテゴリ]` で新規作成できます。

例：
- `/vs create` - 自動的に名前を生成
- `/vs create "技術文書"` - 名前を指定
- `/vs create "技術文書" programming` - カテゴリも指定

## 他人のベクトルストアを使用
IDを知っている場合は、他人のベクトルストアも使用できます（読み取り専用）：
`/vs use [ベクトルストアID]`"""
    else:
        message = f"# 📁 マイベクトルストア\n\n"
        message += f"👤 **ユーザー**: {user_id}\n"
        message += f"📊 **所有数**: {len(my_stores)}個\n\n"
        
        for store in my_stores:
            message += f"## {store['name']}\n"
            message += f"🆔 `{store['id']}`\n"
            message += f"📄 ファイル数: {store['file_counts'].total if hasattr(store['file_counts'], 'total') else 0}\n"
            message += f"🏷️ カテゴリ: {store['category']}\n"
            message += f"📅 作成日: {datetime.fromtimestamp(store['created_at']).strftime('%Y-%m-%d %H:%M')}\n\n"
        
        message += "---\n\n"
        message += "## 💡 コマンド\n"
        message += "- `/vs create [名前]` - 新規作成\n"
        message += "- `/vs use [ID]` - 使用設定（他人のIDも可）\n"
        message += "- `/vs rename [ID] [新名前]` - 名前変更\n"
        message += "- `/vs delete [ID]` - 削除\n"
        message += "- `/vs files [ID]` - ファイル一覧\n\n"
        message += "**注意**: 表示されるのはあなたが所有するベクトルストアのみです。\n"
        message += "他人のベクトルストアはIDを直接指定すれば使用できます（読み取り専用）。"
    
    await cl.Message(content=message, author="System").send()


async def create_secure_vector_store(user_id: str, name: Optional[str] = None, 
                                    category: Optional[str] = None):
    """セキュアなベクトルストア作成"""
    from utils.secure_vector_store_manager import secure_vs_manager
    
    msg = cl.Message(content="🔄 ベクトルストアを作成中...", author="System")
    await msg.send()
    
    vs_id = await secure_vs_manager.create_personal_vector_store(user_id, name, category)
    
    if vs_id:
        # セッションに保存
        cl.user_session.set("personal_vs_id", vs_id)
        
        message = f"""✅ ベクトルストアを作成しました

🆔 **ID**: `{vs_id}`
📁 **名前**: {name or f"Personal KB - {datetime.now().strftime('%Y%m%d_%H%M')}"}
🏷️ **カテゴリ**: {category or 'general'}
👤 **所有者**: あなた

このベクトルストアはあなた専用です。
他のユーザーには表示されません。
IDを共有すれば、他のユーザーも読み取り専用で使用できます。"""
        
        await cl.Message(content=message, author="System").send()
    else:
        await cl.Message(
            content="❌ ベクトルストアの作成に失敗しました",
            author="System"
        ).send()


async def delete_secure_vector_store(vs_id: str, user_id: str):
    """セキュアなベクトルストア削除"""
    from utils.secure_vector_store_manager import secure_vs_manager
    from utils.action_helper import ask_confirmation
    
    # 確認
    if await ask_confirmation(
        f"⚠️ ベクトルストア `{vs_id}` を削除しますか？\nこの操作は取り消せません。",
        yes_label="削除する",
        no_label="キャンセル"
    ):
        success, message = await secure_vs_manager.delete_vector_store(vs_id, user_id)
        await cl.Message(content=message, author="System").send()
    else:
        await cl.Message(content="削除をキャンセルしました", author="System").send()


async def rename_secure_vector_store(vs_id: str, user_id: str, new_name: str):
    """セキュアなベクトルストア名前変更"""
    from utils.secure_vector_store_manager import secure_vs_manager
    
    success, message = await secure_vs_manager.rename_vector_store(vs_id, user_id, new_name)
    await cl.Message(content=message, author="System").send()


async def use_vector_store_by_id(vs_id: str, user_id: str):
    """IDを指定してベクトルストアを使用（他人のものも可）"""
    from utils.secure_vector_store_manager import secure_vs_manager
    from utils.vector_store_handler import vector_store_handler
    
    success, message, vs_info = await secure_vs_manager.use_vector_store(vs_id, user_id)
    
    if success:
        # セッションに保存
        cl.user_session.set("personal_vs_id", vs_id)
        vector_store_handler.personal_vs_id = vs_id
        
        # 使用中のベクトルストア情報を保存
        cl.user_session.set("current_vs_info", vs_info)
    
    await cl.Message(content=message, author="System").send()


async def show_vector_store_info_secure(vs_id: str, user_id: str):
    """ベクトルストア詳細情報を表示（読み取り可能なもののみ）"""
    from utils.secure_vector_store_manager import secure_vs_manager
    from utils.vector_store_handler import vector_store_handler
    
    # 読み取り権限チェック
    if not await secure_vs_manager.can_read(vs_id, user_id):
        await cl.Message(
            content=f"❌ ベクトルストア `{vs_id}` が見つからないか、アクセス権限がありません",
            author="System"
        ).send()
        return
    
    # 詳細情報取得
    vs_info = await vector_store_handler.get_vector_store_info(vs_id)
    
    if vs_info:
        # 所有権ステータスを追加
        is_owner = await secure_vs_manager.can_modify(vs_id, user_id)
        status = "🔐 所有者" if is_owner else "👁️ 読み取り専用"
        
        message = f"# 📁 ベクトルストア詳細\n\n"
        message += f"**アクセス権限**: {status}\n\n"
        message += vector_store_handler.format_vector_store_info(vs_info)
        
        if not is_owner:
            message += "\n⚠️ **注意**: このベクトルストアは他のユーザーが所有しています。\n"
            message += "読み取りは可能ですが、変更はできません。"
        
        await cl.Message(content=message, author="System").send()
    else:
        await cl.Message(
            content=f"❌ ベクトルストア情報の取得に失敗しました",
            author="System"
        ).send()


async def show_vector_store_files_secure(vs_id: str, user_id: str):
    """ベクトルストアのファイル一覧を表示（読み取り可能なもののみ）"""
    from utils.secure_vector_store_manager import secure_vs_manager
    from utils.vector_store_handler import vector_store_handler
    
    # 読み取り権限チェック
    if not await secure_vs_manager.can_read(vs_id, user_id):
        await cl.Message(
            content=f"❌ ベクトルストア `{vs_id}` が見つからないか、アクセス権限がありません",
            author="System"
        ).send()
        return
    
    # ファイル一覧取得
    files = await vector_store_handler.list_vector_store_files(vs_id)
    
    if files:
        # 所有権ステータスを追加
        is_owner = await secure_vs_manager.can_modify(vs_id, user_id)
        status = "🔐 所有者" if is_owner else "👁️ 読み取り専用"
        
        message = f"# 📄 ベクトルストアのファイル\n\n"
        message += f"🆔 **ベクトルストアID**: `{vs_id}`\n"
        message += f"**アクセス権限**: {status}\n\n"
        message += "## ファイル一覧\n"
        message += vector_store_handler.format_file_list(files)
        
        if not is_owner:
            message += "\n⚠️ このベクトルストアへのファイル追加・削除はできません（所有者のみ）"
        
        await cl.Message(content=message, author="System").send()
    else:
        await cl.Message(
            content=f"📁 ベクトルストア `{vs_id}` にファイルがありません",
            author="System"
        ).send()


async def validate_and_use_vector_stores(vs_ids_string: str):
    """
    カンマ区切りのベクトルストアIDを検証して使用設定
    
    Args:
        vs_ids_string: カンマ区切りのベクトルストアID文字列
    """
    from utils.secure_vector_store_manager import secure_vs_manager
    
    user_id = await get_current_user_id()
    vs_ids = [id.strip() for id in vs_ids_string.split(",") if id.strip()]
    
    if not vs_ids:
        return []
    
    # 各IDを検証
    validation_results = await secure_vs_manager.validate_vector_store_ids(vs_ids, user_id)
    
    valid_ids = []
    message = "## ベクトルストアID検証結果\n\n"
    
    for vs_id, result in validation_results.items():
        if result["exists"]:
            valid_ids.append(vs_id)
            message += f"✅ `{vs_id}` - {result['status']}\n"
        else:
            message += f"❌ `{vs_id}` - 無効なID\n"
    
    if valid_ids:
        message += f"\n✅ {len(valid_ids)}個のベクトルストアが使用可能です"
    else:
        message += "\n⚠️ 有効なベクトルストアIDがありません"
    
    await cl.Message(content=message, author="System").send()
    
    return valid_ids


async def handle_file_upload_to_vector_store(files: List, vs_id: Optional[str] = None):
    """
    ファイルアップロード時のベクトルストア追加処理（所有者のみ）
    
    Args:
        files: アップロードされたファイルリスト
        vs_id: ベクトルストアID（省略時は現在のpersonal_vs_id）
    """
    from utils.secure_vector_store_manager import secure_vs_manager
    from utils.vector_store_handler import vector_store_handler
    
    user_id = await get_current_user_id()
    
    # ベクトルストアIDを決定
    if not vs_id:
        vs_id = cl.user_session.get("personal_vs_id")
    
    if not vs_id:
        # 新規作成
        vs_id = await secure_vs_manager.create_personal_vector_store(user_id)
        if vs_id:
            cl.user_session.set("personal_vs_id", vs_id)
            await cl.Message(
                content=f"✅ 新しい個人用ベクトルストアを作成しました: `{vs_id}`",
                author="System"
            ).send()
        else:
            await cl.Message(
                content="❌ ベクトルストアの作成に失敗しました",
                author="System"
            ).send()
            return
    
    # 変更権限チェック
    if not await secure_vs_manager.can_modify(vs_id, user_id):
        await cl.Message(
            content=f"❌ ベクトルストア `{vs_id}` にファイルを追加する権限がありません\n（所有者のみファイルを追加できます）",
            author="System"
        ).send()
        return
    
    # ファイル処理
    successful_ids, failed_files = await vector_store_handler.process_uploaded_files(files)
    
    if successful_ids:
        # ベクトルストアに追加
        success, message = await secure_vs_manager.add_files_to_vector_store(
            vs_id, user_id, successful_ids
        )
        await cl.Message(content=message, author="System").send()
    
    if failed_files:
        await cl.Message(
            content=f"⚠️ 以下のファイルの処理に失敗しました:\n" + "\n".join(f"- {f}" for f in failed_files),
            author="System"
        ).send()


async def show_vs_help():
    """ベクトルストアコマンドのヘルプ表示"""
    message = """# 📁 ベクトルストアコマンド

## 基本コマンド
- `/vs` または `/vs list` - 自分のベクトルストア一覧
- `/vs create [名前] [カテゴリ]` - 新規作成
- `/vs use [ID]` - ベクトルストアを使用（他人のIDも可）
- `/vs delete [ID]` - 削除（所有者のみ）
- `/vs rename [ID] [新名前]` - 名前変更（所有者のみ）
- `/vs info [ID]` - 詳細情報
- `/vs files [ID]` - ファイル一覧

## 重要な仕様
1. **プライバシー保護**
   - `/vs`コマンドで表示されるのは自分が作成したもののみ
   - 他人のベクトルストアは一覧に表示されません

2. **共有機能**
   - ベクトルストアIDを知っていれば、他人のVSも使用可能
   - ただし読み取り専用（変更・削除不可）

3. **所有者権限**
   - 名前変更、削除、ファイル追加は所有者のみ
   - 他人のVSは読み取りのみ可能

## 使用例
```
# 自分のVSを作成
/vs create "技術文書" programming

# 他人から共有されたIDを使用
/vs use vs_abc123def456

# 自分のVSを削除
/vs delete vs_xyz789
```"""
    
    await cl.Message(content=message, author="System").send()
