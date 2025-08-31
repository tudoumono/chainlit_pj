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
            "vector_store_layers": {  # ベクトルストア層の有効/無効
                "company": True,    # 1層目：会社全体
                "personal": True,   # 2層目：個人ユーザー
                "thread": True      # 3層目：チャット単位
            },
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
                    "file_ids": [],  # 検索対象のファイルID
                    "vector_store_ids": []  # 参照対象のベクトルストアID（カンマ区切りで複数指定可）
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
    
    def get_tools_status(self) -> Dict[str, bool]:
        """
        各ツールの有効/無効状態を取得
        
        Returns:
            ツール名と状態の辞書
        """
        status = {}
        if self.config and 'tools' in self.config:
            for tool_name, tool_config in self.config['tools'].items():
                status[tool_name] = tool_config.get('enabled', False)
        return status
    
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
    
    def update_vector_store_ids(self, vector_store_ids: str) -> None:
        """
        ベクトルストアIDを更新（カンマ区切りの文字列から）
        
        Args:
            vector_store_ids: カンマ区切りのベクトルストアID文字列
        """
        if "file_search" in self.config.get("tools", {}):
            # カンマ区切りの文字列をリストに変換
            ids_list = [id.strip() for id in vector_store_ids.split(',') if id.strip()]
            self.config["tools"]["file_search"]["vector_store_ids"] = ids_list
            self._save_config()
    
    def get_vector_store_ids(self) -> List[str]:
        """ベクトルストアIDリストを取得"""
        return self.config.get("tools", {}).get("file_search", {}).get("vector_store_ids", [])
    
    def get_vector_store_ids_string(self) -> str:
        """ベクトルストアIDをカンマ区切り文字列として取得"""
        ids = self.get_vector_store_ids()
        return ",".join(ids) if ids else ""
    
    def update_enabled(self, enabled: bool) -> None:
        """
        Tools機能全体の有効/無効を更新
        
        Args:
            enabled: 有効にする場合はTrue
        """
        self.config["enabled"] = enabled
        self._save_config()
    
    def enable_all_tools(self) -> None:
        """すべてのツールを有効化"""
        self.config["enabled"] = True
        for tool_name in self.config.get("tools", {}):
            self.config["tools"][tool_name]["enabled"] = True
        self._save_config()
    
    def disable_all_tools(self) -> None:
        """すべてのツールを無効化"""
        self.config["enabled"] = False
        self._save_config()
    
    def enable_tool(self, tool_name: str) -> None:
        """特定のツールを有効化"""
        if tool_name in self.config.get("tools", {}):
            self.config["enabled"] = True  # Tools機能全体も有効に
            self.config["tools"][tool_name]["enabled"] = True
            self._save_config()
    
    def disable_tool(self, tool_name: str) -> None:
        """特定のツールを無効化"""
        if tool_name in self.config.get("tools", {}):
            self.config["tools"][tool_name]["enabled"] = False
            self._save_config()
    
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
    
    def is_layer_enabled(self, layer_name: str) -> bool:
        """ベクトルストア層が有効かどうか"""
        return self.config.get("vector_store_layers", {}).get(layer_name, True)
    
    def set_layer_enabled(self, layer_name: str, enabled: bool) -> None:
        """ベクトルストア層の有効/無効を設定"""
        if "vector_store_layers" not in self.config:
            self.config["vector_store_layers"] = {}
        self.config["vector_store_layers"][layer_name] = enabled
        self._save_config()
    
    def build_tools_parameter(self, session=None) -> Optional[List[Dict[str, Any]]]:
        """
        OpenAI APIのtoolsパラメータを構築
        注: Responses APIではweb_search_previewタイプを使用
        
        Args:
            session: Chainlitセッションオブジェクト（ベクトルストアID取得用）
        
        Returns:
            有効なツールのリスト（API用フォーマット）
        """
        print(f"🔍 [DEBUG] build_tools_parameter - セッション: {session is not None}")
        if session:
            print(f"🔍 [DEBUG] セッションキー: {list(session.keys()) if isinstance(session, dict) else 'Not a dict'}")
        
        # Tools全体が無効でも、個別のツールが有効なら動作させる
        tools = []
        
        # Web検索ツール (web_search_previewタイプとして定義)
        if self.is_enabled() and self.is_tool_enabled("web_search"):
            tools.append({
                "type": "web_search_preview",
                "search_context_size": "medium",  # low, medium, high
            })
        
        # ファイル検索ツール (file_searchタイプとして定義)
        # Tools全体が無効でもfile_searchが有効なら動作
        if self.is_tool_enabled("file_search"):
            print(f"🔍 [DEBUG] file_searchツール有効")
            vector_store_ids = []
            
            # 1層目：会社全体（.envから）
            if self.is_layer_enabled("company"):
                print(f"🔍 [DEBUG] 会社全体VS層有効")
                # .envから取得
                company_vs_id = os.getenv("COMPANY_VECTOR_STORE_ID")
                
                # セッションからも取得を試みる（設定更新後の値）
                if session and not company_vs_id:
                    company_vs_id = session.get("company_vs_id")
                    if not company_vs_id:
                        vs_ids = session.get("vector_store_ids", {})
                        company_vs_id = vs_ids.get("company")
                
                print(f"🔍 [DEBUG] 会社全体VS ID: {company_vs_id[:8] if company_vs_id else 'None'}...")
                if company_vs_id and company_vs_id.strip():
                    vector_store_ids.append(company_vs_id.strip())
                    print(f"✅ 会社VSを検索対象に追加: {company_vs_id[:8]}...")
            
            # 2層目：個人（セッションから）
            if session and self.is_layer_enabled("personal"):
                print(f"🔍 [DEBUG] 個人VS層有効")
                # 複数の方法で取得を試みる
                personal_vs_id = session.get("personal_vs_id")
                if not personal_vs_id:
                    vs_ids = session.get("vector_store_ids", {})
                    personal_vs_id = vs_ids.get("personal")
                
                print(f"🔍 [DEBUG] 個人VS ID: {personal_vs_id[:8] if personal_vs_id else 'None'}...")
                if personal_vs_id and personal_vs_id.strip():
                    vector_store_ids.append(personal_vs_id.strip())
                    print(f"✅ 個人VSを検索対象に追加: {personal_vs_id[:8]}...")
            
            # 3層目：チャット（セッションから）
            if session and self.is_layer_enabled("thread"):
                print(f"🔍 [DEBUG] チャットVS層有効")
                # 複数の方法で取得を試みる
                chat_vs_id = session.get("chat_vs_id")
                print(f"🔍 [DEBUG] chat_vs_id直接: {chat_vs_id[:8] if chat_vs_id else 'None'}...")
                
                if not chat_vs_id:
                    # 互換性のため古い名前もチェック
                    chat_vs_id = session.get("session_vs_id") or session.get("thread_vs_id")
                    print(f"🔍 [DEBUG] 互換性チェック: {chat_vs_id[:8] if chat_vs_id else 'None'}...")
                
                if not chat_vs_id:
                    vs_ids = session.get("vector_store_ids", {})
                    chat_vs_id = vs_ids.get("chat") or vs_ids.get("session") or vs_ids.get("thread")
                    print(f"🔍 [DEBUG] vs_ids辞書から: {chat_vs_id[:8] if chat_vs_id else 'None'}...")
                
                if chat_vs_id and chat_vs_id.strip():
                    vector_store_ids.append(chat_vs_id.strip())
                    print(f"✅ チャットVSを検索対象に追加: {chat_vs_id[:8]}...")
            
            # vector_store_idsが空の場合はfile_searchツールを追加しない
            # OpenAI APIは空のvector_store_idsを許可しないため
            print(f"🔍 [DEBUG] 収集されたベクトルストアID数: {len(vector_store_ids)}")
            if vector_store_ids:
                print(f"🔍 [DEBUG] ベクトルストアIDリスト: {[vs[:8] + '...' for vs in vector_store_ids]}")
                # Responses API形式のfile_searchツール構造
                file_search_config = {
                    "type": "file_search",
                    "vector_store_ids": vector_store_ids  # 直接vector_store_idsを配置
                }
                tools.append(file_search_config)
                print(f"✅ file_searchツールを追加しました")
            else:
                print("⚠️ file_searchツールは有効ですが、ベクトルストアIDが設定されていないためスキップします")
                print("   ヒント: 1) 会社VSのIDを.envまたは設定画面で設定")
                print("         2) 個人VSのIDをユーザー設定で設定")
                print("         3) ファイルを添付してセッションVSを作成")
        
        # コードインタープリター (code_interpreterタイプとして定義)
        if self.is_enabled() and self.is_tool_enabled("code_interpreter"):
            tools.append({
                "type": "code_interpreter"
            })
        
        # カスタム関数
        if self.is_enabled() and self.is_tool_enabled("custom_functions"):
            custom_functions = self.config.get("tools", {}).get("custom_functions", {}).get("functions", [])
            for func in custom_functions:
                tools.append({
                    "type": "function",
                    "function": func
                })
        
        print(f"🔍 [DEBUG] 最終的なツール数: {len(tools)}")
        if tools:
            for i, tool in enumerate(tools):
                print(f"🔍 [DEBUG] ツール[{i}]: {tool.get('type', 'unknown')}")
                if tool.get('type') == 'file_search':
                    print(f"🔍 [DEBUG]   - vector_store_ids: {tool.get('vector_store_ids', [])}")
        
        return tools if tools else None


# グローバルインスタンス
tools_config = ToolsConfig()
