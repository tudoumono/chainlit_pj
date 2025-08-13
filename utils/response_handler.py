"""
OpenAI Responses API管理モジュール
- Responses APIの呼び出し（Web検索、ファイル検索対応）
- ストリーミング応答処理
- Tools機能（Web検索、ファイル検索、カスタム関数）
- メッセージ履歴管理
- エラーハンドリング
"""

import os
import json
import base64
from typing import Dict, List, Optional, AsyncGenerator, Any, Union, Literal
from openai import OpenAI, AsyncOpenAI
import httpx
from datetime import datetime
import asyncio
from pathlib import Path


class ResponseHandler:
    """OpenAI Responses API管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.default_model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        self.client = None
        self.async_client = None
        
        # ツール設定（環境変数またはデフォルト値）
        self.enable_web_search = os.getenv("ENABLE_WEB_SEARCH", "false").lower() == "true"
        self.enable_file_search = os.getenv("ENABLE_FILE_SEARCH", "false").lower() == "true"
        self.enable_function_calling = os.getenv("ENABLE_FUNCTION_CALLING", "true").lower() == "true"
        
        self._init_clients()
    
    def _init_clients(self):
        """OpenAIクライアントを初期化"""
        if not self.api_key or self.api_key == "your_api_key_here":
            return
        
        # プロキシ設定を確認
        http_proxy = os.getenv("HTTP_PROXY", "")
        https_proxy = os.getenv("HTTPS_PROXY", "")
        
        http_client = None
        if http_proxy or https_proxy:
            proxies = {}
            if http_proxy:
                proxies["http://"] = http_proxy
            if https_proxy:
                proxies["https://"] = https_proxy
            http_client = httpx.Client(proxies=proxies)
        
        # 同期クライアント
        self.client = OpenAI(
            api_key=self.api_key,
            http_client=http_client
        )
        
        # 非同期クライアント
        async_http_client = None
        if http_proxy or https_proxy:
            async_http_client = httpx.AsyncClient(proxies=proxies)
        
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            http_client=async_http_client
        )
    
    def update_api_key(self, api_key: str):
        """APIキーを更新"""
        self.api_key = api_key
        os.environ["OPENAI_API_KEY"] = api_key
        self._init_clients()
    
    def update_model(self, model: str):
        """デフォルトモデルを更新"""
        self.default_model = model
        os.environ["DEFAULT_MODEL"] = model
    
    def set_tool_settings(
        self,
        web_search: Optional[bool] = None,
        file_search: Optional[bool] = None,
        function_calling: Optional[bool] = None
    ):
        """
        ツール設定を更新
        
        Args:
            web_search: Web検索の有効/無効
            file_search: ファイル検索の有効/無効
            function_calling: Function callingの有効/無効
        """
        if web_search is not None:
            self.enable_web_search = web_search
            os.environ["ENABLE_WEB_SEARCH"] = str(web_search).lower()
        
        if file_search is not None:
            self.enable_file_search = file_search
            os.environ["ENABLE_FILE_SEARCH"] = str(file_search).lower()
        
        if function_calling is not None:
            self.enable_function_calling = function_calling
            os.environ["ENABLE_FUNCTION_CALLING"] = str(function_calling).lower()
    
    async def create_response(
        self,
        input: Union[str, List[Dict[str, Any]]],
        model: str = None,
        instructions: str = None,
        tools: Optional[List[Dict]] = None,
        file_ids: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        stream: bool = False,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> AsyncGenerator[Dict, None]:
        """
        Responses APIを呼び出し
        
        Args:
            input: 入力（文字列またはメッセージ配列）
            model: 使用モデル
            instructions: システム指示
            tools: 使用するツール（自動設定も可能）
            file_ids: 検索対象のファイルID
            metadata: メタデータ
            temperature: 創造性パラメータ
            max_tokens: 最大トークン数
            stream: ストリーミング有効/無効
            response_format: 応答フォーマット（JSON mode等）
            **kwargs: その他のパラメータ
        
        Yields:
            Responses APIの応答
        """
        if not self.async_client:
            yield {
                "error": "APIキーが設定されていません",
                "type": "configuration_error"
            }
            return
        
        model = model or self.default_model
        
        # ツールの自動設定
        if tools is None:
            tools = []
            
            # Web検索ツール
            if self.enable_web_search:
                tools.append({
                    "type": "web_search"
                })
            
            # ファイル検索ツール
            if self.enable_file_search and file_ids:
                tools.append({
                    "type": "file_search",
                    "file_search": {
                        "file_ids": file_ids
                    }
                })
        
        # API呼び出しのパラメータを構築
        api_params = {
            "model": model,
            "input": input,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }
        
        # オプションパラメータを追加
        if instructions:
            api_params["instructions"] = instructions
        if tools:
            api_params["tools"] = tools
        if metadata:
            api_params["metadata"] = metadata
        if max_tokens:
            api_params["max_tokens"] = max_tokens
        if response_format:
            api_params["response_format"] = response_format
        
        try:
            # Responses API呼び出し
            response = await self.async_client.responses.create(**api_params)
            
            if stream:
                # ストリーミングモード
                async for chunk in response:
                    yield self._format_response_chunk(chunk)
            else:
                # 非ストリーミングモード
                yield self._format_response(response)
        
        except AttributeError:
            # Responses APIがまだ利用できない場合のフォールバック
            # Chat Completions APIを使用
            yield await self._fallback_to_chat_completions(
                input, model, instructions, tools, temperature, 
                max_tokens, stream, response_format, **kwargs
            )
        
        except Exception as e:
            yield {
                "error": str(e),
                "type": "api_error"
            }
    
    async def _fallback_to_chat_completions(
        self,
        input: Union[str, List[Dict[str, Any]]],
        model: str,
        instructions: str,
        tools: Optional[List[Dict]],
        temperature: float,
        max_tokens: int,
        stream: bool,
        response_format: Optional[Dict],
        **kwargs
    ):
        """
        Responses APIが利用できない場合のフォールバック
        Chat Completions APIを使用
        """
        # 入力をメッセージ形式に変換
        if isinstance(input, str):
            messages = [
                {"role": "system", "content": instructions or "You are a helpful assistant."},
                {"role": "user", "content": input}
            ]
        else:
            messages = []
            if instructions:
                messages.append({"role": "system", "content": instructions})
            messages.extend(input)
        
        # Chat Completions用のツール形式に変換
        chat_tools = []
        for tool in (tools or []):
            if tool["type"] == "web_search":
                chat_tools.append({
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Search the web for information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                })
            elif tool["type"] == "file_search":
                chat_tools.append({
                    "type": "function",
                    "function": {
                        "name": "file_search",
                        "description": "Search within uploaded files",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query"
                                },
                                "file_ids": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "File IDs to search within"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                })
        
        # Chat Completions APIを呼び出し
        api_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        if chat_tools:
            api_params["tools"] = chat_tools
            api_params["tool_choice"] = "auto"
        if max_tokens:
            api_params["max_tokens"] = max_tokens
        if response_format:
            api_params["response_format"] = response_format
        
        response = await self.async_client.chat.completions.create(**api_params)
        
        if stream:
            # ストリーミング応答を処理
            full_content = ""
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_content += chunk.choices[0].delta.content
                    yield {
                        "type": "stream_chunk",
                        "content": chunk.choices[0].delta.content
                    }
            
            # 最終的な応答を返す
            return {
                "id": "fallback_response",
                "object": "response",
                "output_text": full_content,
                "model": model,
                "created_at": datetime.now().timestamp()
            }
        else:
            # 非ストリーミング応答
            content = response.choices[0].message.content if response.choices else ""
            tool_calls = response.choices[0].message.tool_calls if response.choices and hasattr(response.choices[0].message, 'tool_calls') else None
            
            return {
                "id": response.id,
                "object": "response",
                "output_text": content,
                "model": model,
                "created_at": response.created,
                "tool_calls": tool_calls
            }
    
    def _format_response(self, response) -> Dict:
        """
        Responses APIの応答をフォーマット
        """
        return {
            "id": response.id,
            "object": response.object,
            "created_at": response.created_at,
            "model": response.model,
            "output": response.output,
            "output_text": response.output_text if hasattr(response, 'output_text') else None,
            "instructions": response.instructions,
            "metadata": response.metadata,
            "error": response.error,
            "incomplete_details": response.incomplete_details
        }
    
    def _format_response_chunk(self, chunk) -> Dict:
        """
        ストリーミングチャンクをフォーマット
        """
        return {
            "type": "stream_chunk",
            "id": chunk.id if hasattr(chunk, 'id') else None,
            "content": chunk.content if hasattr(chunk, 'content') else None,
            "delta": chunk.delta if hasattr(chunk, 'delta') else None
        }
    
    async def upload_file(
        self,
        file_path: str,
        purpose: Literal["assistants", "vision", "batch", "fine-tune"] = "assistants"
    ) -> Optional[str]:
        """
        ファイルをOpenAIにアップロード
        
        Args:
            file_path: アップロードするファイルのパス
            purpose: ファイルの用途
        
        Returns:
            ファイルID
        """
        if not self.async_client:
            print("❌ APIキーが設定されていません")
            return None
        
        try:
            with open(file_path, "rb") as file:
                response = await self.async_client.files.create(
                    file=file,
                    purpose=purpose
                )
                return response.id
        except Exception as e:
            print(f"❌ ファイルアップロードエラー: {e}")
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """
        アップロードされたファイルを削除
        
        Args:
            file_id: 削除するファイルのID
        
        Returns:
            削除成功の可否
        """
        if not self.async_client:
            return False
        
        try:
            await self.async_client.files.delete(file_id)
            return True
        except Exception as e:
            print(f"❌ ファイル削除エラー: {e}")
            return False
    
    async def list_files(self) -> List[Dict]:
        """
        アップロードされたファイル一覧を取得
        
        Returns:
            ファイル情報のリスト
        """
        if not self.async_client:
            return []
        
        try:
            files = await self.async_client.files.list()
            return [
                {
                    "id": f.id,
                    "filename": f.filename,
                    "purpose": f.purpose,
                    "created_at": f.created_at,
                    "bytes": f.bytes
                }
                for f in files
            ]
        except Exception as e:
            print(f"❌ ファイル一覧取得エラー: {e}")
            return []
    
    def encode_file_to_base64(self, file_path: str) -> Optional[str]:
        """
        ファイルをBase64エンコード（画像やPDF用）
        
        Args:
            file_path: エンコードするファイルのパス
        
        Returns:
            Base64エンコードされた文字列
        """
        try:
            with open(file_path, "rb") as file:
                return base64.b64encode(file.read()).decode('utf-8')
        except Exception as e:
            print(f"❌ ファイルエンコードエラー: {e}")
            return None
    
    def create_image_input(self, image_path: str) -> Dict:
        """
        画像入力を作成
        
        Args:
            image_path: 画像ファイルのパス
        
        Returns:
            画像入力オブジェクト
        """
        base64_image = self.encode_file_to_base64(image_path)
        if not base64_image:
            return {}
        
        # MIMEタイプを判定
        suffix = Path(image_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        mime_type = mime_types.get(suffix, 'image/jpeg')
        
        return {
            "type": "input_image",
            "image_url": f"data:{mime_type};base64,{base64_image}"
        }
    
    def create_pdf_input(self, pdf_path: str) -> Dict:
        """
        PDF入力を作成
        
        Args:
            pdf_path: PDFファイルのパス
        
        Returns:
            PDF入力オブジェクト
        """
        base64_pdf = self.encode_file_to_base64(pdf_path)
        if not base64_pdf:
            return {}
        
        return {
            "type": "input_file",
            "filename": Path(pdf_path).name,
            "file_data": f"data:application/pdf;base64,{base64_pdf}"
        }
    
    def format_messages_for_responses_api(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = None
    ) -> Union[str, List[Dict]]:
        """
        メッセージ履歴をResponses API用にフォーマット
        
        Args:
            messages: メッセージ履歴
            system_prompt: システムプロンプト
        
        Returns:
            Responses API用の入力
        """
        # 単純なケース：メッセージが1つだけ
        if len(messages) == 1 and messages[0].get("role") == "user":
            return messages[0]["content"]
        
        # 複雑なケース：複数メッセージ
        formatted = []
        
        # システムプロンプトがある場合は最初に追加
        if system_prompt:
            formatted.append({
                "role": "system",
                "content": system_prompt
            })
        
        # メッセージを追加
        formatted.extend(messages)
        
        return formatted
    
    def calculate_token_estimate(self, text: str) -> int:
        """
        テキストのトークン数を推定
        
        Args:
            text: テキスト
        
        Returns:
            推定トークン数
        """
        # 簡易的な推定（実際はtiktokenを使うべき）
        # 日本語: 1文字 ≈ 2-3トークン
        # 英語: 1単語 ≈ 1-1.5トークン
        # ここでは簡易的に文字数の1/3として推定
        return len(text) // 3
    
    async def generate_title(self, input_text: str) -> str:
        """
        入力テキストからタイトルを自動生成
        
        Args:
            input_text: 入力テキスト
        
        Returns:
            生成されたタイトル
        """
        if not self.async_client:
            return f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        try:
            response = await self.create_response(
                input=f"以下のテキストから短く簡潔なタイトルを日本語で生成してください（20文字以内）:\n\n{input_text[:500]}",
                model="gpt-4o-mini",
                temperature=0.5,
                max_tokens=30,
                stream=False
            )
            
            # 応答からタイトルを抽出
            async for result in response:
                if "output_text" in result:
                    title = result["output_text"].strip()
                    if len(title) > 30:
                        title = title[:27] + "..."
                    return title
            
            return f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        except Exception as e:
            print(f"Error generating title: {e}")
            return f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    def format_token_usage(self, usage: Dict[str, int]) -> str:
        """
        トークン使用量をフォーマット
        
        Args:
            usage: トークン使用量
        
        Returns:
            フォーマットされた文字列
        """
        if not usage:
            return ""
        
        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
        total = usage.get("total_tokens", 0)
        
        # 概算コスト計算（GPT-4o-miniの料金: $0.15/1M input, $0.6/1M output）
        input_cost = prompt * 0.00000015
        output_cost = completion * 0.0000006
        total_cost = input_cost + output_cost
        
        return f"📊 トークン使用量: 入力 {prompt} + 出力 {completion} = 合計 {total} (約${total_cost:.4f})"


# グローバルインスタンス
response_handler = ResponseHandler()
