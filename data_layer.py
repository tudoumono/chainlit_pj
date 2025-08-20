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
                vector_store_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 既存のテーブルにカラムを追加（既存のDBのため）
        try:
            cursor.execute("ALTER TABLE threads ADD COLUMN vector_store_id TEXT")
        except sqlite3.OperationalError:
            pass  # カラムが既に存在する場合はスキップ
        
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
        
        # ユーザーベクトルストアテーブル（新規追加）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_vector_stores (
                user_id TEXT PRIMARY KEY,
                vector_store_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        # ペルソナテーブル（Phase 6で追加）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personas (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                system_prompt TEXT,
                model TEXT,
                temperature REAL,
                max_tokens INTEGER,
                description TEXT,
                tags TEXT,
                is_active BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # デフォルトペルソナの挿入（存在しない場合のみ）
        cursor.execute("""
            INSERT OR IGNORE INTO personas (id, name, system_prompt, model, temperature, description, is_active)
            VALUES 
            ('default', 'デフォルト', 'あなたは親切で役立つアシスタントです。', 'gpt-4o-mini', 0.7, '標準的なアシスタント', 1),
            ('professional', 'プロフェッショナル', 'あなたはビジネスプロフェッショナルのアシスタントです。丁寧で専門的な言葉遣いを心がけ、正確な情報を提供します。', 'gpt-4o', 0.5, 'ビジネス向けフォーマルなアシスタント', 0),
            ('creative', 'クリエイティブ', 'あなたは創造的で革新的なアイデアを生み出すクリエイティブアシスタントです。斬新な視点と想像力豊かな提案を心がけます。', 'gpt-4o', 0.9, '創造的なアイデア出しに特化', 0),
            ('technical', 'テクニカル', 'あなたは技術的な専門知識を持つアシスタントです。プログラミング、システム設計、技術的な問題解決に精通しています。', 'gpt-4o', 0.3, '技術的な質問に特化', 0),
            ('educator', '教育者', 'あなたは教育者として振る舞います。わかりやすく段階的に説明し、学習者の理解を深めることを目的とします。', 'gpt-4o-mini', 0.6, '教育・学習サポートに特化', 0)
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
                # 既存スレッドを返す（通常の動作）
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
                        # 重複エラーは正常・・・既存スレッドを返す
                        return await self.get_thread(thread.get("id"))
                    else:
                        print(f"   ❌ スレッド作成エラー: {e}")
                        raise
        return thread
    
    async def delete_thread(self, thread_id: str) -> None:
        """スレッドを削除（ベクトルストアも一緒に削除）"""
        print(f"🔧 SQLite: delete_threadが呼ばれました - Thread ID: {thread_id}")
        
        # まずベクトルストアIDを取得
        thread = await self.get_thread(thread_id)
        if thread and thread.get("vector_store_id"):
            vector_store_id = thread["vector_store_id"]
            print(f"   🗑️ ベクトルストアを削除: {vector_store_id}")
            
            # OpenAI側のベクトルストアを削除
            try:
                from utils.vector_store_handler import vector_store_handler
                await vector_store_handler.delete_vector_store(vector_store_id)
                print(f"   ✅ ベクトルストア削除完了: {vector_store_id}")
            except Exception as e:
                print(f"   ⚠️ ベクトルストア削除失敗: {e}")
                # エラーでも履歴削除は続行
        
        # データベースからスレッドを削除
        async with aiosqlite.connect(self.db_path) as db:
            # 関連するステップを削除
            await db.execute("DELETE FROM steps WHERE thread_id = ?", (thread_id,))
            # 関連するエレメントを削除
            await db.execute("DELETE FROM elements WHERE thread_id = ?", (thread_id,))
            # スレッド本体を削除
            await db.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
            await db.commit()
            print(f"   ✅ スレッドと関連データを削除しました")
    
    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        vector_store_id: Optional[str] = None,
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
            if vector_store_id is not None:
                updates.append("vector_store_id = ?")
                values.append(vector_store_id)
            
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
                # ステップを取得（作成日時とIDで並び替え）
                step_cursor = await db.execute(
                    "SELECT * FROM steps WHERE thread_id = ? ORDER BY created_at ASC, id ASC",
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
                    "vector_store_id": row["vector_store_id"],  # ベクトルストアIDを追加
                    "createdAt": row["created_at"],
                    "steps": steps  # ステップを含める
                }
                print(f"   ✅ スレッドを取得しました: ステップ数={len(steps)}")
                return thread_dict
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
                "SELECT * FROM steps WHERE thread_id = ? ORDER BY created_at ASC, id ASC",
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
        
        # システムメッセージの一時的なものを除外
        # 復元通知・復元完了メッセージ・ウェルカムメッセージは保存しない
        step_input = step.get("input", "")
        step_output = step.get("output", "")
        step_name = step.get("name", "")
        
        # 除外するメッセージのパターンを定義
        exclude_patterns = [
            # 復元関連
            "📂 過去の会話を復元中",
            "✅ 復元完了",
            "Avatar for Assistant",
            # ウェルカムメッセージ
            "🎯 AI Workspace へようこそ",
            "へようこそ！",
            "利用可能なコマンド",
            "APIキーが設定されていません",
            "データレイヤーの状態",
            "AIと会話を始めましょう！",
            "Version:",
            "現在の状態",
            # コマンド応答
            "📚 コマンド一覧",
            "📊 現在のセッションの統計",
            "📊 現在の設定",
            "🔧 Tools機能の設定",
            "✅ モデルを",
            "✅ システムプロンプトを",
            "✅ APIキーを設定しました",
            "✅ 新しい会話を開始しました",
            "✅ 接続成功",
            "✅ すべてのツールを",
            "❌ エラー:",
            "❌ 接続失敗",
            "❌ モデル名を",
            "❌ APIキーを",
            "❌ 不明な",
            "⚠️ APIキーが",
            "🔄 接続テスト中",
            # ツール関連
            "🔍 **Web検索中**",
            "📁 **ファイル検索中**",
            "📊 **ツール結果**"
        ]
        
        # 出力をチェック
        if isinstance(step_output, str):
            for pattern in exclude_patterns:
                if pattern in step_output:
                    print(f"   ℹ️ システム/ウェルカムメッセージのため保存をスキップ: {step_output[:50]}")
                    return
        
        # 入力をチェック
        if isinstance(step_input, str):
            for pattern in exclude_patterns:
                if pattern in step_input:
                    print(f"   ℹ️ システム/ウェルカムメッセージのため保存をスキップ: {step_input[:50]}")
                    return
        
        # 名前をチェック
        if isinstance(step_name, str):
            for pattern in exclude_patterns:
                if pattern in step_name:
                    print(f"   ℹ️ システム/ウェルカムメッセージのため保存をスキップ: {step_name[:50]}")
                    return
        
        # ユーザーメッセージの場合のみスレッドを自動作成
        thread_id = step.get("threadId")
        if thread_id and step.get("type") == "user_message":
            # スレッドが存在しない場合は作成
            existing_thread = await self.get_thread(thread_id)
            if not existing_thread:
                print(f"   ℹ️ 新規スレッドを自動作成: {thread_id}")
                
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
                # まず既存のステップがあるか確認
                cursor = await db.execute(
                    "SELECT id FROM steps WHERE id = ?",
                    (step.get("id"),)
                )
                existing_step = await cursor.fetchone()
                
                if existing_step:
                    # 既存の場合は更新
                    print(f"   ℹ️ ステップが既に存在します。更新します: {step.get('id')}")
                    await db.execute("""
                        UPDATE steps 
                        SET thread_id = ?, name = ?, type = ?, generation = ?, 
                            input = ?, output = ?, metadata = ?, parent_id = ?, 
                            start_time = ?, end_time = ?
                        WHERE id = ?
                    """, (
                        step.get("threadId"),
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
                else:
                    # 新規作成
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
    
    async def create_element(self, element) -> None:
        """エレメントを作成"""
        # elementがFileオブジェクトの場合は辞書に変換
        if hasattr(element, '__dict__'):
            element_dict = {
                "id": getattr(element, 'id', None),
                "threadId": getattr(element, 'thread_id', None),
                "forId": getattr(element, 'for_id', None),
                "type": getattr(element, 'type', 'file'),
                "name": getattr(element, 'name', None),
                "display": getattr(element, 'display', None),
                "mime": getattr(element, 'mime', None),
                "path": getattr(element, 'path', None),
                "url": getattr(element, 'url', None),
                "content": getattr(element, 'content', None)
            }
        else:
            element_dict = element
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO elements 
                (id, thread_id, for_id, type, name, display, mime, path, url, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                element_dict.get("id"),
                element_dict.get("threadId"),
                element_dict.get("forId"),
                element_dict.get("type"),
                element_dict.get("name"),
                element_dict.get("display"),
                element_dict.get("mime"),
                element_dict.get("path"),
                element_dict.get("url"),
                element_dict.get("content")
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
    
    # =============== ペルソナ関連のメソッド（Phase 6で追加） ===============
    
    async def get_persona(self, persona_id: str) -> Optional[Dict]:
        """ペルソナを取得"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM personas WHERE id = ?", (persona_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "system_prompt": row["system_prompt"],
                    "model": row["model"],
                    "temperature": row["temperature"],
                    "max_tokens": row["max_tokens"],
                    "description": row["description"],
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "is_active": row["is_active"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
        return None
    
    async def get_persona_by_name(self, name: str) -> Optional[Dict]:
        """名前からペルソナを取得"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM personas WHERE name = ?", (name,)
            )
            row = await cursor.fetchone()
            
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "system_prompt": row["system_prompt"],
                    "model": row["model"],
                    "temperature": row["temperature"],
                    "max_tokens": row["max_tokens"],
                    "description": row["description"],
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "is_active": row["is_active"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
        return None
    
    async def list_personas(self) -> List[Dict]:
        """全てのペルソナを取得"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM personas ORDER BY name ASC"
            )
            rows = await cursor.fetchall()
            
            personas = []
            for row in rows:
                personas.append({
                    "id": row["id"],
                    "name": row["name"],
                    "system_prompt": row["system_prompt"],
                    "model": row["model"],
                    "temperature": row["temperature"],
                    "max_tokens": row["max_tokens"],
                    "description": row["description"],
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "is_active": row["is_active"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })
            
            return personas
    
    async def get_active_persona(self) -> Optional[Dict]:
        """アクティブなペルソナを取得"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM personas WHERE is_active = 1 LIMIT 1"
            )
            row = await cursor.fetchone()
            
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "system_prompt": row["system_prompt"],
                    "model": row["model"],
                    "temperature": row["temperature"],
                    "max_tokens": row["max_tokens"],
                    "description": row["description"],
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "is_active": row["is_active"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
        return None
    
    async def create_persona(self, persona: Dict) -> str:
        """新しいペルソナを作成"""
        persona_id = persona.get("id") or str(uuid.uuid4())
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO personas 
                (id, name, system_prompt, model, temperature, max_tokens, description, tags, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                persona_id,
                persona.get("name"),
                persona.get("system_prompt"),
                persona.get("model", "gpt-4o-mini"),
                persona.get("temperature", 0.7),
                persona.get("max_tokens"),
                persona.get("description"),
                json.dumps(persona.get("tags", [])),
                persona.get("is_active", 0)
            ))
            await db.commit()
        
        return persona_id
    
    async def update_persona(self, persona_id: str, updates: Dict) -> None:
        """ペルソナを更新"""
        async with aiosqlite.connect(self.db_path) as db:
            update_fields = []
            values = []
            
            if "name" in updates:
                update_fields.append("name = ?")
                values.append(updates["name"])
            if "system_prompt" in updates:
                update_fields.append("system_prompt = ?")
                values.append(updates["system_prompt"])
            if "model" in updates:
                update_fields.append("model = ?")
                values.append(updates["model"])
            if "temperature" in updates:
                update_fields.append("temperature = ?")
                values.append(updates["temperature"])
            if "max_tokens" in updates:
                update_fields.append("max_tokens = ?")
                values.append(updates["max_tokens"])
            if "description" in updates:
                update_fields.append("description = ?")
                values.append(updates["description"])
            if "tags" in updates:
                update_fields.append("tags = ?")
                values.append(json.dumps(updates["tags"]))
            if "is_active" in updates:
                update_fields.append("is_active = ?")
                values.append(updates["is_active"])
            
            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                values.append(persona_id)
                
                query = f"UPDATE personas SET {', '.join(update_fields)} WHERE id = ?"
                await db.execute(query, values)
                await db.commit()
    
    async def set_active_persona(self, persona_id: str) -> None:
        """ペルソナをアクティブに設定"""
        async with aiosqlite.connect(self.db_path) as db:
            # 全てのペルソナを非アクティブにする
            await db.execute("UPDATE personas SET is_active = 0")
            # 指定のペルソナをアクティブにする
            await db.execute(
                "UPDATE personas SET is_active = 1 WHERE id = ?",
                (persona_id,)
            )
            await db.commit()
    
    async def delete_persona(self, persona_id: str) -> None:
        """ペルソナを削除"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM personas WHERE id = ?", (persona_id,))
            await db.commit()
    
    # =============== ユーザーベクトルストア関連のメソッド ===============
    
    async def get_user_vector_store_id(self, user_id: str) -> Optional[str]:
        """ユーザーのベクトルストアIDを取得"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT vector_store_id FROM user_vector_stores WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return row["vector_store_id"] if row else None
    
    async def set_user_vector_store_id(self, user_id: str, vector_store_id: str) -> None:
        """ユーザーのベクトルストアIDを設定"""
        async with aiosqlite.connect(self.db_path) as db:
            # UPSERT操作（存在すれば更新、なければ挿入）
            await db.execute("""
                INSERT OR REPLACE INTO user_vector_stores 
                (user_id, vector_store_id, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (user_id, vector_store_id))
            await db.commit()
    
    async def delete_user_vector_store(self, user_id: str) -> None:
        """ユーザーのベクトルストア情報を削除"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM user_vector_stores WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
    
    async def update_thread_vector_store(self, thread_id: str, vector_store_id: str) -> None:
        """スレッドのベクトルストアIDを更新"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE threads 
                SET vector_store_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (vector_store_id, thread_id))
            await db.commit()


# データレイヤーを設定
import chainlit.data as cl_data
cl_data._data_layer = SQLiteDataLayer()
