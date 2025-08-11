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
from chainlit.data.utils import queue_until_user_message
import aiosqlite
import uuid


class SQLiteDataLayer(BaseDataLayer):
    """
    SQLiteを使用したカスタムデータレイヤー
    チャット履歴を永続化するために必要
    """
    
    def __init__(self, db_path: str = ".chainlit/chainlit.db"):
        """データベースを初期化"""
        self.db_path = db_path
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
        return User(identifier=identifier)
    
    async def create_user(self, user: User) -> Optional[User]:
        """ユーザーを作成"""
        return user
    
    async def create_thread(
        self,
        thread: ThreadDict,
    ) -> Optional[ThreadDict]:
        """新しいスレッドを作成"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO threads (id, name, user_id, user_identifier, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                thread.get("id"),
                thread.get("name"),
                thread.get("user_id"),
                thread.get("user_identifier"),
                json.dumps(thread.get("tags", [])),
                json.dumps(thread.get("metadata", {}))
            ))
            await db.commit()
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
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM threads WHERE id = ?", (thread_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "user_id": row["user_id"],
                    "user_identifier": row["user_identifier"],
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "createdAt": row["created_at"],
                    "steps": []  # ステップは別途取得
                }
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
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # フィルタを構築
            where_clauses = []
            params = []
            
            if filters.user_id:
                where_clauses.append("user_id = ?")
                params.append(filters.user_id)
            
            where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            # 総数を取得
            cursor = await db.execute(
                f"SELECT COUNT(*) as count FROM threads{where_clause}", params
            )
            count_row = await cursor.fetchone()
            total = count_row["count"]
            
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
                    "user_identifier": row["user_identifier"],
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "createdAt": row["created_at"],
                    "steps": []
                })
        
        return {
            "data": threads,
            "pageInfo": {
                "hasNextPage": offset + limit < total,
                "startCursor": offset,
                "endCursor": offset + len(threads)
            }
        }
    
    async def get_thread_author(self, thread_id: str) -> Optional[str]:
        """スレッドの作成者を取得"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_identifier FROM threads WHERE id = ?", (thread_id,)
            )
            row = await cursor.fetchone()
            return row["user_identifier"] if row else None
    
    @queue_until_user_message
    async def create_step(self, step: StepDict) -> None:
        """ステップを作成"""
        async with aiosqlite.connect(self.db_path) as db:
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
    
    @queue_until_user_message
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
    
    async def delete_element(self, element_id: str) -> None:
        """エレメントを削除"""
        async with aiosqlite.connect(self.db_path) as db:
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


# データレイヤーを設定
import chainlit.data as cl_data
cl_data._data_layer = SQLiteDataLayer()
