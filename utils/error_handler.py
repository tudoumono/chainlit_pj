"""
エラーハンドリングの統一処理
アプリケーション全体で一貫したエラー処理を提供
"""

import traceback
from typing import Optional, Dict, Any
from utils.logger import app_logger
from utils.ui_helper import ChainlitHelper as ui


class ErrorHandler:
    """統一されたエラーハンドリングクラス"""
    
    @staticmethod
    async def handle_api_error(error: Exception, operation: str, show_to_user: bool = True):
        """
        API関連エラーの処理
        
        Args:
            error: 発生した例外
            operation: 実行していた操作名
            show_to_user: ユーザーにエラーメッセージを表示するか
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # ログに詳細を記録
        app_logger.error(f"❌ {operation}でAPIエラー: {error_type} - {error_msg}")
        app_logger.debug(f"スタックトレース:\n{traceback.format_exc()}")
        
        if not show_to_user:
            return
            
        # ユーザー向けメッセージを生成
        user_message = ErrorHandler._get_user_friendly_api_error_message(error_type, error_msg, operation)
        await ui.send_error_message(user_message)
    
    @staticmethod
    def _get_user_friendly_api_error_message(error_type: str, error_msg: str, operation: str) -> str:
        """ユーザーフレンドリーなAPIエラーメッセージを生成"""
        if "AuthenticationError" in error_type:
            return f"{operation}に失敗しました。APIキーが無効または未設定です。設定を確認してください。"
        elif "RateLimitError" in error_type:
            return f"{operation}に失敗しました。APIのレート制限に達しました。しばらくお待ちください。"
        elif "InvalidRequestError" in error_type:
            return f"{operation}に失敗しました。リクエストに問題があります: {error_msg}"
        elif "APIConnectionError" in error_type:
            return f"{operation}に失敗しました。API接続エラーです。ネットワーク接続を確認してください。"
        elif "APITimeoutError" in error_type:
            return f"{operation}に失敗しました。APIがタイムアウトしました。再度お試しください。"
        else:
            return f"{operation}に失敗しました: {error_msg}"
    
    @staticmethod
    async def handle_validation_error(field_name: str, error_message: str, show_to_user: bool = True):
        """
        バリデーションエラーの処理
        
        Args:
            field_name: エラーが発生したフィールド名
            error_message: エラーメッセージ
            show_to_user: ユーザーにエラーメッセージを表示するか
        """
        log_msg = f"バリデーションエラー - {field_name}: {error_message}"
        app_logger.warning(log_msg)
        
        if show_to_user:
            await ui.send_error_message(f"入力エラー - {field_name}: {error_message}")
    
    @staticmethod
    async def handle_file_error(error: Exception, operation: str, filename: str = "", show_to_user: bool = True):
        """
        ファイル操作エラーの処理
        
        Args:
            error: 発生した例外
            operation: 実行していた操作名
            filename: 対象ファイル名
            show_to_user: ユーザーにエラーメッセージを表示するか
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        file_info = f" (ファイル: {filename})" if filename else ""
        log_msg = f"ファイル操作エラー - {operation}{file_info}: {error_type} - {error_msg}"
        app_logger.error(log_msg)
        
        if not show_to_user:
            return
            
        if "FileNotFoundError" in error_type:
            await ui.send_error_message(f"{operation}に失敗しました。ファイルが見つかりません{file_info}")
        elif "PermissionError" in error_type:
            await ui.send_error_message(f"{operation}に失敗しました。ファイルアクセス権限がありません{file_info}")
        elif "IsADirectoryError" in error_type:
            await ui.send_error_message(f"{operation}に失敗しました。ディレクトリが指定されています{file_info}")
        else:
            await ui.send_error_message(f"{operation}に失敗しました{file_info}: {error_msg}")
    
    @staticmethod
    async def handle_database_error(error: Exception, operation: str, show_to_user: bool = True):
        """
        データベース関連エラーの処理
        
        Args:
            error: 発生した例外
            operation: 実行していた操作名
            show_to_user: ユーザーにエラーメッセージを表示するか
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        log_msg = f"データベースエラー - {operation}: {error_type} - {error_msg}"
        app_logger.error(log_msg)
        app_logger.debug(f"スタックトレース:\n{traceback.format_exc()}")
        
        if show_to_user:
            await ui.send_error_message(f"データベース操作に失敗しました - {operation}: データの整合性を確認してください")
    
    @staticmethod
    async def handle_vector_store_error(error: Exception, operation: str, vs_id: str = "", show_to_user: bool = True):
        """
        ベクトルストア関連エラーの処理
        
        Args:
            error: 発生した例外
            operation: 実行していた操作名
            vs_id: ベクトルストアID
            show_to_user: ユーザーにエラーメッセージを表示するか
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        vs_info = f" (VS ID: {vs_id})" if vs_id else ""
        log_msg = f"ベクトルストアエラー - {operation}{vs_info}: {error_type} - {error_msg}"
        app_logger.error(log_msg)
        
        if not show_to_user:
            return
            
        if "vector_store" in error_msg.lower() or "not found" in error_msg.lower():
            await ui.send_error_message(f"ベクトルストア操作に失敗しました - {operation}: ベクトルストアが見つからないか、設定に問題があります{vs_info}")
        else:
            await ui.send_error_message(f"ベクトルストア操作に失敗しました - {operation}{vs_info}: {error_msg}")
    
    @staticmethod
    async def handle_unexpected_error(error: Exception, operation: str, show_to_user: bool = True):
        """
        予期しないエラーの処理
        
        Args:
            error: 発生した例外
            operation: 実行していた操作名
            show_to_user: ユーザーにエラーメッセージを表示するか
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        log_msg = f"予期しないエラー - {operation}: {error_type} - {error_msg}"
        app_logger.error(log_msg)
        app_logger.debug(f"スタックトレース:\n{traceback.format_exc()}")
        
        if show_to_user:
            await ui.send_error_message(f"予期しないエラーが発生しました - {operation}: システム管理者にお問い合わせください")
    
    @staticmethod
    def log_operation_start(operation: str, details: Optional[Dict[str, Any]] = None):
        """操作開始のログを記録"""
        if details:
            app_logger.info(f"🔧 {operation}開始", **details)
        else:
            app_logger.info(f"🔧 {operation}開始")
    
    @staticmethod
    def log_operation_success(operation: str, details: Optional[Dict[str, Any]] = None):
        """操作成功のログを記録"""
        if details:
            app_logger.info(f"✅ {operation}完了", **details)
        else:
            app_logger.info(f"✅ {operation}完了")
    
    @staticmethod
    async def safe_execute(operation: str, func, *args, show_errors: bool = True, **kwargs):
        """
        安全な関数実行（例外処理付き）
        
        Args:
            operation: 操作名
            func: 実行する関数
            *args: 関数の引数
            show_errors: エラーをユーザーに表示するか
            **kwargs: 関数のキーワード引数
        
        Returns:
            関数の実行結果、エラー時はNone
        """
        try:
            ErrorHandler.log_operation_start(operation)
            result = await func(*args, **kwargs) if hasattr(func, '__await__') else func(*args, **kwargs)
            ErrorHandler.log_operation_success(operation)
            return result
        except Exception as e:
            await ErrorHandler.handle_unexpected_error(e, operation, show_errors)
            return None


# 短縮形のエイリアス
error_handler = ErrorHandler