"""
既存コードとの互換性を保つためのレイヤー
Chat Completions API形式の呼び出しをResponses API形式に変換
"""
from typing import Dict, List, Any, Optional, AsyncGenerator
import logging
from .true_responses_api_handler import TrueResponsesAPIHandler
from .message_converter import (
    extract_input_from_messages,
    extract_system_prompt,
    convert_messages_to_context,
    validate_messages_format,
    convert_response_to_message
)

logger = logging.getLogger(__name__)


class ResponsesCompatibilityLayer:
    """既存コードとの互換性を保つためのレイヤー"""
    
    def __init__(self, handler: TrueResponsesAPIHandler = None):
        """
        初期化
        
        Args:
            handler: TrueResponsesAPIHandlerインスタンス
        """
        self.handler = handler or TrueResponsesAPIHandler()
    
    def convert_chat_to_responses(self, chat_params: Dict) -> Dict:
        """
        Chat Completions形式をResponses API形式に変換
        
        Args:
            chat_params: Chat Completions APIのパラメータ
        
        Returns:
            Responses API形式のパラメータ
        """
        # メッセージを取得
        messages = chat_params.get("messages", [])
        
        # バリデーション
        is_valid, error_msg = validate_messages_format(messages)
        if not is_valid:
            logger.error(f"Invalid message format: {error_msg}")
            raise ValueError(f"Invalid message format: {error_msg}")
        
        # 基本パラメータの変換
        responses_params = {
            "model": chat_params.get("model"),
            "stream": chat_params.get("stream", True),
            "messages": messages  # 互換性のためにメッセージも渡す
        }
        
        # 入力テキストとinstructionsの抽出
        input_text = extract_input_from_messages(messages)
        instructions = extract_system_prompt(messages)
        
        if input_text:
            responses_params["input_text"] = input_text
        if instructions:
            responses_params["instructions"] = instructions
        
        # 温度パラメータ
        if "temperature" in chat_params:
            responses_params["temperature"] = chat_params["temperature"]
        
        # トークン制限の変換
        if "max_tokens" in chat_params:
            responses_params["max_tokens"] = chat_params["max_tokens"]
        
        # ツール関連の変換
        if "tools" in chat_params:
            responses_params["tools"] = chat_params["tools"]
        if "tool_choice" in chat_params:
            responses_params["tool_choice"] = chat_params["tool_choice"]
        
        # その他のパラメータをそのまま追加
        skip_keys = {"messages", "model", "stream", "temperature", "max_tokens", "tools", "tool_choice"}
        for key, value in chat_params.items():
            if key not in skip_keys:
                responses_params[key] = value
        
        return responses_params
    
    async def create_response_compat(
        self,
        **chat_params
    ) -> AsyncGenerator[Dict, None]:
        """
        互換性のあるcreate_responseメソッド
        Chat Completions API形式の呼び出しを受け付けて、
        Responses API形式に変換して処理
        
        Args:
            **chat_params: Chat Completions APIのパラメータ
        
        Yields:
            応答チャンク
        """
        try:
            # パラメータ変換
            responses_params = self.convert_chat_to_responses(chat_params)
            
            # Responses APIハンドラーを呼び出し
            async for chunk in self.handler.create_response(**responses_params):
                yield chunk
                
        except Exception as e:
            logger.error(f"Compatibility layer error: {e}")
            yield {
                "error": str(e),
                "type": "compatibility_error"
            }
    
    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncGenerator[Dict, None]:
        """
        Chat Completions API互換のインターフェース
        
        Args:
            messages: メッセージ履歴
            model: 使用するモデル
            stream: ストリーミングの有無
            **kwargs: その他のパラメータ
        
        Yields:
            応答チャンク
        """
        chat_params = {
            "messages": messages,
            "model": model,
            "stream": stream,
            **kwargs
        }
        
        async for chunk in self.create_response_compat(**chat_params):
            yield chunk
    
    async def handle_tool_calls(
        self,
        tool_calls: List[Dict],
        available_tools: Dict[str, Any]
    ) -> List[Dict]:
        """
        ツール呼び出しを処理（互換性メソッド）
        
        Args:
            tool_calls: ツール呼び出しのリスト
            available_tools: 利用可能なツールの辞書
        
        Returns:
            ツール実行結果のリスト
        """
        return await self.handler.handle_tool_calls(tool_calls, available_tools)
    
    async def test_connection(self) -> bool:
        """
        API接続テスト（互換性メソッド）
        
        Returns:
            接続成功の場合True
        """
        return await self.handler.test_connection()
    
    async def generate_title(
        self,
        messages: List[Dict[str, str]],
        max_length: int = 30
    ) -> str:
        """
        会話のタイトルを生成（互換性メソッド）
        
        Args:
            messages: 会話履歴
            max_length: タイトルの最大文字数
        
        Returns:
            生成されたタイトル
        """
        return await self.handler.generate_title(messages, max_length)
    
    def convert_response_format(self, response: Dict) -> Dict:
        """
        Responses API形式の応答をChat Completions API形式に変換
        
        Args:
            response: Responses API形式の応答
        
        Returns:
            Chat Completions API形式の応答
        """
        # 基本構造の作成
        converted = {
            "id": response.get("id", response.get("response_id", "")),
            "object": "chat.completion" if response.get("type") != "stream_chunk" else "chat.completion.chunk",
            "created": None,  # タイムスタンプがあれば変換
            "model": response.get("model", ""),
            "choices": []
        }
        
        # choiceの作成
        choice = {
            "index": 0,
            "finish_reason": response.get("finish_reason")
        }
        
        # ストリームチャンクの場合
        if response.get("type") == "stream_chunk":
            delta = {}
            if "content" in response:
                delta["content"] = response["content"]
            if "tool_calls" in response:
                delta["tool_calls"] = response["tool_calls"]
            choice["delta"] = delta
        else:
            # 通常の応答の場合
            message = {
                "role": response.get("role", "assistant")
            }
            if "content" in response:
                message["content"] = response["content"]
            elif "output_text" in response:
                message["content"] = response["output_text"]
            
            if "tool_calls" in response:
                message["tool_calls"] = response["tool_calls"]
            
            choice["message"] = message
        
        converted["choices"] = [choice]
        
        # 使用統計がある場合
        if "usage" in response:
            converted["usage"] = response["usage"]
        
        return converted


# グローバルインスタンスの作成
compatibility_layer = ResponsesCompatibilityLayer()
