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
from datetime import datetime

# 既存ハンドラーをインポート
try:
    from handlers.persona_handler import persona_handler_instance
    from handlers.analytics_handler import analytics_handler_instance  
    from utils.vector_store_handler import vector_store_handler
    from data_layer import SQLiteDataLayer
    from utils.logger import app_logger
except ImportError as e:
    print(f"Warning: Some handlers not available: {e}")
    # 開発時のフォールバック
    persona_handler_instance = None
    analytics_handler_instance = None
    vector_store_handler = None
    SQLiteDataLayer = None
    app_logger = None

app = FastAPI(
    title="Chainlit Electron API",
    description="ElectronアプリケーションのAPI管理機能",
    version="1.0.0"
)

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
    """システム状態情報を取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 基本統計情報
        cursor.execute("SELECT COUNT(*) as count FROM threads")
        thread_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM personas")
        persona_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM user_vector_stores")
        vector_store_count = cursor.fetchone()['count']
        
        conn.close()
        
        return {
            "status": "success",
            "data": {
                "threads": thread_count,
                "personas": persona_count,
                "vector_stores": vector_store_count,
                "database_path": ".chainlit/chainlit.db",
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

# ベクトルストア管理エンドポイント
@app.get("/api/vectorstores")
async def list_vector_stores():
    """ベクトルストア一覧取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, vector_store_id, created_at, updated_at
            FROM user_vector_stores
            ORDER BY created_at DESC
        """)
        vector_stores = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"status": "success", "data": vector_stores}
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