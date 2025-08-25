"""
ベクトルストア管理モジュール（OpenAI Responses API対応版）
Phase 7: OpenAI File Search APIを使った三層ナレッジベース管理

========================================================
重要: OpenAI Responses APIのFile Search機能を使用
========================================================

参照ドキュメント:
- F:\10_code\AI_Workspace_App_Chainlit\openai_responseAPI_reference\openai responseAPI reference (File search).md

三層のベクトルストア構造:
1. 会社全体（Company） - 共有ナレッジベース（読み取り専用）
2. 個人ユーザー（Personal） - 個人用ナレッジベース
3. チャット単位（Session） - 一時的なナレッジベース

実装方針:
- OpenAI Responses APIのvector_stores.create()を使用（betaではない）
- File Search機能による高精度な検索
- 動的なベクトルストアID管理
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
from utils.vector_store_api_helper import (
    get_vector_store_api,
    get_vector_store_files_api,
    safe_create_vector_store,
    safe_list_vector_stores,
    safe_retrieve_vector_store,
    safe_delete_vector_store,
    safe_update_vector_store
)


class VectorStoreHandler:
    """ベクトルストア管理クラス（Responses API対応）"""
    
    # サポートされるファイル形式（公式ドキュメント準拠）
    SUPPORTED_FILE_TYPES = {
        # テキスト形式
        '.c': 'text/x-c',
        '.cpp': 'text/x-c++',
        '.cs': 'text/x-csharp',
        '.css': 'text/css',
        '.go': 'text/x-golang',
        '.html': 'text/html',
        '.java': 'text/x-java',
        '.js': 'text/javascript',
        '.json': 'application/json',
        '.md': 'text/markdown',
        '.php': 'text/x-php',
        '.py': 'text/x-python',
        '.rb': 'text/x-ruby',
        '.sh': 'application/x-sh',
        '.tex': 'text/x-tex',
        '.ts': 'application/typescript',
        '.txt': 'text/plain',
        
        # ドキュメント形式
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.pdf': 'application/pdf',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    }
    
    def __init__(self):
        """初期化"""
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.client = None
        self.async_client = None
        self._init_clients()
        
        # 三層のベクトルストアID管理
        self.company_vs_id = os.getenv("COMPANY_VECTOR_STORE_ID", "")  # 1層目: 社内共有
        self.personal_vs_id = None  # 2層目: 個人用
        self.session_vs_id = None   # 3層目: セッション用（一時的）
    
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
                verify=True
            )
            async_http_client = httpx.AsyncClient(
                proxies=proxies,
                timeout=timeout,
                verify=True
            )
        
        try:
            # 同期クライアント
            self.client = OpenAI(
                api_key=self.api_key,
                http_client=http_client,
                max_retries=3,
                timeout=60.0
            )
            
            # 非同期クライアント
            self.async_client = AsyncOpenAI(
                api_key=self.api_key,
                http_client=async_http_client,
                max_retries=3,
                timeout=60.0
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
        ベクトルストアを作成（API ヘルパー使用）
        
        Args:
            name: ベクトルストア名
            file_ids: 含めるファイルIDのリスト（オプション）
        
        Returns:
            作成されたベクトルストアのID
        """
        try:
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return None
            
            print(f"📝 ベクトルストア作成開始: {name}")
            
            # APIヘルパーを使用してベクトルストアAPIを取得
            vs_api = get_vector_store_api(self.async_client)
            if not vs_api:
                print("❌ ベクトルストアAPIが利用できません")
                print("   OpenAI SDKのバージョンを確認してください")
                return None
            
            # ベクトルストアを作成
            if file_ids:
                vector_store = await vs_api.create(
                    name=name,
                    file_ids=file_ids
                )
            else:
                vector_store = await vs_api.create(
                    name=name
                )
            
            print(f"✅ ベクトルストア作成成功: {vector_store.id}")
            print(f"   名前: {vector_store.name}")
            
            # ステータス確認
            max_wait = 30
            waited = 0
            while waited < max_wait:
                vs = await safe_retrieve_vector_store(self.async_client, vector_store.id)
                if not vs:
                    print(f"⚠️ ベクトルストアの取得に失敗: {vector_store.id}")
                    break
                    
                status = getattr(vs, 'status', 'completed')  # statusがない場合はcompletedとみなす
                if status == "completed":
                    print(f"✅ ベクトルストアの準備が完了しました: {vs.id}")
                    break
                elif status == "failed":
                    print(f"❌ ベクトルストアの作成に失敗しました: {vs.id}")
                    return None
                print(f"⏳ ベクトルストアを準備中... ({status})")
                await asyncio.sleep(2)
                waited += 2
            
            return vector_store.id
                
        except Exception as e:
            print(f"❌ ベクトルストア作成エラー: {e}")
            print(f"   エラータイプ: {type(e).__name__}")
            import traceback
            print(f"   スタックトレース:\n{traceback.format_exc()}")
            return None
    
    async def upload_file(self, file_path: str, purpose: str = "assistants") -> Optional[str]:
        """
        ファイルをOpenAIにアップロード
        
        参照: openai responseAPI reference (File search).md - Upload the file to the File API
        
        Args:
            file_path: アップロードするファイルパス
            purpose: ファイルの用途 ("assistants")
        
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
                    purpose=purpose
                )
            
            print(f"✅ ファイルアップロード成功: {response.id}")
            print(f"   ファイルID: {response.id}")
            print(f"   ファイル名: {response.filename}")
            return response.id
            
        except Exception as e:
            import traceback
            print(f"❌ ファイルアップロードエラー: {e}")
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
            
            file_size = len(file_bytes)
            print(f"📤 ファイルアップロード開始（バイトデータ）: {filename}")
            print(f"   ファイルサイズ: {file_size:,} bytes")
            
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
        ベクトルストアにファイルを追加（APIヘルパー使用）
        
        Args:
            vector_store_id: ベクトルストアID
            file_id: 追加するファイルID
        
        Returns:
            成功/失敗
        """
        try:
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return False
            
            # ベクトルストアAPIを取得
            vs_api = get_vector_store_api(self.async_client)
            if not vs_api:
                print("❌ ベクトルストアAPIが利用できません")
                return False
            
            print(f"📎 ファイルをベクトルストアに追加中: {file_id}")
            
            # file_batchesが利用可能か確認
            if hasattr(vs_api, 'file_batches'):
                file_batch = await vs_api.file_batches.create(
                    vector_store_id=vector_store_id,
                    file_ids=[file_id]
                )
                
                print(f"✅ ファイルバッチ作成: {file_batch.id}")
                
                # 処理完了を待つ
                max_wait = 30
                waited = 0
                while waited < max_wait:
                    batch = await vs_api.file_batches.retrieve(
                        vector_store_id=vector_store_id,
                        batch_id=file_batch.id
                    )
                    status = getattr(batch, 'status', 'completed')
                    if status == "completed":
                        print(f"✅ ファイルのベクトル化が完了しました")
                        return True
                    elif status == "failed":
                        print(f"❌ ファイルのベクトル化に失敗しました")
                        return False
                    print(f"⏳ ファイルを処理中... ({status})")
                    await asyncio.sleep(2)
                    waited += 2
            
            # filesが利用可能な場合
            elif hasattr(vs_api, 'files'):
                result = await vs_api.files.create(
                    vector_store_id=vector_store_id,
                    file_id=file_id
                )
                print(f"✅ ファイルを追加しました: {file_id}")
                return True
            
            else:
                print("❌ ファイル追加APIが見つかりません")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ ファイル追加エラー: {e}")
            import traceback
            print(f"   スタックトレース:\n{traceback.format_exc()}")
            return False
    
    async def list_vector_stores(self) -> List[Dict]:
        """
        ベクトルストア一覧を取得（APIヘルパー使用）
        
        Returns:
            ベクトルストアのリスト
        """
        try:
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return []
            
            print(f"📁 ベクトルストア一覧を取得中...")
            
            # APIヘルパーを使用して一覧を取得
            vector_stores_data = await safe_list_vector_stores(self.async_client)
            
            stores_list = []
            for vs in vector_stores_data:
                try:
                    vs_detail = await safe_retrieve_vector_store(self.async_client, vs.id)
                    if vs_detail:
                        stores_list.append({
                            "id": vs_detail.id,
                            "name": getattr(vs_detail, 'name', 'Unnamed'),
                            "file_counts": getattr(vs_detail, 'file_counts', {}),
                            "created_at": getattr(vs_detail, 'created_at', 0),
                            "status": getattr(vs_detail, 'status', 'unknown')
                        })
                except Exception as e:
                    print(f"⚠️ ベクトルストア {vs.id} の取得に失敗しました: {e}")
                    continue
            
            return stores_list
            
        except Exception as e:
            print(f"❌ ベクトルストア一覧取得エラー: {e}")
            import traceback
            print(f"   スタックトレース:\n{traceback.format_exc()}")
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
                print("⚠️ OpenAIクライアントが初期化されていません")
                return []
            
            # Responses API形式で取得を試みる
            try:
                result = await self.async_client.vector_stores.files.list(
                    vector_store_id=vector_store_id
                )
                files_list = []
                for file in result.data:
                    files_list.append({
                        "id": file.id,
                        "created_at": file.created_at,
                        "status": "processed"
                    })
                return files_list
                
            except AttributeError:
                # Beta APIにフォールバック
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
                print("⚠️ OpenAIクライアントが初期化されていません")
                return False
            
            # Responses API形式で削除を試みる
            try:
                await self.async_client.vector_stores.delete(
                    vector_store_id=vector_store_id
                )
                print(f"✅ ベクトルストア削除: {vector_store_id}")
                return True
                
            except AttributeError:
                # Beta APIにフォールバック
                await self.async_client.beta.vector_stores.delete(
                    vector_store_id=vector_store_id
                )
                print(f"✅ ベクトルストア削除（Beta API）: {vector_store_id}")
                return True
            
        except Exception as e:
            print(f"❌ ベクトルストア削除エラー: {e}")
            return False
    
    async def rename_vector_store(self, vector_store_id: str, new_name: str) -> bool:
        """
        ベクトルストアの名前を変更
        
        Args:
            vector_store_id: ベクトルストアID
            new_name: 新しい名前
        
        Returns:
            成功/失敗
        """
        try:
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return False
            
            # Responses API形式で更新を試みる
            try:
                await self.async_client.vector_stores.update(
                    vector_store_id=vector_store_id,
                    name=new_name
                )
                print(f"✅ ベクトルストア名を変更: {vector_store_id} -> {new_name}")
                return True
                
            except AttributeError:
                # Beta APIにフォールバック
                await self.async_client.beta.vector_stores.update(
                    vector_store_id=vector_store_id,
                    name=new_name
                )
                print(f"✅ ベクトルストア名を変更（Beta API）: {vector_store_id} -> {new_name}")
                return True
            
        except Exception as e:
            print(f"❌ ベクトルストア名変更エラー: {e}")
            return False
    
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
    
    async def process_uploaded_file(self, element) -> Optional[str]:
        """
        Chainlitのファイルエレメントを処理してOpenAIにアップロード
        
        Args:
            element: Chainlitのファイルエレメント
        
        Returns:
            アップロードされたファイルID、失敗時はNone
        """
        try:
            filename = element.name
            file_ext = Path(filename).suffix.lower()
            
            # サポートされているファイル形式かチェック
            if file_ext not in self.SUPPORTED_FILE_TYPES:
                print(f"⚠️ サポートされていないファイル形式: {file_ext}")
                print(f"   サポートされる形式: {', '.join(self.SUPPORTED_FILE_TYPES.keys())}")
                return None
            
            print(f"📤 ファイル処理開始: {filename}")
            
            # ファイルの内容を取得
            file_bytes = None
            
            # pathがある場合（ローカルファイル）
            if hasattr(element, 'path') and element.path:
                print(f"   📁 ファイルパス: {element.path}")
                async with aiofiles.open(element.path, 'rb') as f:
                    file_bytes = await f.read()
            
            # contentがある場合（アップロードされたファイル）
            elif hasattr(element, 'content'):
                print(f"   📦 アップロードされたファイルを処理")
                file_bytes = element.content
                if isinstance(file_bytes, str):
                    import base64
                    file_bytes = base64.b64decode(file_bytes)
            
            # read メソッドがある場合
            elif hasattr(element, 'read'):
                print(f"   📖 ファイルを読み込み中")
                file_bytes = await element.read()
            
            else:
                print(f"❌ ファイルの内容を取得できませんでした")
                return None
            
            if not file_bytes:
                print(f"❌ ファイルの内容が空です")
                return None
            
            # ファイルサイズチェック（最大512MB）
            max_size = 512 * 1024 * 1024  # 512MB
            file_size = len(file_bytes)
            
            if file_size > max_size:
                print(f"❌ ファイルサイズが大きすぎます: {file_size / (1024 * 1024):.2f}MB (最大: 512MB)")
                return None
            
            print(f"   📏 ファイルサイズ: {file_size:,} bytes ({file_size / 1024:.2f}KB)")
            
            # OpenAIにアップロード
            file_id = await self.upload_file_from_bytes(
                file_bytes=file_bytes,
                filename=filename,
                purpose="assistants"
            )
            
            if file_id:
                print(f"✅ ファイル処理完了: {filename} -> {file_id}")
                return file_id
            else:
                print(f"❌ ファイルアップロード失敗: {filename}")
                return None
                
        except Exception as e:
            import traceback
            print(f"❌ ファイル処理エラー: {e}")
            print(f"   スタックトレース:\n{traceback.format_exc()}")
            return None
    
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
    
    async def create_personal_vector_store(self, user_id: str) -> Optional[str]:
        """
        個人用ベクトルストアを作成（2層目）
        
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
                print(f"✅ 個人用ベクトルストア作成: {vs_id}")
            
            return vs_id
            
        except Exception as e:
            print(f"❌ 個人用ベクトルストア作成エラー: {e}")
            return None
    
    async def create_session_vector_store(self, session_id: str) -> Optional[str]:
        """
        セッション用ベクトルストアを作成（3層目・一時的）
        
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
        アクティブな三層のベクトルストアを取得
        
        Returns:
            ベクトルストアIDの辞書
        """
        stores = {}
        
        # 1層目: 会社全体
        if self.company_vs_id:
            stores["company"] = self.company_vs_id
        
        # 2層目: 個人ユーザー
        if self.personal_vs_id:
            stores["personal"] = self.personal_vs_id
        
        # 3層目: チャット単位
        if self.session_vs_id:
            stores["session"] = self.session_vs_id
        
        return stores
    
    def get_active_vector_store_ids(self) -> List[str]:
        """
        アクティブなベクトルストアのIDリストを取得
        
        Returns:
            ベクトルストアIDのリスト
        """
        ids = []
        
        # 1層目: 会社全体
        if self.company_vs_id:
            ids.append(self.company_vs_id)
        
        # 2層目: 個人ユーザー
        if self.personal_vs_id:
            ids.append(self.personal_vs_id)
        
        # 3層目: チャット単位
        if self.session_vs_id:
            ids.append(self.session_vs_id)
        
        return ids
    
    def build_file_search_tool(self, vector_store_ids: List[str] = None) -> Dict:
        """
        file_searchツールを構築（Responses API準拠）
        
        参照: openai responseAPI reference (File search).md - File search tool
        
        Args:
            vector_store_ids: 使用するベクトルストアIDのリスト
        
        Returns:
            ツール定義
        """
        if not vector_store_ids:
            vector_store_ids = []
            
            # アクティブな三層のベクトルストアを追加
            stores = self.get_active_vector_stores()
            if stores:
                vector_store_ids.extend(stores.values())
        
        # Responses API形式のfile_searchツール定義
        return {
            "type": "file_search",
            "vector_store_ids": vector_store_ids if vector_store_ids else []
        }
    
    async def get_vector_store_info(self, vector_store_id: str) -> Optional[Dict]:
        """
        ベクトルストアの詳細情報を取得
        
        Args:
            vector_store_id: ベクトルストアID
        
        Returns:
            ベクトルストア情報
        """
        try:
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return None
            
            # IDの型チェック（リスト形式で渡される場合の対処）
            if isinstance(vector_store_id, list):
                print(f"⚠️ ベクトルストアIDがリスト形式で渡されました: {vector_store_id}")
                if vector_store_id:
                    vector_store_id = vector_store_id[0]  # 最初の要素を使用
                    print(f"   最初の要素を使用: {vector_store_id}")
                else:
                    print("   空のリストのため処理をスキップ")
                    return None
            
            # Responses API形式で取得を試みる
            try:
                vector_store = await self.async_client.vector_stores.retrieve(
                    vector_store_id=vector_store_id
                )
                
                return {
                    "id": vector_store.id,
                    "name": vector_store.name,
                    "created_at": vector_store.created_at,
                    "status": "completed"
                }
                
            except AttributeError:
                # Beta APIにフォールバック
                print(f"ℹ️ Responses APIが利用できないため、Beta APIにフォールバック")
                vector_store = await self.async_client.beta.vector_stores.retrieve(
                    vector_store_id=vector_store_id
                )
                
                return {
                    "id": vector_store.id,
                    "name": vector_store.name,
                    "file_counts": vector_store.file_counts,
                    "created_at": vector_store.created_at,
                    "status": vector_store.status
                }
            
        except Exception as e:
            import traceback
            print(f"❌ ベクトルストア情報取得エラー (ID: {vector_store_id}):")
            print(f"   エラーの型: {type(e).__name__}")
            print(f"   エラー詳細: {str(e)}")
            print(f"   トレースバック:\n{traceback.format_exc()}")
            return None
    
    async def list_vector_store_files(self, vector_store_id: str) -> List[Dict]:
        """
        ベクトルストア内のファイル一覧を取得（エイリアス）
        """
        return await self.get_vector_store_files(vector_store_id)
    
    def format_vector_store_info(self, vs_info: Dict) -> str:
        """
        ベクトルストア情報をフォーマット
        """
        if not vs_info:
            return "ベクトルストア情報がありません"
        
        file_count = 0
        if 'file_counts' in vs_info:
            file_count = vs_info.get('file_counts', {}).get('total', 0)
        
        return f"""
