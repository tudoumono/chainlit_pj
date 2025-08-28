"""
プロジェクト設定管理
Pydanticベースの型安全な設定管理システム
"""

from pathlib import Path
from typing import Dict, List, Optional, Union
from pydantic import BaseSettings, Field, validator, root_validator
from dataclasses import dataclass
import os


class ProjectPaths:
    """プロジェクトパスの統一管理（Pathlib使用）"""
    
    # プロジェクトルートを自動検出
    PROJECT_ROOT = Path(__file__).parent.parent.resolve()
    
    # 主要ディレクトリ
    UPLOADS_DIR = PROJECT_ROOT / "uploads"
    SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots" 
    DATA_DIR = PROJECT_ROOT / "data"
    DOCS_DIR = PROJECT_ROOT / "docs"
    TEST_SCRIPTS_DIR = PROJECT_ROOT / "test_scripts"
    HANDLERS_DIR = PROJECT_ROOT / "handlers"
    UTILS_DIR = PROJECT_ROOT / "utils"
    
    # 設定ファイル
    CHAINLIT_CONFIG_DIR = PROJECT_ROOT / ".chainlit"
    TOOLS_CONFIG_PATH = CHAINLIT_CONFIG_DIR / "tools_config.json"
    ENV_FILE = PROJECT_ROOT / ".env"
    ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"
    
    # データベース
    CHAT_HISTORY_DB = DATA_DIR / "chat_history.db"
    CIPHER_SESSIONS_DB = DATA_DIR / "cipher-sessions.db"
    
    # ログファイル
    LOGS_DIR = PROJECT_ROOT / "logs"
    WEBSOCKET_DEBUG_LOG = LOGS_DIR / "websocket_debug.log"
    APP_LOG = LOGS_DIR / "app.log"
    
    # テスト関連
    TEST_RESULTS_DIR = TEST_SCRIPTS_DIR / "results"
    TEST_REPORT_FILE = TEST_RESULTS_DIR / "test_report.json"
    COMPREHENSIVE_TEST_SUITE = TEST_SCRIPTS_DIR / "comprehensive_test_suite.json"
    
    @classmethod
    def ensure_directories(cls):
        """必要なディレクトリを作成"""
        directories = [
            cls.UPLOADS_DIR,
            cls.SCREENSHOTS_DIR,
            cls.DATA_DIR,
            cls.LOGS_DIR,
            cls.TEST_RESULTS_DIR,
            cls.CHAINLIT_CONFIG_DIR
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_relative_path(cls, absolute_path: Union[str, Path]) -> Path:
        """絶対パスをプロジェクト相対パスに変換"""
        absolute_path = Path(absolute_path)
        try:
            return absolute_path.relative_to(cls.PROJECT_ROOT)
        except ValueError:
            return absolute_path


class AppSettings(BaseSettings):
    """アプリケーション設定（Pydantic BaseSettings使用）"""
    
    # OpenAI API設定
    openai_api_key: str = Field(..., description="OpenAI API Key")
    default_model: str = Field(default="gpt-4o-mini", description="Default OpenAI model")
    
    # プロキシ設定
    http_proxy: Optional[str] = Field(default=None, description="HTTP Proxy URL")
    https_proxy: Optional[str] = Field(default=None, description="HTTPS Proxy URL") 
    proxy_enabled: bool = Field(default=False, description="Enable proxy")
    
    # ベクトルストア設定
    company_vector_store_id: Optional[str] = Field(default=None, description="Company Vector Store ID")
    personal_vector_store_id: Optional[str] = Field(default=None, description="Personal Vector Store ID")
    
    # サーバー設定
    chainlit_host: str = Field(default="0.0.0.0", description="Chainlit host")
    chainlit_port: int = Field(default=8000, description="Chainlit port")
    
    # データベース設定
    db_path: Path = Field(default=ProjectPaths.CHAT_HISTORY_DB, description="Database path")
    
    # ファイル制限
    max_file_size: int = Field(default=10 * 1024 * 1024, description="Maximum file size (10MB)")
    max_files_per_upload: int = Field(default=5, description="Maximum files per upload")
    
    # アップロード設定
    upload_dir: Path = Field(default=ProjectPaths.UPLOADS_DIR, description="Upload directory")
    allowed_file_extensions: List[str] = Field(
        default=['.txt', '.md', '.pdf', '.docx', '.py', '.js', '.html', '.css', '.json'],
        description="Allowed file extensions"
    )
    
    # ログ設定
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Path = Field(default=ProjectPaths.APP_LOG, description="Log file path")
    debug_websocket_log: Path = Field(default=ProjectPaths.WEBSOCKET_DEBUG_LOG, description="WebSocket debug log")
    
    # パフォーマンス設定
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    @validator('openai_api_key')
    def api_key_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('OpenAI API key is required and cannot be empty')
        return v.strip()
    
    @validator('default_model')
    def validate_model_name(cls, v):
        allowed_models = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo']
        if v not in allowed_models:
            raise ValueError(f'Model must be one of: {", ".join(allowed_models)}')
        return v
    
    @validator('chainlit_port')
    def validate_port(cls, v):
        if not (1024 <= v <= 65535):
            raise ValueError('Port must be between 1024 and 65535')
        return v
    
    @validator('max_file_size')
    def validate_file_size(cls, v):
        if v <= 0 or v > 100 * 1024 * 1024:  # 100MB limit
            raise ValueError('File size must be between 1 byte and 100MB')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of: {", ".join(allowed_levels)}')
        return v.upper()
    
    @root_validator(pre=True)
    def ensure_paths_exist(cls, values):
        """パス設定時に必要なディレクトリを作成"""
        ProjectPaths.ensure_directories()
        return values
    
    class Config:
        env_file = ProjectPaths.ENV_FILE
        env_file_encoding = 'utf-8'
        case_sensitive = False
        # 環境変数のプレフィックス（例: CHAINLIT_OPENAI_API_KEY）
        env_prefix = 'CHAINLIT_'


class MimeTypeSettings(BaseSettings):
    """MIME型設定"""
    
    # コードファイル
    code_types: Dict[str, str] = Field(default_factory=lambda: {
        '.py': 'text/x-python',
        '.js': 'text/javascript', 
        '.ts': 'application/typescript',
        '.html': 'text/html',
        '.css': 'text/css',
        '.json': 'application/json',
        '.cpp': 'text/x-c++',
        '.cs': 'text/x-csharp',
        '.go': 'text/x-golang',
        '.java': 'text/x-java',
        '.php': 'text/x-php',
        '.rb': 'text/x-ruby',
        '.sh': 'application/x-sh',
    })
    
    # ドキュメントファイル
    document_types: Dict[str, str] = Field(default_factory=lambda: {
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.tex': 'text/x-tex',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    })
    
    @property
    def all_types(self) -> Dict[str, str]:
        """すべてのMIME型を統合"""
        return {**self.code_types, **self.document_types}
    
    def get_mime_type(self, file_extension: str) -> Optional[str]:
        """ファイル拡張子からMIME型を取得"""
        return self.all_types.get(file_extension.lower())
    
    def is_supported_type(self, file_extension: str) -> bool:
        """サポート対象のファイル型かチェック"""
        return file_extension.lower() in self.all_types


# シングルトンインスタンス
project_paths = ProjectPaths()
app_settings = AppSettings()
mime_settings = MimeTypeSettings()


def get_app_settings() -> AppSettings:
    """アプリケーション設定を取得"""
    return app_settings


def get_project_paths() -> ProjectPaths:
    """プロジェクトパス設定を取得"""
    return project_paths


def get_mime_settings() -> MimeTypeSettings:
    """MIME型設定を取得"""
    return mime_settings


# 後方互換性のためのエイリアス
def get_project_root() -> Path:
    """プロジェクトルートパスを取得（後方互換性）"""
    return ProjectPaths.PROJECT_ROOT