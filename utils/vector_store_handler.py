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
# Chainlitのインポートは型ヒント用のみ
# 実行時にはChainlitファイルオブジェクトを直接扱う
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
        print(f"🔧 OpenAIクライアント初期化中...")
        
        if not self.api_key or self.api_key == "your_api_key_here":
            print(f"⚠️ OpenAI APIキーが設定されていません")
            return
        
        print(f"✅ APIキー確認済み: {self.api_key[:8]}...{self.api_key[-4:]}")
        
        # プロキシ設定を確認
        proxy_enabled = os.getenv("PROXY_ENABLED", "false").lower() == "true"
        http_proxy = os.getenv("HTTP_PROXY", "") if proxy_enabled else ""
        https_proxy = os.getenv("HTTPS_PROXY", "") if proxy_enabled else ""
        
        print(f"🌐 プロキシ設定:")
        print(f"   プロキシ有効: {proxy_enabled}")
        if proxy_enabled:
            print(f"   HTTPプロキシ: {http_proxy if http_proxy else '未設定'}")
            print(f"   HTTPSプロキシ: {https_proxy if https_proxy else '未設定'}")
        
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
            
            print(f"🔄 httpxクライアントをプロキシ設定で作成")
            
            # タイムアウト設定を追加
            timeout = httpx.Timeout(60.0, connect=10.0)
            
            http_client = httpx.Client(
                proxies=proxies,
                timeout=timeout,
                verify=True  # SSL証明書の検証を有効化
            )
            async_http_client = httpx.AsyncClient(
                proxies=proxies,
                timeout=timeout,
                verify=True  # SSL証明書の検証を有効化
            )
        
        try:
            # 同期クライアント
            self.client = OpenAI(
                api_key=self.api_key,
                http_client=http_client,
                max_retries=3,  # リトライ回数を設定
                timeout=60.0     # デフォルトタイムアウト
            )
            
            # 非同期クライアント
            self.async_client = AsyncOpenAI(
                api_key=self.api_key,
                http_client=async_http_client,
                max_retries=3,  # リトライ回数を設定
                timeout=60.0     # デフォルトタイムアウト
            )
            
            print(f"✅ OpenAIクライアント初期化完了")
            
        except Exception as e:
            print(f"❌ OpenAIクライアント初期化エラー: {e}")
            print(f"   エラータイプ: {type(e).__name__}")
            self.client = None
            self.async_client = None
    
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
            
            # ファイルサイズ確認
            file_size = os.path.getsize(file_path)
            print(f"📤 ファイルアップロード開始: {file_path}")
            print(f"   ファイルサイズ: {file_size:,} bytes")
            print(f"   用途: {purpose}")
            
            # ファイルを開いてアップロード
            with open(file_path, 'rb') as file:
                print(f"📝 OpenAI APIへの送信開始...")
                response = await self.async_client.files.create(
                    file=file,
                    purpose=purpose,
                    timeout=60.0  # タイムアウトを60秒に設定
                )
            
            print(f"✅ ファイルアップロード成功: {response.id}")
            print(f"   ファイルID: {response.id}")
            print(f"   ファイル名: {response.filename}")
            print(f"   ステータス: {response.status if hasattr(response, 'status') else 'uploaded'}")
            return response.id
            
        except Exception as e:
            import traceback
            print(f"❌ ファイルアップロードエラー: {e}")
            print(f"   エラータイプ: {type(e).__name__}")
            print(f"   エラー詳細: {str(e)}")
            print(f"   スタックトレース:\n{traceback.format_exc()}")
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
            
            # ファイルサイズ確認
            file_size = len(file_bytes)
            print(f"📤 ファイルアップロード開始（バイトデータ）: {filename}")
            print(f"   ファイルサイズ: {file_size:,} bytes")
            print(f"   用途: {purpose}")
            
            # APIキーの確認
            if not self.api_key or self.api_key == "your_api_key_here":
                raise ValueError("OpenAI APIキーが設定されていません")
            
            print(f"📝 OpenAI APIへの送信開始...")
            print(f"   APIエンドポイント: https://api.openai.com/v1/files")
            
            # バイトデータからファイルを作成
            response = await self.async_client.files.create(
                file=(filename, file_bytes),
                purpose=purpose,
                timeout=60.0  # タイムアウトを60秒に設定
            )
            
            print(f"✅ ファイルアップロード成功: {response.id}")
            print(f"   ファイルID: {response.id}")
            print(f"   ファイル名: {response.filename}")
            print(f"   ステータス: {response.status if hasattr(response, 'status') else 'uploaded'}")
            return response.id
            
        except Exception as e:
            import traceback
            print(f"❌ ファイルアップロードエラー: {e}")
            print(f"   エラータイプ: {type(e).__name__}")
            print(f"   エラー詳細: {str(e)}")
            print(f"   スタックトレース:\n{traceback.format_exc()}")
            
            # 特定のエラーに対する対処法を提示
            if "Connection error" in str(e):
                print("   💡 対処法: ネットワーク接続を確認してください")
                print("   💡 プロキシ設定が必要な場合は.envファイルで設定してください")
            elif "timeout" in str(e).lower():
                print("   💡 対処法: ファイルサイズが大きすぎる可能性があります")
                print(f"   💡 現在のファイルサイズ: {file_size:,} bytes")
            elif "api_key" in str(e).lower():
                print("   💡 対処法: OpenAI APIキーを確認してください")
            
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
    
    async def process_uploaded_file(self, file) -> Optional[str]:
        """
        Chainlitでアップロードされたファイルを処理
        
        Args:
            file: ChainlitのファイルオブジェクトまたはElement
        
        Returns:
            アップロードされたファイルID
        """
        try:
            print(f"📄 ファイル処理開始: {file.name if hasattr(file, 'name') else '不明'}")
            print(f"   ファイルタイプ: {type(file).__name__}")
            print(f"   属性: {dir(file)}" if hasattr(file, '__dict__') else "")
            
            # ファイルタイプを確認
            if not self.is_supported_file(file.name):
                supported_exts = ', '.join(self.SUPPORTED_FILE_TYPES.keys())
                raise ValueError(f"サポートされていないファイル形式です。対応形式: {supported_exts}")
            
            # ファイルを読み込み
            print(f"📥 ファイルデータ読み込み中...")
            file_bytes = None
            
            # content属性がある場合（まず内容を確認）
            if hasattr(file, 'content') and file.content:
                print(f"   content属性から読み込み")
                file_bytes = file.content
                print(f"   contentサイズ: {len(file_bytes):,} bytes")
            # path属性がある場合
            elif hasattr(file, 'path') and file.path:
                print(f"   path属性から読み込み: {file.path}")
                try:
                    with open(file.path, 'rb') as f:
                        file_bytes = f.read()
                    print(f"   ファイル読み込み成功: {len(file_bytes):,} bytes")
                except Exception as e:
                    print(f"   ❌ ファイル読み込みエラー: {e}")
                    raise ValueError(f"ファイルの読み込みに失敗しました: {e}")
            # url属性がある場合（Chainlitの一時ファイルURL）
            elif hasattr(file, 'url') and file.url:
                print(f"   url属性が存在: {file.url}")
                # URLからのダウンロードは現在未実装
                raise ValueError("URLからのファイル取得は未実装です")
            else:
                # 利用可能な属性を表示
                available_attrs = []
                if hasattr(file, 'content'):
                    available_attrs.append(f"content={file.content is not None}")
                if hasattr(file, 'path'):
                    available_attrs.append(f"path={file.path}")
                if hasattr(file, 'url'):
                    available_attrs.append(f"url={file.url}")
                print(f"   利用可能な属性: {', '.join(available_attrs)}")
                raise ValueError(f"ファイルのデータを読み込めません。属性: {available_attrs}")
            
            if not file_bytes or len(file_bytes) == 0:
                print(f"   ⚠️ ファイルが空です")
                # pathを再度確認
                if hasattr(file, 'path') and file.path:
                    import os
                    if os.path.exists(file.path):
                        file_size = os.path.getsize(file.path)
                        print(f"   ファイルは存在します: {file.path} ({file_size} bytes)")
                        if file_size > 0:
                            print(f"   再度読み込みを試行...")
                            with open(file.path, 'rb') as f:
                                file_bytes = f.read()
                            if file_bytes:
                                print(f"   再読み込み成功: {len(file_bytes):,} bytes")
                
                if not file_bytes or len(file_bytes) == 0:
                    raise ValueError("ファイルが空です")
            
            print(f"   ファイルサイズ: {len(file_bytes):,} bytes")
            
            # OpenAIにアップロード
            file_id = await self.upload_file_from_bytes(
                file_bytes,
                file.name,
                purpose="assistants"
            )
            
            return file_id
            
        except Exception as e:
            import traceback
            print(f"❌ ファイル処理エラー: {e}")
            print(f"   エラータイプ: {type(e).__name__}")
            print(f"   スタックトレース:\n{traceback.format_exc()}")
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


    async def process_uploaded_files(self, files: list) -> tuple[list[str], list[str]]:
        """
        複数のファイルを処理
        
        Args:
            files: ファイルのリスト
        
        Returns:
            (成功したファイルIDのリスト, 失敗したファイル名のリスト)
        """
        successful_ids = []
        failed_files = []
        
        for file in files:
            try:
                file_id = await self.process_uploaded_file(file)
                if file_id:
                    successful_ids.append(file_id)
                else:
                    failed_files.append(file.name)
            except Exception as e:
                print(f"❌ ファイル処理失敗: {file.name} - {e}")
                failed_files.append(file.name)
        
        return successful_ids, failed_files
    
    async def add_files_to_vector_store(self, vector_store_id: str, file_ids: list[str]) -> bool:
        """
        複数のファイルをベクトルストアに追加
        
        Args:
            vector_store_id: ベクトルストアID
            file_ids: ファイルIDのリスト
        
        Returns:
            成功/失敗
        """
        try:
            for file_id in file_ids:
                success = await self.add_file_to_vector_store(vector_store_id, file_id)
                if not success:
                    print(f"⚠️ ファイル {file_id} のベクトルストアへの追加に失敗")
            return True
        except Exception as e:
            print(f"❌ ファイルのベクトルストアへの追加エラー: {e}")
            return False


# グローバルインスタンス
vector_store_handler = VectorStoreHandler()
