"""
統合されたベクトルストアコマンドハンドラー
フェーズ2（自動化）とフェーズ3（GUI）を統合
"""

import chainlit as cl
from typing import Optional, List
from datetime import datetime


async def handle_integrated_vs_commands(message_content: str):
    """
    統合されたベクトルストアコマンドの処理
    
    Args:
        message_content: メッセージ内容
    """
    from utils.vector_store_handler import vector_store_handler
    from utils.secure_vector_store_manager import secure_vs_manager, initialize_secure_manager
    from utils.auto_vector_store_manager import auto_vs_manager, initialize_auto_manager
    from utils.vector_store_gui_manager import gui_manager, initialize_gui_manager
    from utils.secure_vs_commands import get_current_user_id
    
    # マネージャーを初期化（まだの場合）
    _secure_vs_manager = secure_vs_manager
    _auto_vs_manager = auto_vs_manager
    _gui_manager = gui_manager
    
    if _secure_vs_manager is None:
        _secure_vs_manager = initialize_secure_manager(vector_store_handler)
    if _auto_vs_manager is None:
        _auto_vs_manager = initialize_auto_manager(vector_store_handler, _secure_vs_manager)
    if _gui_manager is None:
        _gui_manager = initialize_gui_manager(_secure_vs_manager)
    
    # 現在のユーザーIDを取得
    user_id = await get_current_user_id()
    
    # コマンドをパース
    parts = message_content.split()
    
    # /vs gui - GUI管理パネル表示
    if len(parts) >= 2 and parts[1] == "gui":
        await _gui_manager.show_management_panel(user_id)
    
    # /vs stats - カテゴリ別統計
    elif len(parts) >= 2 and parts[1] == "stats":
        await _gui_manager.show_category_stats(user_id)
    
    # /vs session - セッションVS情報
    elif len(parts) >= 2 and parts[1] == "session":
        await show_session_vs_info()
    
    # /vs auto - 自動化設定
    elif len(parts) >= 2 and parts[1] == "auto":
        await show_auto_settings()
    
    # 既存のセキュアコマンド
    else:
        from utils.secure_vs_commands import handle_vs_command_secure
        await handle_vs_command_secure(message_content)


async def handle_integrated_file_upload(elements: List):
    """
    統合されたファイルアップロード処理（自動化対応）
    
    Args:
        elements: Chainlitのエレメントリスト（ファイルを含む）
    """
    from utils.auto_vector_store_manager import auto_vs_manager, initialize_auto_manager
    from utils.secure_vs_commands import get_current_user_id
    from utils.vector_store_handler import vector_store_handler
    from utils.secure_vector_store_manager import secure_vs_manager, initialize_secure_manager
    
    # マネージャーを初期化（まだの場合）
    _secure_vs_manager = secure_vs_manager
    _auto_vs_manager = auto_vs_manager
    
    if _secure_vs_manager is None:
        _secure_vs_manager = initialize_secure_manager(vector_store_handler)
    if _auto_vs_manager is None:
        _auto_vs_manager = initialize_auto_manager(vector_store_handler, _secure_vs_manager)
    
    # ファイルを抽出
    files = [element for element in elements if element.type == "file"]
    
    if not files:
        await cl.Message(
            content="ℹ️ ファイルが見つかりませんでした。",
            author="System"
        ).send()
        return
    
    # ユーザーIDとセッションIDを取得
    user_id = await get_current_user_id()
    session_id = cl.user_session.get("session_id", cl.context.session.thread_id if hasattr(cl.context.session, 'thread_id') else "unknown")
    
    # 自動処理を実行
    success, message = await _auto_vs_manager.auto_handle_file_upload(
        files, user_id, session_id
    )
    
    await cl.Message(content=message, author="System").send()
    
    # GUI更新の提案
    if success:
        await cl.Message(
            content="💡 **ヒント**: `/vs gui` でナレッジベース管理パネルを開けます",
            author="System"
        ).send()


async def show_session_vs_info():
    """セッションベクトルストア情報を表示"""
    from utils.auto_vector_store_manager import auto_vs_manager, initialize_auto_manager
    from utils.vector_store_handler import vector_store_handler
    from utils.secure_vector_store_manager import secure_vs_manager, initialize_secure_manager
    
    # マネージャーを初期化（まだの場合）
    _auto_vs_manager = auto_vs_manager
    if _auto_vs_manager is None:
        _secure_vs_manager = secure_vs_manager
        if _secure_vs_manager is None:
            _secure_vs_manager = initialize_secure_manager(vector_store_handler)
        _auto_vs_manager = initialize_auto_manager(vector_store_handler, _secure_vs_manager)
    
    info = await _auto_vs_manager.get_session_vs_info()
    
    if info:
        message = f"""# 🔄 セッションベクトルストア

## 現在のセッション情報
- **ID**: `{info['id']}`
- **名前**: {info['name']}
- **ファイル数**: {info['file_count']}個
- **作成時刻**: {datetime.fromtimestamp(info['created_at']).strftime('%Y-%m-%d %H:%M')}

## アップロードされたファイル
"""
        
        if info['uploaded_files']:
            for i, file_info in enumerate(info['uploaded_files'], 1):
                uploaded_time = datetime.fromisoformat(file_info['uploaded_at']).strftime('%H:%M')
                message += f"{i}. `{file_info['file_id']}` (アップロード: {uploaded_time})\n"
        else:
            message += "*ファイルがアップロードされていません*\n"
        
        message += """

### 📝 説明
セッションベクトルストアは、このチャット内でアップロードしたファイルを
自動的に管理する一時的なナレッジベースです。

- チャット終了時に自動削除されます
- ファイルアップロード時に自動作成されます
- 個人用VSとは独立して管理されます"""
        
    else:
        message = """# 🔄 セッションベクトルストア

現在、セッションベクトルストアは作成されていません。

ファイルをアップロードすると自動的に作成されます。"""
    
    await cl.Message(content=message, author="System").send()


