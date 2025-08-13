"""
Chainlitアプリケーション用のログシステム
標準出力とファイルの両方に詳細なログを出力
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
import os

class ChainlitLogger:
    """カスタムログハンドラー"""
    
    def __init__(self, log_file: str = ".chainlit/app.log"):
        """ログシステムを初期化"""
        self.log_file = log_file
        
        # ログディレクトリを作成
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # ログフォーマットを設定
        self.formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # ルートロガーを取得
        self.logger = logging.getLogger('chainlit_app')
        self.logger.setLevel(logging.DEBUG)
        
        # 既存のハンドラーをクリア
        self.logger.handlers.clear()
        
        # コンソールハンドラーを追加
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)
        
        # ファイルハンドラーを追加（追記モード）
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)
        
        # アプリケーション起動の区切りを記録
        self._write_session_separator()
    
    def _write_session_separator(self):
        """セッション開始の区切り線を記録"""
        separator = "=" * 80
        startup_msg = f"アプリケーション起動: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # ファイルに直接書き込み（フォーマットなし）
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{separator}\n")
            f.write(f"{startup_msg}\n")
            f.write(f"{separator}\n")
        
        # コンソールにも表示
        print(f"\n{separator}")
        print(f"{startup_msg}")
        print(f"{separator}\n")
    
    def debug(self, message: str, **kwargs):
        """デバッグレベルのログ"""
        extra_info = ' | '.join([f"{k}={v}" for k, v in kwargs.items()])
        if extra_info:
            message = f"{message} | {extra_info}"
        self.logger.debug(message)
    
    def info(self, message: str, **kwargs):
        """情報レベルのログ"""
        extra_info = ' | '.join([f"{k}={v}" for k, v in kwargs.items()])
        if extra_info:
            message = f"{message} | {extra_info}"
        self.logger.info(message)
    
    def warning(self, message: str, **kwargs):
        """警告レベルのログ"""
        extra_info = ' | '.join([f"{k}={v}" for k, v in kwargs.items()])
        if extra_info:
            message = f"{message} | {extra_info}"
        self.logger.warning(message)
    
    def error(self, message: str, **kwargs):
        """エラーレベルのログ"""
        extra_info = ' | '.join([f"{k}={v}" for k, v in kwargs.items()])
        if extra_info:
            message = f"{message} | {extra_info}"
        self.logger.error(message)
    
    def step_created(self, step_id: str, thread_id: str, step_type: str, **kwargs):
        """ステップ作成のログ"""
        self.debug(f"📝 STEP_CREATED", 
                  step_id=step_id[:8], 
                  thread_id=thread_id[:8], 
                  type=step_type,
                  **kwargs)
    
    def thread_created(self, thread_id: str, name: str, user: str):
        """スレッド作成のログ"""
        self.info(f"🆕 THREAD_CREATED",
                 thread_id=thread_id[:8],
                 name=name,
                 user=user)
    
    def message_received(self, message: str, user: str):
        """メッセージ受信のログ"""
        preview = message[:100] + "..." if len(message) > 100 else message
        self.info(f"📥 MESSAGE_RECEIVED",
                 user=user,
                 preview=preview,
                 length=len(message))
    
    def ai_response(self, response: str, model: str = None):
        """AI応答のログ"""
        preview = response[:100] + "..." if len(response) > 100 else response
        self.info(f"🤖 AI_RESPONSE",
                 model=model or "unknown",
                 preview=preview,
                 length=len(response))
    
    def history_restored(self, thread_id: str, message_count: int):
        """履歴復元のログ"""
        self.info(f"📂 HISTORY_RESTORED",
                 thread_id=thread_id[:8],
                 messages=message_count)
    
    def database_operation(self, operation: str, table: str, success: bool, **kwargs):
        """データベース操作のログ"""
        level = "✅" if success else "❌"
        self.debug(f"{level} DB_OPERATION",
                  operation=operation,
                  table=table,
                  success=success,
                  **kwargs)

# グローバルロガーインスタンス
app_logger = ChainlitLogger()

# 便利なショートカット
debug = app_logger.debug
info = app_logger.info
warning = app_logger.warning
error = app_logger.error
