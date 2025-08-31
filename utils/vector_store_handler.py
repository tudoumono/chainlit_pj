"""
ベクトルストア管理モジュール（統合版）
Phase 7: OpenAI File Search APIを使った三層ナレッジベース管理

========================================================
🎯 このモジュールの役割
========================================================
AIアプリケーションで文書を検索可能にするための「ベクトルストア」を管理します。
ベクトルストアとは、文書をAIが理解できる数値データに変換して保存する仕組みです。

📚 三層のベクトルストア構造（初心者向け説明）
========================================================
1. 会社全体（Company）
   - 全社員が共有できる文書（会社規則、マニュアルなど）
   - .envファイルに設定されたIDで管理
   
2. 個人ユーザー（Personal）
   - 個人専用の文書（個人メモ、作業履歴など）
   - データベースに永続的に保存される
   
3. セッション（Session）
   - 一時的な文書（今の会話で使うファイルなど）
   - メモリ内のみで保存、24時間後自動削除

🔧 実装機能（技術詳細）
========================================================
- OpenAI Assistant APIのbeta.vector_stores エンドポイントを活用
- 各階層のベクトルストアを適切に分離・管理
- セキュアな所有者管理機能（権限チェック付き）
- 自動削除機能（リソース節約のため24時間後削除）
- GUI管理機能のサポート（ユーザーインターフェース対応）
- 単一のインターフェースで全階層にアクセス可能（APIの統一）

📅 変更履歴
========================================================
- 2025-08-25: 重複実装を統合、セキュリティ機能と自動管理機能を統合
- 2025-08-28: Pydantic設定システム対応、pathlib使用、初心者向けコメント追加
"""

import os
import json
import shutil
from typing import Dict, List, Optional, Tuple, Any
from openai import OpenAI, AsyncOpenAI
import asyncio
from datetime import datetime, timedelta
import aiofiles
import mimetypes
from pathlib import Path
import chainlit as cl
# from utils.project_settings import get_app_settings, get_project_paths, get_mime_settings
from utils.vector_store_api_helper import (
    get_vector_store_api,
    get_vector_store_files_api,
    safe_create_vector_store,
    safe_list_vector_stores,
    safe_retrieve_vector_store,
    safe_delete_vector_store,
    safe_update_vector_store
)

# 設定システムから取得（一時的にコメントアウト）
# _app_settings = get_app_settings()
# _project_paths = get_project_paths()
# _mime_settings = get_mime_settings()


