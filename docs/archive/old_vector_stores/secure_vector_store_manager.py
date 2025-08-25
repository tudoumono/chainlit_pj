"""
セキュアなベクトルストア管理
所有者のみ表示・変更可能、IDを知っていれば他人のVSも読み取り可能
"""

from typing import Dict, List, Optional, Tuple
import os
from datetime import datetime
import json
from utils.vector_store_api_helper import (
    safe_create_vector_store,
    safe_list_vector_stores,
    safe_retrieve_vector_store,
    safe_delete_vector_store,
    safe_update_vector_store
)


class SecureVectorStoreManager:
    """セキュアなベクトルストア管理クラス"""
    
    def __init__(self, vector_store_handler):
        """
        初期化
        
        Args:
            vector_store_handler: 既存のVectorStoreHandlerインスタンス
        """
        self.handler = vector_store_handler
        self._ownership_cache = {}  # VSの所有者情報をキャッシュ
    
    async def create_personal_vector_store(self, user_id: str, name: str = None, 
                                          category: str = None) -> Optional[str]:
        """
        個人用ベクトルストアを作成（所有者情報付き）
        
        Args:
            user_id: ユーザーID
            name: ベクトルストア名
            category: カテゴリ
        
        Returns:
            作成されたベクトルストアID
        """
        try:
            if not name:
                name = f"Personal KB - {user_id} - {datetime.now().strftime('%Y%m%d_%H%M')}"
            
            # メタデータに所有者情報を含める
            metadata = {
                "owner_id": user_id,  # 所有者ID
                "created_at": datetime.now().isoformat(),
                "category": category or "general",
                "visibility": "private"  # デフォルトはプライベート
            }
            
            # ベクトルストアを作成（APIヘルパーを使用）
            vs_id = await safe_create_vector_store(
                self.handler.async_client,
                name=name,
                metadata=metadata
            )
            
            if not vs_id:
                print("❌ ベクトルストアの作成に失敗しました")
                return None
            
            # キャッシュに追加
            self._ownership_cache[vs_id] = user_id
            
            print(f"✅ 個人用ベクトルストア作成: {vs_id} (所有者: {user_id})")
            return vs_id
            
        except Exception as e:
            print(f"❌ ベクトルストア作成エラー: {e}")
            return None
    
    async def list_my_vector_stores(self, user_id: str) -> List[Dict]:
        """
        自分が所有するベクトルストアのみを取得
        
        Args:
            user_id: ユーザーID
        
        Returns:
            所有するベクトルストアのリスト
        """
        try:
            if not self.handler.async_client:
                return []
            
            # 全てのベクトルストアを取得（APIヘルパーを使用）
            all_stores = await safe_list_vector_stores(self.handler.async_client)
            
            if not all_stores:
                print("⚠️ ベクトルストアが見つかりません")
                return []
            
            my_stores = []
            for vs in all_stores:
                try:
                    # 詳細情報を取得してメタデータを確認
                    vs_detail = await safe_retrieve_vector_store(self.handler.async_client, vs.id)
                    if not vs_detail:
                        continue
                    metadata = getattr(vs_detail, 'metadata', {}) or {}
                    
                    # 所有者チェック
                    owner_id = metadata.get("owner_id")
                    if owner_id == user_id:
                        # 自分のVSのみ追加
                        my_stores.append({
                            "id": vs_detail.id,
                            "name": vs_detail.name,
                            "file_counts": vs_detail.file_counts,
                            "created_at": vs_detail.created_at,
                            "status": vs_detail.status,
                            "category": metadata.get("category", "general"),
                            "is_mine": True
                        })
                        
                        # キャッシュ更新
                        self._ownership_cache[vs_detail.id] = user_id
                    
                except Exception as e:
                    print(f"⚠️ ベクトルストア {vs.id} の取得エラー: {e}")
                    continue
            
            return my_stores
            
        except Exception as e:
            print(f"❌ ベクトルストア一覧取得エラー: {e}")
            return []
    
    async def can_modify(self, vs_id: str, user_id: str) -> bool:
        """
        ベクトルストアの変更権限をチェック
        
        Args:
            vs_id: ベクトルストアID
            user_id: ユーザーID
        
        Returns:
            変更可能かどうか
        """
        try:
            # キャッシュを確認
            if vs_id in self._ownership_cache:
                return self._ownership_cache[vs_id] == user_id
            
            # APIから取得
            vs_detail = await safe_retrieve_vector_store(self.handler.async_client, vs_id)
            if not vs_detail:
                print(f"❌ ベクトルストア {vs_id} が見つかりません")
                return False
            metadata = getattr(vs_detail, 'metadata', {}) or {}
            owner_id = metadata.get("owner_id")
            
            # キャッシュ更新
            if owner_id:
                self._ownership_cache[vs_id] = owner_id
            
            return owner_id == user_id
            
        except Exception as e:
            print(f"⚠️ 権限チェックエラー: {e}")
            return False
    
    async def can_read(self, vs_id: str, user_id: str = None) -> bool:
        """
        ベクトルストアの読み取り権限をチェック
        
        Args:
            vs_id: ベクトルストアID
            user_id: ユーザーID（オプション）
        
        Returns:
            読み取り可能かどうか
        """
        try:
            # IDを知っていれば読み取り可能（デフォルト動作）
            vs_detail = await safe_retrieve_vector_store(self.handler.async_client, vs_id)
            if not vs_detail:
                print(f"❌ ベクトルストア {vs_id} が見つかりません")
                return False
            
            if vs_detail:
                metadata = getattr(vs_detail, 'metadata', {}) or {}
                visibility = metadata.get("visibility", "private")
                
                # visibilityがpublicまたはIDを知っている場合は読み取り可能
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ ベクトルストア {vs_id} が見つかりません")
            return False
    
    async def delete_vector_store(self, vs_id: str, user_id: str) -> Tuple[bool, str]:
        """
        ベクトルストアを削除（所有者のみ）
        
        Args:
            vs_id: ベクトルストアID
            user_id: ユーザーID
        
        Returns:
            (成功/失敗, メッセージ)
        """
        try:
            # 変更権限チェック
            if not await self.can_modify(vs_id, user_id):
                return False, "❌ このベクトルストアを削除する権限がありません（所有者のみ削除可能）"
            
            # 削除実行
            success = await safe_delete_vector_store(self.handler.async_client, vs_id)
            if not success:
                return False, "❌ ベクトルストアの削除に失敗しました"
            
            # キャッシュから削除
            if vs_id in self._ownership_cache:
                del self._ownership_cache[vs_id]
            
            return True, f"✅ ベクトルストア {vs_id} を削除しました"
            
        except Exception as e:
            return False, f"❌ 削除エラー: {e}"
    
    async def rename_vector_store(self, vs_id: str, user_id: str, new_name: str) -> Tuple[bool, str]:
        """
        ベクトルストアの名前を変更（所有者のみ）
        
        Args:
            vs_id: ベクトルストアID
            user_id: ユーザーID
            new_name: 新しい名前
        
        Returns:
            (成功/失敗, メッセージ)
        """
        try:
            # 変更権限チェック
            if not await self.can_modify(vs_id, user_id):
                return False, "❌ このベクトルストアを変更する権限がありません（所有者のみ変更可能）"
            
            # 名前変更実行
            success = await safe_update_vector_store(self.handler.async_client, vs_id, name=new_name)
            if not success:
                return False, "❌ ベクトルストア名の変更に失敗しました"
            
            return True, f"✅ ベクトルストア名を「{new_name}」に変更しました"
            
        except Exception as e:
            return False, f"❌ 名前変更エラー: {e}"
    
    async def use_vector_store(self, vs_id: str, user_id: str) -> Tuple[bool, str, Dict]:
        """
        ベクトルストアを使用（IDを知っていれば他人のものも使用可能）
        
        Args:
            vs_id: ベクトルストアID
            user_id: 使用するユーザーID
        
        Returns:
            (成功/失敗, メッセージ, ベクトルストア情報)
        """
        try:
            # 読み取り権限チェック（IDを知っていれば読み取り可能）
            if not await self.can_read(vs_id, user_id):
                return False, f"❌ ベクトルストア {vs_id} が見つかりません", {}
            
            # ベクトルストア情報を取得
            vs_detail = await safe_retrieve_vector_store(self.handler.async_client, vs_id)
            if not vs_detail:
                return False, "❌ ベクトルストアが見つかりません", {}
            metadata = getattr(vs_detail, 'metadata', {}) or {}
            owner_id = metadata.get("owner_id", "unknown")
            
            # 使用権限の説明
            is_owner = owner_id == user_id
            permission_msg = "（所有者として全権限）" if is_owner else "（読み取り専用）"
            
            vs_info = {
                "id": vs_detail.id,
                "name": vs_detail.name,
                "is_owner": is_owner,
                "owner_id": owner_id if not is_owner else None,
                "file_counts": vs_detail.file_counts,
                "category": metadata.get("category", "general")
            }
            
            message = f"""✅ ベクトルストアを使用設定しました {permission_msg}

🆔 **ID**: `{vs_detail.id}`
📁 **名前**: {vs_detail.name}
📄 **ファイル数**: {vs_detail.file_counts.total if hasattr(vs_detail.file_counts, 'total') else 0}
🏷️ **カテゴリ**: {metadata.get('category', 'general')}"""
            
            if not is_owner:
                message += f"\n👤 **所有者**: 他のユーザー"
                message += f"\n⚠️ **注意**: 読み取り専用です。変更はできません。"
            
            return True, message, vs_info
            
        except Exception as e:
            return False, f"❌ ベクトルストア使用エラー: {e}", {}
    
    async def add_files_to_vector_store(self, vs_id: str, user_id: str, 
                                       file_ids: List[str]) -> Tuple[bool, str]:
        """
        ベクトルストアにファイルを追加（所有者のみ）
        
        Args:
            vs_id: ベクトルストアID
            user_id: ユーザーID
            file_ids: ファイルIDリスト
        
        Returns:
            (成功/失敗, メッセージ)
        """
        try:
            # 変更権限チェック
            if not await self.can_modify(vs_id, user_id):
                return False, "❌ このベクトルストアにファイルを追加する権限がありません（所有者のみ追加可能）"
            
            # ファイル追加実行
            for file_id in file_ids:
                success = await self.handler.add_file_to_vector_store(vs_id, file_id)
                if not success:
                    return False, f"⚠️ ファイル {file_id} の追加に失敗しました"
            
            return True, f"✅ {len(file_ids)}件のファイルを追加しました"
            
        except Exception as e:
            return False, f"❌ ファイル追加エラー: {e}"
    
    def get_ownership_status(self, vs_id: str, user_id: str) -> str:
        """
        所有権ステータスを取得
        
        Args:
            vs_id: ベクトルストアID
            user_id: ユーザーID
        
        Returns:
            ステータス文字列
        """
        if vs_id in self._ownership_cache:
            if self._ownership_cache[vs_id] == user_id:
                return "🔐 所有者"
            else:
                return "👁️ 読み取り専用"
        return "❓ 不明"
    
    async def validate_vector_store_ids(self, vs_ids: List[str], user_id: str) -> Dict[str, Dict]:
        """
        複数のベクトルストアIDを検証
        
        Args:
            vs_ids: ベクトルストアIDリスト
            user_id: ユーザーID
        
        Returns:
            各IDの状態辞書
        """
        results = {}
        
        for vs_id in vs_ids:
            vs_id = vs_id.strip()
            if not vs_id:
                continue
            
            try:
                # 読み取り可能かチェック
                can_read = await self.can_read(vs_id, user_id)
                can_modify = await self.can_modify(vs_id, user_id) if can_read else False
                
                results[vs_id] = {
                    "exists": can_read,
                    "can_read": can_read,
                    "can_modify": can_modify,
                    "is_owner": can_modify,
                    "status": self.get_ownership_status(vs_id, user_id) if can_read else "❌ 無効"
                }
                
            except Exception as e:
                results[vs_id] = {
                    "exists": False,
                    "can_read": False,
                    "can_modify": False,
                    "is_owner": False,
                    "status": "❌ エラー"
                }
        
        return results


# グローバルインスタンス（初期化は後で行う）
secure_vs_manager = None

def initialize_secure_manager(vector_store_handler):
    """
    セキュアマネージャーを初期化
    
    Args:
        vector_store_handler: VectorStoreHandlerインスタンス
    """
    global secure_vs_manager
    secure_vs_manager = SecureVectorStoreManager(vector_store_handler)
    return secure_vs_manager
