"""
ベクトルストア同期管理モジュール
ローカルストレージとOpenAI APIの同期を管理
"""

import os
import json
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path


class VectorStoreSync:
    """ベクトルストアの同期管理クラス"""
    
    def __init__(self, vector_store_handler=None):
        """
        初期化
        
        Args:
            vector_store_handler: VectorStoreHandlerインスタンス
        """
        self.vector_store_handler = vector_store_handler
        self.local_store_dir = ".chainlit/vector_stores"
        self.sync_status_file = ".chainlit/vector_store_sync.json"
        self.tools_config_file = ".chainlit/tools_config.json"
        
    async def sync_all(self) -> Dict[str, any]:
        """
        すべてのベクトルストアを同期
        
        Returns:
            同期結果のサマリー
        """
        print("🔄 ベクトルストア同期開始...")
        
        result = {
            "synced": [],
            "removed_from_local": [],
            "removed_from_config": [],
            "errors": []
        }
        
        # 1. OpenAI APIから実際のベクトルストア一覧を取得
        api_stores = await self._get_api_vector_stores()
        api_store_ids = {store["id"] for store in api_stores}
        
        # 2. ローカルファイルの一覧を取得
        local_stores = self._get_local_vector_stores()
        local_store_ids = {store["id"] for store in local_stores}
        
        # 3. tools_config.jsonのIDを取得
        config_ids = self._get_config_vector_store_ids()
        
        # 4. 同期処理
        # 4.1 ローカルにあるがAPIにないものを削除
        for local_id in local_store_ids:
            if local_id not in api_store_ids:
                self._remove_local_store(local_id)
                result["removed_from_local"].append(local_id)
                print(f"🗑️ ローカルストア削除: {local_id}")
        
        # 4.2 設定にあるがAPIにないものを削除
        for config_id in config_ids:
            if config_id not in api_store_ids:
                result["removed_from_config"].append(config_id)
                print(f"🗑️ 設定から削除: {config_id}")
        
        # 4.3 APIにあるがローカルにないものを作成
        for api_store in api_stores:
            if api_store["id"] not in local_store_ids:
                self._create_local_store(api_store)
                result["synced"].append(api_store["id"])
                print(f"✅ ローカルストア作成: {api_store['id']}")
        
        # 5. tools_config.jsonを更新（APIに存在するIDのみ）
        valid_config_ids = [id for id in config_ids if id in api_store_ids]
        self._update_config_vector_store_ids(valid_config_ids)
        
        # 6. 同期ステータスを保存
        self._save_sync_status({
            "last_sync": datetime.now().isoformat(),
            "api_count": len(api_stores),
            "local_count": len(local_stores),
            "synced_ids": list(api_store_ids)
        })
        
        print(f"✅ 同期完了: API={len(api_stores)}, ローカル={len(result['synced'])}, 削除={len(result['removed_from_local'])}")
        return result
    
    async def _get_api_vector_stores(self) -> List[Dict]:
        """OpenAI APIからベクトルストア一覧を取得"""
        if not self.vector_store_handler:
            return []
        
        try:
            stores = await self.vector_store_handler.list_vector_stores()
            return stores
        except Exception as e:
            print(f"❌ API取得エラー: {e}")
            return []
    
    def _get_local_vector_stores(self) -> List[Dict]:
        """ローカルのベクトルストア一覧を取得"""
        stores = []
        
        if not os.path.exists(self.local_store_dir):
            return stores
        
        for file_path in Path(self.local_store_dir).glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    store_data = json.load(f)
                    stores.append(store_data)
            except Exception as e:
                print(f"⚠️ ローカルファイル読み込みエラー: {file_path} - {e}")
        
        return stores
    
    def _get_config_vector_store_ids(self) -> List[str]:
        """tools_config.jsonからベクトルストアIDを取得"""
        if not os.path.exists(self.tools_config_file):
            return []
        
        try:
            with open(self.tools_config_file, "r") as f:
                config = json.load(f)
                return config.get("tools", {}).get("file_search", {}).get("vector_store_ids", [])
        except Exception as e:
            print(f"⚠️ 設定ファイル読み込みエラー: {e}")
            return []
    
    def _update_config_vector_store_ids(self, valid_ids: List[str]) -> None:
        """tools_config.jsonのベクトルストアIDを更新"""
        if not os.path.exists(self.tools_config_file):
            return
        
        try:
            with open(self.tools_config_file, "r") as f:
                config = json.load(f)
            
            if "tools" in config and "file_search" in config["tools"]:
                config["tools"]["file_search"]["vector_store_ids"] = valid_ids
                
                with open(self.tools_config_file, "w") as f:
                    json.dump(config, f, indent=2)
                    
        except Exception as e:
            print(f"❌ 設定ファイル更新エラー: {e}")
    
    def _create_local_store(self, store_data: Dict) -> None:
        """ローカルにベクトルストア情報を作成"""
        os.makedirs(self.local_store_dir, exist_ok=True)
        
        file_path = os.path.join(self.local_store_dir, f"{store_data['id']}.json")
        local_data = {
            "id": store_data["id"],
            "name": store_data.get("name", "Unknown"),
            "file_ids": [],  # APIから取得できれば更新
            "created_at": datetime.now().isoformat(),
            "synced_from_api": True
        }
        
        with open(file_path, "w") as f:
            json.dump(local_data, f, indent=2)
    
    def _remove_local_store(self, store_id: str) -> None:
        """ローカルのベクトルストア情報を削除"""
        file_path = os.path.join(self.local_store_dir, f"{store_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
    
    def _save_sync_status(self, status: Dict) -> None:
        """同期ステータスを保存"""
        os.makedirs(os.path.dirname(self.sync_status_file), exist_ok=True)
        
        with open(self.sync_status_file, "w") as f:
            json.dump(status, f, indent=2)
    
    def get_last_sync_status(self) -> Optional[Dict]:
        """最後の同期ステータスを取得"""
        if not os.path.exists(self.sync_status_file):
            return None
        
        try:
            with open(self.sync_status_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 同期ステータス読み込みエラー: {e}")
            return None
    
    async def validate_and_clean(self) -> Dict[str, List[str]]:
        """
        検証とクリーンアップ
        存在しないベクトルストアの参照を削除
        
        Returns:
            クリーンアップ結果
        """
        result = {
            "removed_local": [],
            "removed_config": [],
            "valid": []
        }
        
        # APIから有効なIDを取得
        api_stores = await self._get_api_vector_stores()
        valid_ids = {store["id"] for store in api_stores}
        
        # ローカルファイルをチェック
        local_stores = self._get_local_vector_stores()
        for store in local_stores:
            if store["id"] not in valid_ids:
                self._remove_local_store(store["id"])
                result["removed_local"].append(store["id"])
            else:
                result["valid"].append(store["id"])
        
        # 設定ファイルをチェック
        config_ids = self._get_config_vector_store_ids()
        valid_config_ids = [id for id in config_ids if id in valid_ids]
        removed_config_ids = [id for id in config_ids if id not in valid_ids]
        
        if removed_config_ids:
            self._update_config_vector_store_ids(valid_config_ids)
            result["removed_config"] = removed_config_ids
        
        return result


# シングルトンインスタンス
_sync_instance = None

def get_sync_manager(vector_store_handler=None) -> VectorStoreSync:
    """
    同期マネージャーのシングルトンインスタンスを取得
    
    Args:
        vector_store_handler: VectorStoreHandlerインスタンス
    
    Returns:
        VectorStoreSyncインスタンス
    """
    global _sync_instance
    if _sync_instance is None:
        _sync_instance = VectorStoreSync(vector_store_handler)
    elif vector_store_handler:
        _sync_instance.vector_store_handler = vector_store_handler
    return _sync_instance
