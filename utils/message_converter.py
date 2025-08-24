"""
Chat Completions形式からResponses API形式への変換ヘルパー
"""
from typing import List, Dict, Optional, Tuple, Any


def extract_input_from_messages(messages: List[Dict[str, str]]) -> str:
    """
    メッセージ履歴から最新のユーザー入力を抽出
    
    Args:
        messages: メッセージ履歴
    
    Returns:
        最新のユーザー入力テキスト
    """
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def extract_system_prompt(messages: List[Dict[str, str]]) -> Optional[str]:
    """
    メッセージ履歴からシステムプロンプトを抽出
    
    Args:
        messages: メッセージ履歴
    
    Returns:
        システムプロンプト（存在しない場合はNone）
    """
    for msg in messages:
        if msg.get("role") == "system":
            return msg.get("content")
    return None


def extract_assistant_messages(messages: List[Dict[str, str]]) -> List[str]:
    """
    メッセージ履歴からアシスタントの応答を抽出
    
    Args:
        messages: メッセージ履歴
    
    Returns:
        アシスタントの応答リスト
    """
    assistant_messages = []
    for msg in messages:
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if content:
                assistant_messages.append(content)
    return assistant_messages


def convert_messages_to_context(messages: List[Dict[str, str]]) -> str:
    """
    会話履歴を文脈として変換
    
    Args:
        messages: メッセージ履歴
    
    Returns:
        文脈としてフォーマットされた文字列
    """
    context = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        # システムメッセージは文脈に含めない
        if role != "system" and content:
            if role == "user":
                context.append(f"ユーザー: {content}")
            elif role == "assistant":
                context.append(f"アシスタント: {content}")
            elif role == "tool":
                # ツール結果の場合
                tool_name = msg.get("name", "tool")
                context.append(f"ツール[{tool_name}]: {content}")
    
    return "\n".join(context)


def prepare_responses_api_params(
    messages: List[Dict[str, str]],
    **kwargs
) -> Dict[str, Any]:
    """
    Chat Completions形式からResponses API形式へ変換
    
    Args:
        messages: Chat Completions形式のメッセージ履歴
        **kwargs: その他のパラメータ
    
    Returns:
        Responses API形式のパラメータ辞書
    """
    # 最新のユーザー入力を抽出
    input_text = extract_input_from_messages(messages)
    
    # システムプロンプトを抽出
    instructions = extract_system_prompt(messages)
    
    # 最新のメッセージ以外を文脈として変換
    context_messages = messages[:-1] if len(messages) > 1 else []
    context = convert_messages_to_context(context_messages) if context_messages else None
    
    params = {
        "input": input_text,
        **kwargs
    }
    
    # オプションパラメータの追加
    if instructions:
        params["instructions"] = instructions
    
    if context:
        params["context"] = context
    
    return params


def convert_response_to_message(response: Dict) -> Dict[str, str]:
    """
    Responses API形式の応答をChat Completions形式のメッセージに変換
    
    Args:
        response: Responses API形式の応答
    
    Returns:
        Chat Completions形式のメッセージ
    """
    message = {
        "role": response.get("role", "assistant")
    }
    
    # コンテンツの取得（複数の可能性のあるフィールドから）
    content = (
        response.get("content") or 
        response.get("output_text") or 
        response.get("output") or 
        ""
    )
    
    if content:
        message["content"] = content
    
    # ツール呼び出しがある場合
    if "tool_calls" in response:
        message["tool_calls"] = response["tool_calls"]
    
    # メッセージIDがある場合
    if "id" in response:
        message["id"] = response["id"]
    
    return message