async def show_auto_settings():
    """自動化設定を表示"""
    from utils.auto_vector_store_manager import auto_vs_manager, initialize_auto_manager
    from utils.vector_store_handler import vector_store_handler
    from utils.secure_vector_store_manager import secure_vs_manager, initialize_secure_manager
    
    # マネージャーを初期化（まだの場合）
    _auto_vs_manager = auto_vs_manager
    if _auto_vs_manager is None:
        _secure_vs_manager = secure_vs_manager
        if _secure_vs_manager is None:
            _secure_vs_manager = initialize_secure_manager(vector_store_handler)
        _auto_vs_manager = initialize_auto_manager(vector_store_handler, _secure_vs_manager)
    
    message = """# ⚙️ ベクトルストア自動化設定

## 現在の自動化機能

### ✅ 有効な機能
1. **ファイルアップロード時の自動VS作成**
   - ファイルをアップロードすると自動的にセッションVSを作成
   - セッションVS内のファイルは自動的に検索対象

2. **三層構造の自動管理**
   - **層1（会社）**: 環境変数で設定（読み取り専用）
   - **層2（個人）**: GUI/コマンドで管理
   - **層3（セッション）**: 自動作成・自動削除

3. **カテゴリ自動分類**
   - GUI作成時にカテゴリを選択
   - カテゴリ別の整理・統計表示

### 🔧 設定可能な項目
- セッションVSの自動削除: チャット終了時
- デフォルトカテゴリ: "general"
- ファイルサイズ制限: 512MB

### 📊 現在の状態"""
    
    # 各層の状態を取得
    stores = _auto_vs_manager.get_active_vector_stores_with_session()
    
    message += "\n\n**アクティブなベクトルストア:**\n"
    if stores.get("company"):
        message += f"- 層1（会社）: `{stores['company']}`\n"
    if stores.get("personal"):
        message += f"- 層2（個人）: `{stores['personal']}`\n"
    if stores.get("session"):
        message += f"- 層3（セッション）: `{stores['session']}`\n"
    
    if not stores:
        message += "*アクティブなベクトルストアがありません*\n"
    
    await cl.Message(content=message, author="System").send()


async def handle_gui_action(action_response):
    """
    GUI関連のアクション処理
    
    Args:
        action_response: アクションレスポンス
    """
    from utils.vector_store_gui_manager import gui_manager, initialize_gui_manager
    from utils.secure_vs_commands import get_current_user_id
    from utils.secure_vector_store_manager import secure_vs_manager, initialize_secure_manager
    from utils.vector_store_handler import vector_store_handler
    
    # マネージャーを初期化（まだの場合）
    _gui_manager = gui_manager
    if _gui_manager is None:
        _secure_vs_manager = secure_vs_manager
        if _secure_vs_manager is None:
            _secure_vs_manager = initialize_secure_manager(vector_store_handler)
        _gui_manager = initialize_gui_manager(_secure_vs_manager)
    
    action = action_response.get("payload", {}).get("action")
    user_id = await get_current_user_id()
    
    if action == "create":
        await _gui_manager.create_with_category_dialog(user_id)
    
    elif action == "manage":
        await _gui_manager.manage_category_dialog(user_id)
    
    elif action == "export":
        await _gui_manager.export_vs_list(user_id)
    
    elif action == "bulk":
        await cl.Message(
            content="📤 ファイルをドラッグ&ドロップしてアップロードしてください。\n自動的に適切なベクトルストアに追加されます。",
            author="System"
        ).send()


# app.pyへの統合用ヘルパー関数
async def on_chat_start_integrated():
    """チャット開始時の統合初期化"""
    from utils.vector_store_handler import vector_store_handler
    from utils.secure_vector_store_manager import initialize_secure_manager
    from utils.auto_vector_store_manager import initialize_auto_manager
    from utils.vector_store_gui_manager import initialize_gui_manager
    
    # 各マネージャーを初期化
    secure_manager = initialize_secure_manager(vector_store_handler)
    auto_manager = initialize_auto_manager(vector_store_handler, secure_manager)
    gui_manager = initialize_gui_manager(secure_manager)
    
    # セッションに保存
    cl.user_session.set("vs_managers", {
        "secure": secure_manager,
        "auto": auto_manager,
        "gui": gui_manager
    })
    
    # 初期メッセージ
    await cl.Message(
        content="""🚀 **ベクトルストア管理システム起動**

利用可能なコマンド:
- `/vs` - 自分のベクトルストア一覧
- `/vs gui` - 📊 管理パネル（カテゴリ管理）
- `/vs session` - 🔄 セッション情報
- `/vs stats` - 📈 統計情報
- `/vs auto` - ⚙️ 自動化設定

ファイルをアップロードすると自動的にナレッジベースに追加されます。""",
        author="System"
    ).send()


# セッションVSのクリーンアップは履歴削除時にdata_layer.pyが自動的に行うため不要


# エクスポート
__all__ = [
    'handle_integrated_vs_commands',
    'handle_integrated_file_upload',
    'handle_gui_action',
    'on_chat_start_integrated'
]
