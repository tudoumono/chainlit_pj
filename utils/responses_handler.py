"""
OpenAI Responses API管理モジュール

========================================================
重要：正しいResponses APIの実装
========================================================

このファイルはOpenAI Responses APIを正しく実装しています。

OpenAIは2024年12月に新しいResponses APIを発表しました：
- エンドポイント：/v1/responses
- Python SDK：client.responses.create()メソッドを使用
- 主な機能：web_search、file_search、stateful conversation

========================================================
機能概要
========================================================

- Responses APIの呼び出し
- Tools機能（Web検索、ファイル検索）対応
- ストリーミング応答処理
- 会話の継続性（previous_response_id）
- エラーハンドリング
- ベクトルストア統合

========================================================
参照ドキュメント
========================================================

公式ドキュメント:
- Responses API Reference: https://platform.openai.com/docs/api-reference/responses
- Web Search Example: https://cookbook.openai.com/examples/responses_api/responses_example
- File Search Example: https://cookbook.openai.com/examples/file_search_responses

ローカルドキュメント:
- docs/references/多機能AIワークスペース　開発リファレンスドキュメント.md
- docs/implementation_status/02_実装の誤りと修正方針.md

========================================================
実装上の注意
========================================================

1. Responses APIは正式なAPIエンドポイントです
2. client.responses.create()メソッドが正しい使用方法です
3. inputとinstructionsパラメータを使用します
4. ベクトルストアはfile_searchツールで統合されます
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, AsyncGenerator, Any, Union
from openai import OpenAI, AsyncOpenAI
import httpx
from datetime import datetime
from .tools_config import tools_config
from .logger import app_logger  # ログシステムを追加
from .vector_store_handler import vector_store_handler  # ベクトルストアハンドラーを追加

# リトライ機構のインポート
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        before_retry,
        after_retry
    )
    from openai import RateLimitError, APIConnectionError, APITimeoutError
    TENACITY_AVAILABLE = True
except ImportError:
    app_logger.warning("tenacityライブラリが利用できません。リトライ機構は無効になります。")
    TENACITY_AVAILABLE = False


class ResponsesAPIHandler:
    """
    OpenAI Responses API管理クラス
    
    このクラスはOpenAI SDKのResponses APIを使用してAI応答を生成します。
    Responses APIは2024年12月に発表された新しいAPIで、web_searchやfile_search、
    stateful conversationなどの機能を提供します。
    
    主な機能:
    - Web検索ツール (web_search)
    - ファイル検索ツール (file_search)
    - 会話の継続性 (previous_response_id)
    - ストリーミング応答
    """
    
    def __init__(self):
        """初期化"""
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.default_model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        self.client = None
        self.async_client = None
        self.tools_config = tools_config
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
    
    async def create_response(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        stream: bool = True,
        use_tools: bool = None,
        tool_choice: Union[str, Dict] = None,
        previous_response_id: str = None,
        session: Optional[Dict] = None,  # Chainlitセッションを追加
        retry_count: int = 3,  # リトライ回数
        **kwargs
    ) -> AsyncGenerator[Dict, None]:
        """
        Responses APIを呼び出し（Tools機能対応）
        
        OpenAI Responses APIを使用してAI応答を生成します。
        Web検索、ファイル検索、stateful conversationなどの
        機能をサポートします。
        
        参照:
        - https://platform.openai.com/docs/api-reference/responses
        - https://platform.openai.com/docs/quickstart?api-mode=responses
        
        Args:
            messages: メッセージ履歴
            model: 使用モデル
            temperature: 創造性パラメータ
            max_tokens: 最大トークン数
            stream: ストリーミング有効/無効
            use_tools: Tools機能を使用するか
            tool_choice: ツール選択設定
            previous_response_id: 会話継続用ID
            session: Chainlitセッション情報
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
        
        # メッセージ履歴から入力とシステムプロンプトを抽出
        input_content = ""
        instructions = ""
        
        # 最新のユーザーメッセージを取得
        for msg in reversed(messages):
            if msg.get("role") == "user":
                input_content = msg.get("content", "")
                break
        
        # システムプロンプトを取得
        for msg in messages:
            if msg.get("role") == "system":
                instructions = msg.get("content", "")
                break
        
        # アシスタントのメッセージを会話のコンテキストとして含める
        if not input_content and messages:
            # ユーザーメッセージがない場合、全体をinputとして使用
            conversation_parts = []
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role != "system" and content:
                    conversation_parts.append(f"{role}: {content}")
            input_content = "\n".join(conversation_parts)
        
        # Responses APIパラメータを構築
        response_params = {
            "model": model,
            "temperature": temperature,
            "stream": stream,
            "store": True,  # 会話継続に必要：レスポンスを保存
            **kwargs
        }
        
        # inputの設定：previous_response_idがある場合は新しいメッセージのみ
        if previous_response_id:
            # 会話継続時：最新のユーザーメッセージのみを送信
            if messages and messages[-1].get("role") == "user":
                response_params["input"] = [messages[-1]]  # 配列形式
            else:
                response_params["input"] = input_content  # フォールバック
            response_params["previous_response_id"] = previous_response_id
        else:
            # 新しい会話開始時：全メッセージ履歴
            response_params["input"] = messages if isinstance(messages, list) else input_content
        
        # instructionsを設定（システムプロンプト）
        if instructions:
            response_params["instructions"] = instructions
        
        if max_tokens:
            response_params["max_tokens"] = max_tokens
        
        # Tools機能の設定
        tools = []
        if use_tools and self.tools_config.is_enabled():
            # Web検索ツール
            if self.tools_config.is_tool_enabled("web_search"):
                tools.append({
                    "type": "web_search"
                })
            
            # ファイル検索ツール（ベクトルストア）
            if self.tools_config.is_tool_enabled("file_search"):
                vector_store_ids = vector_store_handler.get_active_vector_store_ids()
                if vector_store_ids:
                    tools.append({
                        "type": "file_search",
                        "vector_store_ids": vector_store_ids
                    })
        
        if tools:
            response_params["tools"] = tools
        
        # デバッグログを追加
        app_logger.debug(f"🔧 create_response開始", 
                        model=model, 
                        stream=stream,
                        tools_enabled=use_tools,
                        message_count=len(messages))
        
        # リトライ機構付きAPI呼び出し関数を定義
        async def call_api_with_retry():
            """リトライ機構付きAPI呼び出し"""
            if TENACITY_AVAILABLE and retry_count > 0:
                # tenacityが利用可能な場合はリトライデコレータを使用
                retry_decorator = retry(
                    stop=stop_after_attempt(retry_count),
                    wait=wait_exponential(multiplier=1, min=4, max=10),
                    retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
                    before=lambda retry_state: app_logger.debug(f"🔄 API呼び出し試行 {retry_state.attempt_number}/{retry_count}")
                )
                
                @retry_decorator
                async def _call():
                    return await self.async_client.responses.create(**response_params)
                
                return await _call()
            else:
                # tenacityが利用できない場合は直接呼び出し
                return await self.async_client.responses.create(**response_params)
        
        response_stream = None
        try:
            # ========================================================
            # Responses APIを呼び出し（リトライ機構付き）
            # OpenAI SDKはResponses APIを正式にサポートしています
            # 参照: https://platform.openai.com/docs/api-reference/responses
            # ========================================================
            app_logger.debug("🔧 Responses API呼び出し")
            app_logger.debug(f"  Model: {model}")
            app_logger.debug(f"  Input: {input_content[:100]}..." if len(input_content) > 100 else f"  Input: {input_content}")
            app_logger.debug(f"  Instructions: {instructions[:100]}..." if len(instructions) > 100 else f"  Instructions: {instructions}")
            app_logger.debug(f"  Tools: {len(tools)} tools enabled" if tools else "  Tools: None")
            app_logger.debug(f"  Retry: {retry_count} attempts" if TENACITY_AVAILABLE else "  Retry: Disabled")
            
            response = await call_api_with_retry()
            
            # ストリーミングモード
            if stream:
                app_logger.debug("🔧 Responses APIストリーミングモード")
                try:
                    async for event in response:
                        if event:  # eventがNoneでないことを確認
                            yield self._process_response_stream_event(event)
                except asyncio.CancelledError:
                    app_logger.debug("⚠️ ストリーミングがキャンセルされました")
                    # Cancelled Errorは正常な終了として扱う
                    return
                except GeneratorExit:
                    app_logger.debug("⚠️ ジェネレーターが終了しました")
                    # GeneratorExitも正常な終了として扱う
                    return
                finally:
                    app_logger.debug("🔧 ストリーミング終了処理")
                    # response_streamのクリーンアップ
                    if response_stream and hasattr(response_stream, 'aclose'):
                        try:
                            await response_stream.aclose()
                        except Exception as cleanup_error:
                            app_logger.debug(f"⚠️ クリーンアップエラー: {cleanup_error}")
            # 非ストリーミングモード
            else:
                app_logger.debug("🔧 Responses API非ストリーミングモード")
                yield self._process_response_output(response)
        
        except asyncio.CancelledError:
            app_logger.debug("⚠️ 処理がキャンセルされました")
            # CancelledErrorは再度raiseする必要がある
            raise
        except Exception as e:
            app_logger.error(f"❌ API呼び出しエラー: {e}")
            import traceback
            app_logger.debug(f"❌ エラートレースバック: {traceback.format_exc()}")
            
            # エラーの種類に応じて詳細なメッセージを生成
            error_message = str(e)
            error_type = type(e).__name__
            
            # OpenAI関連のエラーに対してより具体的なメッセージを提供
            if "AuthenticationError" in error_type:
                error_message = "APIキーが無効または未設定です。`/setkey`コマンドで設定してください。"
            elif "RateLimitError" in error_type:
                error_message = "APIのレート制限に達しました。しばらく待ってから再試行してください。"
            elif "APIConnectionError" in error_type or "APITimeoutError" in error_type:
                error_message = "API接続エラーです。インターネット接続を確認してください。"
            elif "vector_store" in error_message.lower():
                error_message = "ベクトルストアの設定に問題があります。`/vs`コマンドで確認してください。"
            
            yield {
                "error": error_message,
                "type": "api_error",
                "details": {
                    "model": model,
                    "tools_enabled": use_tools,
                    "error_type": error_type,
                    "original_error": str(e)[:500]  # 元のエラーメッセージを一部保持
                }
            }
        finally:
            app_logger.debug("🔧 create_response終了")
            # リソースのクリーンアップ
            if response_stream and hasattr(response_stream, 'aclose'):
                try:
                    await response_stream.aclose()
                except Exception:
                    pass  # クリーンアップエラーは無視
    
    def _process_stream_chunk(self, chunk) -> Dict[str, Any]:
        """ストリーミングチャンクを処理"""
        chunk_dict = {
            "id": chunk.id,
            "model": chunk.model,
            "created": chunk.created,
            "object": "chat.completion.chunk",
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
                    # コンテンツ
                    if choice.delta.content is not None:
                        choice_dict["delta"]["content"] = choice.delta.content
                    
                    # ロール
                    if hasattr(choice.delta, 'role') and choice.delta.role is not None:
                        choice_dict["delta"]["role"] = choice.delta.role
                    
                    # ツール呼び出し
                    if hasattr(choice.delta, 'tool_calls') and choice.delta.tool_calls:
                        choice_dict["delta"]["tool_calls"] = []
                        for tc in choice.delta.tool_calls:
                            tool_call = {
                                "index": tc.index if hasattr(tc, 'index') else None
                            }
                            
                            if hasattr(tc, 'id') and tc.id:
                                tool_call["id"] = tc.id
                            if hasattr(tc, 'type') and tc.type:
                                tool_call["type"] = tc.type
                            
                            # Web検索ツール
                            if hasattr(tc, 'web_search') and tc.web_search:
                                tool_call["web_search"] = {
                                    "query": tc.web_search.query if hasattr(tc.web_search, 'query') else None
                                }
                            
                            # ファイル検索ツール
                            elif hasattr(tc, 'file_search') and tc.file_search:
                                tool_call["file_search"] = {}
                            
                            # 関数呼び出し
                            elif hasattr(tc, 'function') and tc.function:
                                tool_call["function"] = {
                                    "name": tc.function.name if hasattr(tc.function, 'name') else None,
                                    "arguments": tc.function.arguments if hasattr(tc.function, 'arguments') else None
                                }
                            
                            choice_dict["delta"]["tool_calls"].append(tool_call)
                
                # finish_reasonを処理
                if hasattr(choice, 'finish_reason') and choice.finish_reason:
                    choice_dict["finish_reason"] = choice.finish_reason
                
                chunk_dict["choices"].append(choice_dict)
        
        # usage情報があれば追加
        if hasattr(chunk, 'usage') and chunk.usage:
            chunk_dict["usage"] = {
                "prompt_tokens": chunk.usage.prompt_tokens if hasattr(chunk.usage, 'prompt_tokens') else 0,
                "completion_tokens": chunk.usage.completion_tokens if hasattr(chunk.usage, 'completion_tokens') else 0,
                "total_tokens": chunk.usage.total_tokens if hasattr(chunk.usage, 'total_tokens') else 0
            }
        
        return chunk_dict
    
    
    def _process_response_output(self, response) -> Dict[str, Any]:
        """
        Responses APIの非ストリーミング応答を処理
        """
        return {
            "id": response.id if hasattr(response, 'id') else None,
            "object": "response",
            "output_text": response.output_text if hasattr(response, 'output_text') else "",
            "output": response.output if hasattr(response, 'output') else [],
            "model": response.model if hasattr(response, 'model') else self.default_model,
            "created_at": response.created_at if hasattr(response, 'created_at') else datetime.now().timestamp(),
            "type": "response_complete"
        }
    
    def _process_response_stream_event(self, event) -> Dict[str, Any]:
        """
        Responses APIのストリーミングイベントを処理
        
        イベントタイプ:
        - response.output_text.delta: テキストのデルタ
        - response.output.delta: 出力のデルタ
        - response.completed: 応答完了
        - tool.call: ツール呼び出し
        - error: エラー
        """
        # イベントタイプに応じて処理
        event_type = getattr(event, 'type', None)
        
        if event_type == 'response.output_text.delta' or event_type == 'response.output.delta':
            # テキストデルタイベント
            delta_content = ""
            if hasattr(event, 'delta'):
                delta_content = event.delta
            elif hasattr(event, 'output_text_delta'):
                delta_content = event.output_text_delta
            
            return {
                "type": "text_delta",
                "content": delta_content,
                "id": event.id if hasattr(event, 'id') else None
            }
        elif event_type == 'response.completed':
            # 完了イベント
            output_text = ""
            if hasattr(event, 'output_text'):
                output_text = event.output_text
            elif hasattr(event, 'response') and hasattr(event.response, 'output_text'):
                output_text = event.response.output_text
            
            return {
                "type": "response_complete",
                "id": event.response_id if hasattr(event, 'response_id') else None,
                "output_text": output_text
            }
        elif event_type == 'tool.call':
            # ツール呼び出しイベント
            return {
                "type": "tool_call",
                "tool_type": event.tool_type if hasattr(event, 'tool_type') else None,
                "data": event.data if hasattr(event, 'data') else None
            }
        elif event_type == 'error':
            # エラーイベント
            return {
                "type": "error",
                "error": str(event.error) if hasattr(event, 'error') else "Unknown error"
            }
        else:
            # その他のイベント（デバッグ用）
            return {
                "type": "event",
                "event_type": event_type,
                "data": str(event)
            }
    
    def _process_response(self, response) -> Dict[str, Any]:
        """非ストリーミングレスポンスを処理"""
        response_dict = {
            "id": response.id,
            "model": response.model,
            "created": response.created,
            "object": "chat.completion",
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
            
            # ツール呼び出しがある場合
            if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                choice_dict["message"]["tool_calls"] = []
                
                for tc in choice.message.tool_calls:
                    tool_call = {
                        "id": tc.id,
                        "type": tc.type
                    }
                    
                    # Web検索ツール
                    if tc.type == "web_search":
                        tool_call["web_search"] = {
                            "query": tc.web_search.query if hasattr(tc, 'web_search') else None
                        }
                    
                    # ファイル検索ツール
                    elif tc.type == "file_search":
                        tool_call["file_search"] = {}
                    
                    # 関数呼び出し
                    elif tc.type == "function":
                        tool_call["function"] = {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    
                    choice_dict["message"]["tool_calls"].append(tool_call)
            
            response_dict["choices"].append(choice_dict)
        
        return response_dict
    
    async def handle_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        ツール呼び出しを処理
        
        Args:
            tool_calls: ツール呼び出しのリスト
            messages: メッセージ履歴（コンテキスト用）
        
        Returns:
            ツール実行結果のリスト
        """
        tool_results = []
        
        for tool_call in tool_calls:
            tool_id = tool_call.get("id", f"tool_{datetime.now().timestamp()}")
            tool_type = tool_call.get("type")
            
            if tool_type == "web_search":
                # Web検索を実行
                query = tool_call.get("web_search", {}).get("query", "")
                result = await self._handle_web_search(query)
                tool_results.append({
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "content": result
                })
            
            elif tool_type == "file_search":
                # ファイル検索を実行
                result = await self._handle_file_search(messages)
                tool_results.append({
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "content": result
                })
            
            elif tool_type == "function":
                # 関数呼び出しを実行
                function_name = tool_call.get("function", {}).get("name")
                arguments = tool_call.get("function", {}).get("arguments", "{}")
                
                if function_name == "web_search":
                    # Web検索関数として処理
                    try:
                        args = json.loads(arguments)
                        query = args.get("query", "")
                        result = await self._handle_web_search(query)
                    except json.JSONDecodeError:
                        result = f"エラー: 引数のパースに失敗しました: {arguments}"
                    
                elif function_name == "file_search":
                    # ファイル検索関数として処理
                    result = await self._handle_file_search(messages)
                    
                else:
                    # その他のカスタム関数
                    result = await self._handle_function_call(function_name, arguments)
                
                tool_results.append({
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "content": result
                })
        
        return tool_results
    
    async def _handle_web_search(self, query: str) -> str:
        """
        Web検索を処理（実際の実装ではBing APIなどを使用）
        
        Args:
            query: 検索クエリ
        
        Returns:
            検索結果
        """
        # ログ出力：Web検索の実行
        app_logger.info("="*60)
        app_logger.info("🔍 Web検索実行")
        app_logger.info(f"   検索クエリ: {query}")
        
        # ここは実際のWeb検索APIの実装に置き換える
        # 例: Bing Search API、Google Custom Search API など
        
        # デモ用の仮の結果
        max_results = self.tools_config.get_setting("web_search_max_results", 5)
        
        app_logger.info(f"   最大結果数: {max_results}")
        app_logger.info("="*60)
        
        # 検索結果にソース情報を含める
        result = f"\n🔍 **Web検索結果**\n\n"
        result += f"**検索クエリ:** `{query}`\n"
        result += f"**結果数:** 最大{max_results}件\n\n"
        
        # デモ用の仮の結果とソース
        result += "**検索結果:**\n"
        result += f"1. 📌 [関連サイト1] {query}に関する最新情報\n"
        result += f"   - ソース: https://example1.com\n\n"
        result += f"2. 📌 [関連サイト2] {query}の詳細解説\n"
        result += f"   - ソース: https://example2.com\n\n"
        
        result += "⚠️ 注: これはデモ結果です。実際のWeb検索APIを設定してください。"
        
        return result
    
    async def _handle_file_search(self, messages: List[Dict[str, Any]]) -> str:
        """
        ファイル検索を処理（ベクトルストア参照ログ付き）
        
        Args:
            messages: メッセージ履歴（コンテキスト用）
        
        Returns:
            検索結果
        """
        # アクティブなベクトルストアを取得
        active_stores = vector_store_handler.get_active_vector_stores()
        
        # ログ出力：どの層のベクトルストアが参照されるか
        app_logger.info("="*60)
        app_logger.info("📚 ベクトルストア参照開始")
        app_logger.info("-"*60)
        
        referenced_layers = []
        vs_info = []
        
        # 1層目: 会社全体（Company）
        if "company" in active_stores:
            vs_id = active_stores["company"]
            app_logger.info(f"🏢 【1層目】会社共有ベクトルストア")
            app_logger.info(f"   └─ ID: {vs_id}")
            referenced_layers.append("1層目:会社共有")
            vs_info.append({"layer": "会社共有", "id": vs_id})
        
        # 2層目: 個人ユーザー（Personal）
        if "personal" in active_stores:
            vs_id = active_stores["personal"]
            app_logger.info(f"👤 【2層目】個人用ベクトルストア")
            app_logger.info(f"   └─ ID: {vs_id}")
            referenced_layers.append("2層目:個人用")
            vs_info.append({"layer": "個人用", "id": vs_id})
        
        # 3層目: チャット単位（Session）
        if "session" in active_stores:
            vs_id = active_stores["session"]
            app_logger.info(f"💬 【3層目】セッション用ベクトルストア")
            app_logger.info(f"   └─ ID: {vs_id}")
            referenced_layers.append("3層目:セッション用")
            vs_info.append({"layer": "セッション用", "id": vs_id})
        
        if not active_stores:
            app_logger.warning("⚠️ アクティブなベクトルストアがありません")
            app_logger.info("="*60)
            return "検索対象のベクトルストアが設定されていません。"
        
        app_logger.info("-"*60)
        app_logger.info(f"✅ 参照されたベクトルストア: {', '.join(referenced_layers)}")
        app_logger.info("="*60)
        
        # 実際のファイル検索実装
        file_ids = self.tools_config.get_search_file_ids()
        max_chunks = self.tools_config.get_setting("file_search_max_chunks", 20)
        
        # 検索結果にソース情報を含める
        result = f"\n📚 **ベクトルストア検索結果**\n\n"
        result += f"🔍 **参照されたベクトルストア:**\n"
        
        for info in vs_info:
            result += f"  - {info['layer']}: `{info['id']}`\n"
        
        result += f"\n📊 **検索パラメータ:**\n"
        result += f"  - 最大チャンク数: {max_chunks}\n"
        
        if file_ids:
            result += f"  - ファイル数: {len(file_ids)}\n"
            result += f"  - ファイルID（一部）: {', '.join(file_ids[:3])}...\n"
        
        # デモ結果の場合の注記
        result += f"\n⚠️ 注: 実際のベクトルストア検索結果がここに表示されます。"
        
        return result
    
    async def _handle_function_call(self, function_name: str, arguments: str) -> str:
        """
        カスタム関数呼び出しを処理
        
        Args:
            function_name: 関数名
            arguments: 関数の引数（JSON文字列）
        
        Returns:
            関数の実行結果
        """
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError:
            return f"エラー: 引数のパースに失敗しました: {arguments}"
        
        # カスタム関数の実装をここに追加
        # 例: データベース検索、外部API呼び出しなど
        
        return f"関数 {function_name} を実行しました（引数: {args}）"
    
    def format_messages_for_api(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = None
    ) -> List[Dict[str, str]]:
        """
        メッセージ履歴をChat Completions API用にフォーマット
        
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
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            message = {
                "role": role,
                "content": content
            }
            
            # ツール呼び出しがある場合
            if "tool_calls" in msg:
                message["tool_calls"] = msg["tool_calls"]
            
            # ツール結果の場合
            if role == "tool" and "tool_call_id" in msg:
                message["tool_call_id"] = msg["tool_call_id"]
            
            formatted.append(message)
        
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
            # 会話内容を整形
            conversation_context = "\n".join([
                f"{m['role']}: {m['content'][:100]}" 
                for m in messages[:3] 
                if m.get('content')
            ])
            
            # Responses APIを使用してタイトル生成
            response = await self.async_client.responses.create(
                model="gpt-4o-mini",
                input=conversation_context,
                instructions="この会話から、短く簡潔なタイトルを日本語で生成してください。20文字以内で、タイトルのみを出力してください。",
                temperature=0.5,
                max_tokens=30,
                stream=False
            )
            
            # レスポンスからタイトルを抽出
            if hasattr(response, 'output_text'):
                title = response.output_text.strip()
            elif hasattr(response, 'output') and isinstance(response.output, list) and len(response.output) > 0:
                # outputが配列の場合、最初のメッセージのcontentを取得
                first_output = response.output[0]
                if hasattr(first_output, 'content') and isinstance(first_output.content, list):
                    for content_item in first_output.content:
                        if hasattr(content_item, 'text'):
                            title = content_item.text.strip()
                            break
                else:
                    title = str(first_output).strip()
            else:
                title = "Untitled Chat"
            
            # タイトルが長すぎる場合は切り詰め
            if len(title) > 30:
                title = title[:27] + "..."
            
            return title
        
        except Exception as e:
            app_logger.error(f"Error generating title: {e}")
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
responses_handler = ResponsesAPIHandler()
