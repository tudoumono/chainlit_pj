"""
ベクトルストア管理モジュール - Responses API対応版
最新のOpenAI File Search API対応
参考: https://platform.openai.com/docs/guides/tools-file-search
"""

import os
import json
from typing import Dict, List, Optional, Tuple, Any
from openai import OpenAI, AsyncOpenAI
import asyncio
from datetime import datetime
import aiofiles
from pathlib import Path


class VectorStoreHandlerResponses:
    """ベクトルストア管理クラス（Responses API対応版）"""
    
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
        
        # ローカル管理（フォールバック用）
        self._local_vector_stores = {}
        self._load_local_stores()
    
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
            self.client = None
            self.async_client = None
    
    def _load_local_stores(self):
        """ローカルベクトルストア情報を読み込み"""
        vs_dir = ".chainlit/vector_stores"
        if not os.path.exists(vs_dir):
            os.makedirs(vs_dir, exist_ok=True)
        
        vs_file = f"{vs_dir}/local_stores.json"
        if os.path.exists(vs_file):
            try:
                with open(vs_file, "r") as f:
                    self._local_vector_stores = json.load(f)
            except:
                self._local_vector_stores = {}
    
    def _save_local_stores(self):
        """ローカルベクトルストア情報を保存"""
        vs_dir = ".chainlit/vector_stores"
        os.makedirs(vs_dir, exist_ok=True)
        
        vs_file = f"{vs_dir}/local_stores.json"
        with open(vs_file, "w") as f:
            json.dump(self._local_vector_stores, f, indent=2)
    
    def update_api_key(self, api_key: str):
        """APIキーを更新"""
        self.api_key = api_key
        self._init_clients()
    
    async def create_vector_store(self, name: str, file_ids: List[str] = None) -> Optional[str]:
        """
        ベクトルストアを作成（Responses API用）
        
        Args:
            name: ベクトルストア名
            file_ids: 含めるファイルIDのリスト
        
        Returns:
            作成されたベクトルストアのID
        """
        try:
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return None
            
            print(f"📝 ベクトルストア作成開始: {name}")
            
            # ベクトルストアを作成
            vector_store = await self.async_client.beta.vector_stores.create(
                name=name
            )
            
            print(f"✅ ベクトルストア作成成功: {vector_store.id}")
            print(f"   名前: {vector_store.name}")
            print(f"   ステータス: {getattr(vector_store, 'status', 'created')}")
            
            # ファイルがある場合は追加
            if file_ids:
                for file_id in file_ids:
                    await self.add_file_to_vector_store(vector_store.id, file_id)
            
            # ローカルにも保存
            self._local_vector_stores[vector_store.id] = {
                'id': vector_store.id,
                'name': name,
                'file_ids': file_ids or [],
                'status': 'completed',
                'created_at': datetime.now().isoformat()
            }
            self._save_local_stores()
            
            return vector_store.id
            
        except AttributeError as e:
            # APIが利用できない場合のフォールバック
            print(f"⚠️ ベクトルストアAPIエラー: {e}")
            import uuid
            dummy_id = f"vs_{uuid.uuid4().hex[:16]}"
            
            self._local_vector_stores[dummy_id] = {
                'id': dummy_id,
                'name': name,
                'file_ids': file_ids or [],
                'status': 'completed',
                'created_at': datetime.now().isoformat()
            }
            self._save_local_stores()
            
            print(f"⚠️ ローカルベクトルストアを作成: {dummy_id}")
            return dummy_id
            
        except Exception as e:
            print(f"❌ ベクトルストア作成エラー: {e}")
            return None
    
    async def upload_file(self, file_path: str, purpose: str = "assistants") -> Optional[str]:
        """
        ファイルをOpenAIにアップロード
        
        Args:
            file_path: アップロードするファイルパス
            purpose: ファイルの用途 ("assistants")
        
        Returns:
            アップロードされたファイルID
        """
        try:
            if not self.async_client:
                raise ValueError("OpenAI client not initialized")
            
            file_size = os.path.getsize(file_path)
            print(f"📤 ファイルアップロード開始: {file_path}")
            print(f"   ファイルサイズ: {file_size:,} bytes")
            
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
            
            file_size = len(file_bytes)
            print(f"📤 ファイルアップロード開始: {filename}")
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
        ベクトルストアにファイルを追加
        
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
            
            # ベクトルストアにファイルを追加
            vs_file = await self.async_client.beta.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            
            print(f"✅ ファイルをベクトルストアに追加: {file_id}")
            print(f"   ステータス: {getattr(vs_file, 'status', 'added')}")
            
            # 処理完了を待つ（最大30秒）
            max_wait = 30
            waited = 0
            while waited < max_wait:
                try:
                    vs_file = await self.async_client.beta.vector_stores.files.retrieve(
                        vector_store_id=vector_store_id,
                        file_id=file_id
                    )
                    if getattr(vs_file, 'status', '') == 'completed':
                        print(f"✅ ファイルのベクトル化が完了しました")
                        break
                    elif getattr(vs_file, 'status', '') == 'failed':
                        print(f"❌ ファイルのベクトル化に失敗しました")
                        return False
                except:
                    # ステータス確認に失敗してもファイルは追加されている
                    break
                
                await asyncio.sleep(2)
                waited += 2
            
            # ローカルにも記録
            if vector_store_id in self._local_vector_stores:
                if file_id not in self._local_vector_stores[vector_store_id].get('file_ids', []):
                    self._local_vector_stores[vector_store_id]['file_ids'].append(file_id)
                    self._save_local_stores()
            
            return True
            
        except Exception as e:
            print(f"❌ ファイル追加エラー: {e}")
            # ローカルにだけ記録
            if vector_store_id in self._local_vector_stores:
                if file_id not in self._local_vector_stores[vector_store_id].get('file_ids', []):
                    self._local_vector_stores[vector_store_id]['file_ids'].append(file_id)
                    self._save_local_stores()
            return False
    
    async def list_vector_stores(self) -> List[Dict]:
        """
        ベクトルストア一覧を取得
        
        Returns:
            ベクトルストアのリスト
        """
        try:
            if not self.async_client:
                print("⚠️ OpenAIクライアントが初期化されていません")
                return list(self._local_vector_stores.values())
            
            # APIからベクトルストア一覧を取得
            vector_stores = await self.async_client.beta.vector_stores.list()
            
            stores_list = []
            for vs in vector_stores.data:
                stores_list.append({
                    "id": vs.id,
                    "name": vs.name,
                    "file_counts": getattr(vs, 'file_counts', {"total": 0}),
                    "created_at": getattr(vs, 'created_at', datetime.now().isoformat()),
                    "status": getattr(vs, 'status', 'unknown')
                })
            
            return stores_list
            
        except Exception as e:
            print(f"⚠️ API一覧取得エラー、ローカル一覧を返します: {e}")
            return list(self._local_vector_stores.values())
    
    async def delete_vector_store(self, vector_store_id: str) -> bool:
        """
        ベクトルストアを削除
        
        Args:
            vector_store_id: 削除するベクトルストアID
        
        Returns:
            成功/失敗
        """
        try:
            if self.async_client:
                # APIから削除
                await self.async_client.beta.vector_stores.delete(
                    vector_store_id=vector_store_id
                )
                print(f"✅ ベクトルストア削除: {vector_store_id}")
            
            # ローカルからも削除
            if vector_store_id in self._local_vector_stores:
                del self._local_vector_stores[vector_store_id]
                self._save_local_stores()
            
            return True
            
        except Exception as e:
            print(f"⚠️ API削除エラー、ローカルのみ削除: {e}")
            # ローカルからだけ削除
            if vector_store_id in self._local_vector_stores:
                del self._local_vector_stores[vector_store_id]
                self._save_local_stores()
            return True
    
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
            if self.async_client:
                # APIで名前を更新
                await self.async_client.beta.vector_stores.update(
                    vector_store_id=vector_store_id,
                    name=new_name
                )
                print(f"✅ ベクトルストア名を変更: {new_name}")
            
            # ローカルでも更新
            if vector_store_id in self._local_vector_stores:
                self._local_vector_stores[vector_store_id]['name'] = new_name
                self._save_local_stores()
            
            return True
            
        except Exception as e:
            print(f"⚠️ API更新エラー、ローカルのみ更新: {e}")
            # ローカルだけ更新
            if vector_store_id in self._local_vector_stores:
                self._local_vector_stores[vector_store_id]['name'] = new_name
                self._save_local_stores()
            return True
    
    async def get_vector_store_info(self, vector_store_id: str) -> Optional[Dict]:
        """
        ベクトルストア情報を取得
        
        Args:
            vector_store_id: ベクトルストアID
        
        Returns:
            ベクトルストア情報
        """
        try:
            if self.async_client:
                # APIから取得
                vector_store = await self.async_client.beta.vector_stores.retrieve(
                    vector_store_id=vector_store_id
                )
                
                return {
                    "id": vector_store.id,
                    "name": vector_store.name,
                    "file_counts": getattr(vector_store, 'file_counts', {"total": 0}),
                    "created_at": getattr(vector_store, 'created_at', datetime.now().isoformat()),
                    "status": getattr(vector_store, 'status', 'unknown')
                }
        except:
            pass
        
        # ローカルから取得
        if vector_store_id in self._local_vector_stores:
            return self._local_vector_stores[vector_store_id]
        
        return None
    
    async def get_vector_store_files(self, vector_store_id: str) -> List[Dict]:
        """
        ベクトルストア内のファイル一覧を取得
        
        Args:
            vector_store_id: ベクトルストアID
        
        Returns:
            ファイルのリスト
        """
        try:
            if self.async_client:
                # APIから取得
                files = await self.async_client.beta.vector_stores.files.list(
                    vector_store_id=vector_store_id
                )
                
                files_list = []
                for file in files.data:
                    files_list.append({
                        "id": file.id,
                        "created_at": getattr(file, 'created_at', datetime.now().isoformat()),
                        "status": getattr(file, 'status', 'processed')
                    })
                
                return files_list
        except:
            pass
        
        # ローカルから取得
        if vector_store_id in self._local_vector_stores:
            files_list = []
            for file_id in self._local_vector_stores[vector_store_id].get('file_ids', []):
                files_list.append({
                    "id": file_id,
                    "created_at": datetime.now().isoformat(),
                    "status": "processed"
                })
            return files_list
        
        return []
    
    def build_file_search_tool(self, vector_store_ids: List[str] = None) -> Dict:
        """
        file_searchツール定義を構築（Responses API用）
        
        Args:
            vector_store_ids: 使用するベクトルストアIDのリスト
        
        Returns:
            ツール定義
        """
        if not vector_store_ids:
            vector_store_ids = []
            
            # アクティブなベクトルストアを追加
            stores = self.get_active_vector_stores()
            if stores:
                vector_store_ids.extend(stores.values())
        
        # Responses API用のfile_searchツール定義
        return {
            "type": "file_search"
        }
    
    def build_tool_resources(self, vector_store_ids: List[str] = None) -> Dict:
        """
        tool_resourcesを構築（Responses API用）
        
        Args:
            vector_store_ids: 使用するベクトルストアIDのリスト
        
        Returns:
            tool_resources定義
        """
        if not vector_store_ids:
            vector_store_ids = []
            
            # アクティブなベクトルストアを追加
            stores = self.get_active_vector_stores()
            if stores:
                vector_store_ids.extend(stores.values())
        
        if not vector_store_ids:
            return {}
        
        return {
            "file_search": {
                "vector_store_ids": vector_store_ids
            }
        }
    
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
            アップロードされたファイルID
        """
        try:
            filename = element.name
            file_ext = Path(filename).suffix.lower()
            
            # サポートされているファイル形式かチェック
            if file_ext not in self.SUPPORTED_FILE_TYPES:
                print(f"⚠️ サポートされていないファイル形式: {file_ext}")
                return None
            
            print(f"📤 ファイル処理開始: {filename}")
            
            # ファイルの内容を取得
            file_bytes = None
            
            # pathがある場合
            if hasattr(element, 'path') and element.path:
                async with aiofiles.open(element.path, 'rb') as f:
                    file_bytes = await f.read()
            
            # contentがある場合
            elif hasattr(element, 'content'):
                file_bytes = element.content
                if isinstance(file_bytes, str):
                    import base64
                    file_bytes = base64.b64decode(file_bytes)
            
            if not file_bytes:
                print(f"❌ ファイルの内容が空です")
                return None
            
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
            print(f"❌ ファイル処理エラー: {e}")
            return None
    
    async def create_personal_vector_store(self, user_id: str) -> Optional[str]:
        """
        個人用ベクトルストアを作成
        
        Args:
            user_id: ユーザーID
        
        Returns:
            作成されたベクトルストアID
        """
        name = f"Personal VS for {user_id}"
        vs_id = await self.create_vector_store(name)
        
        if vs_id:
            self.personal_vs_id = vs_id
            print(f"✅ 個人用ベクトルストア作成: {vs_id}")
        
        return vs_id
    
    async def create_session_vector_store(self, session_id: str) -> Optional[str]:
        """
        セッション用ベクトルストアを作成（一時的）
        
        Args:
            session_id: セッションID
        
        Returns:
            作成されたベクトルストアID
        """
        name = f"Session VS - {session_id[:8]}"
        vs_id = await self.create_vector_store(name)
        
        if vs_id:
            self.session_vs_id = vs_id
            print(f"✅ セッション用ベクトルストア作成: {vs_id}")
        
        return vs_id
    
    async def cleanup_session_vector_store(self):
        """セッション用ベクトルストアをクリーンアップ"""
        if self.session_vs_id:
            try:
                await self.delete_vector_store(self.session_vs_id)
                self.session_vs_id = None
                print("✅ セッション用ベクトルストアをクリーンアップしました")
            except Exception as e:
                print(f"⚠️ セッション用ベクトルストアのクリーンアップに失敗: {e}")
    
    def format_vector_store_info(self, vs_info: Dict) -> str:
        """ベクトルストア情報をフォーマット"""
        if not vs_info:
            return "ベクトルストア情報がありません"
        
        return f"""
🆔 ID: `{vs_info['id']}`
📁 名前: {vs_info['name']}
📄 ファイル数: {vs_info.get('file_counts', {}).get('total', len(vs_info.get('file_ids', [])))}
✅ ステータス: {vs_info.get('status', 'unknown')}
📅 作成日: {vs_info.get('created_at', 'unknown')}
"""
    
    def format_file_list(self, files: List[Dict]) -> str:
        """ファイルリストをフォーマット"""
        if not files:
            return "ファイルがありません"
        
        formatted = ""
        for i, file_info in enumerate(files, 1):
            formatted += f"{i}. 📄 ID: `{file_info['id']}`\n"
            formatted += f"   ステータス: {file_info.get('status', 'unknown')}\n\n"
        
        return formatted
    
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
    
    async def list_vector_store_files(self, vector_store_id: str) -> List[Dict]:
        """
        ベクトルストア内のファイル一覧を取得（エイリアス）
        """
        return await self.get_vector_store_files(vector_store_id)


# グローバルインスタンス
vector_store_handler = VectorStoreHandlerResponses()
