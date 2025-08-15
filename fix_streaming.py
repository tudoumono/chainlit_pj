"""
ストリーミング処理の修正パッチ
app.pyのストリーミング処理を修正します
"""

import os
import shutil
from datetime import datetime

def fix_streaming_in_app():
    """app.pyのストリーミング処理を修正"""
    
    # バックアップを作成
    backup_path = f"app.py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy("app.py", backup_path)
    print(f"✅ バックアップを作成しました: {backup_path}")
    
    # app.pyを読み込み
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 修正1: ストリーミングチャンクの処理を修正
    old_chunk_handling = '''    # Responses APIを呼び出し（ストリーミング有効）
    async for chunk in responses_handler.create_response(
        messages=messages,
        model=model,
        stream=True,
        use_tools=tools_enabled,
        previous_response_id=previous_response_id
    ):
        if "error" in chunk:
            app_logger.error(f"API Error: {chunk['error']}")
            await ai_message.update(content=f"❌ エラー: {chunk['error']}")
            response_text = None
            break
        
        # ストリーミングチャンクの処理
        elif "type" in chunk and chunk["type"] == "stream_chunk":
            if chunk.get("content"):
                response_text += chunk["content"]
                await ai_message.stream_token(chunk["content"])
        
        # 完了時の処理
        elif "choices" in chunk and chunk["choices"]:
            choice = chunk["choices"][0]
            message_data = choice.get("message", {})
            
            # 通常の応答
            if message_data.get("content"):
                if not response_text:  # ストリーミングしていない場合
                    response_text = message_data["content"]
                    await ai_message.update(content=response_text)
            
            # ツール呼び出しがある場合
            if message_data.get("tool_calls"):'''
    
    new_chunk_handling = '''    # Responses APIを呼び出し（ストリーミング有効）
    async for chunk in responses_handler.create_response(
        messages=messages,
        model=model,
        stream=True,
        use_tools=tools_enabled,
        previous_response_id=previous_response_id
    ):
        if "error" in chunk:
            app_logger.error(f"API Error: {chunk['error']}")
            await ai_message.update(content=f"❌ エラー: {chunk['error']}")
            response_text = None
            break
        
        # Chat Completions APIのチャンク処理
        elif "choices" in chunk and chunk["choices"]:
            choice = chunk["choices"][0]
            
            # ストリーミングモード（deltaを処理）
            if "delta" in choice:
                delta = choice["delta"]
                
                # テキストコンテンツの処理
                if delta.get("content"):
                    response_text += delta["content"]
                    await ai_message.stream_token(delta["content"])
                
                # ツール呼び出しの処理（ストリーミング）
                if delta.get("tool_calls"):
                    # ツール呼び出しの処理は後で実装
                    pass
                
                # finish_reasonがある場合は完了
                if choice.get("finish_reason"):
                    # response_idを保存（会話継続用）
                    if "id" in chunk:
                        cl.user_session.set("previous_response_id", chunk["id"])
                    break
            
            # 非ストリーミングモード（messageを処理）
            elif "message" in choice:
                message_data = choice["message"]
                
                # 通常の応答
                if message_data.get("content"):
                    response_text = message_data["content"]
                    await ai_message.update(content=response_text)
                
                # ツール呼び出しがある場合
                if message_data.get("tool_calls"):'''
    
    # 修正を適用
    if old_chunk_handling in content:
        content = content.replace(old_chunk_handling, new_chunk_handling)
        print("✅ ストリーミングチャンク処理を修正しました")
    else:
        print("⚠️ 修正対象のコードが見つかりませんでした（すでに修正済みの可能性があります）")
    
    # 修正2: ツール呼び出し後の再ストリーミング処理も修正
    old_tool_streaming = '''                async for final_chunk in responses_handler.create_response(
                    messages=messages,
                    model=model,
                    stream=True,
                    use_tools=False,  # ツールは一度だけ使用
                    previous_response_id=previous_response_id
                ):
                    if "type" in final_chunk and final_chunk["type"] == "stream_chunk":
                        if final_chunk.get("content"):
                            response_text += final_chunk["content"]
                            await final_msg.stream_token(final_chunk["content"])
                    elif "choices" in final_chunk and final_chunk["choices"]:
                        final_message = final_chunk["choices"][0].get("message", {})
                        if final_message.get("content") and not response_text:
                            response_text = final_message["content"]
                            await final_msg.update(content=response_text)
                        break'''
    
    new_tool_streaming = '''                async for final_chunk in responses_handler.create_response(
                    messages=messages,
                    model=model,
                    stream=True,
                    use_tools=False,  # ツールは一度だけ使用
                    previous_response_id=previous_response_id
                ):
                    if "choices" in final_chunk and final_chunk["choices"]:
                        final_choice = final_chunk["choices"][0]
                        
                        # ストリーミングモード
                        if "delta" in final_choice:
                            delta = final_choice["delta"]
                            if delta.get("content"):
                                response_text += delta["content"]
                                await final_msg.stream_token(delta["content"])
                            
                            if final_choice.get("finish_reason"):
                                break
                        
                        # 非ストリーミングモード
                        elif "message" in final_choice:
                            final_message = final_choice["message"]
                            if final_message.get("content"):
                                response_text = final_message["content"]
                                await final_msg.update(content=response_text)
                            break'''
    
    if old_tool_streaming in content:
        content = content.replace(old_tool_streaming, new_tool_streaming)
        print("✅ ツール呼び出し後のストリーミング処理を修正しました")
    else:
        print("⚠️ ツール呼び出し後のストリーミング処理が見つかりませんでした")
    
    # 修正3: ツール呼び出しの表示処理も修正（functionタイプを処理）
    old_tool_display = '''                # ツール呼び出しをUIに表示（設定による）
                if tools_config.get_setting("show_tool_calls", True):
                    for tc in tool_calls:
                        tool_type = tc.get("type")
                        if tool_type == "web_search":
                            query = tc.get("web_search", {}).get("query", "")
                            await cl.Message(
                                content=f"🔍 **Web検索中**: `{query}`",
                                author="System"
                            ).send()
                        elif tool_type == "file_search":
                            await cl.Message(
                                content=f"📁 **ファイル検索中**",
                                author="System"
                            ).send()'''
    
    new_tool_display = '''                # ツール呼び出しをUIに表示（設定による）
                if tools_config.get_setting("show_tool_calls", True):
                    for tc in tool_calls:
                        tool_type = tc.get("type")
                        if tool_type == "function":
                            func_name = tc.get("function", {}).get("name", "")
                            if func_name == "web_search":
                                args = tc.get("function", {}).get("arguments", "{}")
                                try:
                                    import json
                                    args_dict = json.loads(args)
                                    query = args_dict.get("query", "")
                                    await cl.Message(
                                        content=f"🔍 **Web検索中**: `{query}`",
                                        author="System"
                                    ).send()
                                except:
                                    pass
                            elif func_name == "file_search":
                                await cl.Message(
                                    content=f"📁 **ファイル検索中**",
                                    author="System"
                                ).send()'''
    
    if old_tool_display in content:
        content = content.replace(old_tool_display, new_tool_display)
        print("✅ ツール呼び出し表示処理を修正しました")
    else:
        print("⚠️ ツール呼び出し表示処理が見つかりませんでした")
    
    # ファイルを保存
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ app.pyの修正が完了しました")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("📝 ストリーミング処理の修正を開始します")
    print("=" * 50)
    
    if fix_streaming_in_app():
        print("\n✅ すべての修正が完了しました！")
        print("📌 アプリケーションを再起動してください")
    else:
        print("\n⚠️ 修正に失敗しました")