🆔 ID: `{vs_info['id']}`
📁 名前: {vs_info['name']}
📄 ファイル数: {file_count}
✅ ステータス: {vs_info.get('status', 'unknown')}
📅 作成日: {datetime.fromtimestamp(vs_info.get('created_at', 0)).strftime('%Y-%m-%d %H:%M')}
"""
    
    def format_file_list(self, files: List[Dict]) -> str:
        """
        ファイルリストをフォーマット
        """
        if not files:
            return "ファイルがありません"
        
        formatted = ""
        for i, file_info in enumerate(files, 1):
            formatted += f"{i}. 📄 ID: `{file_info['id']}`\n"
            formatted += f"   ステータス: {file_info.get('status', 'unknown')}\n\n"
        
        return formatted
    
    async def upload_file_to_vector_store(self, vector_store_id: str, file_path: str = None, file_bytes: bytes = None, filename: str = None) -> Optional[str]:
        """
        ファイルを直接ベクトルストアにアップロード（統合処理）
        
        Args:
            vector_store_id: ベクトルストアID
            file_path: ファイルパス（ファイルシステムから読み込む場合）
            file_bytes: ファイルのバイトデータ（メモリから直接アップロードする場合）
            filename: ファイル名（file_bytes使用時は必須）
        
        Returns:
            アップロードされたファイルID、失敗時はNone
        """
        try:
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return None
            
            # ベクトルストアの存在確認
            try:
                vs = await safe_retrieve_vector_store(self.async_client, vector_store_id)
                if not vs:
                    print(f"❌ ベクトルストア {vector_store_id} が見つかりません")
                    return None
            except Exception as e:
                print(f"❌ ベクトルストア確認エラー: {e}")
                return None
            
            # ファイルをアップロード
            file_id = None
            if file_path:
                file_id = await self.upload_file(file_path, purpose="assistants")
            elif file_bytes and filename:
                file_id = await self.upload_file_from_bytes(file_bytes, filename, purpose="assistants")
            else:
                print("❌ ファイルパスまたはファイルデータが必要です")
                return None
            
            if not file_id:
                return None
            
            # ベクトルストアに直接追加
            success = await self.add_file_to_vector_store(vector_store_id, file_id)
            if success:
                print(f"✅ ファイルをベクトルストアに統合アップロード: {file_id} -> {vector_store_id}")
                return file_id
            else:
                # 失敗した場合はファイルを削除（クリーンアップ）
                try:
                    await self.async_client.files.delete(file_id)
                    print(f"🗑️ 失敗したファイルをクリーンアップ: {file_id}")
                except:
                    pass
                return None
                
        except Exception as e:
            print(f"❌ 統合アップロードエラー: {e}")
            return None
    
    async def process_uploaded_file(self, element, vector_store_id: str = None) -> Optional[str]:
        """
        Chainlitのファイルエレメントを処理してベクトルストアにアップロード
        
        Args:
            element: Chainlitのファイルエレメント
            vector_store_id: ベクトルストアID（必須）
        
        Returns:
            アップロードされたファイルID、失敗時はNone
        """
        try:
            if not vector_store_id:
                print("❌ ベクトルストアIDが指定されていません")
                return None
            
            # ファイル名とパスを取得
            filename = element.name if hasattr(element, 'name') else 'unknown'
            file_path = element.path if hasattr(element, 'path') else None
            
            # サポートされているファイルか確認
            if not self.is_supported_file(filename):
                print(f"⚠️ サポートされていないファイル形式: {filename}")
                return None
            
            print(f"📤 ファイル処理開始: {filename}")
            
            # ファイルを読み込み
            if file_path and os.path.exists(file_path):
                # パスから直接アップロード
                return await self.upload_file_to_vector_store(
                    vector_store_id=vector_store_id,
                    file_path=file_path
                )
            elif hasattr(element, 'content'):
                # バイトデータからアップロード
                return await self.upload_file_to_vector_store(
                    vector_store_id=vector_store_id,
                    file_bytes=element.content,
                    filename=filename
                )
            else:
                print(f"❌ ファイルの読み込みに失敗: {filename}")
                return None
                
        except Exception as e:
            print(f"❌ ファイル処理エラー: {e}")
            return None
    
    async def cleanup_session_vector_store(self):
        """セッション用ベクトルストアをクリーンアップ（3層目）"""
        if self.session_vs_id:
            try:
                await self.delete_vector_store(self.session_vs_id)
                self.session_vs_id = None
                print("✅ セッション用ベクトルストアをクリーンアップしました")
            except Exception as e:
                print(f"⚠️ セッション用ベクトルストアのクリーンアップに失敗: {e}")


# グローバルインスタンス
vector_store_handler = VectorStoreHandler()
