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
    # analytics_handler_instance は未定義のため読み込みをスキップ
    # from handlers.analytics_handler import analytics_handler_instance
    pass
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
        
        # スレッド統計
        cursor.execute("""
            SELECT COUNT(*) as thread_count, 
                   DATE(created_at) as date
            FROM threads 
            WHERE user_id = ? OR user_identifier = ?
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        """, (user_id, user_id))
        thread_stats = [dict(row) for row in cursor.fetchall()]
        
        # メッセージ統計
        cursor.execute("""
            SELECT COUNT(*) as message_count,
                   DATE(s.created_at) as date
            FROM steps s
            JOIN threads t ON s.thread_id = t.id
            WHERE (t.user_id = ? OR t.user_identifier = ?) AND s.type = 'assistant_message'
            GROUP BY DATE(s.created_at)
            ORDER BY date DESC
            LIMIT 30
        """, (user_id, user_id))
        message_stats = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "status": "success", 
            "data": {
                "thread_statistics": thread_stats,
                "message_statistics": message_stats,
                "generated_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/usage/{user_id}")
async def get_usage_analytics(user_id: str, period: str = "7d"):
    """使用状況分析取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 期間に応じたクエリ調整
        days = 7 if period == "7d" else 30 if period == "30d" else 1
        
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT t.id) as total_threads,
                COUNT(s.id) as total_messages,
                AVG(LENGTH(s.output)) as avg_message_length
            FROM threads t
            LEFT JOIN steps s ON t.id = s.thread_id
            WHERE (t.user_id = ? OR t.user_identifier = ?)
              AND t.created_at >= datetime('now', '-{} days')
        """.format(days), (user_id, user_id))
        
        usage_data = dict(cursor.fetchone())
        conn.close()
        
        return {"status": "success", "data": usage_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ログ管理エンドポイント
@app.get("/api/system/logs")
async def get_system_logs():
    """システムログ取得"""
    try:
        log_file = ".chainlit/app.log"
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()[-100:]  # 最新100行
            return {"status": "success", "data": {"logs": logs}}
        else:
            return {"status": "success", "data": {"logs": []}}
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
        host="127.0.0.1", 
        port=8001, 
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
