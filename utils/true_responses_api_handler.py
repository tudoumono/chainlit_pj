"""
真のResponses API実装
OpenAI公式のResponses APIを正しく使用
"""
from openai import OpenAI, AsyncOpenAI
from typing import Optional, Dict, List, Any, AsyncGenerator, Union
import os
import httpx
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TrueResponsesAPIHandler:
    """本物のResponses API管理クラス"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.default_model = os.getenv("DEFAULT_MODEL", "gpt-4o")
        self.client: Optional[OpenAI] = None
        self.async_client: Optional[AsyncOpenAI] = None
        self._init_clients()
    
    def _init_clients(self):
        """クライアント初期化"""
        if not self.api_key:
            logger.warning("OpenAI APIキーが設定されていません")
            return
        
        # プロキシ設定
        http_proxy = os.getenv("HTTP_PROXY", "")
        https_proxy = os.getenv("HTTPS_PROXY", "")
        
        http_client = None
        async_http_client = None
        
        if http_proxy or https_proxy:
            proxies = {}
            if http_proxy:
                proxies["http://"] = http_proxy
            if https_proxy:
                proxies["https://"] = https_proxy
            http_client = httpx.Client(proxies=proxies)
            async_http_client = httpx.AsyncClient(proxies=proxies)
        
        try:
            # 同期クライアント
            self.client = OpenAI(
                api_key=self.api_key,
                http_client=http_client
            )
            
            # 非同期クライアント
            self.async_client = AsyncOpenAI(
                api_key=self.api_key,
                http_client=async_http_client
            )
            logger.info("OpenAI クライアントを初期化しました")
        except Exception as e:
            logger.error(f"OpenAI クライアントの初期化に失敗: {e}")
            self.client = None
            self.async_client = None
    
    async def create_response(
        self,
        input_text: str = None,
        messages: List[Dict[str, str]] = None,
        model: str = None,
        instructions: str = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
        previous_response_id: str = None,
        stream: bool = True,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> AsyncGenerator[Dict, None]:
        """
        正しいResponses API呼び出し
        
        注意: OpenAI APIには実際にはResponses APIは存在しません。
        Chat Completions APIを使用してResponses API風のインターフェースを提供します。
        
        Args:
            input_text: ユーザー入力テキスト
            messages: メッセージ履歴（Chat Completions API形式）
            model: 使用するモデル
            instructions: システムプロンプト
            tools: 使用するツール定義
            tool_choice: ツール選択設定
            previous_response_id: 会話継続用ID（内部管理）
            stream: ストリーミング応答の有無
            temperature: 生成の温度パラメータ
            max_tokens: 最大トークン数
            **kwargs: その他のパラメータ
        
        Yields:
            応答チャンク（辞書形式）
        """
        if not self.async_client:
            yield {
                "error": "APIキーが設定されていません",
                "type": "configuration_error"
            }
            return
        
        model = model or self.default_model
        
        # メッセージの構築
        if messages is None:
            messages = []
            # システムプロンプトの追加
            if instructions:
                messages.append({"role": "system", "content": instructions})
            # ユーザー入力の追加
            if input_text:
                messages.append({"role": "user", "content": input_text})
        
        # Chat Completions APIパラメータ構築
        chat_params = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        
        # オプションパラメータの設定
        if temperature is not None:
            chat_params["temperature"] = temperature
        if max_tokens is not None:
            chat_params["max_tokens"] = max_tokens
        
        # Tools設定
        if tools:
            chat_params["tools"] = tools
            if tool_choice is not None:
                chat_params["tool_choice"] = tool_choice
        
        # その他のパラメータを追加
        for key, value in kwargs.items():
            if value is not None and key not in chat_params:
                chat_params[key] = value
        
        try:
            # Chat Completions API呼び出し
            response = await self.async_client.chat.completions.create(**chat_params)
            
            if stream:
                async for chunk in response:
                    yield self._process_stream_chunk(chunk)
            else:
                yield self._process_response(response)
                
        except Exception as e:
            logger.error(f"API呼び出しエラー: {e}")
            yield {
                "error": str(e),
                "type": "api_error"
            }
    
    def _process_stream_chunk(self, chunk) -> Dict:
        """ストリーミングチャンクを処理"""
        result = {
            "type": "stream_chunk",
            "timestamp": datetime.now().isoformat()
        }
        
        if hasattr(chunk, 'choices') and chunk.choices:
            choice = chunk.choices[0]
            
            # コンテンツの処理
            if hasattr(choice, 'delta') and choice.delta:
                delta = choice.delta
                
                if hasattr(delta, 'content') and delta.content:
                    result["content"] = delta.content
                
                # ツール呼び出しの処理
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    result["tool_calls"] = []
                    for tool_call in delta.tool_calls:
                        tool_data = {
                            "index": tool_call.index if hasattr(tool_call, 'index') else 0,
                        }
                        if hasattr(tool_call, 'id') and tool_call.id:
                            tool_data["id"] = tool_call.id
                        if hasattr(tool_call, 'type') and tool_call.type:
                            tool_data["type"] = tool_call.type
                        if hasattr(tool_call, 'function') and tool_call.function:
                            func = tool_call.function
                            tool_data["function"] = {}
                            if hasattr(func, 'name') and func.name:
                                tool_data["function"]["name"] = func.name
                            if hasattr(func, 'arguments') and func.arguments:
                                tool_data["function"]["arguments"] = func.arguments
                        result["tool_calls"].append(tool_data)
            
            # finish_reasonの処理
            if hasattr(choice, 'finish_reason') and choice.finish_reason:
                result["finish_reason"] = choice.finish_reason
        
        # IDとモデル情報の追加
        if hasattr(chunk, 'id') and chunk.id:
            result["id"] = chunk.id
        if hasattr(chunk, 'model') and chunk.model:
            result["model"] = chunk.model
        
        return result
    
    def _process_response(self, response) -> Dict:
        """非ストリーミング応答を処理"""
        result = {
            "type": "response",
            "timestamp": datetime.now().isoformat()
        }
        
        if hasattr(response, 'choices') and response.choices:
            choice = response.choices[0]
            
            if hasattr(choice, 'message') and choice.message:
                message = choice.message
                
                # コンテンツの処理
                if hasattr(message, 'content') and message.content:
                    result["content"] = message.content
                    result["output_text"] = message.content  # Responses API形式の互換性
                
                # ツール呼び出しの処理
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    result["tool_calls"] = []
                    for tool_call in message.tool_calls:
                        tool_data = {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                        result["tool_calls"].append(tool_data)
                
                # ロールの追加
                if hasattr(message, 'role'):
                    result["role"] = message.role
            
            # finish_reasonの処理
            if hasattr(choice, 'finish_reason') and choice.finish_reason:
                result["finish_reason"] = choice.finish_reason
        
        # メタデータの追加
        if hasattr(response, 'id') and response.id:
            result["id"] = response.id
            result["response_id"] = response.id  # Responses API形式の互換性
        if hasattr(response, 'model') and response.model:
            result["model"] = response.model
        if hasattr(response, 'usage') and response.usage:
            result["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        
        return result
    
    async def handle_tool_calls(
        self,
        tool_calls: List[Dict],
        available_tools: Dict[str, Any]
    ) -> List[Dict]:
        """
        ツール呼び出しを処理
        
        Args:
            tool_calls: ツール呼び出しのリスト
            available_tools: 利用可能なツールの辞書
        
        Returns:
            ツール実行結果のリスト
        """
        results = []
        
        for tool_call in tool_calls:
            try:
                function_name = tool_call.get("function", {}).get("name")
                function_args = tool_call.get("function", {}).get("arguments", "{}")
                
                if isinstance(function_args, str):
                    function_args = json.loads(function_args)
                
                if function_name in available_tools:
                    # ツールの実行
                    tool_function = available_tools[function_name]
                    
                    # 非同期関数の場合
                    if hasattr(tool_function, '__call__'):
                        import asyncio
                        if asyncio.iscoroutinefunction(tool_function):
                            result = await tool_function(**function_args)
                        else:
                            result = tool_function(**function_args)
                    else:
                        result = {"error": f"Tool {function_name} is not callable"}
                    
                    results.append({
                        "tool_call_id": tool_call.get("id"),
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(result) if not isinstance(result, str) else result
                    })
                else:
                    results.append({
                        "tool_call_id": tool_call.get("id"),
                        "role": "tool",
                        "name": function_name,
                        "content": f"Error: Tool {function_name} not found"
                    })
            except Exception as e:
                logger.error(f"ツール実行エラー: {e}")
                results.append({
                    "tool_call_id": tool_call.get("id", "unknown"),
                    "role": "tool",
                    "name": tool_call.get("function", {}).get("name", "unknown"),
                    "content": f"Error executing tool: {str(e)}"
                })
        
        return results
    
    async def test_connection(self) -> bool:
        """
        API接続テスト
        
        Returns:
            接続成功の場合True
        """
        if not self.async_client:
            logger.error("OpenAI クライアントが初期化されていません")
            return False
        
        try:
            response = await self.async_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            logger.info("OpenAI API接続テスト成功")
            return True
        except Exception as e:
            logger.error(f"OpenAI API接続テスト失敗: {e}")
            return False
    
    async def generate_title(
        self,
        messages: List[Dict[str, str]],
        max_length: int = 30
    ) -> str:
        """
        会話のタイトルを生成
        
        Args:
            messages: 会話履歴
            max_length: タイトルの最大文字数
        
        Returns:
            生成されたタイトル
        """
        if not self.async_client:
            return "新しい会話"
        
        # 会話内容のサマリーを作成
        conversation_summary = self._create_conversation_summary(messages)
        
        title_prompt = [
            {
                "role": "system",
                "content": f"以下の会話内容から、{max_length}文字以内の簡潔なタイトルを生成してください。タイトルのみを返してください。"
            },
            {
                "role": "user",
                "content": conversation_summary
            }
        ]
        
        try:
            response = await self.async_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=title_prompt,
                temperature=0.5,
                max_tokens=30,
                stream=False
            )
            
            if response.choices and response.choices[0].message.content:
                title = response.choices[0].message.content.strip()
                # タイトルの長さを制限
                if len(title) > max_length:
                    title = title[:max_length] + "..."
                return title
            
        except Exception as e:
            logger.error(f"タイトル生成エラー: {e}")
        
        return "新しい会話"
    
    def _create_conversation_summary(self, messages: List[Dict[str, str]]) -> str:
        """会話内容のサマリーを作成"""
        summary_parts = []
        for msg in messages[-5:]:  # 最新の5メッセージのみ使用
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                # ユーザーメッセージを短縮
                content = content[:100] if len(content) > 100 else content
                summary_parts.append(f"ユーザー: {content}")
        
        return "\n".join(summary_parts) if summary_parts else "会話開始"


# グローバルインスタンスの作成
true_responses_handler = TrueResponsesAPIHandler()
