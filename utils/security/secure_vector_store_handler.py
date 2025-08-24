"""
セキュア版ベクトルストアハンドラー
既存のvector_store_handler.pyに統合するためのセキュリティ強化版メソッド
"""

from typing import Dict, List, Optional
import os
from datetime import datetime


class SecureVectorStoreHandler:
    """セキュリティ機能を追加したベクトルストアハンドラー"""
    
    async def create_secure_vector_store(self, name: str, user_id: str, 
                                        category: str = None, 
                                        file_ids: List[str] = None) -> Optional[str]:
        """
        セキュアなベクトルストアを作成（メタデータ付き）
        
        Args:
            name: ベクトルストア名
            user_id: 作成ユーザーID
            category: カテゴリ
            file_ids: 含めるファイルIDのリスト
        
        Returns:
            作成されたベクトルストアのID
        """
        try:
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return None
            
            print(f"📝 セキュアなベクトルストア作成開始: {name}")
            print(f"   作成者: {user_id}")
            print(f"   カテゴリ: {category or 'general'}")
            
            # セキュアなメタデータを作成
            from utils.security.vector_store_security import security_manager
            metadata = security_manager.create_secure_metadata(
                user_id=user_id,
                category=category,
                api_key=self.api_key
            )
            
            # Beta APIを使用してベクトルストアを作成
            if file_ids:
                vector_store = await self.async_client.beta.vector_stores.create(
                    name=name,
                    file_ids=file_ids,
                    metadata=metadata  # メタデータを追加
                )
            else:
                vector_store = await self.async_client.beta.vector_stores.create(
                    name=name,
                    metadata=metadata  # メタデータを追加
                )
            
            print(f"✅ セキュアなベクトルストア作成成功: {vector_store.id}")
            
            # アクセスログを記録
            from utils.security.vector_store_security import access_logger
            access_logger.log_access(
                user_id=user_id,
                vector_store_id=vector_store.id,
                action="create",
                success=True
            )
            
            return vector_store.id
            
        except Exception as e:
            print(f"❌ ベクトルストア作成エラー: {e}")
            
            # エラーログを記録
            from utils.security.vector_store_security import access_logger
            access_logger.log_access(
                user_id=user_id,
                vector_store_id="N/A",
                action="create",
                success=False,
                reason=str(e)
            )
            
            return None
    
    async def list_user_vector_stores(self, user_id: str) -> List[Dict]:
        """
        ユーザーがアクセス可能なベクトルストア一覧を取得
        
        Args:
            user_id: ユーザーID
        
        Returns:
            アクセス可能なベクトルストアのリスト
        """
        try:
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return []
            
            # 全てのベクトルストアを取得
            all_stores = await self.async_client.beta.vector_stores.list()
            
            stores_list = []
            for vs in all_stores.data:
                try:
                    # 詳細情報を取得
                    vs_detail = await self.async_client.beta.vector_stores.retrieve(vs.id)
                    
                    # メタデータを取得
                    metadata = getattr(vs_detail, 'metadata', {}) or {}
                    
                    # アクセス権限をチェック
                    from utils.security.vector_store_security import security_manager
                    if security_manager.can_access(metadata, user_id, self.api_key, "read"):
                        # センシティブ情報をマスク
                        masked_metadata = security_manager.mask_sensitive_metadata(metadata)
                        
                        stores_list.append({
                            "id": vs_detail.id,
                            "name": vs_detail.name,
                            "file_counts": vs_detail.file_counts,
                            "created_at": vs_detail.created_at,
                            "status": vs_detail.status,
                            "metadata": masked_metadata,
                            "is_owner": metadata.get("user_id") == user_id
                        })
                    
                except Exception as e:
                    print(f"⚠️ ベクトルストア {vs.id} の取得に失敗: {e}")
                    continue
            
            # アクセスログを記録
            from utils.security.vector_store_security import access_logger
            access_logger.log_access(
                user_id=user_id,
                vector_store_id="LIST",
                action="read",
                success=True,
                reason=f"Found {len(stores_list)} accessible stores"
            )
            
            return stores_list
            
        except Exception as e:
            print(f"❌ ベクトルストア一覧取得エラー: {e}")
            return []
    
    async def delete_secure_vector_store(self, vector_store_id: str, user_id: str) -> bool:
        """
        セキュアなベクトルストア削除（所有者のみ削除可能）
        
        Args:
            vector_store_id: 削除するベクトルストアID
            user_id: 削除を要求するユーザーID
        
        Returns:
            成功/失敗
        """
        try:
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return False
            
            # ベクトルストアの詳細を取得
            vs_detail = await self.async_client.beta.vector_stores.retrieve(vector_store_id)
            metadata = getattr(vs_detail, 'metadata', {}) or {}
            
            # 削除権限をチェック
            from utils.security.vector_store_security import security_manager
            if not security_manager.can_access(metadata, user_id, self.api_key, "delete"):
                print(f"❌ 削除権限がありません: {vector_store_id}")
                
                # アクセス拒否ログを記録
                from utils.security.vector_store_security import access_logger
                access_logger.log_access(
                    user_id=user_id,
                    vector_store_id=vector_store_id,
                    action="delete",
                    success=False,
                    reason="Access denied"
                )
                
                return False
            
            # ベクトルストアを削除
            await self.async_client.beta.vector_stores.delete(vector_store_id)
            
            print(f"✅ ベクトルストア削除: {vector_store_id}")
            
            # 成功ログを記録
            from utils.security.vector_store_security import access_logger
            access_logger.log_access(
                user_id=user_id,
                vector_store_id=vector_store_id,
                action="delete",
                success=True
            )
            
            return True
            
        except Exception as e:
            print(f"❌ ベクトルストア削除エラー: {e}")
            
            # エラーログを記録
            from utils.security.vector_store_security import access_logger
            access_logger.log_access(
                user_id=user_id,
                vector_store_id=vector_store_id,
                action="delete",
                success=False,
                reason=str(e)
            )
            
            return False
    
    async def update_vector_store_metadata(self, vector_store_id: str, user_id: str,
                                          updates: Dict) -> bool:
        """
        ベクトルストアのメタデータを更新（所有者のみ）
        
        Args:
            vector_store_id: ベクトルストアID
            user_id: 更新を要求するユーザーID
            updates: 更新するメタデータ
        
        Returns:
            成功/失敗
        """
        try:
            if not self.async_client:
                return False
            
            # 現在のベクトルストアを取得
            vs_detail = await self.async_client.beta.vector_stores.retrieve(vector_store_id)
            current_metadata = getattr(vs_detail, 'metadata', {}) or {}
            
            # 更新権限をチェック
            from utils.security.vector_store_security import security_manager
            if not security_manager.can_access(current_metadata, user_id, self.api_key, "write"):
                print(f"❌ 更新権限がありません: {vector_store_id}")
                
                # アクセス拒否ログ
                from utils.security.vector_store_security import access_logger
                access_logger.log_access(
                    user_id=user_id,
                    vector_store_id=vector_store_id,
                    action="update",
                    success=False,
                    reason="Access denied"
                )
                
                return False
            
            # メタデータを更新
            new_metadata = {**current_metadata, **updates}
            new_metadata["updated_at"] = datetime.now().isoformat()
            new_metadata["updated_by"] = user_id
            
            # ベクトルストアを更新
            await self.async_client.beta.vector_stores.update(
                vector_store_id=vector_store_id,
                metadata=new_metadata
            )
            
            print(f"✅ メタデータ更新成功: {vector_store_id}")
            
            # 成功ログ
            from utils.security.vector_store_security import access_logger
            access_logger.log_access(
                user_id=user_id,
                vector_store_id=vector_store_id,
                action="update",
                success=True,
                reason=f"Updated: {list(updates.keys())}"
            )
            
            return True
            
        except Exception as e:
            print(f"❌ メタデータ更新エラー: {e}")
            return False
    
    async def share_vector_store(self, vector_store_id: str, owner_id: str,
                                access_level: str = "team") -> bool:
        """
        ベクトルストアの共有設定を変更
        
        Args:
            vector_store_id: ベクトルストアID
            owner_id: 所有者ID
            access_level: アクセスレベル（private, team, public）
        
        Returns:
            成功/失敗
        """
        return await self.update_vector_store_metadata(
            vector_store_id=vector_store_id,
            user_id=owner_id,
            updates={"access_level": access_level}
        )
