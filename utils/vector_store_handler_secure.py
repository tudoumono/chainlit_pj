"""
セキュア版ベクトルストアハンドラー
所有者管理機能を統合した完全版
"""

import os
import json
from typing import Dict, List, Optional, Tuple, Any
from openai import OpenAI, AsyncOpenAI
import asyncio
from datetime import datetime
import aiofiles
import mimetypes
from pathlib import Path
from utils.vector_store_handler import VectorStoreHandler


class SecureVectorStoreHandler(VectorStoreHandler):
    """セキュリティ機能を追加したベクトルストアハンドラー"""
    
    def __init__(self):
        """初期化"""
        super().__init__()
        # 所有権情報をローカルに保存（バックアップ用）
        self.ownership_file = ".chainlit/vector_store_ownership.json"
        self._ensure_ownership_file()
    
    def _ensure_ownership_file(self):
        """所有権ファイルを確保"""
        os.makedirs(os.path.dirname(self.ownership_file), exist_ok=True)
        if not os.path.exists(self.ownership_file):
            with open(self.ownership_file, "w") as f:
                json.dump({}, f)
    
    def _save_ownership(self, vs_id: str, user_id: str):
        """所有権情報をローカルに保存"""
        try:
            with open(self.ownership_file, "r") as f:
                ownership = json.load(f)
            ownership[vs_id] = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat()
            }
            with open(self.ownership_file, "w") as f:
                json.dump(ownership, f, indent=2)
        except Exception as e:
            print(f"⚠️ 所有権情報の保存エラー: {e}")
    
    def _get_ownership(self, vs_id: str) -> Optional[str]:
        """所有権情報を取得"""
        try:
            with open(self.ownership_file, "r") as f:
                ownership = json.load(f)
            return ownership.get(vs_id, {}).get("user_id")
        except Exception:
            return None
    
    async def create_vector_store_secure(self, name: str, user_id: str, 
                                        file_ids: List[str] = None) -> Optional[str]:
        """
        セキュアなベクトルストアを作成（所有者情報付き）
        
        Args:
            name: ベクトルストア名
            user_id: 作成ユーザーID
            file_ids: 含めるファイルIDのリスト
        
        Returns:
            作成されたベクトルストアのID
        """
        try:
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return None
            
            print(f"📝 ベクトルストア作成開始: {name}")
            print(f"   所有者: {user_id}")
            
            # メタデータに所有者情報を含める
            metadata = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "access_level": "private"  # デフォルトはプライベート
            }
            
            # ベクトルストアを作成
            try:
                if file_ids:
                    vector_store = await self.async_client.beta.vector_stores.create(
                        name=name,
                        file_ids=file_ids,
                        metadata=metadata
                    )
                else:
                    vector_store = await self.async_client.beta.vector_stores.create(
                        name=name,
                        metadata=metadata
                    )
                
                print(f"✅ ベクトルストア作成成功: {vector_store.id}")
                
                # 所有権情報をローカルにも保存（バックアップ）
                self._save_ownership(vector_store.id, user_id)
                
                return vector_store.id
                
            except Exception as e:
                print(f"❌ ベクトルストア作成エラー: {e}")
                return None
                
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
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return []
            
            # 全てのベクトルストアを取得
            try:
                vector_stores = await self.async_client.beta.vector_stores.list()
                
                my_stores = []
                for vs in vector_stores.data:
                    try:
                        # 詳細情報を取得
                        vs_detail = await self.async_client.beta.vector_stores.retrieve(vs.id)
                        
                        # メタデータから所有者を確認
                        metadata = getattr(vs_detail, 'metadata', {}) or {}
                        owner_id = metadata.get("user_id")
                        
                        # ローカルの所有権情報も確認（フォールバック）
                        if not owner_id:
                            owner_id = self._get_ownership(vs.id)
                        
                        # 自分のもののみ追加
                        if owner_id == user_id:
                            file_count = 0
                            if hasattr(vs_detail, 'file_counts'):
                                file_count = vs_detail.file_counts.total if hasattr(vs_detail.file_counts, 'total') else 0
                            
                            my_stores.append({
                                "id": vs_detail.id,
                                "name": vs_detail.name,
                                "file_counts": {"total": file_count},
                                "created_at": vs_detail.created_at,
                                "status": getattr(vs_detail, 'status', 'completed'),
                                "metadata": metadata
                            })
                    
                    except Exception as e:
                        print(f"⚠️ ベクトルストア {vs.id} の取得エラー: {e}")
                        continue
                
                return my_stores
                
            except Exception as e:
                print(f"❌ ベクトルストア一覧取得エラー: {e}")
                return []
            
        except Exception as e:
            print(f"❌ ベクトルストア一覧取得エラー: {e}")
            return []
    
    async def can_modify(self, vector_store_id: str, user_id: str) -> bool:
        """
        ベクトルストアの変更権限を確認
        
        Args:
            vector_store_id: ベクトルストアID
            user_id: ユーザーID
        
        Returns:
            変更可能かどうか
        """
        try:
            if not self.async_client:
                return False
            
            # ベクトルストアの詳細を取得
            vs_detail = await self.async_client.beta.vector_stores.retrieve(vector_store_id)
            metadata = getattr(vs_detail, 'metadata', {}) or {}
            
            # メタデータから所有者を確認
            owner_id = metadata.get("user_id")
            
            # ローカルの所有権情報も確認
            if not owner_id:
                owner_id = self._get_ownership(vector_store_id)
            
            # 所有者のみ変更可能
            return owner_id == user_id
            
        except Exception as e:
            print(f"⚠️ 権限確認エラー: {e}")
            return False
    
    async def delete_vector_store_secure(self, vector_store_id: str, user_id: str) -> bool:
        """
        セキュアなベクトルストア削除（所有者のみ）
        
        Args:
            vector_store_id: 削除するベクトルストアID
            user_id: 削除を要求するユーザーID
        
        Returns:
            成功/失敗
        """
        try:
            # 変更権限を確認
            if not await self.can_modify(vector_store_id, user_id):
                print(f"❌ 削除権限がありません: {vector_store_id}")
                return False
            
            # 削除実行
            success = await self.delete_vector_store(vector_store_id)
            
            if success:
                # ローカルの所有権情報も削除
                try:
                    with open(self.ownership_file, "r") as f:
                        ownership = json.load(f)
                    if vector_store_id in ownership:
                        del ownership[vector_store_id]
                        with open(self.ownership_file, "w") as f:
                            json.dump(ownership, f, indent=2)
                except Exception:
                    pass
            
            return success
            
        except Exception as e:
            print(f"❌ ベクトルストア削除エラー: {e}")
            return False
    
    async def rename_vector_store_secure(self, vector_store_id: str, new_name: str, 
                                        user_id: str) -> bool:
        """
        セキュアなベクトルストア名変更（所有者のみ）
        
        Args:
            vector_store_id: ベクトルストアID
            new_name: 新しい名前
            user_id: 変更を要求するユーザーID
        
        Returns:
            成功/失敗
        """
        try:
            # 変更権限を確認
            if not await self.can_modify(vector_store_id, user_id):
                print(f"❌ 変更権限がありません: {vector_store_id}")
                return False
            
            # 名前変更実行
            return await self.rename_vector_store(vector_store_id, new_name)
            
        except Exception as e:
            print(f"❌ ベクトルストア名変更エラー: {e}")
            return False
    
    async def get_vector_store_info_secure(self, vector_store_id: str, 
                                          user_id: str) -> Optional[Dict]:
        """
        ベクトルストア情報を取得（IDを知っていれば誰でも取得可能）
        
        Args:
            vector_store_id: ベクトルストアID
            user_id: 要求するユーザーID
        
        Returns:
            ベクトルストア情報（所有者情報はマスク）
        """
        try:
            vs_info = await self.get_vector_store_info(vector_store_id)
            
            if vs_info:
                # メタデータから所有者情報を取得
                metadata = vs_info.get("metadata", {})
                owner_id = metadata.get("user_id")
                
                # 所有者でない場合は所有者情報をマスク
                if owner_id and owner_id != user_id:
                    # 所有者IDを部分的にマスク
                    if len(owner_id) > 4:
                        masked_id = f"{owner_id[:2]}***{owner_id[-2:]}"
                    else:
                        masked_id = "***"
                    
                    vs_info["is_owner"] = False
                    vs_info["owner_id_masked"] = masked_id
                else:
                    vs_info["is_owner"] = True
                    vs_info["owner_id"] = owner_id
                
                return vs_info
            
            return None
            
        except Exception as e:
            print(f"❌ ベクトルストア情報取得エラー: {e}")
            return None
    
    def can_use_vector_store(self, vector_store_id: str) -> bool:
        """
        ベクトルストアが使用可能かを確認（IDを知っていれば使用可能）
        
        Args:
            vector_store_id: ベクトルストアID
        
        Returns:
            使用可能かどうか
        """
        # IDを知っていれば誰でも使用可能
        # ただし、実際に存在するかは実行時に確認される
        return bool(vector_store_id and vector_store_id.startswith("vs_"))
    
    def build_file_search_tool_with_shared(self, 
                                          owned_ids: List[str] = None,
                                          shared_ids: List[str] = None) -> Dict:
        """
        file_searchツールを構築（所有+共有ベクトルストア）
        
        Args:
            owned_ids: 所有するベクトルストアID
            shared_ids: 共有されたベクトルストアID（他人のIDなど）
        
        Returns:
            ツール定義
        """
        vector_store_ids = []
        
        # 所有するベクトルストアを追加
        if owned_ids:
            vector_store_ids.extend(owned_ids)
        
        # 共有されたベクトルストア（他人のID）を追加
        if shared_ids:
            # IDの形式を簡単にチェック
            valid_shared_ids = [
                vs_id for vs_id in shared_ids 
                if vs_id and vs_id.startswith("vs_")
            ]
            vector_store_ids.extend(valid_shared_ids)
        
        # 重複を削除
        vector_store_ids = list(set(vector_store_ids))
        
        # file_searchツール定義
        if vector_store_ids:
            return {
                "type": "file_search",
                "vector_store_ids": vector_store_ids
            }
        else:
            return None


# グローバルインスタンス（シングルトン）
secure_vector_store_handler = SecureVectorStoreHandler()
