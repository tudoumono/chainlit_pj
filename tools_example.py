"""
Tools機能を使用したWeb検索の例
OpenAI Tools Web Search機能の実装サンプル
"""

from utils.response_handler_corrected import response_handler
import asyncio
import json


# Web検索ツールの定義
web_search_tool = {
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
}


async def handle_web_search(query: str) -> str:
    """
    Web検索を実行（実際の実装では検索APIを呼び出す）
    """
    # ここは実際の検索APIの実装に置き換える
    return f"検索結果: '{query}'に関する情報が見つかりました。"


async def chat_with_tools_example():
    """
    Tools機能を使用したチャットの例
    """
    messages = [
        {"role": "system", "content": "You are a helpful assistant with web search capabilities."},
        {"role": "user", "content": "最新のAI技術について教えてください。必要に応じてWeb検索を使ってください。"}
    ]
    
    tools = [web_search_tool]
    
    print("🤖 Tools機能を使用したチャット開始")
    
    # 初回のAPI呼び出し
    async for chunk in response_handler.create_chat_completion_with_tools(
        messages=messages,
        tools=tools,
        model="gpt-4o-mini",
        stream=False
    ):
        if "error" in chunk:
            print(f"❌ エラー: {chunk['error']}")
            return
        
        if "choices" in chunk and chunk["choices"]:
            choice = chunk["choices"][0]
            message = choice.get("message", {})
            
            # 通常の応答
            if message.get("content"):
                print(f"AI: {message['content']}")
            
            # ツール呼び出しがある場合
            if message.get("tool_calls"):
                print("🔧 ツール呼び出しを検出")
                
                for tool_call in message["tool_calls"]:
                    function_name = tool_call["function"]["name"]
                    arguments = json.loads(tool_call["function"]["arguments"])
                    
                    print(f"  実行: {function_name}({arguments})")
                    
                    # ツールを実行
                    if function_name == "web_search":
                        result = await handle_web_search(arguments["query"])
                        
                        # ツールの結果をメッセージに追加
                        messages.append(message)
                        messages.append({
                            "role": "tool",
                            "content": result,
                            "tool_call_id": tool_call["id"]
                        })
                        
                        # 再度API呼び出し（ツールの結果を踏まえた応答）
                        async for final_chunk in response_handler.create_chat_completion(
                            messages=messages,
                            model="gpt-4o-mini",
                            stream=False
                        ):
                            if "choices" in final_chunk and final_chunk["choices"]:
                                final_message = final_chunk["choices"][0]["message"]["content"]
                                print(f"AI (最終応答): {final_message}")
                                break


if __name__ == "__main__":
    asyncio.run(chat_with_tools_example())
