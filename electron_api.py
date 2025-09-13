"""
Electron用REST APIサーバー
Chainlitと並行して動作し、Electron管理機能用のAPIエンドポイントを提供
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from typing import Dict, Any, List, Optional
import sqlite3
import json
import os
from dotenv import load_dotenv
from datetime import datetime
import time
from openai import AsyncOpenAI

# 既存ハンドラーをインポート（依存ごとに独立して読み込み、片方の失敗で全体を落とさない）
persona_handler_instance = None
analytics_handler_instance = None
vector_store_handler = None
SQLiteDataLayer = None
app_logger = None

try:
    from handlers.persona_handler import persona_handler_instance  # type: ignore
except Exception as e:
    print(f"Warning: persona_handler not available: {e}")

try:
    # Electron APIではanalytics.dbを直接参照して集計するため、
    # handlers.analytics_handler への依存は必須ではない。
    # 将来的な拡張に備えて読み込みを試みるが、失敗しても続行する。
    from handlers.analytics_handler import analytics_handler  # type: ignore
    analytics_handler_instance = analytics_handler
except Exception as e:
    print(f"Warning: analytics_handler not available: {e}")

try:
    from utils.vector_store_handler import vector_store_handler  # type: ignore
except Exception as e:
    print(f"Warning: vector_store_handler not available: {e}")

try:
    from data_layer import SQLiteDataLayer  # type: ignore
except Exception as e:
    print(f"Warning: SQLiteDataLayer not available: {e}")

try:
    from utils.logger import app_logger  # type: ignore
except Exception as e:
    print(f"Warning: app_logger not available: {e}")

# .envファイルの読み込み（DOTENV_PATH優先）
_dotenv_path = os.environ.get("DOTENV_PATH")
if _dotenv_path and os.path.exists(_dotenv_path):
    load_dotenv(_dotenv_path)
else:
    load_dotenv()

# .env読み込み後にVector Store Handlerを再初期化
try:
    if 'vector_store_handler' in globals() and vector_store_handler is not None:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            # APIキーを反映しつつクライアント再初期化
            try:
                vector_store_handler.update_api_key(api_key)
            except Exception:
                # update_api_keyが失敗した場合は直接初期化を試みる
                vector_store_handler._init_clients()
        else:
            # APIキーが空でも初期化だけは実行（ログに警告が出る）
            vector_store_handler._init_clients()
except Exception as _e:
    print(f"Vector store handler reinit failed: {_e}")

app = FastAPI(
    title="Chainlit Electron API",
    description="ElectronアプリケーションのAPI管理機能",
    version="1.0.0"
)

# 内部ユーティリティ: Vector Store Handlerの初期化保証
def _ensure_vector_store_ready() -> bool:
    try:
        global vector_store_handler
        if not vector_store_handler:
            return False
        if getattr(vector_store_handler, 'async_client', None) is None:
            # .env反映後の再初期化を試行
            api_key = os.getenv("OPENAI_API_KEY", "")
            if api_key:
                try:
                    vector_store_handler.update_api_key(api_key)
                except Exception:
                    vector_store_handler._init_clients()
            else:
                vector_store_handler._init_clients()
        return getattr(vector_store_handler, 'async_client', None) is not None
    except Exception:
        return False

# CORS設定（Electronからのアクセス許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],  # Electron renderer
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データモデル定義
class PersonaData(BaseModel):
    name: str
    system_prompt: str
    model: Optional[str] = "gpt-3.5-turbo"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000
    description: Optional[str] = ""
    tags: Optional[str] = ""
    is_active: Optional[bool] = False

class PersonaStatusUpdate(BaseModel):
    is_active: bool


class CleanupResponse(BaseModel):
    removed_files: int
    removed_dirs: int
    details: Dict[str, int]


class FactoryResetRequest(BaseModel):
    confirm: bool = False
    preview: bool = False


def _safe_remove(path: str, counters: Dict[str, int]):
    try:
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path, ignore_errors=True)
            counters['dirs'] += 1
        elif os.path.isfile(path):
            os.remove(path)
            counters['files'] += 1
    except Exception:
        pass


def _collect_paths_for_cleanup() -> Dict[str, list]:
    """ローカルの一時/生成物をクリーンアップ対象として収集（OpenAI側は対象外）。"""
    targets: Dict[str, list] = {
        'db': [],
        'tmp': [],
        'logs': [],
        'exports': [],
        'uploads': []
    }
    base = os.getcwd()
    # SQLite DB（ローカルのみ）
    targets['db'].extend([
        os.path.join(base, '.chainlit', 'chainlit.db'),
        os.path.join(base, '.chainlit', 'analytics.db')
    ])
    # 一時ファイル/ローカルキャッシュ
    targets['tmp'].append(os.path.join(base, '.chainlit', 'vector_store_files'))
    # ログ（Python側既定なし。存在すれば削除）
    targets['logs'].append(os.path.join(base, 'Log'))
    # エクスポート/アップロード
    targets['exports'].append(os.path.join(base, 'exports'))
    targets['uploads'].append(os.path.join(base, 'uploads'))
    return targets


@app.get('/api/system/export')
async def export_system_info():
    """システム情報をJSONでエクスポート（ローカルのみ）。"""
    try:
        info = {
            'timestamp': datetime.now().isoformat(),
            'cwd': os.getcwd(),
            'env': {
                'DOTENV_PATH': os.environ.get('DOTENV_PATH'),
                'CHAINLIT_CONFIG_PATH': os.environ.get('CHAINLIT_CONFIG_PATH'),
            }
        }
        # 依存/バージョン
        try:
            import sys
            import platform
            info['runtime'] = {
                'python': sys.version,
                'platform': platform.platform(),
            }
        except Exception:
            pass

        export_dir = 'exports'
        os.makedirs(export_dir, exist_ok=True)
        filename = f"system_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_path = os.path.join(export_dir, filename)
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        return {"status": "success", "data": {"export_path": export_path, "filename": filename}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/system/test-openai-key')
async def test_openai_key(request: Dict[str, Any]):
    """OpenAI APIキー疎通テスト（既存キー使用が基本）。"""
    try:
        api_key = (request.get('api_key') or os.getenv('OPENAI_API_KEY') or '').strip()
        if not api_key or api_key == 'your_api_key_here':
            raise HTTPException(status_code=400, detail='APIキーが設定されていません')

        # モデルはenv優先、ダメなら安全な既定にフォールバック
        model_env = (request.get('model') or os.getenv('DEFAULT_MODEL') or '').strip()
        safe_default = 'gpt-4o-mini'
        candidate_models = [m for m in [model_env, safe_default] if m]

        client = AsyncOpenAI(api_key=api_key)
        last_error = None
        import asyncio
        for mdl in candidate_models:
            try:
                t0 = time.monotonic()
                # 400回避のため追加パラメータは付けず最小呼び出し
                resp = await client.responses.create(model=mdl, input='ping')
                dt_ms = int((time.monotonic() - t0) * 1000)
                return {"status": "success", "data": {"model": getattr(resp, 'model', mdl), "latency_ms": dt_ms, "ok": True}}
            except Exception as e:
                last_error = e
                await asyncio.sleep(0)  # yield
                continue
        raise HTTPException(status_code=500, detail=f'OpenAI疎通エラー: {last_error}')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'OpenAI疎通エラー: {e}')


@app.post('/api/system/cleanup')
async def system_cleanup() -> Dict[str, Any]:
    """ローカル生成物のクリーンアップ。OpenAI側のベクトルストア等は対象外。"""
    try:
        targets = _collect_paths_for_cleanup()
        counters = {'files': 0, 'dirs': 0}
        for cat, paths in targets.items():
            for p in paths:
                if os.path.isdir(p):
                    # ディレクトリ配下を削除
                    import shutil
                    if os.path.exists(p):
                        shutil.rmtree(p, ignore_errors=True)
                        counters['dirs'] += 1
                elif os.path.isfile(p):
                    _safe_remove(p, counters)
        return {"status": "success", "data": CleanupResponse(removed_files=counters['files'], removed_dirs=counters['dirs'], details=counters).dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/system/factory-reset')
async def factory_reset(req: FactoryResetRequest):
    """アプリ範囲の全データリセット（OpenAI API側は触らない）。"""
    try:
        targets = _collect_paths_for_cleanup()
        # 追加: personas.json（存在すれば）
        targets.setdefault('personas', []).append(os.path.join(os.getcwd(), '.chainlit', 'personas.json'))

        # プレビュー
        preview_data: Dict[str, int] = {}
        for cat, paths in targets.items():
            count = 0
            for p in paths:
                if os.path.isdir(p):
                    if os.path.exists(p):
                        count += 1
                elif os.path.isfile(p):
                    if os.path.exists(p):
                        count += 1
            preview_data[cat] = count

        if req.preview and not req.confirm:
            return {"status": "success", "data": {"preview": preview_data}}

        if not req.confirm:
            raise HTTPException(status_code=400, detail="Confirmation required")

        # 削除実行（OpenAI API側の削除呼び出しは一切行わない）
        counters = {'files': 0, 'dirs': 0}
        for paths in targets.values():
            for p in paths:
                if os.path.isdir(p):
                    import shutil
                    shutil.rmtree(p, ignore_errors=True)
                    counters['dirs'] += 1
                elif os.path.isfile(p):
                    _safe_remove(p, counters)

        return {"status": "success", "data": {"removed_files": counters['files'], "removed_dirs": counters['dirs'], "note": "OpenAI側のベクトルストア等は変更していません"}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class VectorStoreData(BaseModel):
    name: str
    category: Optional[str] = "general"
    description: Optional[str] = ""

# SQLiteデータベースアクセス
def get_db_connection():
    """SQLiteデータベース接続を取得"""
    try:
        conn = sqlite3.connect('.chainlit/chainlit.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        if app_logger:
            app_logger.error(f"データベース接続エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {e}")

# analytics.db 接続（存在しない場合はNoneを返すラッパ）
def get_analytics_db_connection():
    path = os.path.join('.chainlit', 'analytics.db')
    if not os.path.exists(path):
        return None
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        try:
            if app_logger:
                app_logger.error(f"analytics.db接続エラー: {e}")
        except Exception:
            pass
        return None

# ヘルスチェックエンドポイント
@app.get("/api/health")
async def health_check():
    """APIサーバーのヘルスチェック"""
    return {
        "status": "ok",
        "message": "Electron API Server is running",
        "timestamp": datetime.now().isoformat()
    }

# システム情報エンドポイント
@app.get("/api/system/status")
async def get_system_status():
    """システム状態情報を取得（UIが期待するフィールドを含む）"""
    try:
        import sys
        electron_version = os.environ.get('ELECTRON_VERSION', '')
        app_version = os.environ.get('APP_VERSION', '')
        python_version = sys.version.split(' ')[0]
        # Chainlitバージョン取得
        try:
            import chainlit  # type: ignore
            chainlit_version = getattr(chainlit, '__version__', '')
        except Exception:
            chainlit_version = ''

        # DB統計/状態
        db_path = '.chainlit/chainlit.db'
        database_status = 'unknown'
        thread_count = 0
        persona_count = 0
        vector_store_count = 0
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM threads")
            thread_count = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM personas")
            persona_count = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM user_vector_stores")
            vector_store_count = cursor.fetchone()['count']
            database_status = 'healthy'
            conn.close()
        except Exception:
            database_status = 'unhealthy'

        # OpenAI設定状態（疎通までは行わない）
        openai_status = 'healthy' if os.getenv('OPENAI_API_KEY') else 'unknown'

        return {
            "status": "success",
            "data": {
                "app_version": app_version,
                "electron_version": electron_version,
                "python_version": python_version,
                "chainlit_version": chainlit_version,
                "threads": thread_count,
                "personas": persona_count,
                "vector_stores": vector_store_count,
                "database_path": db_path,
                "database_status": database_status,
                "openai_status": openai_status,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ペルソナ管理エンドポイント
@app.get("/api/personas")
async def list_personas():
    """ペルソナ一覧取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, system_prompt, model, temperature, max_tokens, 
                   description, tags, is_active, created_at, updated_at
            FROM personas
            ORDER BY created_at DESC
        """)
        personas = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"status": "success", "data": personas}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/personas")
async def create_persona(persona_data: PersonaData):
    """ペルソナ作成"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO personas (name, system_prompt, model, temperature, max_tokens, 
                                description, tags, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            persona_data.name,
            persona_data.system_prompt,
            persona_data.model,
            persona_data.temperature,
            persona_data.max_tokens,
            persona_data.description,
            persona_data.tags,
            persona_data.is_active,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        persona_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"status": "success", "data": {"persona_id": persona_id}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/personas/{persona_id}")