class VectorStoreHandler:
    """ベクトルストア管理クラス（統合版）
    
    🔍 このクラスの役割（初心者向け）
    =======================================
    文書をAIが検索できるように管理する「司書」のような役割を果たします。
    図書館の司書が本を分類・整理・貸し出しするように、
    このクラスは文書を3つのカテゴリ（会社・個人・一時）に分類して管理します。
    
    🏗️ 統合機能一覧
    =======================================
    - 3階層のベクトルストア管理（会社全体、個人、セッション）
      → 文書を適切な「本棚」に分類
    - セキュアな所有者管理
      → 誰がどの文書にアクセスできるかを制御
    - 自動削除機能
      → 不要になった一時ファイルを24時間後に自動削除
    - GUI管理機能
      → ユーザーが画面操作で文書管理できるよう支援
    - Responses API対応
      → OpenAIの最新API仕様に準拠
    """
    
    @property
    def SUPPORTED_FILE_TYPES(self) -> Dict[str, str]:
        """サポートされるファイル形式（設定から取得）
        
        🎯 目的: アップロード可能なファイルの種類を定義
        📋 動作: 中央設定システムからMIME型マッピングを取得
        💡 初心者向け: .txt, .pdf, .py などの拡張子に対応するファイル種別辞書を返す
        
        Returns:
            Dict[str, str]: ファイル拡張子とMIME型の対応辞書
                           例: {'.txt': 'text/plain', '.pdf': 'application/pdf'}
        """
        # 一時的にハードコーディング（設定システム修正後に元に戻す）
        return {
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
        """クラスの初期化処理
        
        🎯 目的: ベクトルストアハンドラーのセットアップ
        📋 実行内容:
        1. OpenAI APIクライアントの初期化
        2. 3層のベクトルストア管理用変数の準備
        3. キャッシュシステムの初期化
        4. ローカルディレクトリの作成
        
        💡 初心者向け: このメソッドはクラスのインスタンス作成時に自動実行されます
        """
        # OpenAI API接続設定
        self.api_key = os.getenv("OPENAI_API_KEY", "")  # 環境変数からAPIキーを取得
        self.client = None          # 同期用OpenAIクライアント（後で初期化）
        self.async_client = None    # 非同期用OpenAIクライアント（後で初期化）
        self._init_clients()        # 実際のクライアント初期化を実行
        
        # 三層のベクトルストアID管理（データ分離のため）
        self.company_vs_id = os.getenv("COMPANY_VECTOR_STORE_ID", "")  # 1層目: 会社全体共有
        self.personal_vs_ids = {}   # 2層目: 個人用（ユーザーIDをキーとした辞書）
        self.session_vs_ids = {}    # 3層目: セッション用（セッションIDをキーとした辞書）
        
        # パフォーマンス向上用キャッシュシステム
        self._ownership_cache = {}      # ベクトルストアの所有者情報をメモリに保存
        self._session_vs_cache = {}     # セッション用ベクトルストアの情報をキャッシュ
        self._user_preferences = {}     # ユーザー設定をメモリに保存（高速アクセス用）
        
        # 自動削除設定（リソース節約のため）
        self.auto_delete_hours = 24     # 24時間後に一時ファイルを自動削除
        
        # ローカルファイル管理用ディレクトリ（旧バージョンとの互換性維持）
        self.vs_dir = ".chainlit/vector_stores"      # ベクトルストア情報保存先
        self.files_dir = ".chainlit/vector_store_files"  # ファイル一時保存先
        self._ensure_directories()  # 必要なディレクトリを作成
    
    def _ensure_directories(self):
        """必要なディレクトリを作成
        
        🎯 目的: ローカルファイル管理用のフォルダを準備
        📋 動作: ベクトルストア情報とファイル保存用ディレクトリを作成
        💡 初心者向け: フォルダが存在しない場合のみ作成、既存フォルダは変更しません
        
        Note:
            exist_ok=True により、既存ディレクトリがあってもエラーにならない
        """
        os.makedirs(self.vs_dir, exist_ok=True)     # ベクトルストア設定保存用
        os.makedirs(self.files_dir, exist_ok=True)  # アップロードファイル一時保存用
    
    def _init_clients(self):
        """OpenAIクライアントを初期化
        
        🎯 目的: OpenAI APIとの通信準備
        📋 実行内容:
        1. APIキーの検証
        2. プロキシ設定の確認
        3. 同期・非同期クライアントの作成
        
        💡 初心者向け: OpenAI APIを使うための「電話回線」のようなものを準備します
        """
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
                files = await self.async_client.vector_stores.files.list(
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
                await self.async_client.vector_stores.delete(
                    vector_store_id=vector_store_id
                )
                print(f"✅ ベクトルストア削除（Beta API）: {vector_store_id}")
                return True
            
        except Exception as e:
            print(f"❌ ベクトルストア削除エラー: {e}")
            return False
    
    async def rename_vector_store(self, vector_store_id: str, new_name: str) -> bool:
        """ベクトルストアの名前を変更
        
        🎯 目的: 既存のベクトルストアに新しい名前を設定
        📋 動作: OpenAI APIを使用してベクトルストアの名前を更新
        💡 初心者向け: ファイルの名前を変更するように、ベクトルストアの表示名を変更します
        
        Args:
            vector_store_id (str): 変更対象のベクトルストアID
                                  例: "vs_abc123def456"
            new_name (str): 新しい名前
                           例: "新しいプロジェクト資料"
        
        Returns:
            bool: 成功時True、失敗時False
            
        Raises:
            Exception: API通信エラーまたは権限エラー時
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
                await self.async_client.vector_stores.update(
                    vector_store_id=vector_store_id,
                    name=new_name
                )
                print(f"✅ ベクトルストア名を変更（Beta API）: {vector_store_id} -> {new_name}")
                return True
            
        except Exception as e:
            print(f"❌ ベクトルストア名変更エラー: {e}")
            return False
    
    def is_supported_file(self, filename: str) -> bool:
        """ファイルがアップロード対応形式かを確認
        
        🎯 目的: ファイルがシステムで処理可能かを事前チェック
        📋 動作: ファイルの拡張子を確認し、サポート対象リストと照合
        💡 初心者向け: .txt, .pdf などの許可されたファイル形式かを判定します
        
        Args:
            filename (str): 確認するファイル名
                          例: "document.pdf", "code.py"
        
        Returns:
            bool: サポート対象の場合True、未対応の場合False
            
        Example:
            >>> handler.is_supported_file("document.pdf")
            True
            >>> handler.is_supported_file("image.bmp")
            False
        """
        ext = Path(filename).suffix.lower()  # 拡張子を小文字で取得（大文字小文字を区別しない）
        return ext in self.SUPPORTED_FILE_TYPES
    
    def get_mime_type(self, filename: str) -> str:
        """ファイルのMIME型を取得
        
        🎯 目的: ファイル種別をWebの標準形式で特定
        📋 動作: 拡張子からMIME型を決定、未知の形式はバイナリとして扱う
        💡 初心者向け: .txt → text/plain のように、ファイルの「身分証明書」を取得します
        
        Args:
            filename (str): 対象ファイル名
                          例: "report.pdf", "script.py"
        
        Returns:
            str: MIME型文字列
                例: "application/pdf", "text/x-python"
                未対応の場合は "application/octet-stream" (汎用バイナリ)
                
        Note:
            MIME型はブラウザやAPI通信でファイル種別を識別するために使用
        """
        ext = Path(filename).suffix.lower()
        return self.SUPPORTED_FILE_TYPES.get(ext, 'application/octet-stream')
    
    async def process_uploaded_file(self, element) -> Optional[str]:
        """ChainlitのファイルをOpenAIにアップロード処理
        
        🎯 目的: ユーザーがアップロードしたファイルをAI処理可能な形式に変換
        📋 実行手順:
        1. Chainlitファイル要素から実ファイルを取得
        2. 一時保存場所にファイルを保存
        3. OpenAI APIにファイルをアップロード
        4. 一時ファイルを削除（セキュリティ・容量対策）
        
        💡 初心者向け: ユーザーの画面からのファイル→AI用ファイルへの「変換器」です
        
        Args:
            element: Chainlitのファイル要素オブジェクト
                    .path（ファイルパス）と .name（ファイル名）を含む
        
        Returns:
            Optional[str]: 成功時はOpenAIファイルID（例: "file_abc123"）
                          失敗時はNone
                          
        Raises:
            Exception: ファイルアクセスエラーまたはAPI通信エラー時
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
                vector_store = await self.async_client.vector_stores.retrieve(
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
    
    def set_layer_vector_store(self, layer: str, vs_id: str):
        """
        特定の階層のベクトルストアIDを設定
        
        Args:
            layer: 階層名 ("company", "personal", "session")
            vs_id: ベクトルストアID
        """
        if layer == "company":
            self.company_vs_id = vs_id
        elif layer == "personal":
            self.personal_vs_id = vs_id
        elif layer == "session":
            self.session_vs_id = vs_id
        else:
            print(f"⚠️ 不明な階層: {layer}")
    
    def get_layer_vector_store(self, layer: str) -> Optional[str]:
        """
        特定の階層のベクトルストアIDを取得
        
        Args:
            layer: 階層名 ("company", "personal", "session")
        
        Returns:
            ベクトルストアID
        """
        if layer == "company":
            return self.company_vs_id
        elif layer == "personal":
            return self.personal_vs_id
        elif layer == "session":
            return self.session_vs_id
        else:
            return None
    
    async def initialize_from_session(self, session_data: Dict):
        """
        セッションデータから3階層のベクトルストアIDを初期化
        
        Args:
            session_data: セッション情報を含む辞書
        """
        # 会社全体VSは.envから既に読み込まれている
        
        # 個人VSをセッションから取得
        if "personal_vs_id" in session_data and session_data["personal_vs_id"]:
            self.personal_vs_id = session_data["personal_vs_id"]
            print(f"✅ 個人ベクトルストアを設定: {self.personal_vs_id}")
        
        # セッションVSを取得（複数のキーを確認）
        session_vs_id = (
            session_data.get("session_vs_id") or
            session_data.get("thread_vs_id") or
            session_data.get("vector_store_ids", {}).get("session")
        )
        if session_vs_id:
            self.session_vs_id = session_vs_id
            print(f"✅ セッションベクトルストアを設定: {self.session_vs_id}")
    
    async def get_or_create_layer_store(self, layer: str, identifier: str = None) -> Optional[str]:
        """
        指定階層のベクトルストアを取得または作成
        
        Args:
            layer: 階層名 ("company", "personal", "session")
            identifier: ユーザーIDまたはセッションID
        
        Returns:
            ベクトルストアID
        """
        if layer == "company":
            # 会社VSは.envから読み込み（作成しない）
            return self.company_vs_id
        
        elif layer == "personal":
            if identifier in self.personal_vs_ids:
                return self.personal_vs_ids[identifier]
            elif self.personal_vs_id:  # 互換性のため
                return self.personal_vs_id
            elif identifier:
                # 新規作成
                vs_id = await self.create_personal_vector_store_with_ownership(identifier)
                if vs_id:
                    self.personal_vs_ids[identifier] = vs_id
                    self.personal_vs_id = vs_id  # 互換性のため
                return vs_id
            else:
                print("⚠️ 個人VSの作成にはユーザーIDが必要です")
                return None
        
        elif layer == "session":
            cache_key = f"{identifier}" if identifier else "default"
            if cache_key in self.session_vs_ids:
                return self.session_vs_ids[cache_key]
            elif self.session_vs_id:  # 互換性のため
                return self.session_vs_id
            elif identifier:
                # 新規作成
                vs_id = await self.create_session_vector_store_with_auto_delete(identifier)
                if vs_id:
                    self.session_vs_ids[cache_key] = vs_id
                    self.session_vs_id = vs_id  # 互換性のため
                return vs_id
            else:
                print("⚠️ セッションVSの作成にはセッションIDが必要です")
                return None
        
        return None
    
    async def create_personal_vector_store_with_ownership(self, user_id: str, name: str = None, 
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
                "owner_id": user_id,
                "category": category or "personal",
                "created_at": datetime.now().isoformat(),
                "type": "personal"
            }
            
            # APIヘルパーを使用してベクトルストアを作成
            vs_api = get_vector_store_api(self.async_client)
            if not vs_api:
                print("❌ ベクトルストアAPIが利用できません")
                return None
            
            vector_store = await vs_api.create(
                name=name,
                metadata=metadata
            )
            
            # 所有者情報をキャッシュ
            self._ownership_cache[vector_store.id] = user_id
            
            print(f"✅ 個人用ベクトルストア作成（所有者付き）: {vector_store.id}")
            return vector_store.id
            
        except Exception as e:
            print(f"❌ 個人用ベクトルストア作成エラー: {e}")
            return None
    
    async def create_session_vector_store_with_auto_delete(self, thread_id: str) -> Optional[str]:
        """
        チャット用ベクトルストアを作成（自動削除機能付き）
        
        Args:
            thread_id: ChainlitスレッドID（チャットID）
        
        Returns:
            作成されたベクトルストアID
        """
        try:
            name = f"Chat VS - {thread_id[:8]} - {datetime.now().strftime('%H%M')}"
            
            # メタデータに自動削除情報を含める
            metadata = {
                "thread_id": thread_id,
                "type": "chat",
                "created_at": datetime.now().isoformat(),
                "auto_delete_at": (datetime.now() + timedelta(hours=self.auto_delete_hours)).isoformat(),
                "temporary": True
            }
            
            # APIヘルパーを使用してベクトルストアを作成
            vs_api = get_vector_store_api(self.async_client)
            if not vs_api:
                print("❌ ベクトルストアAPIが利用できません")
                return None
            
            vector_store = await vs_api.create(
                name=name,
                metadata=metadata
            )
            
            # セッションキャッシュに保存
            cache_key = f"session:{session_id}"
            self._session_vs_cache[cache_key] = {
                "vs_id": vector_store.id,
                "created_at": datetime.now(),
                "auto_delete_at": datetime.now() + timedelta(hours=self.auto_delete_hours)
            }
            
            print(f"✅ セッション用ベクトルストア作成（自動削除付き）: {vector_store.id}")
            return vector_store.id
            
        except Exception as e:
            print(f"❌ セッション用ベクトルストア作成エラー: {e}")
            return None
    
    async def check_ownership(self, vs_id: str, user_id: str) -> bool:
        """
        ベクトルストアの所有権を確認
        
        Args:
            vs_id: ベクトルストアID
            user_id: ユーザーID
        
        Returns:
            所有者かどうか
        """
        try:
            # キャッシュを確認
            if vs_id in self._ownership_cache:
                return self._ownership_cache[vs_id] == user_id
            
            # APIから情報を取得
            vs_info = await self.get_vector_store_info(vs_id)
            if not vs_info:
                return False
            
            # メタデータから所有者情報を取得
            metadata = vs_info.get("metadata", {})
            owner_id = metadata.get("owner_id")
            
            # キャッシュに保存
            if owner_id:
                self._ownership_cache[vs_id] = owner_id
            
            return owner_id == user_id
            
        except Exception as e:
            print(f"❌ 所有権確認エラー: {e}")
            return False
    
    async def cleanup_expired_session_stores(self):
        """
        期限切れのセッションベクトルストアを自動削除
        """
        try:
            current_time = datetime.now()
            expired_stores = []
            
            # 期限切れのストアを特定
            for cache_key, cache_data in self._session_vs_cache.items():
                if cache_data.get("auto_delete_at") and cache_data["auto_delete_at"] < current_time:
                    expired_stores.append((cache_key, cache_data["vs_id"]))
            
            # 削除処理
            for cache_key, vs_id in expired_stores:
                try:
                    await self.delete_vector_store(vs_id)
                    del self._session_vs_cache[cache_key]
                    print(f"🗑️ 期限切れセッションVSを自動削除: {vs_id}")
                except Exception as e:
                    print(f"⚠️ セッションVS削除失敗: {vs_id} - {e}")
            
            if expired_stores:
                print(f"✅ {len(expired_stores)}個の期限切れセッションVSを削除しました")
                
        except Exception as e:
            print(f"❌ 自動削除処理エラー: {e}")
    
    def get_enabled_vector_store_ids(self, enabled_layers: Dict[str, bool] = None) -> List[str]:
        """
        有効な階層のベクトルストアIDリストを取得
        
        Args:
            enabled_layers: 各階層の有効/無効設定
                           例: {"company": True, "personal": True, "session": False}
        
        Returns:
            有効なベクトルストアIDのリスト
        """
        if enabled_layers is None:
            # デフォルトは全階層有効
            enabled_layers = {"company": True, "personal": True, "session": True}
        
        ids = []
        
        # 1層目: 会社全体
        if enabled_layers.get("company", True) and self.company_vs_id:
            ids.append(self.company_vs_id)
        
        # 2層目: 個人ユーザー
        if enabled_layers.get("personal", True) and self.personal_vs_id:
            ids.append(self.personal_vs_id)
        
        # 3層目: セッション
        if enabled_layers.get("session", True) and self.session_vs_id:
            ids.append(self.session_vs_id)
        
        return ids


    # データベース連携メソッド（互換性のため）
    async def get_user_vector_store_from_db(self, user_id: str) -> Optional[str]:
        """
        データベースからユーザーのベクトルストアIDを取得
        
        Args:
            user_id: ユーザーID
        
        Returns:
            ベクトルストアID
        """
        try:
            # まずキャッシュを確認
            if user_id in self.personal_vs_ids:
                return self.personal_vs_ids[user_id]
            
            # data_layerから取得を試みる
            import chainlit.data as cl_data
            data_layer_instance = cl_data._data_layer
            
            if data_layer_instance and hasattr(data_layer_instance, 'get_user_vector_store_id'):
                vs_id = await data_layer_instance.get_user_vector_store_id(user_id)
                if vs_id:
                    self.personal_vs_ids[user_id] = vs_id
                    self.personal_vs_id = vs_id  # 互換性のため
                return vs_id
            
            return None
            
        except Exception as e:
            print(f"❌ DBからのベクトルストアID取得エラー: {e}")
            return None
    
    async def set_user_vector_store_in_db(self, user_id: str, vs_id: str) -> bool:
        """
        データベースにユーザーのベクトルストアIDを保存
        
        Args:
            user_id: ユーザーID
            vs_id: ベクトルストアID
        
        Returns:
            成功/失敗
        """
        try:
            # キャッシュに保存
            self.personal_vs_ids[user_id] = vs_id
            self.personal_vs_id = vs_id  # 互換性のため
            
            # data_layerに保存を試みる
            import chainlit.data as cl_data
            data_layer_instance = cl_data._data_layer
            
            if data_layer_instance and hasattr(data_layer_instance, 'set_user_vector_store_id'):
                await data_layer_instance.set_user_vector_store_id(user_id, vs_id)
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ DBへのベクトルストアID保存エラー: {e}")
            return False
    
    def get_all_active_vector_store_ids(self) -> List[str]:
        """
        すべてのアクティブなベクトルストアIDを取得（全階層）
        
        Returns:
            ベクトルストアIDのリスト
        """
        ids = []
        
        # 1層目: 会社全体
        if self.company_vs_id:
            ids.append(self.company_vs_id)
        
        # 2層目: すべての個人ユーザー
        ids.extend(self.personal_vs_ids.values())
        
        # 3層目: すべてのセッション
        ids.extend(self.session_vs_ids.values())
        
        # 重複を除去
        return list(set(ids))
    
    async def save_uploaded_file(self, element) -> Optional[str]:
        """
        Chainlitでアップロードされたファイルをベクトルストアに保存
        
        Args:
            element: Chainlitのファイル要素
            
        Returns:
            保存されたファイルパス（成功時）、None（失敗時）
        """
        try:
            if not hasattr(element, 'path') or not hasattr(element, 'name'):
                print(f"❌ 無効なファイル要素: {element}")
                return None
            
            # 一時保存ディレクトリを作成
            upload_dir = Path("/root/mywork/chainlit_pj/uploads")
            upload_dir.mkdir(exist_ok=True)
            
            # ファイル名の安全化
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', element.name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_name = f"{timestamp}_{safe_name}"
            
            # ファイルを一時ディレクトリにコピー
            final_path = upload_dir / final_name
            shutil.copy2(element.path, final_path)
            
            print(f"✅ ファイル保存完了: {final_path}")
            
            # アクティブなベクトルストアに追加
            await self._add_file_to_active_vector_stores(str(final_path), element.name)
            
            return str(final_path)
            
        except Exception as e:
            print(f"❌ ファイル保存エラー: {e}")
            return None
    
    async def _add_file_to_active_vector_stores(self, file_path: str, original_name: str):
        """
        ファイルをアクティブなベクトルストアに追加
        
        Args:
            file_path: 保存されたファイルパス
            original_name: 元のファイル名
        """
        try:
            # 現在アクティブなベクトルストアIDを取得
            active_ids = self.get_active_vector_store_ids()
            
            if not active_ids:
                print("⚠️ アクティブなベクトルストアが設定されていません")
                print("🔧 セッション用ベクトルストアを自動作成します...")
                
                # チャット用ベクトルストアを自動作成
                try:
                    import chainlit as cl
                    thread_id = cl.user_session.get("thread_id", "unknown_thread")
                except:
                    thread_id = "default_session"  # フォールバック
                    
                vs_name = f"チャット_{thread_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M')}"
                
                vs_id = await self.create_vector_store(vs_name)
                if vs_id:
                    print(f"✅ セッション用ベクトルストア作成: {vs_id}")
                    active_ids = [vs_id]
                    
                    # ベクトルストアIDをチャット（thread）に保存（将来の使用のため）
                    self.session_vs_ids[thread_id] = vs_id
                else:
                    print("❌ ベクトルストア作成に失敗しました")
                    return
            
            # ファイルをOpenAI Files APIにアップロード
            with open(file_path, "rb") as f:
                file_obj = await self.async_client.files.create(
                    file=f,
                    purpose="assistants"
                )
            
            print(f"✅ OpenAI Filesにアップロード: {file_obj.id}")
            
            # 各アクティブベクトルストアに追加
            for vs_id in active_ids:
                try:
                    await self.async_client.vector_stores.files.create(
                        vector_store_id=vs_id,
                        file_id=file_obj.id
                    )
                    print(f"✅ ベクトルストア {vs_id[:8]}... にファイル追加: {original_name}")
                    
                except Exception as vs_error:
                    print(f"❌ ベクトルストア {vs_id[:8]}... へのファイル追加エラー: {vs_error}")
                    continue
            
        except Exception as e:
            print(f"❌ ベクトルストアへのファイル追加エラー: {e}")
    
    def get_active_vector_store_ids(self) -> List[str]:
        """
        現在アクティブなベクトルストアIDを取得（Tools設定に基づく）
        
        Returns:
            アクティブなベクトルストアIDのリスト
        """
        try:
            # tools_config.jsonを読み込み
            tools_config_path = "/root/mywork/chainlit_pj/.chainlit/tools_config.json"
            if not os.path.exists(tools_config_path):
                return []
            
            with open(tools_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # ファイル検索が有効かつベクトルストアIDが設定されている場合
            file_search = config.get("tools", {}).get("file_search", {})
            if not file_search.get("enabled", False):
                return []
            
            vector_store_ids = file_search.get("vector_store_ids", [])
            
            # 空の場合はデフォルトベクトルストアを使用
            if not vector_store_ids:
                # セッション層、個人層、会社層の順で検索
                defaults = []
                
                # セッション層
                if self.session_vs_ids:
                    defaults.extend(list(self.session_vs_ids.values()))
                
                # 個人層
                if self.personal_vs_ids:
                    defaults.extend(list(self.personal_vs_ids.values()))
                
                # 会社層
                if self.company_vs_id:
                    defaults.append(self.company_vs_id)
                
                return defaults[:1]  # 最初の1つのみ使用
            
            return vector_store_ids
            
        except Exception as e:
            print(f"❌ アクティブベクトルストア取得エラー: {e}")
            return []


# グローバルインスタンス
vector_store_handler = VectorStoreHandler()
