"""
ベクトルストア管理モジュール
Phase 7: OpenAI Embeddingsを使った個人ナレッジベース
"""

import os
import json
from typing import Dict, List, Optional, Tuple, Any
from openai import OpenAI, AsyncOpenAI
import asyncio
from datetime import datetime
import chainlit as cl
import aiofiles
import mimetypes
from pathlib import Path


class VectorStoreHandler:
    """ベクトルストア管理クラス"""
    
    # サポートされるファイル形式
    SUPPORTED_FILE_TYPES = {
        # テキスト形式
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.yaml': 'text/yaml',
        '.yml': 'text/yaml',
        
        # ドキュメント形式
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.html': 'text/html',
        '.htm': 'text/html',
        
        # コード形式
        '.py': 'text/x-python',
        '.js': 'text/javascript',
        '.java': 'text/x-java',
        '.cpp': 'text/x-c++',
        '.c': 'text/x-c',
        '.cs': 'text/x-csharp',
        '.php': 'text/x-php',
        '.rb': 'text/x-ruby',
        '.go': 'text/x-go',
        '.rs': 'text/x-rust',
        '.swift': 'text/x-swift',
        '.kt': 'text/x-kotlin',
    }
    
    def __init__(self):
        """初期化"""
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.client = None
        self.async_client = None
        self._init_clients()
        
        # ベクトルストアID管理
        self.personal_vs_id = None  # 個人用ベクトルストア
        self.session_vs_id = None   # セッション用ベクトルストア（一時的）
        self.company_vs_id = os.getenv("COMPANY_VECTOR_STORE_ID", "")  # 社内共有VS
    
    def _init_clients(self):
        """OpenAIクライアントを初期化"""
        if not self.api_key or self.api_key == "your_api_key_here":
            return
        
        # プロキシ設定を確認
        proxy_enabled = os.getenv("PROXY_ENABLED", "false").lower() == "true"
        http_proxy = os.getenv("HTTP_PROXY", "") if proxy_enabled else ""
        https_proxy = os.getenv("HTTPS_PROXY", "") if proxy_enabled else ""
        
        # httpxクライアントの設定
        http_client = None
        async_http_client = None
        
        if proxy_enabled and (http_proxy or https_proxy):
            import httpx
            proxies = {}
            if http_proxy:
                proxies["http://"] = http_proxy
            if https_proxy:
                proxies["https://"] = https_proxy
            
            http_client = httpx.Client(proxies=proxies)
            async_http_client = httpx.AsyncClient(proxies=proxies)
        
        # 同期クライアント
        self.client = OpenAI(
            api_key=self.api_key,
            http_client=http_client
        )
        
        # 非同期クライアント
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            http_client=async_http_client
        )
    
    def update_api_key(self, api_key: str):
        """APIキーを更新"""
        self.api_key = api_key
        self._init_clients()
    
    async def create_vector_store(self, name: str, file_ids: List[str] = None) -> Optional[str]:
        """
        ベクトルストアを作成
        
        Args:
            name: ベクトルストア名
            file_ids: 含めるファイルIDのリスト
        
        Returns:
            作成されたベクトルストアのID
        """
        try:
            if not self.async_client:
                raise ValueError("OpenAI client not initialized")
            
            # ベクトルストアを作成
            vector_store = await self.async_client.beta.vector_stores.create(
                name=name,
                file_ids=file_ids or []
            )
            
            print(f"✅ ベクトルストア作成: {vector_store.id}")
            return vector_store.id
            
        except Exception as e:
            print(f"❌ ベクトルストア作成エラー: {e}")
            return None
    
    async def upload_file(self, file_path: str, purpose: str = "assistants") -> Optional[str]:
        """
        ファイルをOpenAIにアップロード
        
        Args:
            file_path: アップロードするファイルパス
            purpose: ファイルの用途 ("assistants" or "fine-tune")
        
        Returns:
            アップロードされたファイルID
        """
        try:
            if not self.async_client:
                raise ValueError("OpenAI client not initialized")
            
            # ファイルを開いてアップロード
            with open(file_path, 'rb') as file:
                response = await self.async_client.files.create(
                    file=file,
                    purpose=purpose
                )
            
            print(f"✅ ファイルアップロード成功: {response.id}")
            return response.id
            
        except Exception as e:
            print(f"❌ ファイルアップロードエラー: {e}")
            return None
    
    async def upload_file_from_bytes(self, file_bytes: bytes, filename: str, purpose: str = "assistants") -> Optional[str]:
        """
        バイトデータからファイルをアップロード
        
        Args:
            file_bytes: ファイルのバイトデータ
            filename: ファイル名
            purpose: ファイルの用途
        
        Returns:
            アップロードされたファイルID
        """
        try:
            if not self.async_client:
                raise ValueError("OpenAI client not initialized")
            
            # バイトデータからファイルを作成
            response = await self.async_client.files.create(
                file=(filename, file_bytes),
                purpose=purpose
            )
            
            print(f"✅ ファイルアップロード成功: {response.id}")
            return response.id
            
        except Exception as e:
            print(f"❌ ファイルアップロードエラー: {e}")
            return None
    
    async def add_file_to_vector_store(self, vector_store_id: str, file_id: str) -> bool:
        """
        ベクトルストアにファイルを追加
        
        Args:
            vector_store_id: ベクトルストアID
            file_id: 追加するファイルID
        
        Returns:
            成功/失敗
        """
        try:
            if not self.async_client:
                raise ValueError("OpenAI client not initialized")
            
            # ファイルをベクトルストアに追加
            await self.async_client.beta.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            
            print(f"✅ ファイルをベクトルストアに追加: {file_id}")
            return True
            
        except Exception as e:
            print(f"❌ ファイル追加エラー: {e}")
            return False
    
    async def delete_vector_store(self, vector_store_id: str) -> bool:
        """
        ベクトルストアを削除
        
        Args:
            vector_store_id: 削除するベクトルストアID
        
        Returns:
            成功/失敗
        """
        try:
            if not self.async_client:
                raise ValueError("OpenAI client not initialized")
            
            await self.async_client.beta.vector_stores.delete(
                vector_store_id=vector_store_id
            )
            
            print(f"✅ ベクトルストア削除: {vector_store_id}")
            return True
            
        except Exception as e:
            print(f"❌ ベクトルストア削除エラー: {e}")
            return False
    
    async def list_vector_stores(self) -> List[Dict]:
        """
        ベクトルストア一覧を取得
        
        Returns:
            ベクトルストアのリスト
        """
        try:
            if not self.async_client:
                raise ValueError("OpenAI client not initialized")
            
            vector_stores = await self.async_client.beta.vector_stores.list()
            
            stores_list = []
            for vs in vector_stores.data:
                stores_list.append({
                    "id": vs.id,
                    "name": vs.name,
                    "file_counts": vs.file_counts,
                    "created_at": vs.created_at,
                    "status": vs.status
                })
            
            return stores_list
            
        except Exception as e:
            print(f"❌ ベクトルストア一覧取得エラー: {e}")
            return []
    
    async def get_vector_store_files(self, vector_store_id: str) -> List[Dict]:
        """
        ベクトルストア内のファイル一覧を取得
        
        Args:
            vector_store_id: ベクトルストアID
        
        Returns:
            ファイルのリスト
        """
        try:
            if not self.async_client:
                raise ValueError("OpenAI client not initialized")
            
            files = await self.async_client.beta.vector_stores.files.list(
                vector_store_id=vector_store_id
            )
            
            files_list = []
            for file in files.data:
                files_list.append({
                    "id": file.id,
                    "created_at": file.created_at,
                    "status": file.status
                })
            
            return files_list
            
        except Exception as e:
            print(f"❌ ファイル一覧取得エラー: {e}")
            return []
    
    def is_supported_file(self, filename: str) -> bool:
        """
        ファイルがサポートされているか確認
        
        Args:
            filename: ファイル名
        
        Returns:
            サポートされているか
        """
        ext = Path(filename).suffix.lower()
        return ext in self.SUPPORTED_FILE_TYPES
    
    def get_mime_type(self, filename: str) -> str:
        """
        ファイルのMIMEタイプを取得
        
        Args:
            filename: ファイル名
        
        Returns:
            MIMEタイプ
        """
        ext = Path(filename).suffix.lower()
        return self.SUPPORTED_FILE_TYPES.get(ext, 'application/octet-stream')
    
    async def process_uploaded_file(self, file: cl.File) -> Optional[str]:
        """
        Chainlitでアップロードされたファイルを処理
        
        Args:
            file: Chainlitのファイルオブジェクト
        
        Returns:
            アップロードされたファイルID
        """
        try:
            # ファイルタイプを確認
            if not self.is_supported_file(file.name):
                supported_exts = ', '.join(self.SUPPORTED_FILE_TYPES.keys())
                raise ValueError(f"サポートされていないファイル形式です。対応形式: {supported_exts}")
            
            # ファイルを読み込み
            file_bytes = file.content if hasattr(file, 'content') else open(file.path, 'rb').read()
            
            # OpenAIにアップロード
            file_id = await self.upload_file_from_bytes(
                file_bytes,
                file.name,
                purpose="assistants"
            )
            
            return file_id
            
        except Exception as e:
            print(f"❌ ファイル処理エラー: {e}")
            raise e
    
    async def create_personal_vector_store(self, user_id: str) -> Optional[str]:
        """
        個人用ベクトルストアを作成
        
        Args:
            user_id: ユーザーID
        
        Returns:
            作成されたベクトルストアID
        """
        try:
            name = f"Personal Knowledge Base - {user_id}"
            vs_id = await self.create_vector_store(name)
            
            if vs_id:
                self.personal_vs_id = vs_id
                # データベースに保存（実装は後で）
                print(f"✅ 個人用ベクトルストア作成: {vs_id}")
            
            return vs_id
            
        except Exception as e:
            print(f"❌ 個人用ベクトルストア作成エラー: {e}")
            return None
    
    async def create_session_vector_store(self, session_id: str) -> Optional[str]:
        """
        セッション用ベクトルストアを作成（一時的）
        
        Args:
            session_id: セッションID
        
        Returns:
            作成されたベクトルストアID
        """
        try:
            name = f"Session VS - {session_id[:8]}"
            vs_id = await self.create_vector_store(name)
            
            if vs_id:
                self.session_vs_id = vs_id
                print(f"✅ セッション用ベクトルストア作成: {vs_id}")
            
            return vs_id
            
        except Exception as e:
            print(f"❌ セッション用ベクトルストア作成エラー: {e}")
            return None
    
    def get_active_vector_stores(self) -> Dict[str, str]:
        """
        アクティブなベクトルストアを取得
        
        Returns:
            ベクトルストアIDの辞書
        """
        stores = {}
        
        if self.company_vs_id:
            stores["company"] = self.company_vs_id
        
        if self.personal_vs_id:
            stores["personal"] = self.personal_vs_id
        
        if self.session_vs_id:
            stores["session"] = self.session_vs_id
        
        return stores
    
    def build_file_search_tool(self, vector_store_ids: List[str] = None) -> Dict:
        """
        file_searchツールを構築
        
        Args:
            vector_store_ids: 使用するベクトルストアIDのリスト
        
        Returns:
            ツール定義
        """
        if not vector_store_ids:
            vector_store_ids = []
            
            # アクティブなベクトルストアを追加
            stores = self.get_active_vector_stores()
            vector_store_ids.extend(stores.values())
        
        if not vector_store_ids:
            return None
        
        return {
            "type": "file_search",
            "file_search": {
                "vector_store_ids": vector_store_ids
            }
        }
    
    async def cleanup_session_vector_store(self):
        """セッション用ベクトルストアをクリーンアップ"""
        if self.session_vs_id:
            try:
                await self.delete_vector_store(self.session_vs_id)
                self.session_vs_id = None
                print("✅ セッション用ベクトルストアをクリーンアップしました")
            except Exception as e:
                print(f"⚠️ セッション用ベクトルストアのクリーンアップに失敗: {e}")


# グローバルインスタンス
vector_store_handler = VectorStoreHandler()
