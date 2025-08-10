"""
環境チェックスクリプト
- 必要なライブラリのインポート確認
- ファイルの準備状態確認
- 設定の検証
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple, Dict
import json
import platform

# Windowsでカラー出力を有効化
if platform.system() == 'Windows':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

# カラー出力用のANSIコード
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """ヘッダーを表示"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")

def print_section(text: str):
    """セクションヘッダーを表示"""
    print(f"\n{Colors.BOLD}▶ {text}{Colors.ENDC}")
    print("-" * 40)

def check_mark(success: bool) -> str:
    """チェックマークを返す"""
    return f"{Colors.GREEN}✓{Colors.ENDC}" if success else f"{Colors.RED}✗{Colors.ENDC}"

def check_python_version() -> Tuple[bool, str]:
    """Pythonバージョンをチェック"""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    is_valid = version.major >= 3 and version.minor >= 10
    return is_valid, version_str

def check_imports() -> Dict[str, bool]:
    """必要なライブラリのインポートをチェック"""
    libraries = {
        # Core
        'chainlit': 'Chainlit',
        'openai': 'OpenAI',
        'dotenv': 'python-dotenv',
        
        # Database
        'aiosqlite': 'aiosqlite',
        'sqlite3': 'sqlite3 (built-in)',
        
        # File handling
        'pypdf': 'pypdf',
        'PIL': 'Pillow',
        
        # Export
        'reportlab': 'ReportLab',
        'jinja2': 'Jinja2',
        
        # Utilities
        'httpx': 'httpx',
        'typing_extensions': 'typing-extensions',
        
        # Standard library
        'uuid': 'uuid (built-in)',
        'json': 'json (built-in)',
        'pathlib': 'pathlib (built-in)',
        'asyncio': 'asyncio (built-in)',
    }
    
    results = {}
    for module, name in libraries.items():
        try:
            __import__(module)
            results[name] = True
        except ImportError:
            results[name] = False
    
    return results

def check_files() -> Dict[str, bool]:
    """必要なファイルの存在をチェック"""
    base_path = Path.cwd()
    
    files = {
        # Core files
        'app.py': base_path / 'app.py',
        'pyproject.toml': base_path / 'pyproject.toml',
        '.env.example': base_path / '.env.example',
        '.env': base_path / '.env',
        
        # Directories
        'pages/': base_path / 'pages',
        'utils/': base_path / 'utils',
        
        # Documentation
        'README.md': base_path / 'README.md',
        '開発順序計画書.md': base_path / '開発順序計画書.md',
        'Phase1_動作確認.md': base_path / 'Phase1_動作確認.md',
        
        # Virtual environment
        '.venv/': base_path / '.venv',
    }
    
    results = {}
    for name, path in files.items():
        results[name] = path.exists()
    
    return results

def check_env_config() -> Dict[str, str]:
    """環境変数の設定をチェック"""
    from dotenv import load_dotenv
    
    load_dotenv()
    
    config = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', 'Not set'),
        'DEFAULT_MODEL': os.getenv('DEFAULT_MODEL', 'Not set'),
        'DB_PATH': os.getenv('DB_PATH', 'Not set'),
        'CHAINLIT_HOST': os.getenv('CHAINLIT_HOST', 'Not set'),
        'CHAINLIT_PORT': os.getenv('CHAINLIT_PORT', 'Not set'),
    }
    
    # APIキーをマスク
    if config['OPENAI_API_KEY'] != 'Not set':
        if config['OPENAI_API_KEY'] == 'your_api_key_here':
            config['OPENAI_API_KEY'] = '⚠️ Placeholder (needs real key)'
        else:
            key = config['OPENAI_API_KEY']
            config['OPENAI_API_KEY'] = f"sk-{'*' * 8}...{key[-4:]}" if len(key) > 4 else '***'
    
    return config