def merge_stream_chunks(chunks: List[Dict]) -> Dict[str, Any]:
    """
    ストリームチャンクをマージして完全な応答を作成
    
    Args:
        chunks: ストリームチャンクのリスト
    
    Returns:
        マージされた応答
    """
    merged = {
        "role": "assistant",
        "content": "",
        "tool_calls": []
    }
    
    # IDとモデル情報を最初のチャンクから取得
    if chunks:
        first_chunk = chunks[0]
        if "id" in first_chunk:
            merged["id"] = first_chunk["id"]
        if "model" in first_chunk:
            merged["model"] = first_chunk["model"]
    
    # コンテンツとツール呼び出しをマージ
    tool_calls_by_index = {}
    
    for chunk in chunks:
        # コンテンツの追加
        if "content" in chunk:
            merged["content"] += chunk["content"]
        
        # ツール呼び出しの処理
        if "tool_calls" in chunk:
            for tool_call in chunk["tool_calls"]:
                index = tool_call.get("index", 0)
                
                if index not in tool_calls_by_index:
                    tool_calls_by_index[index] = {
                        "index": index,
                        "id": "",
                        "type": "",
                        "function": {
                            "name": "",
                            "arguments": ""
                        }
                    }
                
                tc = tool_calls_by_index[index]
                
                if "id" in tool_call:
                    tc["id"] = tool_call["id"]
                if "type" in tool_call:
                    tc["type"] = tool_call["type"]
                if "function" in tool_call:
                    func = tool_call["function"]
                    if "name" in func:
                        tc["function"]["name"] = func["name"]
                    if "arguments" in func:
                        tc["function"]["arguments"] += func["arguments"]
        
        # finish_reasonの処理
        if "finish_reason" in chunk:
            merged["finish_reason"] = chunk["finish_reason"]
    
    # ツール呼び出しをリストに変換
    if tool_calls_by_index:
        merged["tool_calls"] = list(tool_calls_by_index.values())
    
    # 空のフィールドを削除
    if not merged["content"]:
        del merged["content"]
    if not merged["tool_calls"]:
        del merged["tool_calls"]
    
    return merged


def validate_messages_format(messages: List[Dict]) -> Tuple[bool, Optional[str]]:
    """
    メッセージ形式の妥当性を検証
    
    Args:
        messages: 検証するメッセージリスト
    
    Returns:
        (有効かどうか, エラーメッセージ)
    """
    if not isinstance(messages, list):
        return False, "Messages must be a list"
    
    if not messages:
        return False, "Messages list cannot be empty"
    
    valid_roles = {"system", "user", "assistant", "tool", "function"}
    
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            return False, f"Message at index {i} must be a dictionary"
        
        if "role" not in msg:
            return False, f"Message at index {i} missing 'role' field"
        
        role = msg["role"]
        if role not in valid_roles:
            return False, f"Message at index {i} has invalid role: {role}"
        
        # コンテンツチェック（toolメッセージ以外は必須）
        if role != "tool" and "content" not in msg:
            # アシスタントメッセージでtool_callsがある場合は許可
            if not (role == "assistant" and "tool_calls" in msg):
                return False, f"Message at index {i} missing 'content' field"
    
    return True, None


def format_tool_response(
    tool_call_id: str,
    tool_name: str,
    result: Any
) -> Dict[str, str]:
    """
    ツールの実行結果をメッセージ形式にフォーマット
    
    Args:
        tool_call_id: ツール呼び出しID
        tool_name: ツール名
        result: ツールの実行結果
    
    Returns:
        フォーマットされたツールメッセージ
    """
    import json
    
    # 結果を文字列に変換
    if isinstance(result, str):
        content = result
    else:
        try:
            content = json.dumps(result, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            content = str(result)
    
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": content
    }


def extract_latest_conversation(
    messages: List[Dict[str, str]],
    max_messages: int = 10
) -> List[Dict[str, str]]:
    """
    最新の会話を抽出（システムメッセージを保持）
    
    Args:
        messages: 完全なメッセージ履歴
        max_messages: 抽出する最大メッセージ数
    
    Returns:
        抽出された会話
    """
    if not messages:
        return []
    
    # システムメッセージを探す
    system_messages = [msg for msg in messages if msg.get("role") == "system"]
    non_system_messages = [msg for msg in messages if msg.get("role") != "system"]
    
    # 最新のメッセージを取得
    recent_messages = non_system_messages[-max_messages:] if non_system_messages else []
    
    # システムメッセージと結合
    result = system_messages + recent_messages
    
    return result
