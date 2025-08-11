"""
シンプルなインメモリデータレイヤー実装
最小限の実装で履歴機能を有効にする
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
import chainlit as cl
from chainlit.data import BaseDataLayer
from chainlit.types import ThreadDict, Pagination, ThreadFilter
from chainlit.element import ElementDict
from chainlit.step import StepDict
from chainlit.user import User
import json


class SimpleDataLayer(BaseDataLayer):
    """
    最小限のインメモリデータレイヤー実装
    """
    
    def __init__(self):
        """初期化"""
        self.threads = {}
        self.steps = {}
        self.feedbacks = {}
        self.elements = {}
        self.users = {}
    
    async def get_user(self, identifier: str) -> Optional[User]:
        """ユーザー情報を取得"""
        return self.users.get(identifier, User(identifier=identifier))
    
    async def create_user(self, user: User) -> Optional[User]:
        """ユーザーを作成"""
        self.users[user.identifier] = user
        return user
    
    async def create_thread(
        self,
        thread: ThreadDict,
    ) -> Optional[ThreadDict]:
        """新しいスレッドを作成"""
        thread_id = thread.get("id")
        self.threads[thread_id] = thread
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
        if thread_id in self.threads:
            thread = self.threads[thread_id]
            if name is not None:
                thread["name"] = name
            if user_id is not None:
                thread["user_id"] = user_id
            if metadata is not None:
                thread["metadata"] = metadata
            if tags is not None:
                thread["tags"] = tags
    
    async def get_thread(self, thread_id: str) -> Optional[ThreadDict]:
        """スレッドを取得"""
        return self.threads.get(thread_id)
    
    async def delete_thread(self, thread_id: str) -> None:
        """スレッドを削除"""
        if thread_id in self.threads:
            del self.threads[thread_id]
    
    async def list_threads(
        self,
        pagination: Pagination,
        filters: ThreadFilter,
    ) -> Pagination:
        """スレッド一覧を取得"""
        # フィルタリング
        filtered_threads = []
        for thread in self.threads.values():
            if filters.user_id and thread.get("user_id") != filters.user_id:
                continue
            filtered_threads.append(thread)
        
        # ソート（作成日時の降順）
        filtered_threads.sort(
            key=lambda x: x.get("createdAt", ""), 
            reverse=True
        )
        
        # ページネーション
        limit = pagination.first or 20
        cursor = pagination.cursor or 0
        
        paginated_threads = filtered_threads[cursor:cursor + limit]
        
        return {
            "data": paginated_threads,
            "pageInfo": {
                "hasNextPage": cursor + limit < len(filtered_threads),
                "startCursor": cursor,
                "endCursor": cursor + len(paginated_threads)
            }
        }
    
    async def get_thread_author(self, thread_id: str) -> Optional[str]:
        """スレッドの作成者を取得"""
        thread = self.threads.get(thread_id)
        return thread.get("user_identifier") if thread else None
    
    async def create_step(self, step: StepDict) -> None:
        """ステップを作成"""
        step_id = step.get("id")
        self.steps[step_id] = step
    
    async def update_step(self, step: StepDict) -> None:
        """ステップを更新"""
        step_id = step.get("id")
        self.steps[step_id] = step
    
    async def delete_step(self, step_id: str) -> None:
        """ステップを削除"""
        if step_id in self.steps:
            del self.steps[step_id]
    
    async def create_element(self, element: ElementDict) -> None:
        """エレメントを作成"""
        element_id = element.get("id")
        self.elements[element_id] = element
    
    async def delete_element(self, element_id: str) -> None:
        """エレメントを削除"""
        if element_id in self.elements:
            del self.elements[element_id]
    
    async def upsert_feedback(
        self,
        feedback: Dict,
    ) -> str:
        """フィードバックを作成または更新"""
        import uuid
        feedback_id = feedback.get("id") or str(uuid.uuid4())
        self.feedbacks[feedback_id] = feedback
        return feedback_id
    
    async def delete_feedback(self, feedback_id: str) -> None:
        """フィードバックを削除"""
        if feedback_id in self.feedbacks:
            del self.feedbacks[feedback_id]


# データレイヤーを設定
import chainlit.data as cl_data
cl_data._data_layer = SimpleDataLayer()

print("✅ シンプルなインメモリデータレイヤーを設定しました")
