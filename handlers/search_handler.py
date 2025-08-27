"""
高度検索機能ハンドラー
会話履歴、ペルソナ、ベクトルストアの横断検索機能
"""

import sqlite3
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from utils.ui_helper import ChainlitHelper as ui
from utils.error_handler import ErrorHandler as error_handler  
from utils.logger import app_logger
from utils.persona_manager import persona_manager
from utils.vector_store_handler import vector_store_handler


@dataclass
class SearchResult:
    """検索結果のデータクラス"""
    result_type: str  # "conversation", "persona", "vector_store"
    title: str
    content: str
    metadata: Dict[str, Any]
    relevance_score: float
    timestamp: Optional[str] = None
    
    
@dataclass
class SearchFilters:
    """検索フィルターのデータクラス"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    persona_names: Optional[List[str]] = None
    models: Optional[List[str]] = None
    result_types: Optional[List[str]] = None
    min_relevance: float = 0.0


class SearchHandler:
    """高度検索機能を統括するクラス"""
    
    def __init__(self):
        """検索ハンドラーを初期化"""
        self.chainlit_db_path = ".chainlit/chainlit.db"
        self.analytics_db_path = ".chainlit/analytics.db"
        
    async def search_all(
        self,
        query: str,
        user_id: str = None,
        filters: SearchFilters = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """全データ横断検索"""
        try:
            if not query.strip():
                await ui.send_error_message("検索クエリを入力してください。")
                return []
            
            app_logger.info("横断検索開始", query=query, user_id=user_id)
            
            filters = filters or SearchFilters()
            results = []
            
            # 会話履歴の検索
            if not filters.result_types or "conversation" in filters.result_types:
                conversation_results = await self._search_conversations(query, user_id, filters)
                results.extend(conversation_results)
            
            # ペルソナの検索
            if not filters.result_types or "persona" in filters.result_types:
                persona_results = await self._search_personas(query)
                results.extend(persona_results)
            
            # ベクトルストアの検索
            if not filters.result_types or "vector_store" in filters.result_types:
                vs_results = await self._search_vector_stores(query, user_id)
                results.extend(vs_results)
            
            # 関連度順にソート
            results.sort(key=lambda r: r.relevance_score, reverse=True)
            
            # 最小関連度フィルター適用
            results = [r for r in results if r.relevance_score >= filters.min_relevance]
            
            app_logger.info("横断検索完了", results_count=len(results))
            return results[:limit]
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "横断検索")
            return []
    
    async def show_search_results(self, results: List[SearchResult], query: str):
        """検索結果を整形して表示"""
        try:
            if not results:
                await ui.send_info_message(
                    f"🔍 検索結果\n\n"
                    f"クエリ: **{query}**\n"
                    f"結果: 該当するデータが見つかりませんでした。"
                )
                return
            
            message = f"# 🔍 検索結果\n\n"
            message += f"**クエリ**: {query}\n"
            message += f"**件数**: {len(results)}件\n\n"
            
            # 結果タイプ別に分類
            conversation_results = [r for r in results if r.result_type == "conversation"]
            persona_results = [r for r in results if r.result_type == "persona"]
            vs_results = [r for r in results if r.result_type == "vector_store"]
            
            # 会話履歴の結果
            if conversation_results:
                message += f"## 💬 会話履歴 ({len(conversation_results)}件)\n\n"
                for i, result in enumerate(conversation_results[:5], 1):
                    highlighted_content = self._highlight_query_in_text(result.content, query)
                    timestamp = result.timestamp[:16] if result.timestamp else "不明"
                    
                    message += f"### {i}. {result.title}\n"
                    message += f"**日時**: {timestamp}\n"
                    message += f"**関連度**: {result.relevance_score:.2f}\n"
                    message += f"**内容**: {highlighted_content[:200]}{'...' if len(result.content) > 200 else ''}\n"
                    
                    if result.metadata:
                        if result.metadata.get("persona"):
                            message += f"**ペルソナ**: {result.metadata['persona']}\n"
                        if result.metadata.get("model"):
                            message += f"**モデル**: {result.metadata['model']}\n"
                    
                    message += "\n"
                
                if len(conversation_results) > 5:
                    message += f"*他{len(conversation_results) - 5}件の会話結果があります*\n\n"
            
            # ペルソナの結果
            if persona_results:
                message += f"## 🎭 ペルソナ ({len(persona_results)}件)\n\n"
                for i, result in enumerate(persona_results, 1):
                    highlighted_content = self._highlight_query_in_text(result.content, query)
                    
                    message += f"### {i}. {result.title}\n"
                    message += f"**関連度**: {result.relevance_score:.2f}\n"
                    message += f"**説明**: {highlighted_content}\n"
                    
                    if result.metadata:
                        if result.metadata.get("model"):
                            message += f"**モデル**: {result.metadata['model']}\n"
                        if result.metadata.get("tags"):
                            message += f"**タグ**: {', '.join(result.metadata['tags'])}\n"
                    
                    message += "\n"
            
            # ベクトルストアの結果
            if vs_results:
                message += f"## 🗂️ ベクトルストア ({len(vs_results)}件)\n\n"
                for i, result in enumerate(vs_results, 1):
                    message += f"### {i}. {result.title}\n"
                    message += f"**関連度**: {result.relevance_score:.2f}\n"
                    message += f"**タイプ**: {result.metadata.get('vs_type', 'Unknown')}\n"
                    
                    if result.content:
                        highlighted_content = self._highlight_query_in_text(result.content, query)
                        message += f"**内容**: {highlighted_content[:150]}{'...' if len(result.content) > 150 else ''}\n"
                    
                    message += "\n"
            
            await ui.send_system_message(message)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "検索結果表示")
    
    async def advanced_search_with_filters(
        self,
        query: str,
        user_id: str = None,
        start_date: str = None,
        end_date: str = None,
        persona_names: List[str] = None,
        models: List[str] = None,
        result_types: List[str] = None
    ):
        """フィルター付き高度検索"""
        try:
            loading_msg = await ui.show_loading_message("高度検索を実行中...")
            
            # フィルター構築
            filters = SearchFilters(
                start_date=start_date,
                end_date=end_date,
                persona_names=persona_names,
                models=models,
                result_types=result_types,
                min_relevance=0.1
            )
            
            # 検索実行
            results = await self.search_all(query, user_id, filters)
            
            await ui.update_loading_message(loading_msg, "検索結果を整理中...")
            
            # 結果表示
            await self.show_search_results(results, query)
            
            # 検索統計
            stats_message = self._generate_search_stats(results, filters)
            if stats_message:
                await ui.send_system_message(stats_message)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "高度検索")
    
    async def search_conversations_only(
        self,
        query: str,
        user_id: str = None,
        limit: int = 10
    ):
        """会話履歴のみを検索"""
        try:
            loading_msg = await ui.show_loading_message("会話履歴を検索中...")
            
            results = await self._search_conversations(query, user_id, SearchFilters())
            results = results[:limit]
            
            if not results:
                await ui.update_loading_message(
                    loading_msg,
                    f"🔍 会話履歴検索結果\n\n"
                    f"クエリ: **{query}**\n"
                    f"該当する会話が見つかりませんでした。"
                )
                return
            
            message = f"# 💬 会話履歴検索結果\n\n"
            message += f"**クエリ**: {query}\n"
            message += f"**件数**: {len(results)}件\n\n"
            
            for i, result in enumerate(results, 1):
                highlighted_content = self._highlight_query_in_text(result.content, query)
                timestamp = result.timestamp[:16] if result.timestamp else "不明"
                
                message += f"## {i}. {result.title}\n"
                message += f"**日時**: {timestamp}\n"
                message += f"**関連度**: {result.relevance_score:.2f}\n\n"
                message += f"{highlighted_content[:300]}{'...' if len(result.content) > 300 else ''}\n\n"
                
                if result.metadata:
                    details = []
                    if result.metadata.get("persona"):
                        details.append(f"ペルソナ: {result.metadata['persona']}")
                    if result.metadata.get("model"):
                        details.append(f"モデル: {result.metadata['model']}")
                    if details:
                        message += f"*{' | '.join(details)}*\n\n"
                
                message += "---\n\n"
            
            await ui.update_loading_message(loading_msg, message)
            
        except Exception as e:
            await error_handler.handle_unexpected_error(e, "会話履歴検索")
    
    async def _search_conversations(
        self,
        query: str,
        user_id: str = None,
        filters: SearchFilters = None
    ) -> List[SearchResult]:
        """会話履歴を検索"""
        try:
            results = []
            
            with sqlite3.connect(self.chainlit_db_path) as conn:
                cursor = conn.cursor()
                
                # 基本的なSQLクエリ
                sql = """
                SELECT e.id, e.type, e.content, e.created_at, s.id as session_id, s.metadata
                FROM element e
                LEFT JOIN step s ON e.step_id = s.id
                WHERE e.content IS NOT NULL 
                AND e.content != ''
                AND e.content LIKE ?
                """
                params = [f"%{query}%"]
                
                # ユーザーフィルター
                if user_id:
                    sql += " AND s.user_id = ?"
                    params.append(user_id)
                
                # 日付フィルター
                if filters and filters.start_date:
                    sql += " AND e.created_at >= ?"
                    params.append(filters.start_date)
                
                if filters and filters.end_date:
                    sql += " AND e.created_at <= ?"
                    params.append(filters.end_date)
                
                sql += " ORDER BY e.created_at DESC LIMIT 50"
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                for row in rows:
                    element_id, element_type, content, created_at, session_id, session_metadata = row
                    
                    # 関連度スコア計算
                    relevance_score = self._calculate_text_relevance(content, query)
                    
                    # メタデータ解析
                    metadata = {}
                    if session_metadata:
                        try:
                            parsed_metadata = json.loads(session_metadata)
                            metadata = {
                                "persona": parsed_metadata.get("active_persona", {}).get("name"),
                                "model": parsed_metadata.get("model"),
                                "session_id": session_id
                            }
                        except (json.JSONDecodeError, AttributeError):
                            pass
                    
                    # フィルター適用
                    if filters:
                        if filters.persona_names and metadata.get("persona") not in filters.persona_names:
                            continue
                        if filters.models and metadata.get("model") not in filters.models:
                            continue
                    
                    result = SearchResult(
                        result_type="conversation",
                        title=f"会話 #{element_id}",
                        content=content,
                        metadata=metadata,
                        relevance_score=relevance_score,
                        timestamp=created_at
                    )
                    
                    results.append(result)
            
            return results
            
        except Exception as e:
            app_logger.error(f"会話履歴検索エラー: {e}")
            return []
    
    async def _search_personas(self, query: str) -> List[SearchResult]:
        """ペルソナを検索"""
        try:
            results = []
            personas = await persona_manager.get_all_personas()
            
            for persona in personas:
                # 名前と説明で検索
                searchable_text = f"{persona.get('name', '')} {persona.get('description', '')} {persona.get('system_prompt', '')}"
                
                relevance_score = self._calculate_text_relevance(searchable_text, query)
                
                if relevance_score > 0.1:  # 最小関連度チェック
                    result = SearchResult(
                        result_type="persona",
                        title=persona.get("name", "Unknown Persona"),
                        content=persona.get("description", ""),
                        metadata={
                            "model": persona.get("model"),
                            "temperature": persona.get("temperature"),
                            "tags": persona.get("tags", [])
                        },
                        relevance_score=relevance_score
                    )
                    results.append(result)
            
            return results
            
        except Exception as e:
            app_logger.error(f"ペルソナ検索エラー: {e}")
            return []
    
    async def _search_vector_stores(self, query: str, user_id: str = None) -> List[SearchResult]:
        """ベクトルストアを検索"""
        try:
            results = []
            
            # 利用可能なベクトルストアIDを取得
            vs_ids = []
            
            # Company VS
            company_vs_id = os.environ.get("COMPANY_VECTOR_STORE_ID")
            if company_vs_id:
                vs_ids.append(("company", company_vs_id))
            
            # Personal VS (簡易実装 - 実際はdata_layerから取得)
            # TODO: data_layerとの連携実装
            
            for vs_type, vs_id in vs_ids:
                try:
                    # ベクトルストア情報を取得
                    vs_info = await vector_store_handler.get_vector_store_info(vs_id)
                    
                    if vs_info:
                        # ベクトルストア名での検索
                        searchable_text = f"{vs_info.get('name', '')} {vs_type}"
                        relevance_score = self._calculate_text_relevance(searchable_text, query)
                        
                        if relevance_score > 0.1:
                            result = SearchResult(
                                result_type="vector_store",
                                title=vs_info.get("name", f"Vector Store {vs_id[:8]}"),
                                content=f"ベクトルストア ({vs_type})",
                                metadata={
                                    "vs_type": vs_type,
                                    "vs_id": vs_id,
                                    "file_count": vs_info.get("file_counts", {}).get("total", 0)
                                },
                                relevance_score=relevance_score
                            )
                            results.append(result)
                            
                except Exception as e:
                    app_logger.warning(f"ベクトルストア {vs_id} 検索エラー: {e}")
                    continue
            
            return results
            
        except Exception as e:
            app_logger.error(f"ベクトルストア検索エラー: {e}")
            return []
    
    def _calculate_text_relevance(self, text: str, query: str) -> float:
        """テキストの関連度スコアを計算"""
        if not text or not query:
            return 0.0
        
        text_lower = text.lower()
        query_lower = query.lower()
        query_words = query_lower.split()
        
        score = 0.0
        
        # 完全一致
        if query_lower in text_lower:
            score += 1.0
        
        # 単語別マッチング
        matched_words = 0
        for word in query_words:
            if word in text_lower:
                matched_words += 1
        
        word_match_ratio = matched_words / len(query_words) if query_words else 0
        score += word_match_ratio * 0.8
        
        # 単語の近接性 (簡易実装)
        if len(query_words) > 1:
            for i, word1 in enumerate(query_words[:-1]):
                word2 = query_words[i + 1]
                # 50文字以内で連続する単語があればボーナス
                word1_pos = text_lower.find(word1)
                if word1_pos != -1:
                    word2_pos = text_lower.find(word2, word1_pos)
                    if word2_pos != -1 and word2_pos - word1_pos < 50:
                        score += 0.3
        
        return min(score, 2.0)  # 最大スコア制限
    
    def _highlight_query_in_text(self, text: str, query: str) -> str:
        """テキスト内のクエリをハイライト"""
        if not text or not query:
            return text
        
        # 簡易ハイライト実装
        query_words = query.split()
        highlighted_text = text
        
        for word in query_words:
            # 大文字小文字を無視して置換
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            highlighted_text = pattern.sub(f"**{word}**", highlighted_text)
        
        return highlighted_text
    
    def _generate_search_stats(self, results: List[SearchResult], filters: SearchFilters) -> str:
        """検索統計の生成"""
        if not results:
            return ""
        
        stats = {
            "conversation": 0,
            "persona": 0,
            "vector_store": 0
        }
        
        for result in results:
            stats[result.result_type] = stats.get(result.result_type, 0) + 1
        
        message = "## 📊 検索統計\n\n"
        message += f"- 💬 会話履歴: {stats['conversation']}件\n"
        message += f"- 🎭 ペルソナ: {stats['persona']}件\n"
        message += f"- 🗂️ ベクトルストア: {stats['vector_store']}件\n"
        
        if filters:
            message += "\n**適用フィルター:**\n"
            if filters.start_date:
                message += f"- 開始日: {filters.start_date[:10]}\n"
            if filters.end_date:
                message += f"- 終了日: {filters.end_date[:10]}\n"
            if filters.persona_names:
                message += f"- ペルソナ: {', '.join(filters.persona_names)}\n"
            if filters.models:
                message += f"- モデル: {', '.join(filters.models)}\n"
        
        return message


# グローバルインスタンス
search_handler = SearchHandler()