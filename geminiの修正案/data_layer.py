# data_layer.py (辞書を返す最終手段版)

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any  # ★★★ Any を追加 ★★★

import aiosqlite

from chainlit.data import BaseDataLayer
from chainlit.element import ElementDict
from chainlit.step import StepDict
from chainlit.types import Pagination, ThreadDict, ThreadFilter
from chainlit.user import User


class SQLiteDataLayer(BaseDataLayer):
    def __init__(self, db_path: str = ".chainlit/chainlit.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # テーブル作成部分は変更なし
        cursor.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, identifier TEXT NOT NULL UNIQUE, metadata TEXT, created_at TIMESTAMP)")
        cursor.execute("CREATE TABLE IF NOT EXISTS threads (id TEXT PRIMARY KEY, name TEXT, user_id TEXT, user_identifier TEXT, tags TEXT, metadata TEXT, created_at TIMESTAMP, updated_at TIMESTAMP)")
        cursor.execute("CREATE TABLE IF NOT EXISTS steps (id TEXT PRIMARY KEY, thread_id TEXT, name TEXT, type TEXT, generation TEXT, input TEXT, output TEXT, metadata TEXT, parent_id TEXT, start_time TIMESTAMP, end_time TIMESTAMP, created_at TIMESTAMP, FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE)")
        cursor.execute("CREATE TABLE IF NOT EXISTS feedbacks (id TEXT PRIMARY KEY, for_id TEXT, value INTEGER, comment TEXT, created_at TIMESTAMP)")
        cursor.execute("CREATE TABLE IF NOT EXISTS elements (id TEXT PRIMARY KEY, thread_id TEXT, for_id TEXT, type TEXT, name TEXT, display TEXT, mime TEXT, path TEXT, url TEXT, content TEXT, created_at TIMESTAMP, FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE)")
        conn.commit()
        conn.close()

    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # ★★★ 最終修正点: get_user と create_user が辞書を返すように変更 ★★★
    
    # 戻り値の型ヒントを Optional[Dict] に変更
    async def get_user(self, identifier: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE identifier = ?", (identifier,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    # Userオブジェクトではなく、単純な辞書として返す
                    return {
                        "id": row["id"],
                        "identifier": row["identifier"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "createdAt": row["created_at"],
                    }
        return None

    # 戻り値の型ヒントを Dict に変更
    async def create_user(self, user: User) -> Dict[str, Any]:
        new_id = str(uuid.uuid4())
        new_createdAt = datetime.now(timezone.utc).isoformat()
        
        user_dict = {
            "id": new_id,
            "identifier": user.identifier,
            "metadata": user.metadata,
            "createdAt": new_createdAt
        }

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO users (id, identifier, metadata, created_at) VALUES (?, ?, ?, ?)",
                (user_dict["id"], user_dict["identifier"], json.dumps(user_dict["metadata"]), user_dict["createdAt"]),
            )
            await db.commit()
        
        # Userオブジェクトではなく、作成した辞書を返す
        return user_dict
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★


    # --- 以下、他の関数は変更なし ---
    # (省略)
    async def list_threads(self, pagination: Pagination, filters: ThreadFilter) -> Pagination:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            where_clauses, params = [], []
            if filters.userId:
                where_clauses.append("user_id = ?")
                params.append(filters.userId)
            if filters.search:
                where_clauses.append("name LIKE ?")
                params.append(f"%{filters.search}%")
            where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            cursor = await db.execute(f"SELECT COUNT(*) as count FROM threads{where_clause}", params)
            total = (await cursor.fetchone())['count']
            limit = pagination.first or 20
            offset = int(pagination.cursor) if pagination.cursor else 0
            cursor = await db.execute(f"SELECT * FROM threads{where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?", params + [limit, offset])
            rows = await cursor.fetchall()
            threads = [dict(row) for row in rows]
            for thread in threads:
                thread["tags"] = json.loads(thread.get("tags") or '[]')
                thread["metadata"] = json.loads(thread.get("metadata") or '{}')
            has_next_page = (offset + len(threads)) < total
            end_cursor = str(offset + len(threads)) if has_next_page else None
            return Pagination(data=threads, pageInfo={"hasNextPage": has_next_page, "startCursor": str(offset) if threads else None, "endCursor": end_cursor})
    async def create_thread(self, thread: ThreadDict) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO threads (id, name, user_id, user_identifier, tags, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (thread["id"], thread.get("name"), thread.get("userId"), thread.get("userIdentifier"), json.dumps(thread.get("tags")), json.dumps(thread.get("metadata")), thread["createdAt"]))
            await db.commit()
    async def get_thread(self, thread_id: str) -> Optional[ThreadDict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            row = await (await db.execute("SELECT * FROM threads WHERE id = ?", (thread_id,))).fetchone()
            if row:
                steps = await self.get_steps(thread_id=thread_id)
                thread_data = dict(row); thread_data.update({"tags": json.loads(row.get("tags") or '[]'), "metadata": json.loads(row.get("metadata") or '{}'), "steps": steps})
                return thread_data
        return None
    async def get_steps(self, thread_id: str) -> List[StepDict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            rows = await (await db.execute("SELECT * FROM steps WHERE thread_id = ? ORDER BY created_at ASC", (thread_id,))).fetchall()
            return [dict(row, metadata=json.loads(row.get("metadata") or '{}')) for row in rows]
    async def create_step(self, step: StepDict) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO steps (id, thread_id, name, type, generation, input, output, metadata, parent_id, start_time, end_time, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (step.get("id"), step.get("threadId"), step.get("name"), step.get("type"), step.get("generation"), step.get("input"), step.get("output"), json.dumps(step.get("metadata", {})), step.get("parentId"), step.get("startTime"), step.get("endTime"), step.get("createdAt")))
            await db.commit()
    async def update_thread(self, thread_id: str, name: Optional[str] = None, user_id: Optional[str] = None, metadata: Optional[Dict] = None, tags: Optional[List[str]] = None) -> None: pass
    async def delete_thread(self, thread_id: str) -> None: pass
    async def get_thread_author(self, thread_id: str) -> str: return ""
    async def update_step(self, step: StepDict) -> None: pass
    async def delete_step(self, step_id: str) -> None: pass
    async def create_element(self, element: ElementDict) -> None: pass
    async def get_element(self, element_id: str) -> Optional[ElementDict]: return None
    async def delete_element(self, element_id: str) -> None: pass
    async def build_debug_url(self, thread_id: str) -> str: return f"local_db/thread/{thread_id}"
    async def upsert_feedback(self, feedback: Dict) -> str: return ""
    async def delete_feedback(self, feedback_id: str) -> None: pass