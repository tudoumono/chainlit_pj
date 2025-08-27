"""
統計データ収集・記録システム
使用量、コスト、ユーザー行動を追跡・記録
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from utils.logger import app_logger


@dataclass
class ApiUsageRecord:
    """API使用量記録"""
    timestamp: str
    user_id: str
    model: str
    operation: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    persona_name: str
    session_id: str


@dataclass
class UserActionRecord:
    """ユーザー行動記録"""
    timestamp: str
    user_id: str
    action: str
    target: str
    duration_seconds: float
    success: bool
    session_id: str


@dataclass
class VectorStoreUsageRecord:
    """ベクトルストア使用記録"""
    timestamp: str
    user_id: str
    vs_id: str
    vs_type: str  # company/personal/session
    operation: str  # create/query/upload/delete
    file_count: int
    file_size_bytes: int
    session_id: str


class AnalyticsLogger:
    """統計データの記録・管理クラス"""
    
    def __init__(self):
        """統計ロガーを初期化"""
        self.db_path = ".chainlit/analytics.db"
        self._ensure_db_directory()
        self._init_database()
        
        # OpenAI料金表（2024年8月時点の概算）
        self.pricing = {
            "gpt-4o": {"input": 0.005, "output": 0.015},  # per 1K tokens
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "default": {"input": 0.001, "output": 0.002}
        }
    
    def _ensure_db_directory(self):
        """DBディレクトリの存在確認・作成"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_database(self):
        """統計データベースの初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # API使用量テーブル
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    estimated_cost REAL NOT NULL,
                    persona_name TEXT,
                    session_id TEXT
                )
                """)
                
                # ユーザー行動テーブル
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT,
                    duration_seconds REAL,
                    success BOOLEAN NOT NULL,
                    session_id TEXT
                )
                """)
                
                # ベクトルストア使用テーブル
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS vector_store_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    vs_id TEXT NOT NULL,
                    vs_type TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    file_count INTEGER DEFAULT 0,
                    file_size_bytes INTEGER DEFAULT 0,
                    session_id TEXT
                )
                """)
                
                # インデックスの作成
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_timestamp ON api_usage(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_user ON api_usage(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_action_timestamp ON user_actions(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_vs_timestamp ON vector_store_usage(timestamp)")
                
                conn.commit()
                app_logger.info("統計データベース初期化完了")
                
        except Exception as e:
            app_logger.error(f"統計データベース初期化エラー: {e}")
    
    def log_api_usage(
        self,
        user_id: str,
        model: str,
        operation: str,
        input_tokens: int,
        output_tokens: int,
        persona_name: str = "",
        session_id: str = ""
    ):
        """API使用量を記録"""
        try:
            total_tokens = input_tokens + output_tokens
            estimated_cost = self._calculate_cost(model, input_tokens, output_tokens)
            
            record = ApiUsageRecord(
                timestamp=datetime.now().isoformat(),
                user_id=user_id,
                model=model,
                operation=operation,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost,
                persona_name=persona_name,
                session_id=session_id
            )
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO api_usage (
                    timestamp, user_id, model, operation, input_tokens, 
                    output_tokens, total_tokens, estimated_cost, persona_name, session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.timestamp, record.user_id, record.model, record.operation,
                    record.input_tokens, record.output_tokens, record.total_tokens,
                    record.estimated_cost, record.persona_name, record.session_id
                ))
                conn.commit()
            
            app_logger.debug("API使用量記録完了", **asdict(record))
            
        except Exception as e:
            app_logger.error(f"API使用量記録エラー: {e}")
    
    def log_user_action(
        self,
        user_id: str,
        action: str,
        target: str = "",
        duration_seconds: float = 0.0,
        success: bool = True,
        session_id: str = ""
    ):
        """ユーザー行動を記録"""
        try:
            record = UserActionRecord(
                timestamp=datetime.now().isoformat(),
                user_id=user_id,
                action=action,
                target=target,
                duration_seconds=duration_seconds,
                success=success,
                session_id=session_id
            )
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO user_actions (
                    timestamp, user_id, action, target, duration_seconds, success, session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.timestamp, record.user_id, record.action, record.target,
                    record.duration_seconds, record.success, record.session_id
                ))
                conn.commit()
            
            app_logger.debug("ユーザー行動記録完了", **asdict(record))
            
        except Exception as e:
            app_logger.error(f"ユーザー行動記録エラー: {e}")
    
    def log_vector_store_usage(
        self,
        user_id: str,
        vs_id: str,
        vs_type: str,
        operation: str,
        file_count: int = 0,
        file_size_bytes: int = 0,
        session_id: str = ""
    ):
        """ベクトルストア使用を記録"""
        try:
            record = VectorStoreUsageRecord(
                timestamp=datetime.now().isoformat(),
                user_id=user_id,
                vs_id=vs_id,
                vs_type=vs_type,
                operation=operation,
                file_count=file_count,
                file_size_bytes=file_size_bytes,
                session_id=session_id
            )
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO vector_store_usage (
                    timestamp, user_id, vs_id, vs_type, operation, 
                    file_count, file_size_bytes, session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.timestamp, record.user_id, record.vs_id, record.vs_type,
                    record.operation, record.file_count, record.file_size_bytes, record.session_id
                ))
                conn.commit()
            
            app_logger.debug("ベクトルストア使用記録完了", **asdict(record))
            
        except Exception as e:
            app_logger.error(f"ベクトルストア使用記録エラー: {e}")
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """API使用コストを計算"""
        pricing = self.pricing.get(model, self.pricing["default"])
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return round(input_cost + output_cost, 6)
    
    def get_usage_summary(
        self,
        user_id: str = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """使用量サマリーを取得"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # ユーザーフィルターの構築
                user_filter = "AND user_id = ?" if user_id else ""
                user_params = [user_id] if user_id else []
                
                # API使用量サマリー
                cursor.execute(f"""
                SELECT 
                    COUNT(*) as request_count,
                    SUM(total_tokens) as total_tokens,
                    SUM(estimated_cost) as total_cost,
                    AVG(estimated_cost) as avg_cost_per_request
                FROM api_usage 
                WHERE timestamp >= ? AND timestamp <= ? {user_filter}
                """, [start_date.isoformat(), end_date.isoformat()] + user_params)
                
                api_summary = cursor.fetchone()
                
                # モデル別使用量
                cursor.execute(f"""
                SELECT 
                    model,
                    COUNT(*) as count,
                    SUM(total_tokens) as tokens,
                    SUM(estimated_cost) as cost
                FROM api_usage 
                WHERE timestamp >= ? AND timestamp <= ? {user_filter}
                GROUP BY model
                ORDER BY cost DESC
                """, [start_date.isoformat(), end_date.isoformat()] + user_params)
                
                model_usage = cursor.fetchall()
                
                # ペルソナ別使用量
                cursor.execute(f"""
                SELECT 
                    persona_name,
                    COUNT(*) as count,
                    SUM(estimated_cost) as cost
                FROM api_usage 
                WHERE timestamp >= ? AND timestamp <= ? {user_filter} 
                AND persona_name IS NOT NULL AND persona_name != ''
                GROUP BY persona_name
                ORDER BY cost DESC
                LIMIT 10
                """, [start_date.isoformat(), end_date.isoformat()] + user_params)
                
                persona_usage = cursor.fetchall()
                
                # 日別使用量（グラフ用）
                cursor.execute(f"""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as requests,
                    SUM(estimated_cost) as cost
                FROM api_usage 
                WHERE timestamp >= ? AND timestamp <= ? {user_filter}
                GROUP BY DATE(timestamp)
                ORDER BY date
                """, [start_date.isoformat(), end_date.isoformat()] + user_params)
                
                daily_usage = cursor.fetchall()
                
                return {
                    "period": {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": days},
                    "api_summary": {
                        "request_count": api_summary[0] or 0,
                        "total_tokens": api_summary[1] or 0,
                        "total_cost": round(api_summary[2] or 0, 4),
                        "avg_cost_per_request": round(api_summary[3] or 0, 6)
                    },
                    "model_usage": [
                        {"model": row[0], "count": row[1], "tokens": row[2], "cost": round(row[3], 4)}
                        for row in model_usage
                    ],
                    "persona_usage": [
                        {"persona": row[0], "count": row[1], "cost": round(row[2], 4)}
                        for row in persona_usage
                    ],
                    "daily_usage": [
                        {"date": row[0], "requests": row[1], "cost": round(row[2], 4)}
                        for row in daily_usage
                    ]
                }
                
        except Exception as e:
            app_logger.error(f"使用量サマリー取得エラー: {e}")
            return {}
    
    def get_vector_store_summary(self, user_id: str = None, days: int = 30) -> Dict[str, Any]:
        """ベクトルストア使用サマリーを取得"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                user_filter = "AND user_id = ?" if user_id else ""
                user_params = [user_id] if user_id else []
                
                # ベクトルストア使用統計
                cursor.execute(f"""
                SELECT 
                    vs_type,
                    operation,
                    COUNT(*) as count,
                    SUM(file_count) as total_files,
                    SUM(file_size_bytes) as total_size
                FROM vector_store_usage 
                WHERE timestamp >= ? AND timestamp <= ? {user_filter}
                GROUP BY vs_type, operation
                ORDER BY vs_type, count DESC
                """, [start_date.isoformat(), end_date.isoformat()] + user_params)
                
                vs_usage = cursor.fetchall()
                
                return {
                    "period": {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": days},
                    "vs_usage": [
                        {
                            "vs_type": row[0],
                            "operation": row[1],
                            "count": row[2],
                            "total_files": row[3] or 0,
                            "total_size_mb": round((row[4] or 0) / 1024 / 1024, 2)
                        }
                        for row in vs_usage
                    ]
                }
                
        except Exception as e:
            app_logger.error(f"ベクトルストア使用サマリー取得エラー: {e}")
            return {}


# グローバルインスタンス
analytics_logger = AnalyticsLogger()