"""
OpenAI Chat Completions API管理モジュール
- Chat Completions APIの呼び出し
- ストリーミング応答処理
- Tools/Function calling対応
- メッセージ履歴管理
- エラーハンドリング
"""

import os
import json
from typing import Dict, List, Optional, AsyncGenerator, Any, Union
from openai import OpenAI, AsyncOpenAI
import httpx
from datetime import datetime
import asyncio


class ResponseHandler:
    """OpenAI Chat Completions API管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.default_model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        self.client = None
        self.async_client = None
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
    
    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        stream: bool = True,
        tools: List[Dict] = None,
        tool_choice: Union[str, Dict] = None,
        **kwargs
    ) -> AsyncGenerator[Dict, None]:
        """
        Chat Completions APIを呼び出し（ストリーミング対応、Tools対応）
        
        Args:
            messages: メッセージ履歴
            model: 使用モデル
            temperature: 創造性パラメータ
            max_tokens: 最大トークン数
            stream: ストリーミング有効/無効
            tools: 使用可能なツール定義
            tool_choice: ツール選択設定
            **kwargs: その他のパラメータ
        
        Yields:
            ストリーミングチャンク or 完了レスポンス
        """
        if not self.async_client:
            yield {
                "error": "APIキーが設定されていません",
                "type": "configuration_error"
            }
            return
        
        model = model or self.default_model
        
        # API呼び出しのパラメータを構築
        api_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }
        
        # オプションパラメータを追加
        if max_tokens:
            api_params["max_tokens"] = max_tokens
        if tools:
            api_params["tools"] = tools
        if tool_choice:
            api_params["tool_choice"] = tool_choice
        
        try:
            # ストリーミングモード
            if stream:
                response = await self.async_client.chat.completions.create(**api_params)
                
                # ストリーミングレスポンスを処理
                async for chunk in response:
                    # チャンクをディクショナリに変換
                    chunk_dict = {
                        "id": chunk.id,
                        "model": chunk.model,
                        "created": chunk.created,
                        "choices": []
                    }
                    
                    # choices を処理
                    if chunk.choices:
                        for choice in chunk.choices:
                            choice_dict = {
                                "index": choice.index,
                                "delta": {}
                            }
                            
                            # deltaの内容を処理
                            if choice.delta:
                                if choice.delta.content is not None:
                                    choice_dict["delta"]["content"] = choice.delta.content
                                if choice.delta.role is not None:
                                    choice_dict["delta"]["role"] = choice.delta.role
                                if hasattr(choice.delta, 'tool_calls') and choice.delta.tool_calls:
                                    choice_dict["delta"]["tool_calls"] = [
                                        {
                                            "index": tc.index,
                                            "id": tc.id if hasattr(tc, 'id') else None,
                                            "type": tc.type if hasattr(tc, 'type') else None,
                                            "function": {
                                                "name": tc.function.name if hasattr(tc.function, 'name') else None,
                                                "arguments": tc.function.arguments if hasattr(tc.function, 'arguments') else None
                                            } if hasattr(tc, 'function') else None
                                        } for tc in choice.delta.tool_calls
                                    ]
                            
                            # finish_reasonを処理
                            if choice.finish_reason:
                                choice_dict["finish_reason"] = choice.finish_reason
                            
                            chunk_dict["choices"].append(choice_dict)
                    
                    # usage情報があれば追加
                    if hasattr(chunk, 'usage') and chunk.usage:
                        chunk_dict["usage"] = {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens
                        }
                    
                    yield chunk_dict
            
            # 非ストリーミングモード
            else:
                response = await self.async_client.chat.completions.create(**api_params)
                
                # レスポンスをディクショナリに変換
                response_dict = {
                    "id": response.id,
                    "model": response.model,
                    "created": response.created,
                    "choices": [],
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
                
                # choicesを処理
                for choice in response.choices:
                    choice_dict = {
                        "index": choice.index,
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content
                        },
                        "finish_reason": choice.finish_reason
                    }
                    
                    # tool_callsがある場合
                    if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                        choice_dict["message"]["tool_calls"] = [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for tc in choice.message.tool_calls
                        ]
                    
                    response_dict["choices"].append(choice_dict)
                
                yield response_dict
        
        except Exception as e:
            yield {
                "error": str(e),
                "type": "api_error"
            }
    
    async def create_chat_completion_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        model: str = None,
        **kwargs
    ) -> AsyncGenerator[Dict, None]:
        """
        Tools/Function callingを使用したChat Completions API呼び出し
        
        Args:
            messages: メッセージ履歴
            tools: ツール定義のリスト
            model: 使用モデル
            **kwargs: その他のパラメータ
        
        Yields:
            API応答
        """
        async for chunk in self.create_chat_completion(
            messages=messages,
            model=model,
            tools=tools,
            tool_choice="auto",
            **kwargs
        ):
            yield chunk
    
    def format_messages_for_api(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = None
    ) -> List[Dict[str, str]]:
        """
        メッセージ履歴をAPI用にフォーマット
        
        Args:
            messages: データベースから取得したメッセージ
            system_prompt: システムプロンプト
        
        Returns:
            API用にフォーマットされたメッセージリスト
        """
        formatted = []
        
        # システムプロンプトを追加
        if system_prompt:
            formatted.append({
                "role": "system",
                "content": system_prompt
            })
        
        # メッセージ履歴を変換
        for msg in messages:
            formatted.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
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
    
    async def generate_title(self, messages: List[Dict[str, str]]) -> str:
        """
        会話からタイトルを自動生成
        
        Args:
            messages: メッセージ履歴
        
        Returns:
            生成されたタイトル
        """
        if not self.async_client:
            return f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        try:
            # タイトル生成用のプロンプト
            title_prompt = [
                {"role": "system", "content": "以下の会話から、短く簡潔なタイトルを日本語で生成してください。20文字以内で。"},
                *messages[:3]  # 最初の3メッセージのみ使用
            ]
            
            response = await self.async_client.chat.completions.create(
                model="gpt-4o-mini",  # 高速モデルを使用
                messages=title_prompt,
                temperature=0.5,
                max_tokens=30,
                stream=False
            )
            
            title = response.choices[0].message.content.strip()
            # タイトルが長すぎる場合は切り詰め
            if len(title) > 30:
                title = title[:27] + "..."
            
            return title
        
        except Exception as e:
            print(f"Error generating title: {e}")
            return f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    def extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """
        テキストからコードブロックを抽出
        
        Args:
            text: テキスト
        
        Returns:
            コードブロックのリスト [{language: str, code: str}]
        """
        import re
        
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        code_blocks = []
        for match in matches:
            language = match[0] or "plaintext"
            code = match[1].strip()
            code_blocks.append({
                "language": language,
                "code": code
            })
        
        return code_blocks
    
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
    
    # Tools/Function calling用のヘルパーメソッド
    def create_tool_definition(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ツール定義を作成
        
        Args:
            name: ツール名
            description: ツールの説明
            parameters: パラメータスキーマ
        
        Returns:
            ツール定義
        """
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
    
    def parse_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        ツール呼び出しをパース
        
        Args:
            tool_call: ツール呼び出しオブジェクト
        
        Returns:
            パースされた結果
        """
        return {
            "id": tool_call.get("id"),
            "type": tool_call.get("type"),
            "function_name": tool_call.get("function", {}).get("name"),
            "arguments": json.loads(tool_call.get("function", {}).get("arguments", "{}"))
        }
    
    def create_tool_response_message(
        self,
        tool_call_id: str,
        content: str
    ) -> Dict[str, Any]:
        """
        ツール応答メッセージを作成
        
        Args:
            tool_call_id: ツール呼び出しID
            content: ツールの実行結果
        
        Returns:
            ツール応答メッセージ
        """
        return {
            "role": "tool",
            "content": content,
            "tool_call_id": tool_call_id
        }


# グローバルインスタンス
response_handler = ResponseHandler()
