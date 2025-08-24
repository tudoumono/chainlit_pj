"""
WebSocket接続エラーのハンドリングとデバッグ機能
"""

import asyncio
import logging
from typing import Optional
import traceback
from datetime import datetime
import sys
import io

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ファイルハンドラーを追加（デバッグログ用）- UTF-8エンコーディングを指定
debug_handler = logging.FileHandler('websocket_debug.log', encoding='utf-8')
debug_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
debug_handler.setFormatter(formatter)
logger.addHandler(debug_handler)

# コンソールハンドラーも追加 - UTF-8エンコーディングを強制
# Windows環境でのエンコーディング問題を回避
if sys.platform == 'win32':
    # Windows環境では、標準出力をUTF-8でラップ
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class ConnectionMonitor:
    """WebSocket接続の監視とデバッグ"""
    
    def __init__(self):
        self.active_connections = {}
        self.connection_errors = []
        
    def log_connection(self, session_id: str, info: dict):
        """接続情報を記録"""
        self.active_connections[session_id] = {
            'connected_at': datetime.now(),
            'info': info
        }
        logger.info(f"[CONNECT] 新規接続: {session_id} - {info}")
        
    def log_disconnection(self, session_id: str, reason: Optional[str] = None):
        """切断情報を記録"""
        if session_id in self.active_connections:
            connection_info = self.active_connections.pop(session_id)
            duration = datetime.now() - connection_info['connected_at']
            logger.info(f"[DISCONNECT] 切断: {session_id} - 接続時間: {duration} - 理由: {reason or '正常終了'}")
        else:
            logger.warning(f"[WARNING] 未登録の接続が切断: {session_id}")
            
    def log_error(self, error_type: str, error_message: str, stack_trace: Optional[str] = None):
        """エラー情報を記録"""
        error_info = {
            'timestamp': datetime.now(),
            'type': error_type,
            'message': error_message,
            'stack_trace': stack_trace
        }
        self.connection_errors.append(error_info)
        
        # 最新10件のエラーのみ保持
        if len(self.connection_errors) > 10:
            self.connection_errors = self.connection_errors[-10:]
            
        logger.error(f"[ERROR] WebSocketエラー: {error_type}")
        logger.error(f"   メッセージ: {error_message}")
        if stack_trace:
            logger.debug(f"   スタックトレース:\n{stack_trace}")
            
    def get_connection_status(self) -> dict:
        """現在の接続状態を取得"""
        return {
            'active_connections': len(self.active_connections),
            'recent_errors': len(self.connection_errors),
            'connections': list(self.active_connections.keys()),
            'last_error': self.connection_errors[-1] if self.connection_errors else None
        }


# グローバルモニターインスタンス
connection_monitor = ConnectionMonitor()


async def handle_websocket_error(error: Exception, context: Optional[dict] = None):
    """WebSocketエラーを処理"""
    error_type = type(error).__name__
    error_message = str(error)
    stack_trace = traceback.format_exc()
    
    # 既知のエラーパターンを判定
    if "WinError 10054" in error_message:
        logger.debug("[INFO] 既知のエラー: Windows WebSocket切断 (通常は無視して問題ありません)")
        connection_monitor.log_error(
            "ConnectionReset",
            "クライアントが接続を切断しました（正常な動作の可能性があります）",
            None  # スタックトレースは不要
        )
    elif "ConnectionResetError" in error_type:
        logger.debug("[INFO] 接続リセット: クライアント側の切断")
        connection_monitor.log_error(
            error_type,
            error_message,
            None
        )
    else:
        # 未知のエラーは詳細ログを出力
        logger.error(f"[WARNING] 未処理のWebSocketエラー: {error_type}")
        connection_monitor.log_error(
            error_type,
            error_message,
            stack_trace
        )
        
    if context:
        logger.debug(f"コンテキスト情報: {context}")


def setup_websocket_error_handler():
    """Windowsプラットフォーム用のエラーハンドラーを設定"""
    import sys
    import platform
    
    if platform.system() == 'Windows':
        logger.info("[SYSTEM] Windows環境を検出 - ProactorEventLoop用の対策を適用")
        
        # Windows特有のエラーを抑制
        import warnings
        warnings.filterwarnings(
            "ignore",
            message=".*ProactorBasePipeTransport.*",
            category=RuntimeWarning
        )
        
        # asyncioのデバッグモードを有効化（詳細なエラー情報を取得）
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # デバッグモードの切り替え（必要に応じて）
        # asyncio.get_event_loop().set_debug(True)
        
        logger.info("[SUCCESS] Windows用WebSocketエラー対策を適用しました")
    else:
        logger.info(f"[SYSTEM] {platform.system()}環境を検出")


# モジュール読み込み時に自動実行
setup_websocket_error_handler()
