"""
ベクトルストア管理ハンドラー
app.pyから分離されたベクトルストア管理機能
"""

import chainlit as cl
import os
from typing import Dict, List, Optional
from utils.ui_helper import ChainlitHelper as ui
from utils.error_handler import ErrorHandler as error_handler
from utils.logger import app_logger
from utils.vector_store_handler import vector_store_handler
from utils.vector_store_sync import get_sync_manager


class VectorStoreHandler:
    """ベクトルストア管理を統括するクラス"""
    
    async def sync_vector_stores(self):
        """ベクトルストアの同期"""
        try:
            loading_msg = await ui.show_loading_message("ベクトルストアを同期中...")
            
            sync_manager = get_sync_manager(vector_store_handler)
            result = await sync_manager.sync_all()
            
            message = "🔄 **ベクトルストア同期完了**\n\n"
            
            if result.get("synced"):
                message += "✅ **同期されたベクトルストア:**\n"
                for vs_id in result["synced"]:
                    message += f"  - `{vs_id}`\n"
                message += "\n"
            
            if result.get("removed_from_local"):
                message += "🗑️ **ローカルから削除:**\n"
                for vs_id in result["removed_from_local"]:
                    message += f"  - `{vs_id}`\n"
                message += "\n"
            
            if result.get("removed_from_config"):
                message += "📝 **設定から削除:**\n"
                for vs_id in result["removed_from_config"]:
                    message += f"  - `{vs_id}`\n"
                message += "\n"
            
            await ui.update_loading_message(loading_msg, message)
            
        except Exception as e:
            await error_handler.handle_vector_store_error(e, "ベクトルストア同期")
    
    async def show_vector_stores(self):
        """ベクトルストア一覧を表示"""
        try:
            vector_stores = await vector_store_handler.list_vector_stores()
            
            if not vector_stores:
                await ui.send_info_message(
                    "ベクトルストアがありません。\n"
                    "ファイルをアップロードするか、手動で作成してください。"
                )
                return
            
            message = "# 🗂️ ベクトルストア一覧\n\n"
            
            personal_vs_id = ui.get_session("personal_vs_id") or vector_store_handler.personal_vs_id
            
            for vs in vector_stores:
                is_active = vs.get("id") == personal_vs_id
                status = " ✅ [アクティブ]" if is_active else ""
                
                message += f"## {vs.get('name', 'Unknown')}{status}\n"
                message += f"🆔 ID: `{vs.get('id', 'N/A')}`\n"
                message += f"📊 ファイル数: {vs.get('file_counts', {}).get('total', 0)}\n"
                message += f"📅 作成日: {vs.get('created_at', 'Unknown')}\n\n"
            
            message += "💡 **使い方**:\n"
            message += "- ファイルをアップロードで自動追加\n"
            message += "- `/vs create` で新規作成\n"
            message += "- `/vs info <ID>` で詳細表示\n"
            
            await ui.send_system_message(message)
            
        except Exception as e:
            await error_handler.handle_vector_store_error(e, "ベクトルストア一覧表示")
    
    async def create_vector_store(self, name: str = "Personal Knowledge Base"):
        """ベクトルストアを作成"""
        try:
            loading_msg = await ui.show_loading_message(f"ベクトルストア '{name}' を作成中...")
            
            vs_id = await vector_store_handler.create_vector_store(name)
            
            if vs_id:
                # セッションに設定
                ui.set_session("personal_vs_id", vs_id)
                vector_store_handler.personal_vs_id = vs_id
                
                await ui.update_loading_message(
                    loading_msg,
                    f"✅ ベクトルストアを作成しました\n\n"
                    f"🆔 ID: `{vs_id}`\n"
                    f"📁 名前: {name}\n\n"
                    f"ファイルをアップロードして知識ベースを構築できます。"
                )
                
                app_logger.info("ベクトルストア作成成功", vs_id=vs_id, name=name)
            else:
                await ui.update_loading_message(
                    loading_msg,
                    f"❌ ベクトルストア '{name}' の作成に失敗しました"
                )
                
        except Exception as e:
            await error_handler.handle_vector_store_error(e, "ベクトルストア作成")
    
    async def show_vector_store_info(self, vs_id: str):
        """ベクトルストア情報を表示"""
        try:
            vs_info = await vector_store_handler.get_vector_store_info(vs_id)
            
            if vs_info:
                message = "# 📊 ベクトルストア情報\n\n"
                message += ui.format_vector_store_info(vs_info)
                await ui.send_system_message(message)
            else:
                await ui.send_error_message(f"ベクトルストア `{vs_id}` が見つかりません。")
                
        except Exception as e:
            await error_handler.handle_vector_store_error(e, "ベクトルストア情報表示", vs_id)
    
    async def delete_vector_store(self, vs_id: str):
        """ベクトルストアを削除"""
        try:
            # 確認ダイアログ
            confirmation = await ui.ask_confirmation(
                f"ベクトルストア `{vs_id}` を削除しますか？\n"
                f"この操作は元に戻せません。"
            )
            
            if not confirmation:
                await ui.send_info_message("削除をキャンセルしました。")
                return
            
            loading_msg = await ui.show_loading_message("ベクトルストアを削除中...")
            
            success = await vector_store_handler.delete_vector_store(vs_id)
            
            if success:
                # アクティブなベクトルストアが削除された場合はセッションから削除
                if ui.get_session("personal_vs_id") == vs_id:
                    ui.set_session("personal_vs_id", None)
                    vector_store_handler.personal_vs_id = None
                
                await ui.update_loading_message(
                    loading_msg,
                    f"✅ ベクトルストア `{vs_id}` を削除しました。"
                )
                
                app_logger.info("ベクトルストア削除成功", vs_id=vs_id)
            else:
                await ui.update_loading_message(
                    loading_msg,
                    f"❌ ベクトルストア `{vs_id}` の削除に失敗しました。"
                )
                
        except Exception as e:
            await error_handler.handle_vector_store_error(e, "ベクトルストア削除", vs_id)
    
    async def show_vector_store_files(self, vs_id: str):
        """ベクトルストア内のファイル一覧を表示"""
        try:
            files = await vector_store_handler.list_vector_store_files(vs_id)
            
            message = "# 📁 ベクトルストアファイル\n\n"
            message += f"🆔 ベクトルストアID: `{vs_id}`\n\n"
            
            if files:
                message += vector_store_handler.format_file_list(files)
            else:
                message += "📁 ベクトルストアにファイルがありません。"
            
            await ui.send_system_message(message)
            
        except Exception as e:
            await error_handler.handle_vector_store_error(e, "ベクトルストアファイル表示", vs_id)
    
    async def rename_vector_store(self, vs_id: str, new_name: str):
        """ベクトルストア名を変更"""
        try:
            # 存在確認
            vs_info = await vector_store_handler.get_vector_store_info(vs_id)
            
            if vs_info:
                loading_msg = await ui.show_loading_message("ベクトルストア名を変更中...")
                
                success = await vector_store_handler.rename_vector_store(vs_id, new_name)
                
                if success:
                    await ui.update_loading_message(
                        loading_msg,
                        f"✅ ベクトルストアの名前を変更しました\n\n"
                        f"🆔 ID: `{vs_id}`\n"
                        f"📁 新しい名前: {new_name}"
                    )
                    
                    app_logger.info("ベクトルストア名変更成功", vs_id=vs_id, new_name=new_name)
                else:
                    await ui.update_loading_message(
                        loading_msg,
                        f"❌ ベクトルストア `{vs_id}` の名前変更に失敗しました。"
                    )
            else:
                await ui.send_error_message(f"ベクトルストア `{vs_id}` が見つかりません。")
                
        except Exception as e:
            await error_handler.handle_vector_store_error(e, "ベクトルストア名変更", vs_id)
    
    async def set_personal_vector_store(self, vs_id: str):
        """パーソナルベクトルストアを設定"""
        try:
            # 存在確認
            vs_info = await vector_store_handler.get_vector_store_info(vs_id)
            
            if vs_info:
                ui.set_session("personal_vs_id", vs_id)
                vector_store_handler.personal_vs_id = vs_id
                
                message = f"✅ ベクトルストアを設定しました\n\n"
                message += ui.format_vector_store_info(vs_info)
                
                await ui.send_success_message(message)
                
                app_logger.info("パーソナルベクトルストア設定", vs_id=vs_id)
            else:
                await ui.send_error_message(f"ベクトルストア `{vs_id}` が見つかりません。")
                
        except Exception as e:
            await error_handler.handle_vector_store_error(e, "パーソナルベクトルストア設定", vs_id)
    
    async def process_file_upload(self, files: List):
        """ファイルアップロード処理"""
        try:
            if not files:
                return
            
            # パーソナルベクトルストアを取得または作成
            personal_vs_id = ui.get_session("personal_vs_id") or vector_store_handler.personal_vs_id
            
            if not personal_vs_id:
                loading_msg = await ui.show_loading_message("パーソナルベクトルストアを作成中...")
                
                personal_vs_id = await vector_store_handler.create_vector_store("Personal Knowledge Base")
                
                if personal_vs_id:
                    ui.set_session("personal_vs_id", personal_vs_id)
                    vector_store_handler.personal_vs_id = personal_vs_id
                    await ui.update_loading_message(loading_msg, "ベクトルストア作成完了")
                else:
                    await ui.update_loading_message(
                        loading_msg, 
                        "❌ ベクトルストアの作成に失敗しました"
                    )
                    return
            
            # ファイルを処理してベクトルストアに追加
            loading_msg = await ui.show_loading_message("ファイルを処理中...")
            
            successful_ids, failed_files = await vector_store_handler.process_uploaded_files(files)
            
            if successful_ids:
                success = await vector_store_handler.add_files_to_vector_store(
                    personal_vs_id, successful_ids
                )
                
                if success:
                    message = f"✅ {len(successful_ids)}個のファイルを追加しました\n\n"
                    message += f"📁 ベクトルストアID: `{personal_vs_id}`\n\n"
                    
                    if failed_files:
                        message += f"⚠️ {len(failed_files)}個のファイルの処理に失敗しました"
                    
                    await ui.update_loading_message(loading_msg, message)
                    
                    app_logger.info(
                        "ファイルアップロード成功", 
                        vs_id=personal_vs_id, 
                        success_count=len(successful_ids),
                        failed_count=len(failed_files)
                    )
                else:
                    await ui.update_loading_message(
                        loading_msg,
                        "❌ ファイルのベクトルストア追加に失敗しました"
                    )
            else:
                await ui.update_loading_message(
                    loading_msg,
                    "❌ 処理可能なファイルがありませんでした"
                )
                
        except Exception as e:
            await error_handler.handle_file_error(e, "ファイルアップロード処理")
    
    async def show_session_info(self):
        """セッションのベクトルストア情報を表示"""
        try:
            vs_ids = ui.get_session("vector_store_ids", {})
            
            message = "# 🔍 セッションベクトルストア情報\n\n"
            
            if vs_ids:
                for store_type, store_id in vs_ids.items():
                    if store_id:
                        message += f"**{store_type.title()}**: `{store_id}`\n"
                    else:
                        message += f"**{store_type.title()}**: 未設定\n"
            else:
                message += "ベクトルストア情報が設定されていません。\n"
            
            # セッションベクトルストアのファイル情報
            session_vs_id = ui.get_session("session_vs_id")
            if session_vs_id:
                try:
                    files = await vector_store_handler.get_vector_store_files(session_vs_id)
                    if files:
                        message += f"\n## 📁 セッションファイル ({len(files)}件)\n"
                        for file_info in files[:5]:  # 最初の5件のみ表示
                            message += f"- {file_info.get('name', 'Unknown')}\n"
                        if len(files) > 5:
                            message += f"- ... 他 {len(files) - 5} 件\n"
                except Exception:
                    message += f"\n⚠️ セッションベクトルストア `{session_vs_id}` へのアクセスに失敗\n"
            
            await ui.send_system_message(message)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "セッション情報表示")
    
    async def cleanup_session_resources(self):
        """セッション終了時のリソースクリーンアップ"""
        try:
            vector_stores = ui.get_session("vector_stores", {})
            
            if vector_stores:
                app_logger.info("セッションベクトルストアをクリーンアップ中")
                
                for store_type, store_id in vector_stores.items():
                    try:
                        success = await vector_store_handler.delete_vector_store(store_id)
                        if success:
                            app_logger.info(f"セッションベクトルストア削除成功: {store_type}={store_id}")
                        else:
                            app_logger.warning(f"セッションベクトルストア削除失敗: {store_type}={store_id}")
                    except Exception as e:
                        app_logger.error(f"セッションベクトルストア削除エラー: {store_type}={store_id}", error=str(e))
                
                # セッションから削除
                ui.set_session("vector_stores", {})
                
        except Exception as e:
            app_logger.error("セッションクリーンアップエラー", error=str(e))


# グローバルインスタンス
vector_store_commands = VectorStoreHandler()