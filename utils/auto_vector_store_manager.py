"""
自動ベクトルストア管理モジュール
層3（チャット単位）のベクトルストア自動管理
"""

import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import chainlit as cl
from utils.vector_store_api_helper import (
    safe_create_vector_store,
    safe_retrieve_vector_store,
    safe_delete_vector_store,
    get_vector_store_api
)


class AutoVectorStoreManager:
    """チャット単位のベクトルストア自動管理クラス"""
    
    def __init__(self, vector_store_handler, secure_manager):
        """
        初期化
        
        Args:
            vector_store_handler: VectorStoreHandlerインスタンス
            secure_manager: SecureVectorStoreManagerインスタンス
        """
        self.handler = vector_store_handler
        self.secure_manager = secure_manager
        self.session_vs_cache = {}  # セッションVSのキャッシュ
    
    async def get_or_create_session_vs(self, session_id: str, user_id: str) -> Optional[str]:
        """
        セッション用ベクトルストアを取得または作成
        
        Args:
            session_id: セッションID
            user_id: ユーザーID
        
        Returns:
            ベクトルストアID
        """
        try:
            # キャッシュを確認
            cache_key = f"{user_id}:{session_id}"
            if cache_key in self.session_vs_cache:
                return self.session_vs_cache[cache_key]
            
            # セッションから取得
            session_vs_id = cl.user_session.get("session_vs_id")
            if session_vs_id:
                # 存在確認
                if await self._verify_vs_exists(session_vs_id):
                    self.session_vs_cache[cache_key] = session_vs_id
                    return session_vs_id
            
            # 新規作成
            name = f"Session VS - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
            metadata = {
                "owner_id": user_id,
                "type": "session",  # セッションVSであることを明示
                "session_id": session_id[:8],  # セッションIDの一部を記録
                "created_at": datetime.now().isoformat(),
                "auto_created": "true",  # 自動作成フラグ（文字列として設定）
                "temporary": "true"  # 一時的なVSフラグ（文字列として設定）
            }
            
            # ベクトルストアを作成（APIヘルパーを使用）
            vs_id = await safe_create_vector_store(
                self.handler.async_client,
                name=name,
                metadata=metadata
            )
            
            if not vs_id:
                print("❌ セッションVSの作成に失敗しました")
                return None
            
            # キャッシュとセッションに保存
            self.session_vs_cache[cache_key] = vs_id
            cl.user_session.set("session_vs_id", vs_id)
            
            # スレッドにVS IDを紐付け（履歴削除時に一緒に削除されるように）
            thread_id = cl.user_session.get("thread_id")
            if not thread_id and hasattr(cl.context, 'session'):
                if hasattr(cl.context.session, 'thread_id'):
                    thread_id = cl.context.session.thread_id
                elif hasattr(cl.context.session, 'id'):
                    thread_id = cl.context.session.id
            
            # さらに別の方法でスレッドIDを取得
            if not thread_id:
                # セッションIDをスレッドIDとして使用（通常同じ）
                thread_id = session_id
            
            # デバッグ情報を追加
            print(f"🔍 [DEBUG] スレッドID取得: {thread_id[:8] if thread_id else 'None'}")
            print(f"🔍 [DEBUG] セッションID: {session_id[:8] if session_id else 'None'}")
            print(f"🔍 [DEBUG] ベクトルストアID: {vs_id}")
            
            if thread_id:
                # データベースに保存
                import chainlit.data as cl_data
                data_layer_instance = cl_data._data_layer
                if data_layer_instance:
                    # まずスレッドが存在するか確認
                    existing_thread = await data_layer_instance.get_thread(thread_id)
                    if not existing_thread:
                        print(f"⚠️ スレッドがまだ存在しません。作成を試みます: {thread_id[:8]}...")
                        # スレッドを作成
                        try:
                            await data_layer_instance.create_thread({
                                "id": thread_id,
                                "name": f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                                "user_id": user_id,
                                "userId": user_id,
                                "user_identifier": user_id,
                                "tags": [],
                                "metadata": {},
                                "vector_store_id": vs_id,  # 作成時にVS IDを設定
                                "createdAt": datetime.now().isoformat()
                            })
                            print(f"✅ スレッドを作成し、VSを紐付けました: {thread_id[:8]}... -> {vs_id}")
                        except Exception as e:
                            print(f"❌ スレッド作成エラー: {e}")
                    else:
                        # 既存スレッドの場合は更新
                        print(f"🔍 [DEBUG] 既存スレッド発見: {thread_id[:8]}...")
                        # update_thread_vector_storeメソッドを使用
                        if hasattr(data_layer_instance, 'update_thread_vector_store'):
                            try:
                                await data_layer_instance.update_thread_vector_store(thread_id, vs_id)
                                print(f"✅ セッションVSをスレッドに紐付け: {thread_id[:8]}... -> {vs_id}")
                            except Exception as e:
                                print(f"❌ スレッド紐付けエラー: {e}")
                                import traceback
                                print(f"🔍 [DEBUG] エラー詳細: {traceback.format_exc()}")
                        else:
                            # update_threadメソッドにフォールバック
                            try:
                                await data_layer_instance.update_thread(thread_id, vector_store_id=vs_id)
                                print(f"✅ セッションVSをスレッドに紐付け（update_thread経由）: {thread_id[:8]}... -> {vs_id}")
                            except Exception as e:
                                print(f"❌ スレッド紐付けエラー（update_thread）: {e}")
                                import traceback
                                print(f"🔍 [DEBUG] エラー詳細: {traceback.format_exc()}")
            else:
                print(f"⚠️ スレッドIDが取得できないため、VSの紐付けをスキップ")
                print(f"🔍 [DEBUG] 利用可能なセッション情報:")
                print(f"   - session_id: {session_id[:8] if session_id else 'None'}")
                print(f"   - user_id: {user_id}")
                print(f"   - cl.context exists: {hasattr(cl, 'context')}")
                if hasattr(cl, 'context'):
                    print(f"   - cl.context.session exists: {hasattr(cl.context, 'session')}")
            
            print(f"✅ セッション用ベクトルストア自動作成: {vs_id}")
            return vs_id
            
        except Exception as e:
            print(f"❌ セッションVS作成エラー: {e}")
            return None
    
    async def auto_handle_file_upload(self, files: List, user_id: str, session_id: str) -> Tuple[bool, str]:
        """
        ファイルアップロード時の自動処理（ベクトルストア中心）
        
        Args:
            files: アップロードされたファイルリスト
            user_id: ユーザーID
            session_id: セッションID
        
        Returns:
            (成功/失敗, メッセージ)
        """
        try:
            # セッションVSを取得または作成（必須）
            session_vs_id = await self.get_or_create_session_vs(session_id, user_id)
            if not session_vs_id:
                return False, "セッション用ベクトルストアの作成に失敗しました"
            
            # ファイル処理（ベクトルストア経由で統合処理）
            successful_ids = []
            failed_files = []
            
            for file in files:
                try:
                    # ベクトルストアに直接アップロード（process_uploaded_fileを使用）
                    file_id = await self.handler.process_uploaded_file(file, vector_store_id=session_vs_id)
                    if file_id:
                        successful_ids.append(file_id)
                        print(f"✅ ファイルをVSに統合アップロード: {file_id}")
                    else:
                        failed_files.append(file.name if hasattr(file, 'name') else 'unknown')
                except Exception as e:
                    print(f"❌ ファイル処理エラー: {e}")
                    failed_files.append(file.name if hasattr(file, 'name') else 'unknown')
            
            # 結果メッセージ作成
            if successful_ids:
                message = f"""✅ **ファイルを自動的にナレッジベースに追加しました**

📁 **セッションベクトルストア**: `{session_vs_id[:8]}...`
📄 **追加ファイル数**: {len(successful_ids)}個
🔄 **ステータス**: アクティブ

このチャット内でアップロードしたファイルは自動的に検索対象になります。"""
                
                if failed_files:
                    message += f"\n\n⚠️ 処理に失敗したファイル:\n"
                    message += "\n".join(f"- {f}" for f in failed_files)
                
                # uploaded_filesセッション変数は廃止
                # ファイル情報はベクトルストアから取得する
                
                return True, message
            else:
                return False, "ファイルの処理に失敗しました"
                
        except Exception as e:
            return False, f"ファイルアップロードエラー: {e}"
    
    async def _verify_vs_exists(self, vs_id: str) -> bool:
        """ベクトルストアの存在確認"""
        try:
            vs = await safe_retrieve_vector_store(self.handler.async_client, vs_id)
            return vs is not None
        except:
            return False
    
    async def cleanup_session_vs(self, session_id: str, user_id: str):
        """
        セッションVSのクリーンアップ
        
        Args:
            session_id: セッションID
            user_id: ユーザーID
        """
        try:
            cache_key = f"{user_id}:{session_id}"
            if cache_key in self.session_vs_cache:
                vs_id = self.session_vs_cache[cache_key]
                
                # ベクトルストアを削除
                success = await safe_delete_vector_store(self.handler.async_client, vs_id)
                if not success:
                    print(f"⚠️ セッションVSの削除に失敗: {vs_id}")
                
                # キャッシュから削除
                del self.session_vs_cache[cache_key]
                
                print(f"✅ セッションVSをクリーンアップ: {vs_id}")
                
        except Exception as e:
            print(f"⚠️ セッションVSクリーンアップエラー: {e}")
    
    def get_active_vector_stores_with_session(self) -> Dict[str, str]:
        """
        アクティブなベクトルストア（セッション含む）を取得
        
        Returns:
            ベクトルストアIDの辞書
        """
        stores = {}
        
        # 会社全体（層1）
        company_vs_id = os.getenv("COMPANY_VECTOR_STORE_ID", "")
        if company_vs_id:
            stores["company"] = company_vs_id
        
        # 個人用（層2）
        personal_vs_id = cl.user_session.get("personal_vs_id")
        if personal_vs_id:
            stores["personal"] = personal_vs_id
        
        # セッション用（層3）
        session_vs_id = cl.user_session.get("session_vs_id")
        if session_vs_id:
            stores["session"] = session_vs_id
        
        return stores
    
    async def get_session_vs_info(self) -> Optional[Dict]:
        """
        現在のセッションVS情報を取得
        
        Returns:
            VS情報の辞書
        """
        session_vs_id = cl.user_session.get("session_vs_id")
        if not session_vs_id:
            return None
        
        try:
            vs = await self.handler.async_client.beta.vector_stores.retrieve(session_vs_id)
            
            # ベクトルストアからファイル情報を取得
            files = await self.handler.get_vector_store_files(session_vs_id)
            uploaded_files = []
            for file in files:
                uploaded_files.append({
                    "file_id": file.get('id', 'unknown'),
                    "uploaded_at": datetime.fromtimestamp(file.get('created_at', 0)).isoformat()
                })
            
            return {
                "id": vs.id,
                "name": vs.name,
                "file_count": vs.file_counts.total if hasattr(vs.file_counts, 'total') else 0,
                "uploaded_files": uploaded_files,
                "created_at": vs.created_at
            }
        except Exception as e:
            print(f"⚠️ セッションVS情報取得エラー: {e}")
            return None
    
    def should_use_session_vs(self, message_content: str) -> bool:
        """
        メッセージ内容からセッションVSを使うべきか判定
        
        Args:
            message_content: メッセージ内容
        
        Returns:
            セッションVSを使うべきか
        """
        # セッションVSが存在し、ファイルがアップロードされている場合
        session_vs_id = cl.user_session.get("session_vs_id")
        uploaded_files = cl.user_session.get("uploaded_files", [])
        
        if session_vs_id and uploaded_files:
            # ファイル関連のキーワードをチェック
            keywords = ["ファイル", "アップロード", "文書", "資料", "添付", 
                       "file", "upload", "document", "attachment"]
            
            for keyword in keywords:
                if keyword in message_content.lower():
                    return True
            
            # デフォルトでセッションVSを優先
            return True
        
        return False


# グローバルインスタンス
auto_vs_manager = None

def initialize_auto_manager(vector_store_handler, secure_manager):
    """
    自動マネージャーを初期化
    
    Args:
        vector_store_handler: VectorStoreHandlerインスタンス
        secure_manager: SecureVectorStoreManagerインスタンス
    """
    global auto_vs_manager
    auto_vs_manager = AutoVectorStoreManager(vector_store_handler, secure_manager)
    return auto_vs_manager