def check_app_py() -> Tuple[bool, List[str]]:
    """app.pyの基本構造をチェック"""
    app_file = Path('app.py')
    if not app_file.exists():
        return False, ["app.py not found"]
    
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_elements = [
        'import chainlit as cl',
        '@cl.on_chat_start',
        '@cl.on_message',
        'async def on_chat_start',
        'async def on_message',
    ]
    
    missing = []
    for element in required_elements:
        if element not in content:
            missing.append(element)
    
    return len(missing) == 0, missing

def main():
    """メインのチェック処理"""
    print_header("AI Workspace Environment Check")
    
    # Pythonバージョンチェック
    print_section("Python Version")
    py_valid, py_version = check_python_version()
    print(f"{check_mark(py_valid)} Python {py_version} {'(>=3.10 required)' if not py_valid else ''}")
    
    # ライブラリインポートチェック
    print_section("Library Imports")
    imports = check_imports()
    all_imports_ok = True
    for lib, available in imports.items():
        if not available and 'built-in' not in lib:
            all_imports_ok = False
        status = check_mark(available)
        color = Colors.GREEN if available else Colors.RED if 'built-in' not in lib else Colors.YELLOW
        print(f"{status} {color}{lib}{Colors.ENDC}")
    
    # ファイル存在チェック
    print_section("File Structure")
    files = check_files()
    all_files_ok = True
    for name, exists in files.items():
        if not exists and name not in ['.env', '.venv/']:
            all_files_ok = False
        status = check_mark(exists)
        color = Colors.GREEN if exists else Colors.YELLOW if name in ['.env', '.venv/'] else Colors.RED
        print(f"{status} {color}{name}{Colors.ENDC}")
    
    # 環境変数チェック
    print_section("Environment Variables")
    if files.get('.env', False):
        env_config = check_env_config()
        for key, value in env_config.items():
            is_set = value != 'Not set'
            status = check_mark(is_set)
            color = Colors.GREEN if is_set else Colors.YELLOW
            print(f"{status} {key}: {color}{value}{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}⚠️ .env file not found. Copy .env.example to .env{Colors.ENDC}")
    
    # app.py構造チェック
    print_section("app.py Structure")
    app_valid, missing_elements = check_app_py()
    if app_valid:
        print(f"{check_mark(True)} All required elements found")
    else:
        for element in missing_elements:
            print(f"{check_mark(False)} Missing: {Colors.RED}{element}{Colors.ENDC}")
    
    # 総合評価
    print_header("Summary")
    
    issues = []
    if not py_valid:
        issues.append("Python version < 3.10")
    if not all_imports_ok:
        missing_libs = [lib for lib, available in imports.items() 
                       if not available and 'built-in' not in lib]
        if missing_libs:
            issues.append(f"Missing libraries: {', '.join(missing_libs)}")
    if not all_files_ok:
        missing_files = [name for name, exists in files.items() 
                        if not exists and name not in ['.env', '.venv/']]
        if missing_files:
            issues.append(f"Missing files: {', '.join(missing_files)}")
    if not app_valid:
        issues.append("app.py structure incomplete")
    
    if not issues:
        print(f"{Colors.GREEN}✅ All checks passed! Environment is ready.{Colors.ENDC}")
        print(f"\n{Colors.BOLD}Next steps:{Colors.ENDC}")
        if not files.get('.venv/', False):
            print(f"  1. Run: {Colors.BLUE}uv venv{Colors.ENDC}")
            print(f"  2. Run: {Colors.BLUE}uv pip install -e .{Colors.ENDC}")
        if not files.get('.env', False):
            print(f"  3. Copy .env.example to .env and add your API key")
        print(f"  4. Run: {Colors.BLUE}uv run chainlit run app.py{Colors.ENDC}")
    else:
        print(f"{Colors.RED}❌ Some issues found:{Colors.ENDC}")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        
        print(f"\n{Colors.BOLD}To fix:{Colors.ENDC}")
        if not all_imports_ok:
            print(f"  • Run: {Colors.BLUE}uv pip install -e .{Colors.ENDC}")
        if not py_valid:
            print(f"  • Install Python 3.10 or higher")
        if not all_files_ok:
            print(f"  • Check missing files and directories")

if __name__ == "__main__":
    main()