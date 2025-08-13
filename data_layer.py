"""
カスタムSQLiteデータレイヤーの実装
Chainlitのデータ永続化機能を有効にする
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import chainlit as cl
from chainlit.data import BaseDataLayer
from chainlit.types import ThreadDict, Pagination, ThreadFilter
from chainlit.element import ElementDict
from chainlit.step import StepDict
from chainlit.user import User
import aiosqlite
import uuid
import asyncio


class SQLitePaginatedResponse:
    """Paginationレスポンスラッパー"""
    def __init__(self, data: List, page_info: Dict):
        self.data = data
        self.pageInfo = page_info
    
    def to_dict(self):
        return {
            "data": self.data,
            "pageInfo": self.pageInfo
        }


class SQLiteDataLayer(BaseDataLayer):
    """
    SQLiteを使用したカスタムデータレイヤー
    チャット履歴を永続化するために必要
    """
    
    def __init__(self, db_path: str = ".chainlit/chainlit.db"):
        """データベースを初期化"""
        self.db_path = db_path
        self._thread_creation_lock = asyncio.Lock()  # スレッド作成の競合状態を防ぐ
        
        # ディレクトリを作成
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # 同期的にテーブルを作成
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # スレッドテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                name TEXT,
                user_id TEXT,
                user_identifier TEXT,
                tags TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ステップテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                name TEXT,
                type TEXT,
                generation TEXT,
                input TEXT,
                output TEXT,
                metadata TEXT,
                parent_id TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES threads(id)
            )
        """)
        
        # フィードバックテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id TEXT PRIMARY KEY,
                for_id TEXT,
                value INTEGER,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # エレメントテーブル  
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS elements (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                for_id TEXT,
                type TEXT,
                name TEXT,
                display TEXT,
                mime TEXT,
                path TEXT,
                url TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES threads(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def get_user(self, identifier: str) -> Optional[User]:
        """ユーザー情報を取得"""
        user = User(identifier=identifier)
        # idプロパティを追加
        user.id = identifier
        return user
    
    async def create_user(self, user: User) -> Optional[User]:
        """ユーザーを作成"""
        # idプロパティを追加
        user.id = user.identifier
        return user
    
    async def create_thread(
        self,
        thread: ThreadDict,
    ) -> Optional[ThreadDict]:
        """新しいスレッドを作成"""
        print(f"🔧 SQLite: create_threadが呼ばれました - ID: {thread.get('id')}")
        print(f"   Thread data: {thread}")
        
        async with self._thread_creation_lock:  # ロックを使用して競合状態を防ぐ
            # 既にスレッドが存在するかチェック
            existing = await self.get_thread(thread.get("id"))
            if existing:
                print(f"   ℹ️ スレッドは既に存在します: {thread.get('id')}")
                return existing
            
            async with aiosqlite.connect(self.db_path) as db:
                # user_idを取得（userIdまたはuser_idから）
                user_id_value = thread.get("userId") or thread.get("user_id")
                try:
                    await db.execute("""
                        INSERT INTO threads (id, name, user_id, user_identifier, tags, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        thread.get("id"),
                        thread.get("name"),
                        user_id_value,
                        thread.get("user_identifier"),
                        json.dumps(thread.get("tags", [])),
                        json.dumps(thread.get("metadata", {}))
                    ))
                    await db.commit()
                    print(f"   ✅ スレッドをSQLiteに保存しました")
                except Exception as e:
                    if "UNIQUE constraint failed" in str(e):
                        print(f"   ℹ️ スレッドは既に存在します（重複エラー）: {thread.get('id')}")
                        return await self.get_thread(thread.get("id"))
                    else:
                        print(f"   ❌ スレッド作成エラー: {e}")
                        raise
        return thread
    
    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """スレッドを更新"""
        async with aiosqlite.connect(self.db_path) as db:
            updates = []
            values = []
            
            if name is not None:
                updates.append("name = ?")
                values.append(name)
            if user_id is not None:
                updates.append("user_id = ?")
                values.append(user_id)
            if metadata is not None:
                updates.append("metadata = ?")
                values.append(json.dumps(metadata))
            if tags is not None:
                updates.append("tags = ?")
                values.append(json.dumps(tags))
            
            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                values.append(thread_id)
                
                query = f"UPDATE threads SET {', '.join(updates)} WHERE id = ?"
                await db.execute(query, values)
                await db.commit()
    
    async def get_thread(self, thread_id: str) -> Optional[ThreadDict]:
        """スレッドを取得"""
        print(f"🔧 SQLite: get_threadが呼ばれました - ID: {thread_id}")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM threads WHERE id = ?", (thread_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                # ステップを取得
                step_cursor = await db.execute(
                    "SELECT * FROM steps WHERE thread_id = ? ORDER BY created_at ASC",
                    (thread_id,)
                )
                steps = []
                for step_row in await step_cursor.fetchall():
                    step_dict = {
                        "id": step_row["id"],
                        "threadId": step_row["thread_id"],
                        "name": step_row["name"],
                        "type": step_row["type"],
                        "generation": step_row["generation"] if step_row["generation"] else None,
                        "input": step_row["input"] if step_row["input"] else "",
                        "output": step_row["output"] if step_row["output"] else "",
                        "metadata": json.loads(step_row["metadata"]) if step_row["metadata"] else {},
                        "parentId": step_row["parent_id"],
                        "startTime": step_row["start_time"],
                        "endTime": step_row["end_time"],
                        "createdAt": step_row["created_at"],
                        "start": step_row["start_time"],
                        "end": step_row["end_time"]
                    }
                    steps.append(step_dict)
                
                thread_dict = {
                    "id": row["id"],
                    "name": row["name"],
                    "user_id": row["user_id"],
                    "userId": row["user_id"],  # Chainlitが期待する形式
                    "userIdentifier": row["user_identifier"],  # 両方の形式で提供
                    "user_identifier": row["user_identifier"],
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "createdAt": row["created_at"],
                    "steps": steps  # ステップを含める
                }
                print(f"   ✅ スレッドを取得しました: ステップ数={len(steps)}")
                return thread_dict
            else:
                print(f"   ❌ スレッドが見つかりません: {thread_id}")
        return None
    
    async def delete_thread(self, thread_id: str) -> None:
        """スレッドを削除"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
            await db.commit()
    
    async def list_threads(
        self,
        pagination: Pagination,
        filters: ThreadFilter,
    ) -> Pagination:
        """スレッド一覧を取得"""
        print(f"🔧 SQLite: list_threadsが呼ばれました")
        print(f"   Filters: userId={getattr(filters, 'userId', None)}")
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # フィルタを構築
            where_clauses = []
            params = []
            
            if hasattr(filters, 'userId') and filters.userId:
                where_clauses.append("user_id = ?")
                params.append(filters.userId)
            
            where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            # 総数を取得
            cursor = await db.execute(
                f"SELECT COUNT(*) as count FROM threads{where_clause}", params
            )
            count_row = await cursor.fetchone()
            total = count_row["count"]
            print(f"   スレッド総数: {total}")
            
            # スレッドを取得
            limit = pagination.first or 20
            offset = pagination.cursor or 0
            
            cursor = await db.execute(
                f"""
                SELECT * FROM threads{where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset]
            )
            
            rows = await cursor.fetchall()
            threads = []
            
            for row in rows:
                threads.append({
                    "id": row["id"],
                    "name": row["name"],
                    "user_id": row["user_id"],
                    "userId": row["user_id"],  # Chainlitが期待する形式
                    "user_identifier": row["user_identifier"],
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "createdAt": row["created_at"],
                    "steps": []
                })
            print(f"   取得したスレッド数: {len(threads)}")
        
        return SQLitePaginatedResponse(
            data=threads,
            page_info={
                "hasNextPage": offset + limit < total,
                "startCursor": offset,
                "endCursor": offset + len(threads)
            }
        )
    
    async def get_thread_author(self, thread_id: str) -> Optional[str]:
        """スレッドの作成者を取得"""
        print(f"🔧 SQLite: get_thread_authorが呼ばれました - ID: {thread_id}")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_identifier FROM threads WHERE id = ?", (thread_id,)
            )
            row = await cursor.fetchone()
            author = row["user_identifier"] if row else None
            print(f"   作成者: {author}")
            return author
    
    async def get_thread_steps(self, thread_id: str) -> List[StepDict]:
        """スレッドのステップを取得"""
        print(f"🔧 SQLite: get_thread_stepsが呼ばれました - ID: {thread_id}")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM steps WHERE thread_id = ? ORDER BY created_at ASC",
                (thread_id,)
            )
            steps = []
            for row in await cursor.fetchall():
                step_dict = {
                    "id": row["id"],
                    "threadId": row["thread_id"],
                    "name": row["name"],
                    "type": row["type"],
                    "generation": row["generation"] if row["generation"] else None,
                    "input": row["input"] if row["input"] else "",
                    "output": row["output"] if row["output"] else "",
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "parentId": row["parent_id"],
                    "startTime": row["start_time"],
                    "endTime": row["end_time"],
                    "createdAt": row["created_at"],
                    "start": row["start_time"],
                    "end": row["end_time"]
                }
                steps.append(step_dict)
            print(f"   ✅ {len(steps)}個のステップを取得しました")
            return steps
    
    async def create_step(self, step: StepDict) -> None:
        """ステップを作成"""
        print(f"🔧 SQLite: create_stepが呼ばれました - ID: {step.get('id')}, ThreadID: {step.get('threadId')}, Type: {step.get('type')}")
        
        # ユーザーメッセージの場合のみスレッドを自動作成
        thread_id = step.get("threadId")
        if thread_id and step.get("type") == "user_message":
            # スレッドが存在しない場合は作成
            existing_thread = await self.get_thread(thread_id)
            if not existing_thread:
                print(f"   ⚠️ スレッドが存在しません。自動作成します: {thread_id}")
                
                # 現在のユーザー情報を取得
                current_user = None
                try:
                    current_user = cl.user_session.get("user")
                except:
                    pass
                
                user_id = "anonymous"
                if current_user and hasattr(current_user, 'identifier'):
                    user_id = current_user.identifier
                
                thread = {
                    "id": thread_id,
                    "name": f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    "user_id": user_id,
                    "userId": user_id,
                    "user_identifier": user_id,
                    "tags": [],
                    "metadata": {},
                    "createdAt": datetime.now().isoformat()
                }
                
                await self.create_thread(thread)
        
        # ステップを保存
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO steps 
                    (id, thread_id, name, type, generation, input, output, metadata, 
                     parent_id, start_time, end_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    step.get("id"),
                    step.get("threadId"),
                    step.get("name"),
                    step.get("type"),
                    step.get("generation"),
                    step.get("input"),
                    step.get("output"),
                    json.dumps(step.get("metadata", {})),
                    step.get("parentId"),
                    step.get("startTime"),
                    step.get("endTime")
                ))
                await db.commit()
                print(f"   ✅ ステップをSQLiteに保存しました")
            except Exception as e:
                print(f"   ❌ ステップ保存エラー: {e}")
    
    async def update_step(self, step: StepDict) -> None:
        """ステップを更新"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE steps 
                SET name = ?, type = ?, generation = ?, input = ?, output = ?, 
                    metadata = ?, parent_id = ?, start_time = ?, end_time = ?
                WHERE id = ?
            """, (
                step.get("name"),
                step.get("type"),
                step.get("generation"),
                step.get("input"),
                step.get("output"),
                json.dumps(step.get("metadata", {})),
                step.get("parentId"),
                step.get("startTime"),
                step.get("endTime"),
                step.get("id")
            ))
            await db.commit()
    
    async def delete_step(self, step_id: str) -> None:
        """ステップを削除"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM steps WHERE id = ?", (step_id,))
            await db.commit()
    
    async def create_element(self, element: ElementDict) -> None:
        """エレメントを作成"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO elements 
                (id, thread_id, for_id, type, name, display, mime, path, url, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                element.get("id"),
                element.get("threadId"),
                element.get("forId"),
                element.get("type"),
                element.get("name"),
                element.get("display"),
                element.get("mime"),
                element.get("path"),
                element.get("url"),
                element.get("content")
            ))
            await db.commit()
    
    async def get_element(self, element_id: str, thread_id: str = None) -> Optional[ElementDict]:
        """エレメントを取得"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if thread_id:
                cursor = await db.execute(
                    "SELECT * FROM elements WHERE id = ? AND thread_id = ?",
                    (element_id, thread_id)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM elements WHERE id = ?",
                    (element_id,)
                )
            row = await cursor.fetchone()
            
            if row:
                return {
                    "id": row["id"],
                    "threadId": row["thread_id"],
                    "forId": row["for_id"],
                    "type": row["type"],
                    "name": row["name"],
                    "display": row["display"],
                    "mime": row["mime"],
                    "path": row["path"],
                    "url": row["url"],
                    "content": row["content"]
                }
        return None
    
    async def delete_element(self, element_id: str, thread_id: str = None) -> None:
        """エレメントを削除"""
        async with aiosqlite.connect(self.db_path) as db:
            if thread_id:
                await db.execute(
                    "DELETE FROM elements WHERE id = ? AND thread_id = ?",
                    (element_id, thread_id)
                )
            else:
                await db.execute("DELETE FROM elements WHERE id = ?", (element_id,))
            await db.commit()
    
    async def upsert_feedback(
        self,
        feedback: Dict,
    ) -> str:
        """フィードバックを作成または更新"""
        feedback_id = feedback.get("id") or str(uuid.uuid4())
        
        async with aiosqlite.connect(self.db_path) as db:
            # 既存のフィードバックがあるか確認
            cursor = await db.execute(
                "SELECT id FROM feedbacks WHERE for_id = ?", 
                (feedback.get("forId"),)
            )
            existing = await cursor.fetchone()
            
            if existing:
                # 更新
                await db.execute("""
                    UPDATE feedbacks 
                    SET value = ?, comment = ?
                    WHERE for_id = ?
                """, (
                    feedback.get("value"),
                    feedback.get("comment"),
                    feedback.get("forId")
                ))
            else:
                # 新規作成
                await db.execute("""
                    INSERT INTO feedbacks (id, for_id, value, comment)
                    VALUES (?, ?, ?, ?)
                """, (
                    feedback_id,
                    feedback.get("forId"),
                    feedback.get("value"),
                    feedback.get("comment")
                ))
            
            await db.commit()
        
        return feedback_id
    
    async def delete_feedback(self, feedback_id: str) -> None:
        """フィードバックを削除"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM feedbacks WHERE id = ?", (feedback_id,))
            await db.commit()
    
    async def build_debug_url(self) -> str:
        """デバッグURLを構築"""
        return "http://localhost:8000/debug"


# データレイヤーを設定
import chainlit.data as cl_data
cl_data._data_layer = SQLiteDataLayer()
