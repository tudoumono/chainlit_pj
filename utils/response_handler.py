"""
OpenAI Responses API管理モジュール
- Responses APIの呼び出し
- ストリーミング応答処理
- メッセージ履歴管理
- エラーハンドリング
"""

import os
import json
from typing import Dict, List, Optional, AsyncGenerator, Any
from openai import OpenAI, AsyncOpenAI
import httpx
from datetime import datetime
import asyncio


class ResponseHandler:
    """OpenAI Responses API管理クラス"""
    
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
        **kwargs
    ) -> AsyncGenerator[Dict, None]:
        """
        チャット完了APIを呼び出し（ストリーミング対応）
        
        Args:
            messages: メッセージ履歴
            model: 使用モデル
            temperature: 創造性パラメータ
            max_tokens: 最大トークン数
            stream: ストリーミング有効/無効
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
        
        try:
            # ストリーミングモード
            if stream:
                response = await self.async_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    **kwargs
                )
                
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
                                    choice_dict["delta"]["tool_calls"] = choice.delta.tool_calls
                            
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
                response = await self.async_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                    **kwargs
                )
                
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
                    response_dict["choices"].append(choice_dict)
                
                yield response_dict
        
        except Exception as e:
            yield {
                "error": str(e),
                "type": "api_error"
            }
    
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


# グローバルインスタンス
response_handler = ResponseHandler()
