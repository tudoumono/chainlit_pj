"""
設定管理モジュール
- .envファイルの読み書き
- OpenAI API接続テスト
- 設定の検証
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dotenv import load_dotenv, set_key, find_dotenv
import openai
from openai import OpenAI
import httpx
import asyncio
import json


class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.env_file = find_dotenv() or Path(".env")
        if not self.env_file:
            # .envファイルが存在しない場合、.env.exampleからコピー
            self._create_env_from_example()
        self.load_config()
    
    def _create_env_from_example(self):
        """env.exampleから.envファイルを作成"""
        example_file = Path(".env.example")
        env_file = Path(".env")
        
        if example_file.exists() and not env_file.exists():
            env_file.write_text(example_file.read_text())
            self.env_file = env_file
    
    def load_config(self) -> Dict[str, str]:
        """環境変数を読み込み"""
        load_dotenv(self.env_file, override=True)
        
        config = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "HTTP_PROXY": os.getenv("HTTP_PROXY", ""),
            "HTTPS_PROXY": os.getenv("HTTPS_PROXY", ""),
            "PROXY_ENABLED": os.getenv("PROXY_ENABLED", "false").lower() == "true",
            "COMPANY_VECTOR_STORE_ID": os.getenv("COMPANY_VECTOR_STORE_ID", ""),
            "PERSONAL_VECTOR_STORE_ID": os.getenv("PERSONAL_VECTOR_STORE_ID", ""),
            "DEFAULT_MODEL": os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
            "DB_PATH": os.getenv("DB_PATH", "chat_history.db"),
            "CHAINLIT_HOST": os.getenv("CHAINLIT_HOST", "0.0.0.0"),
            "CHAINLIT_PORT": os.getenv("CHAINLIT_PORT", "8000"),
        }
        
        return config
    
    def save_config(self, config: Dict[str, str]) -> bool:
        """設定を.envファイルに保存"""
        try:
            for key, value in config.items():
                if value:  # 空でない値のみ保存
                    # クォーテーションを避けるため、quote_mode='never'を使用
                    # quote_mode='never'は値をクォートしない
                    try:
                        set_key(self.env_file, key, value, quote_mode='never')
                    except TypeError:
                        # 古いバージョンのpython-dotenvの場合
                        set_key(self.env_file, key, value)
                    
                    # 環境変数を即座に更新
                    os.environ[key] = value
            
            # 設定を再読み込みして確実に反映
            load_dotenv(self.env_file, override=True)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_api_key(self) -> str:
        """APIキーを取得"""
        return os.getenv("OPENAI_API_KEY", "")
    
    def update_env_value(self, key: str, value: str) -> bool:
        """
        .envファイルの特定の値を更新
        
        Args:
            key: 更新するキー
            value: 新しい値
        
        Returns:
            成功/失敗
        """
        try:
            # 現在の.envファイルを読み込み
            env_path = os.path.join(os.getcwd(), '.env')
            lines = []
            key_found = False
            
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith(f"{key}="):
                            lines.append(f"{key}={value}\n")
                            key_found = True
                        else:
                            lines.append(line)
            
            # キーが存在しない場合は追加
            if not key_found:
                lines.append(f"{key}={value}\n")
            
            # ファイルに書き込み
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            # 環境変数も更新
            os.environ[key] = value
            
            return True
        
        except Exception as e:
            print(f"Error updating .env file: {e}")
            return False
    
    def set_api_key(self, api_key: str) -> bool:
        """APIキーを設定"""
        success = self.save_config({"OPENAI_API_KEY": api_key})
        if success:
            # 環境変数を即座に更新（save_configでも行うが念のため）
            os.environ["OPENAI_API_KEY"] = api_key
        return success
    
    def get_proxy_settings(self) -> Dict[str, str]:
        """プロキシ設定を取得"""
        return {
            "HTTP_PROXY": os.getenv("HTTP_PROXY", ""),
            "HTTPS_PROXY": os.getenv("HTTPS_PROXY", ""),
            "PROXY_ENABLED": os.getenv("PROXY_ENABLED", "false").lower() == "true",
        }
    
    def set_proxy_settings(self, http_proxy: str = "", https_proxy: str = "", proxy_enabled: bool = False) -> bool:
        """プロキシ設定を保存"""
        config = {
            "HTTP_PROXY": http_proxy,
            "HTTPS_PROXY": https_proxy,
            "PROXY_ENABLED": "true" if proxy_enabled else "false"
        }
        return self.save_config(config)
    
    def get_available_models(self) -> List[str]:
        """利用可能なモデルリストを動的に取得"""
        default_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
        
        api_key = self.get_api_key()
        if not api_key:
            return default_models
        
        try:
            # プロキシ設定を適用
            if os.getenv("PROXY_ENABLED", "false").lower() == "true":
                proxy = os.getenv("HTTPS_PROXY", "")
                if proxy:
                    os.environ["HTTPS_PROXY"] = proxy
                    os.environ["HTTP_PROXY"] = proxy
            
            client = OpenAI(api_key=api_key)
            models = client.models.list()
            
            # チャット補完に使用可能なモデルをフィルタリング
            chat_models = []
            for model in models:
                model_id = model.id
                # GPTモデル、o1モデル、その他のチャット可能モデルを含める
                if any(prefix in model_id for prefix in ["gpt-", "o1-", "claude-", "gemini-"]):
                    chat_models.append(model_id)
            
            # モデル名でソート（新しいモデルが上に来るように）
            return sorted(chat_models, reverse=True) if chat_models else default_models
        
        except Exception as e:
            print(f"Error fetching models: {e}")
            return default_models
    
    def get_vector_store_ids(self) -> Dict[str, str]:
        """ベクトルストアIDを取得"""
        return {
            "company": os.getenv("COMPANY_VECTOR_STORE_ID", ""),
            "personal": os.getenv("PERSONAL_VECTOR_STORE_ID", ""),
        }
    
    def set_vector_store_ids(self, company_id: str = "", personal_id: str = "") -> bool:
        """ベクトルストアIDを設定"""
        config = {}
        if company_id:
            config["COMPANY_VECTOR_STORE_ID"] = company_id
        if personal_id:
            config["PERSONAL_VECTOR_STORE_ID"] = personal_id
        return self.save_config(config)
    
    async def test_connection(self) -> Tuple[bool, str, Optional[List[str]]]:
        """
        OpenAI API接続テスト
        
        Returns:
            Tuple[bool, str, Optional[List[str]]]: 
                - 成功/失敗のフラグ
                - メッセージ
                - 利用可能なモデルのリスト（成功時のみ）
        """
        api_key = self.get_api_key()
        
        if not api_key or api_key == "your_api_key_here":
            return False, "APIキーが設定されていません", None
        
        try:
            # プロキシ設定を取得
            proxy_settings = self.get_proxy_settings()
            http_client = None
            
            if proxy_settings["HTTP_PROXY"] or proxy_settings["HTTPS_PROXY"]:
                # プロキシが設定されている場合
                proxies = {}
                if proxy_settings["HTTP_PROXY"]:
                    proxies["http://"] = proxy_settings["HTTP_PROXY"]
                if proxy_settings["HTTPS_PROXY"]:
                    proxies["https://"] = proxy_settings["HTTPS_PROXY"]
                
                http_client = httpx.Client(proxies=proxies)
            
            # OpenAIクライアントを作成
            client = OpenAI(
                api_key=api_key,
                http_client=http_client
            )
            
            # モデル一覧を取得してテスト
            models = await asyncio.to_thread(client.models.list)
            model_ids = [model.id for model in models.data]
            
            # GPTモデルのみフィルタリング
            gpt_models = [m for m in model_ids if 'gpt' in m.lower()]
            gpt_models.sort(reverse=True)  # 新しいモデルを上に
            
            return True, "接続成功！", gpt_models[:10]  # 上位10個のモデル
            
        except openai.AuthenticationError:
            return False, "認証エラー: APIキーが無効です", None
        except openai.APIConnectionError as e:
            return False, f"接続エラー: {str(e)}", None
        except openai.RateLimitError:
            return False, "レート制限エラー: しばらく待ってから再試行してください", None
        except Exception as e:
            return False, f"予期しないエラー: {str(e)}", None
    
    async def test_simple_completion(self) -> Tuple[bool, str]:
        """
        簡単なチャット完了テスト
        
        Returns:
            Tuple[bool, str]: 成功/失敗のフラグとレスポンスメッセージ
        """
        api_key = self.get_api_key()
        
        if not api_key or api_key == "your_api_key_here":
            return False, "APIキーが設定されていません"
        
        try:
            # プロキシ設定を取得
            proxy_settings = self.get_proxy_settings()
            http_client = None
            
            if proxy_settings["HTTP_PROXY"] or proxy_settings["HTTPS_PROXY"]:
                proxies = {}
                if proxy_settings["HTTP_PROXY"]:
                    proxies["http://"] = proxy_settings["HTTP_PROXY"]
                if proxy_settings["HTTPS_PROXY"]:
                    proxies["https://"] = proxy_settings["HTTPS_PROXY"]
                
                http_client = httpx.Client(proxies=proxies)
            
            # OpenAIクライアントを作成
            client = OpenAI(
                api_key=api_key,
                http_client=http_client
            )
            
            # テストメッセージを送信
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'Hello, World!' in Japanese."}
                ],
                max_tokens=50
            )
            
            result = response.choices[0].message.content
            return True, f"テスト成功！レスポンス: {result}"
            
        except Exception as e:
            return False, f"テスト失敗: {str(e)}"
    
    def get_all_settings(self) -> Dict[str, any]:
        """すべての設定を取得（最新の値を反映）"""
        # 環境変数を再読み込みして最新の値を取得
        config = self.load_config()
        
        # APIキーをマスク
        if config["OPENAI_API_KEY"] and config["OPENAI_API_KEY"] != "your_api_key_here":
            key = config["OPENAI_API_KEY"]
            config["OPENAI_API_KEY_DISPLAY"] = f"sk-{'*' * 8}...{key[-4:]}" if len(key) > 4 else "***"
        else:
            config["OPENAI_API_KEY_DISPLAY"] = "未設定"
        
        return config


# グローバルインスタンス
config_manager = ConfigManager()