async def get_persona(persona_id: int):
    """特定のペルソナ取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM personas WHERE id = ?", (persona_id,))
        persona = cursor.fetchone()
        conn.close()
        
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        return {"status": "success", "data": dict(persona)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/personas/{persona_id}")
async def update_persona(persona_id: int, persona_data: PersonaData):
    """ペルソナ更新"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE personas SET 
                name=?, system_prompt=?, model=?, temperature=?, max_tokens=?,
                description=?, tags=?, is_active=?, updated_at=?
            WHERE id=?
        """, (
            persona_data.name,
            persona_data.system_prompt, 
            persona_data.model,
            persona_data.temperature,
            persona_data.max_tokens,
            persona_data.description,
            persona_data.tags,
            persona_data.is_active,
            datetime.now().isoformat(),
            persona_id
        ))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "Persona updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/personas/{persona_id}/status")
async def update_persona_status(persona_id: int, payload: PersonaStatusUpdate):
    """ペルソナのアクティブ状態のみ更新"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE personas SET is_active=?, updated_at=? WHERE id=?",
            (payload.is_active, datetime.now().isoformat(), persona_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Persona not found")
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Persona status updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/personas/{persona_id}")
async def delete_persona(persona_id: int):
    """ペルソナ削除"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM personas WHERE id = ?", (persona_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "Persona deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ベクトルストア管理エンドポイント（OpenAIアカウント全体の一覧）
@app.get("/api/vectorstores")
async def list_vector_stores():
    """OpenAIアカウントに存在するベクトルストアの全体一覧を返す。"""
    try:
        if not _ensure_vector_store_ready():
            raise HTTPException(status_code=503, detail="Vector store handler is not initialized")
        # 取得ログ（可観測性向上）
        try:
            if app_logger:
                app_logger.info("📁 ベクトルストア一覧 取得開始 (OpenAI全体)")
        except Exception:
            pass
        stores = await vector_store_handler.list_vector_stores()
        try:
            if app_logger:
                app_logger.info("📁 ベクトルストア一覧 取得完了", count=len(stores))
        except Exception:
            pass
        return {"status": "success", "data": stores}
    except HTTPException:
        raise
    except Exception as e:
        try:
            if app_logger:
                app_logger.error("❌ ベクトルストア一覧 取得失敗", error=str(e))
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


class CreateVectorStoreRequest(BaseModel):
    name: str
    expires_after_days: Optional[int] = None


@app.post("/api/vectorstores")
async def create_vector_store(req: CreateVectorStoreRequest):
    """ベクトルストア作成"""
    try:
        if not _ensure_vector_store_ready():
            raise HTTPException(status_code=503, detail="Vector store handler is not initialized")

        vs_id = await vector_store_handler.create_vector_store(name=req.name)
        if not vs_id:
            raise HTTPException(status_code=500, detail="Failed to create vector store")

        info = await vector_store_handler.get_vector_store_info(vs_id) or {"id": vs_id, "name": req.name}
        # ローカルDBにマッピングを登録（簡易: user_id='admin'）
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_vector_stores (user_id, vector_store_id, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                ("admin", vs_id, datetime.now().isoformat(), datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        return {"status": "success", "data": info}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpdateVectorStoreRequest(BaseModel):
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@app.patch("/api/vectorstores/{vector_store_id}")
async def update_vector_store(vector_store_id: str, req: UpdateVectorStoreRequest):
    """ベクトルストアの更新（主に表示名変更）。"""
    try:
        if not _ensure_vector_store_ready():
            raise HTTPException(status_code=503, detail="Vector store handler is not initialized")

        # 現状は名前変更の対応を優先
        ok = True
        if req.name:
            ok = await vector_store_handler.rename_vector_store(vector_store_id, req.name)
        # メタデータ更新が必要なら今後ここで対応
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to update vector store")

        info = await vector_store_handler.get_vector_store_info(vector_store_id)
        if not info:
            raise HTTPException(status_code=404, detail="Vector store not found")
        return {"status": "success", "data": info}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vectorstores/{vector_store_id}")
async def get_vector_store(vector_store_id: str):
    """ベクトルストア詳細+ファイル一覧"""
    try:
        if not _ensure_vector_store_ready():
            raise HTTPException(status_code=503, detail="Vector store handler is not initialized")

        info = await vector_store_handler.get_vector_store_info(vector_store_id)
        if not info:
            raise HTTPException(status_code=404, detail="Vector store not found")

        files = await vector_store_handler.get_vector_store_files(vector_store_id)
        # renderer期待フォーマットに合わせた簡易変換
        file_details = []
        for f in files:
            file_details.append({
                "id": f.get("id"),
                "filename": f.get("filename") or f.get("id"),
                "size": f.get("bytes") or f.get("size") or 0,
                "status": f.get("status", "processed"),
                "created_at": f.get("created_at")
            })

        info["file_details"] = file_details
        return {"status": "success", "data": info}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UploadToVectorStoreRequest(BaseModel):
    filename: str
    content: str  # data URLまたはbase64文字列
    size: Optional[int] = 0
    type: Optional[str] = None


@app.post("/api/vectorstores/{vector_store_id}/upload")
async def upload_to_vector_store(vector_store_id: str, req: UploadToVectorStoreRequest):
    """ファイルをアップロードしてベクトルストアに追加"""
    try:
        if not _ensure_vector_store_ready():
            raise HTTPException(status_code=503, detail="Vector store handler is not initialized")

        # contentがdata URL形式の場合にbase64本体を抽出
        content = req.content
        if "," in content:
            content = content.split(",", 1)[1]
        import base64
        try:
            file_bytes = base64.b64decode(content)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid file content encoding")

        # OpenAIにファイルアップロード
        file_id = await vector_store_handler.upload_file_from_bytes(
            file_bytes=file_bytes,
            filename=req.filename,
            purpose="assistants"
        )
        if not file_id:
            raise HTTPException(status_code=500, detail="Failed to upload file")

        # ベクトルストアに追加（ポーリング含む）
        attached = await vector_store_handler.add_file_to_vector_store(vector_store_id, file_id)
        if not attached:
            raise HTTPException(status_code=500, detail="Failed to attach file to vector store")

        return {"status": "success", "data": {"file_id": file_id}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/vectorstores/{vector_store_id}")
async def delete_vector_store(vector_store_id: str):
    """ベクトルストア削除"""
    try:
        if not _ensure_vector_store_ready():
            raise HTTPException(status_code=503, detail="Vector store handler is not initialized")

        ok = await vector_store_handler.delete_vector_store(vector_store_id)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to delete vector store")
        # マッピングも削除
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_vector_stores WHERE vector_store_id = ?", (vector_store_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 分析・統計エンドポイント
@app.get("/api/analytics/dashboard/{user_id}")
async def get_analytics_dashboard(user_id: str):
    """分析ダッシュボードデータ取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 概要合計
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM threads WHERE user_id = ? OR user_identifier = ?",
            (user_id, user_id),
        )
        total_chats = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(s.id) as cnt
            FROM steps s
            JOIN threads t ON s.thread_id = t.id
            WHERE (t.user_id = ? OR t.user_identifier = ?)
            """,
            (user_id, user_id),
        )
        total_messages = cursor.fetchone()[0]

        # personas / vector stores は存在しない場合を考慮
        total_personas = 0
        try:
            cursor.execute("SELECT COUNT(*) FROM personas")
            total_personas = cursor.fetchone()[0]
        except Exception:
            total_personas = 0

        total_vector_stores = 0
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM user_vector_stores WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            total_vector_stores = row[0] if row else 0
        except Exception:
            total_vector_stores = 0

        conn.close()

        return {
            "status": "success",
            "data": {
                "total_chats": int(total_chats or 0),
                "total_messages": int(total_messages or 0),
                "total_vector_stores": int(total_vector_stores or 0),
                "total_personas": int(total_personas or 0),
                "generated_at": datetime.now().isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/usage/{user_id}")
async def get_usage_analytics(user_id: str, period: str = "7d"):
    """使用状況分析取得（rendererが期待する形に整形）"""
    try:
        # 期間
        days = 7 if period == "7d" else 30 if period == "30d" else 90 if period == "90d" else 30

        # 日別集計（Chainlit DB: stepsベース）
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DATE(s.created_at) as date, COUNT(*) as cnt
            FROM steps s
            JOIN threads t ON s.thread_id = t.id
            WHERE (t.user_id = ? OR t.user_identifier = ?)
              AND s.created_at >= datetime('now', ?)
            GROUP BY DATE(s.created_at)
            ORDER BY date ASC
            """,
            (user_id, user_id, f"-{days} days"),
        )
        daily_rows = cursor.fetchall()
        daily_usage = [{"date": row[0], "count": row[1]} for row in daily_rows]

        # 直近アクティビティ & 機能別集計（analytics.dbがあれば利用）
        feature_usage: List[Dict[str, Any]] = []
        recent_activities: List[Dict[str, Any]] = []
        aconn = get_analytics_db_connection()
        if aconn is not None:
            acur = aconn.cursor()
            # 機能別集計
            try:
                acur.execute(
                    """
                    SELECT action as feature_name, COUNT(*) as cnt
                    FROM user_actions
                    WHERE timestamp >= datetime('now', ?)
                      AND user_id = ?
                    GROUP BY action
                    ORDER BY cnt DESC
                    LIMIT 10
                    """,
                    (f"-{days} days", user_id),
                )
                feature_usage = [
                    {"feature_name": r[0], "count": r[1]} for r in acur.fetchall()
                ]
            except Exception:
                feature_usage = []

            # 最近のアクティビティ
            try:
                acur.execute(
                    """
                    SELECT action as type, target as description, timestamp
                    FROM user_actions
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 20
                    """,
                    (user_id,),
                )
                recent_activities = [
                    {"type": r[0], "description": r[1], "timestamp": r[2]}
                    for r in acur.fetchall()
                ]
            except Exception:
                recent_activities = []
            try:
                aconn.close()
            except Exception:
                pass
        else:
            # 代替: analytics.dbが無ければ簡易的に直近のステップをアクティビティとして返す
            try:
                cursor.execute(
                    """
                    SELECT s.type as type, substr(coalesce(s.output, s.name, 'message'), 1, 40) as description, s.created_at
                    FROM steps s
                    JOIN threads t ON s.thread_id = t.id
                    WHERE (t.user_id = ? OR t.user_identifier = ?)
                    ORDER BY s.created_at DESC
                    LIMIT 20
                    """,
                    (user_id, user_id),
                )
                recent_activities = [
                    {"type": r[0] or "message", "description": r[1] or "", "timestamp": r[2]}
                    for r in cursor.fetchall()
                ]
            except Exception:
                recent_activities = []

        conn.close()

        return {
            "status": "success",
            "data": {
                "daily_usage": daily_usage,
                "feature_usage": feature_usage,
                "recent_activities": recent_activities,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/export/{user_id}")
async def export_analytics(user_id: str, format: str = "json"):
    """分析データをエクスポート（json/csv/簡易pdfテキスト）。"""
    try:
        # まず同APIで使用するデータを収集
        usage_res = await get_usage_analytics(user_id=user_id, period="30d")
        dash_res = await get_analytics_dashboard(user_id=user_id)

        export_data = {
            "generated_at": datetime.now().isoformat(),
            "user_id": user_id,
            "dashboard": dash_res.get("data", {}),
            "usage": usage_res.get("data", {}),
        }

        os.makedirs("exports", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format.lower() == "json":
            filename = f"analytics_{user_id}_{ts}.json"
            path = os.path.join("exports", filename)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
        elif format.lower() == "csv":
            # シンプルにdaily_usageをCSV出力
            filename = f"analytics_daily_{user_id}_{ts}.csv"
            path = os.path.join("exports", filename)
            import csv
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["date", "count"]) 
                for row in export_data.get("usage", {}).get("daily_usage", []):
                    writer.writerow([row.get("date"), row.get("count", 0)])
        elif format.lower() == "pdf":
            # 簡易: テキストを.pdf拡張で保存（本格的なPDF生成は別PRで）
            filename = f"analytics_report_{user_id}_{ts}.pdf"
            path = os.path.join("exports", filename)
            report = [
                "Analytics Report",
                f"Generated: {export_data['generated_at']}",
                f"User: {user_id}",
                "",
                "Dashboard Summary:",
            ]
            for k, v in export_data.get("dashboard", {}).items():
                if k == "generated_at":
                    continue
                report.append(f"- {k}: {v}")
            report.append("")
            report.append("Daily Usage (last 30d):")
            for row in export_data.get("usage", {}).get("daily_usage", []):
                report.append(f"- {row.get('date')}: {row.get('count', 0)}")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(report))
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")

        return {"status": "success", "data": {"export_path": path, "filename": filename}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ログ管理エンドポイント
@app.get("/api/system/logs")
async def get_system_logs():
    """システムログ取得（<userData>/logs および従来の .chainlit/app.log を統合）"""
    try:
        import os
        import itertools
        import io
        log_dir = os.getenv('LOG_DIR') or ''
        files = []
        if log_dir and os.path.isdir(log_dir):
            for name in [
                'main.log',
                'chainlit.out.log', 'chainlit.err.log',
                'electron-api.out.log', 'electron-api.err.log'
            ]:
                p = os.path.join(log_dir, name)
                if os.path.exists(p):
                    files.append(p)
        legacy = os.path.join('.chainlit', 'app.log')
        if os.path.exists(legacy):
            files.append(legacy)
        logs = []
        def tail_lines(path, n=100):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.readlines()[-n:]
            except Exception:
                return []
        for fpath in files:
            lst = tail_lines(fpath, 50)
            if lst:
                logs.append(f"===== {os.path.basename(fpath)} =====\n")
                logs.extend(lst)
                if not lst[-1].endswith('
'):
                    logs.append('
')
        # 何もなければ空配列
        return {"status": "success", "data": {"logs": logs}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ファイルエクスポート・インポートエンドポイント
@app.post("/api/files/export")
async def export_data(request: Dict[str, Any]):
    """データエクスポート"""
    try:
        data = request.get("data")
        filename = request.get("filename", "export.json")
        
        export_path = f"exports/{filename}"
        os.makedirs("exports", exist_ok=True)
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success", 
            "data": {"export_path": export_path, "filename": filename}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def run_electron_api():
    """Electron用APIサーバーを起動"""
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("ELECTRON_API_HOST", "127.0.0.1"),
        port=int(os.getenv("ELECTRON_API_PORT", "8001")),
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    run_electron_api()

# ====== System utilities (export/cleanup/reset/test key) ======

class TestOpenAIKeyRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None


## (duplicate removed) older test-openai-key endpoint deleted
