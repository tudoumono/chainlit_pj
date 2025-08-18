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
                print("⚠️ OpenAIクライアントが初期化されていません")
                return None
            
            # ベクトルストアを作成
            print(f"📝 ベクトルストア作成開始: {name}")
            
            # 非同期クライアントでベクトルストアを作成
            # 注意: OpenAI SDKの最新版では、beta.vector_storesが利用可能
            try:
                # file_idsがある場合はそれを含めて作成
                if file_ids:
                    vector_store = await self.async_client.beta.vector_stores.create(
                        name=name,
                        file_ids=file_ids
                    )
                else:
                    vector_store = await self.async_client.beta.vector_stores.create(
                        name=name
                    )
                
                print(f"✅ ベクトルストア作成成功: {vector_store.id}")
                return vector_store.id
                
            except AttributeError as ae:
                # SDKのバージョンが古い、またはAPIが利用できない場合
                print(f"⚠️ ベクトルストアAPIが利用できません: {ae}")
                print("   OpenAI SDKを最新版に更新してください: pip install --upgrade openai")
                
                # フォールバック: ローカル管理（簡易版）
                import uuid
                import json
                import os
                
                vs_id = f"vs_{uuid.uuid4().hex[:12]}"
                vs_data = {
                    "id": vs_id,
                    "name": name,
                    "file_ids": file_ids or [],
                    "created_at": datetime.now().isoformat()
                }
                
                vs_dir = ".chainlit/vector_stores"
                os.makedirs(vs_dir, exist_ok=True)
                
                with open(f"{vs_dir}/{vs_id}.json", "w") as f:
                    json.dump(vs_data, f)
                
                print(f"✅ ベクトルストア作成（ローカル管理）: {vs_id}")
                return vs_id
                
        except Exception as e:
            print(f"❌ ベクトルストア作成エラー: {e}")
            print(f"   エラータイプ: {type(e).__name__}")
            import traceback
            print(f"   スタックトレース:\n{traceback.format_exc()}")
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
                print("⚠️ OpenAIクライアントが初期化されていません")
                return False
            
            try:
                # ファイルをベクトルストアに追加
                await self.async_client.beta.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=file_id
                )
                
                print(f"✅ ファイルをベクトルストアに追加: {file_id}")
                return True
                
            except AttributeError:
                # APIが利用できない場合のフォールバック
                import json
                import os
                
                vs_dir = ".chainlit/vector_stores"
                vs_file = f"{vs_dir}/{vector_store_id}.json"
                
                if os.path.exists(vs_file):
                    with open(vs_file, "r") as f:
                        vs_data = json.load(f)
                    
                    if file_id not in vs_data["file_ids"]:
                        vs_data["file_ids"].append(file_id)
                        
                        with open(vs_file, "w") as f:
                            json.dump(vs_data, f)
                    
                    print(f"✅ ファイルをベクトルストアに追加（ローカル）: {file_id}")
                    return True
                else:
                    print(f"⚠️ ベクトルストアが見つかりません: {vector_store_id}")
                    return False
            
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
                print("⚠️ OpenAIクライアントが初期化されていません")
                return False
            
            try:
                # ベクトルストアを削除
                await self.async_client.beta.vector_stores.delete(
                    vector_store_id=vector_store_id
                )
                
                print(f"✅ ベクトルストア削除: {vector_store_id}")
                return True
                
            except AttributeError:
                # APIが利用できない場合のフォールバック
                import os
                
                vs_dir = ".chainlit/vector_stores"
                vs_file = f"{vs_dir}/{vector_store_id}.json"
                
                if os.path.exists(vs_file):
                    os.remove(vs_file)
                    print(f"✅ ベクトルストア削除（ローカル）: {vector_store_id}")
                    return True
                else:
                    print(f"⚠️ ベクトルストアが見つかりません: {vector_store_id}")
                    return False
            
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
                print("⚠️ OpenAIクライアントが初期化されていません")
                return []
            
            try:
                # ベクトルストア一覧を取得
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
                
            except AttributeError:
                # APIが利用できない場合のフォールバック
                import json
                import os
                import glob
                
                vs_dir = ".chainlit/vector_stores"
                stores_list = []
                
                if os.path.exists(vs_dir):
                    for vs_file in glob.glob(f"{vs_dir}/*.json"):
                        try:
                            with open(vs_file, "r") as f:
                                vs_data = json.load(f)
                            
                            stores_list.append({
                                "id": vs_data["id"],
                                "name": vs_data["name"],
                                "file_counts": {"total": len(vs_data.get("file_ids", []))},
                                "created_at": datetime.fromisoformat(vs_data["created_at"]).timestamp(),
                                "status": "completed"
                            })
                        except Exception as e:
                            print(f"⚠️ ベクトルストアファイル読み込みエラー: {e}")
                
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
                print("⚠️ OpenAIクライアントが初期化されていません")
                return []
            
            try:
                # ベクトルストア内のファイル一覧を取得
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
                
            except AttributeError:
                # APIが利用できない場合のフォールバック
                import json
                import os
                
                vs_dir = ".chainlit/vector_stores"
                vs_file = f"{vs_dir}/{vector_store_id}.json"
                
                if os.path.exists(vs_file):
                    with open(vs_file, "r") as f:
                        vs_data = json.load(f)
                    
                    files_list = []
                    for file_id in vs_data.get("file_ids", []):
                        files_list.append({
                            "id": file_id,
                            "created_at": datetime.now().timestamp(),  # 仮の値
                            "status": "processed"
                        })
                    
                    return files_list
                else:
                    print(f"⚠️ ベクトルストアが見つかりません: {vector_store_id}")
                    return []
            
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
            if stores:
                vector_store_ids.extend(stores.values())
        
        # 必須パラメータとしてvector_store_idsを設定（空でもOK）
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
            
            try:
                # ベクトルストア情報を取得
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
                
            except AttributeError:
                # APIが利用できない場合のフォールバック
                import json
                import os
                
                vs_dir = ".chainlit/vector_stores"
                vs_file = f"{vs_dir}/{vector_store_id}.json"
                
                if os.path.exists(vs_file):
                    with open(vs_file, "r") as f:
                        vs_data = json.load(f)
                    
                    return {
                        "id": vs_data["id"],
                        "name": vs_data["name"],
                        "file_counts": {"total": len(vs_data.get("file_ids", []))},
                        "created_at": datetime.fromisoformat(vs_data["created_at"]).timestamp(),
                        "status": "completed"
                    }
                else:
                    print(f"⚠️ ベクトルストアが見つかりません: {vector_store_id}")
                    return None
            
        except Exception as e:
            print(f"❌ ベクトルストア情報取得エラー: {e}")
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
        
        return f"""
🆔 ID: `{vs_info['id']}`
📁 名前: {vs_info['name']}
📄 ファイル数: {vs_info.get('file_counts', {}).get('total', 0)}
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
