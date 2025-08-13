"""
OpenAI Tools機能の設定管理
- Web検索ツール
- ファイル検索ツール
- その他のツール設定
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path


class ToolsConfig:
    """Tools機能の設定管理クラス"""
    
    def __init__(self, config_file: str = ".chainlit/tools_config.json"):
        """
        初期化
        
        Args:
            config_file: 設定ファイルのパス
        """
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込み"""
        # デフォルト設定
        default_config = {
            "enabled": True,  # Tools機能全体の有効/無効
            "tools": {
                "web_search": {
                    "enabled": True,
                    "name": "web_search",
                    "description": "Search the web for current information",
                    "auto_invoke": True  # 自動的にツールを呼び出すか
                },
                "file_search": {
                    "enabled": True,
                    "name": "file_search", 
                    "description": "Search through uploaded files and documents",
                    "auto_invoke": True,
                    "file_ids": []  # 検索対象のファイルID
                },
                "code_interpreter": {
                    "enabled": False,
                    "name": "code_interpreter",
                    "description": "Execute Python code for calculations and data analysis",
                    "auto_invoke": False
                },
                "custom_functions": {
                    "enabled": False,
                    "functions": []  # カスタム関数のリスト
                }
            },
            "settings": {
                "tool_choice": "auto",  # "auto", "none", "required", または特定のツール
                "parallel_tool_calls": True,  # 並列ツール呼び出しを許可
                "max_tools_per_call": 5,  # 1回の呼び出しで使用可能な最大ツール数
                "web_search_max_results": 5,  # Web検索の最大結果数
                "file_search_max_chunks": 20,  # ファイル検索の最大チャンク数
                "show_tool_calls": True,  # UIにツール呼び出しを表示
                "show_tool_results": True  # UIにツール結果を表示
            }
        }
        
        # 設定ファイルが存在する場合は読み込み
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # デフォルト設定に読み込んだ設定をマージ
                    return self._merge_configs(default_config, loaded_config)
            except Exception as e:
                print(f"⚠️ 設定ファイルの読み込みエラー: {e}")
                return default_config
        else:
            # 設定ファイルが存在しない場合は作成
            self._save_config(default_config)
            return default_config
    
    def _merge_configs(self, default: Dict, loaded: Dict) -> Dict:
        """設定をマージ（再帰的）"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_config(self, config: Dict[str, Any] = None) -> None:
        """設定を保存"""
        if config is None:
            config = self.config
        
        # ディレクトリを作成
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # 設定を保存
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def is_enabled(self) -> bool:
        """Tools機能が有効かどうか"""
        return self.config.get("enabled", False)
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """特定のツールが有効かどうか"""
        if not self.is_enabled():
            return False
        return self.config.get("tools", {}).get(tool_name, {}).get("enabled", False)
    
    def get_enabled_tools(self) -> List[str]:
        """有効なツールのリストを取得"""
        if not self.is_enabled():
            return []
        
        enabled_tools = []
        for tool_name, tool_config in self.config.get("tools", {}).items():
            if tool_config.get("enabled", False):
                enabled_tools.append(tool_name)
        return enabled_tools
    
    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """特定のツールの設定を取得"""
        return self.config.get("tools", {}).get(tool_name, {})
    
    def get_setting(self, setting_name: str, default: Any = None) -> Any:
        """設定値を取得"""
        return self.config.get("settings", {}).get(setting_name, default)
    
    def update_tool_status(self, tool_name: str, enabled: bool) -> None:
        """ツールの有効/無効を更新"""
        if tool_name in self.config.get("tools", {}):
            self.config["tools"][tool_name]["enabled"] = enabled
            self._save_config()
    
    def update_setting(self, setting_name: str, value: Any) -> None:
        """設定値を更新"""
        if "settings" not in self.config:
            self.config["settings"] = {}
        self.config["settings"][setting_name] = value
        self._save_config()
    
    def add_file_for_search(self, file_id: str) -> None:
        """ファイル検索の対象ファイルを追加"""
        if "file_search" in self.config.get("tools", {}):
            if "file_ids" not in self.config["tools"]["file_search"]:
                self.config["tools"]["file_search"]["file_ids"] = []
            if file_id not in self.config["tools"]["file_search"]["file_ids"]:
                self.config["tools"]["file_search"]["file_ids"].append(file_id)
                self._save_config()
    
    def remove_file_from_search(self, file_id: str) -> None:
        """ファイル検索の対象ファイルを削除"""
        if "file_search" in self.config.get("tools", {}):
            if "file_ids" in self.config["tools"]["file_search"]:
                if file_id in self.config["tools"]["file_search"]["file_ids"]:
                    self.config["tools"]["file_search"]["file_ids"].remove(file_id)
                    self._save_config()
    
    def get_search_file_ids(self) -> List[str]:
        """ファイル検索の対象ファイルIDリストを取得"""
        return self.config.get("tools", {}).get("file_search", {}).get("file_ids", [])
    
    def reset_to_default(self) -> None:
        """設定をデフォルトにリセット"""
        self.config = self._load_config()
        # 設定ファイルを削除して再作成
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        self._save_config()
    
    def to_dict(self) -> Dict[str, Any]:
        """設定を辞書として取得"""
        return self.config.copy()
    
    def build_tools_parameter(self) -> Optional[List[Dict[str, Any]]]:
        """
        OpenAI APIのtoolsパラメータを構築
        注: Responses APIではweb_search_previewタイプを使用
        
        Returns:
            有効なツールのリスト（API用フォーマット）
        """
        if not self.is_enabled():
            return None
        
        tools = []
        
        # Web検索ツール (web_search_previewタイプとして定義)
        if self.is_tool_enabled("web_search"):
            tools.append({
                "type": "web_search_preview",
                "search_context_size": "medium",  # low, medium, high
            })
        
        # ファイル検索ツール (file_searchタイプとして定義)
        if self.is_tool_enabled("file_search"):
            file_search_config = {
                "type": "file_search"
            }
            # ファイルIDがある場合は追加
            file_ids = self.get_search_file_ids()
            if file_ids:
                file_search_config["file_search"] = {
                    "vector_store_ids": file_ids
                }
            tools.append(file_search_config)
        
        # コードインタープリター (code_interpreterタイプとして定義)
        if self.is_tool_enabled("code_interpreter"):
            tools.append({
                "type": "code_interpreter"
            })
        
        # カスタム関数
        if self.is_tool_enabled("custom_functions"):
            custom_functions = self.config.get("tools", {}).get("custom_functions", {}).get("functions", [])
            for func in custom_functions:
                tools.append({
                    "type": "function",
                    "function": func
                })
        
        return tools if tools else None


# グローバルインスタンス
tools_config = ToolsConfig()
