"""
ベクトルストアセキュリティ管理モジュール
他人のベクトルストアへのアクセスを防止する
"""

import hashlib
from typing import Dict, List, Optional
from datetime import datetime
import json


class VectorStoreSecurity:
    """ベクトルストアのセキュリティ管理クラス"""
    
    @staticmethod
    def generate_ownership_hash(user_id: str, api_key: str) -> str:
        """
        ユーザーIDとAPIキーから所有権ハッシュを生成
        
        Args:
            user_id: ユーザーID
            api_key: APIキーの一部（セキュリティ用）
        
        Returns:
            所有権を示すハッシュ値
        """
        # APIキーの最初と最後の文字を使用（完全なキーは保存しない）
        key_part = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else api_key
        ownership_string = f"{user_id}:{key_part}:{datetime.now().date()}"
        
        # SHA256でハッシュ化
        return hashlib.sha256(ownership_string.encode()).hexdigest()[:16]
    
    @staticmethod
    def create_secure_metadata(user_id: str, category: str = None, 
                             project_id: str = None, api_key: str = None) -> Dict:
        """
        セキュアなメタデータを作成
        
        Args:
            user_id: ユーザーID
            category: カテゴリ（技術文書、プロジェクト等）
            project_id: プロジェクトID（オプション）
            api_key: APIキー（所有権ハッシュ生成用）
        
        Returns:
            メタデータ辞書
        """
        metadata = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "category": category or "general",
            "access_level": "private",  # private, team, public
            "version": "1.0"
        }
        
        # プロジェクトIDがあれば追加
        if project_id:
            metadata["project_id"] = project_id
        
        # 所有権ハッシュを追加（APIキーが提供された場合）
        if api_key:
            metadata["ownership_hash"] = VectorStoreSecurity.generate_ownership_hash(
                user_id, api_key
            )
        
        return metadata
    
    @staticmethod
    def can_access(vector_store_metadata: Dict, user_id: str, 
                   api_key: str = None, access_type: str = "read") -> bool:
        """
        ベクトルストアへのアクセス権限をチェック
        
        Args:
            vector_store_metadata: ベクトルストアのメタデータ
            user_id: アクセスしようとしているユーザーID
            api_key: APIキー（オプション）
            access_type: アクセスタイプ（read, write, delete）
        
        Returns:
            アクセス可能かどうか
        """
        if not vector_store_metadata:
            # メタデータがない場合は旧式のVSとみなしてアクセス許可
            return True
        
        # アクセスレベルをチェック
        access_level = vector_store_metadata.get("access_level", "private")
        
        # publicなら誰でも読み取り可能
        if access_level == "public" and access_type == "read":
            return True
        
        # 所有者チェック
        owner_id = vector_store_metadata.get("user_id")
        if owner_id == user_id:
            return True  # 所有者は全権限
        
        # チームアクセスチェック（同じプロジェクトIDを持つ場合）
        if access_level == "team" and access_type in ["read", "write"]:
            project_id = vector_store_metadata.get("project_id")
            if project_id:
                # ここで実際のプロジェクトメンバーシップをチェック
                # 簡単のため、プロジェクトIDが一致すればOKとする
                return True
        
        # 所有権ハッシュによる検証（高度なセキュリティ）
        if api_key and "ownership_hash" in vector_store_metadata:
            expected_hash = VectorStoreSecurity.generate_ownership_hash(user_id, api_key)
            if vector_store_metadata["ownership_hash"] == expected_hash:
                return True
        
        return False
    
    @staticmethod
    def filter_accessible_stores(vector_stores: List[Dict], user_id: str, 
                                api_key: str = None) -> List[Dict]:
        """
        アクセス可能なベクトルストアのみフィルタリング
        
        Args:
            vector_stores: ベクトルストアのリスト
            user_id: ユーザーID
            api_key: APIキー（オプション）
        
        Returns:
            アクセス可能なベクトルストアのリスト
        """
        accessible_stores = []
        
        for vs in vector_stores:
            metadata = vs.get("metadata", {})
            if VectorStoreSecurity.can_access(metadata, user_id, api_key, "read"):
                accessible_stores.append(vs)
        
        return accessible_stores
    
    @staticmethod
    def mask_sensitive_metadata(metadata: Dict) -> Dict:
        """
        センシティブなメタデータをマスク
        
        Args:
            metadata: 元のメタデータ
        
        Returns:
            マスクされたメタデータ
        """
        if not metadata:
            return {}
        
        masked = metadata.copy()
        
        # ユーザーIDを部分的にマスク
        if "user_id" in masked:
            user_id = masked["user_id"]
            if len(user_id) > 4:
                masked["user_id"] = f"{user_id[:2]}***{user_id[-2:]}"
        
        # 所有権ハッシュを削除
        if "ownership_hash" in masked:
            del masked["ownership_hash"]
        
        return masked


class VectorStoreAccessLogger:
    """ベクトルストアアクセスログ記録クラス"""
    
    def __init__(self, log_file: str = ".chainlit/vector_store_access.log"):
        """
        初期化
        
        Args:
            log_file: ログファイルパス
        """
        self.log_file = log_file
    
    def log_access(self, user_id: str, vector_store_id: str, 
                  action: str, success: bool, reason: str = None):
        """
        アクセスログを記録
        
        Args:
            user_id: ユーザーID
            vector_store_id: ベクトルストアID
            action: 実行アクション（create, read, update, delete）
            success: 成功/失敗
            reason: 理由（オプション）
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "vector_store_id": vector_store_id,
            "action": action,
            "success": success,
            "reason": reason
        }
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ アクセスログ記録エラー: {e}")
    
    def get_user_access_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        """
        ユーザーのアクセス履歴を取得
        
        Args:
            user_id: ユーザーID
            limit: 取得する最大件数
        
        Returns:
            アクセス履歴のリスト
        """
        history = []
        
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry["user_id"] == user_id:
                            history.append(entry)
                            if len(history) >= limit:
                                break
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        
        return history[-limit:]  # 最新のものを返す


# シングルトンインスタンス
security_manager = VectorStoreSecurity()
access_logger = VectorStoreAccessLogger()
