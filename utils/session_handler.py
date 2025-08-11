"""
セッション管理モジュール
- SQLite3データベースの管理
- セッション情報の永続化
- メッセージ履歴の保存
"""

import sqlite3
import aiosqlite
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import asyncio
import os


class SessionHandler:
    """セッション管理クラス"""
    
    def __init__(self, db_path: str = None):
        """初期化"""
        if db_path is None:
            db_path = os.getenv("DB_PATH", "chat_history.db")
        self.db_path = db_path
        # 同期的にデータベースを初期化
        self._init_db_sync()
    
    def _init_db_sync(self):
        """同期的にデータベースを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # chat_sessions テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                chat_type TEXT DEFAULT 'responses',
                model TEXT,
                system_prompt TEXT,
                thread_or_response_id TEXT,
                session_vs_id TEXT,
                use_company_vs BOOLEAN DEFAULT 0,
                use_personal_vs BOOLEAN DEFAULT 0,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # chat_messages テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                message_json TEXT,
                token_usage TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            )
        """)
        
        # personas テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                model TEXT,
                system_prompt TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # インデックスの作成
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_created_at 
            ON chat_sessions(created_at DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session_id 
            ON chat_messages(session_id)
        """)
        
        conn.commit()
        conn.close()
    
    async def init_db(self):
        """非同期でデータベースを初期化（互換性のため残す）"""
        # すでに同期的に初期化済みなので何もしない
        pass
    
    # === セッション管理 ===
    
    async def create_session(
        self,
        title: str = None,
        chat_type: str = "responses",
        model: str = "gpt-4o-mini",
        system_prompt: str = "",
        tags: List[str] = None
    ) -> str:
        """新しいセッションを作成"""
        session_id = str(uuid.uuid4())
        
        if title is None:
            title = f"New Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        tags_str = ",".join(tags) if tags else ""
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO chat_sessions 
                (id, title, chat_type, model, system_prompt, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, title, chat_type, model, system_prompt, tags_str))
            await db.commit()
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """セッション情報を取得"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM chat_sessions WHERE id = ?
            """, (session_id,))
            row = await cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    async def update_session(
        self,
        session_id: str,
        title: str = None,
        thread_or_response_id: str = None,
        session_vs_id: str = None,
        use_company_vs: bool = None,
        use_personal_vs: bool = None,
        tags: List[str] = None,
        model: str = None,
        system_prompt: str = None
    ) -> bool:
        """セッション情報を更新"""
        updates = []
        values = []
        
        if title is not None:
            updates.append("title = ?")
            values.append(title)
        
        if thread_or_response_id is not None:
            updates.append("thread_or_response_id = ?")
            values.append(thread_or_response_id)
        
        if session_vs_id is not None:
            updates.append("session_vs_id = ?")
            values.append(session_vs_id)
        
        if use_company_vs is not None:
            updates.append("use_company_vs = ?")
            values.append(int(use_company_vs))
        
        if use_personal_vs is not None:
            updates.append("use_personal_vs = ?")
            values.append(int(use_personal_vs))
        
        if tags is not None:
            updates.append("tags = ?")
            values.append(",".join(tags))
        
        if model is not None:
            updates.append("model = ?")
            values.append(model)
        
        if system_prompt is not None:
            updates.append("system_prompt = ?")
            values.append(system_prompt)
        
        if not updates:
            return True
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(session_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"""
                UPDATE chat_sessions 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            await db.commit()
        
        return True
    
    async def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
        search: str = None
    ) -> List[Dict]:
        """セッション一覧を取得"""
        query = """
            SELECT id, title, chat_type, model, tags, created_at, updated_at
            FROM chat_sessions
        """
        params = []
        
        if search:
            query += " WHERE title LIKE ? OR tags LIKE ?"
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
        
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    async def delete_session(self, session_id: str) -> bool:
        """セッションを削除"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM chat_sessions WHERE id = ?
            """, (session_id,))
            await db.commit()
        
        return True
    
    # === メッセージ管理 ===
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        message_json: Dict = None,
        token_usage: Dict = None
    ) -> int:
        """メッセージを追加"""
        message_json_str = json.dumps(message_json) if message_json else None
        token_usage_str = json.dumps(token_usage) if token_usage else None
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO chat_messages 
                (session_id, role, content, message_json, token_usage)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, role, content, message_json_str, token_usage_str))
            await db.commit()
            
            return cursor.lastrowid
    
    async def get_messages(
        self,
        session_id: str,
        limit: int = None,
        offset: int = 0
    ) -> List[Dict]:
        """セッションのメッセージを取得"""
        query = """
            SELECT * FROM chat_messages
            WHERE session_id = ?
            ORDER BY created_at ASC
        """
        params = [session_id]
        
        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            messages = []
            for row in rows:
                msg = dict(row)
                # JSONフィールドをパース
                if msg.get('message_json'):
                    try:
                        msg['message_json'] = json.loads(msg['message_json'])
                    except:
                        pass
                if msg.get('token_usage'):
                    try:
                        msg['token_usage'] = json.loads(msg['token_usage'])
                    except:
                        pass
                messages.append(msg)
            
            return messages
    
    async def get_message_count(self, session_id: str) -> int:
        """セッションのメッセージ数を取得"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM chat_messages WHERE session_id = ?
            """, (session_id,))
            count = await cursor.fetchone()
            return count[0] if count else 0
    
    # === ペルソナ管理 ===
    
    async def create_persona(
        self,
        name: str,
        model: str = "gpt-4o-mini",
        system_prompt: str = "",
        description: str = ""
    ) -> int:
        """新しいペルソナを作成"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO personas (name, model, system_prompt, description)
                VALUES (?, ?, ?, ?)
            """, (name, model, system_prompt, description))
            await db.commit()
            
            return cursor.lastrowid
    
    async def get_persona(self, persona_id: int = None, name: str = None) -> Optional[Dict]:
        """ペルソナを取得"""
        if persona_id:
            query = "SELECT * FROM personas WHERE id = ?"
            param = persona_id
        elif name:
            query = "SELECT * FROM personas WHERE name = ?"
            param = name
        else:
            return None
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, (param,))
            row = await cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    async def list_personas(self) -> List[Dict]:
        """ペルソナ一覧を取得"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM personas ORDER BY name ASC
            """)
            rows = await cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    async def update_persona(
        self,
        persona_id: int,
        name: str = None,
        model: str = None,
        system_prompt: str = None,
        description: str = None
    ) -> bool:
        """ペルソナを更新"""
        updates = []
        values = []
        
        if name is not None:
            updates.append("name = ?")
            values.append(name)
        
        if model is not None:
            updates.append("model = ?")
            values.append(model)
        
        if system_prompt is not None:
            updates.append("system_prompt = ?")
            values.append(system_prompt)
        
        if description is not None:
            updates.append("description = ?")
            values.append(description)
        
        if not updates:
            return True
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(persona_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"""
                UPDATE personas 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            await db.commit()
        
        return True
    
    async def delete_persona(self, persona_id: int) -> bool:
        """ペルソナを削除"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM personas WHERE id = ?
            """, (persona_id,))
            await db.commit()
        
        return True
    
    # === 統計情報 ===
    
    async def get_statistics(self) -> Dict:
        """データベースの統計情報を取得"""
        async with aiosqlite.connect(self.db_path) as db:
            # セッション数
            cursor = await db.execute("SELECT COUNT(*) FROM chat_sessions")
            session_count = (await cursor.fetchone())[0]
            
            # メッセージ数
            cursor = await db.execute("SELECT COUNT(*) FROM chat_messages")
            message_count = (await cursor.fetchone())[0]
            
            # ペルソナ数
            cursor = await db.execute("SELECT COUNT(*) FROM personas")
            persona_count = (await cursor.fetchone())[0]
            
            # 最近のセッション
            cursor = await db.execute("""
                SELECT created_at FROM chat_sessions
                ORDER BY created_at DESC LIMIT 1
            """)
            last_session = await cursor.fetchone()
            last_session_date = last_session[0] if last_session else None
            
            return {
                "session_count": session_count,
                "message_count": message_count,
                "persona_count": persona_count,
                "last_session_date": last_session_date,
                "db_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            }


# グローバルインスタンス
session_handler = SessionHandler()
