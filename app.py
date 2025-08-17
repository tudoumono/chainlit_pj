"""
Phase 5 (SQLite永続化版 + Responses API): Chainlitの履歴管理
- SQLiteデータレイヤーを使用して履歴を永続化
- OpenAI Responses API with Tools機能（Web検索、ファイル検索）
- 認証機能による保護
- 自動的な履歴管理（永続的に保存）
- 詳細なデバッグログシステム

============================================================
重要: OpenAI SDKはResponses APIを正式にサポートしています
============================================================

参照ドキュメント:
- OpenAI公式APIリファレンス: https://platform.openai.com/docs/api-reference/responses
- ローカルドキュメント: F:\10_code\AI_Workspace_App_Chainlit\openai_responseAPI_reference\
  - openai responseAPI reference (Text generation).md
  - openai responseAPI reference (Conversation state).md
  - openai responseAPI reference (Streaming API responses).md

このアプリケーションはResponses APIの仕様に完全に準拠して実装されています。
SDKのバージョンや環境によりResponses APIが利用できない場合は、
Chat Completions APIに自動的にフォールバックしますが、
これはSDKがResponses APIをサポートしていないという意味ではありません。
"""

import chainlit as cl
from chainlit.types import ThreadDict
from dotenv import load_dotenv
import os
import auth  # 認証設定をインポート
from typing import Optional, Dict, List
from datetime import datetime
import json
import uuid  # スレッドID生成用
import chainlit.data as cl_data  # データレイヤーアクセス用

# .envファイルの読み込み
load_dotenv()

# ログシステムをインポート
from utils.logger import app_logger

# データレイヤーをインポート（SQLiteを優先して永続化）
data_layer_type = None

# SQLiteデータレイヤーを優先的に使用（永続化のため）
try:
    # SQLiteデータレイヤーを使用（優先）
    import data_layer
    data_layer_type = "SQLite (Persistent)"
    app_logger.info("✅ SQLiteデータレイヤーを使用")
    app_logger.info("📝 履歴は.chainlit/chainlit.dbに永続化されます")
    print("✅ SQLiteデータレイヤーを使用")
    print("📝 履歴は.chainlit/chainlit.dbに永続化されます")
except Exception as e:
    app_logger.error(f"⚠️ SQLiteデータレイヤーのエラー: {e}")
    print(f"⚠️ SQLiteデータレイヤーのエラー: {e}")
    try:
        # インメモリデータレイヤーをフォールバックとして使用
        import simple_data_layer
        data_layer_type = "Simple In-Memory"
        app_logger.info("✅ シンプルなインメモリデータレイヤーを使用")
        print("✅ シンプルなインメモリデータレイヤーを使用")
        print("📝 注意: 履歴はアプリケーション再起動で消失します")
    except ImportError:
        try:
            # SQLAlchemyDataLayerを試す（PostgreSQL）
            import chainlit.data as cl_data
            from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
            
            # PostgreSQL接続文字列（環境変数から読み込む）
            pg_conninfo = os.getenv("POSTGRES_CONNECTION_STRING")
            if pg_conninfo:
                cl_data._data_layer = SQLAlchemyDataLayer(conninfo=pg_conninfo)
                data_layer_type = "SQLAlchemy (PostgreSQL)"
                app_logger.info("✅ SQLAlchemyDataLayer（PostgreSQL）を使用")
                print("✅ SQLAlchemyDataLayer（PostgreSQL）を使用")
            else:
                app_logger.warning("⚠️ PostgreSQL接続文字列が設定されていません")
                print("⚠️ PostgreSQL接続文字列が設定されていません")
                print("📝 履歴機能を使用するには、data_layerまたは")
                print("   simple_data_layer.pyを確認してください")
        except Exception as e:
            app_logger.error(f"⚠️ SQLAlchemyDataLayerのエラー: {e}")
            print(f"⚠️ SQLAlchemyDataLayerのエラー: {e}")
            print("📝 data_layer.pyまたはsimple_data_layer.pyを使用してください")

# utils モジュールをインポート（設定管理とAPI呼び出しのみ使用）
from utils.config import config_manager
from utils.responses_handler import responses_handler
from utils.tools_config import tools_config
from utils.persona_manager import persona_manager  # Phase 6: ペルソナ管理

# アプリケーション設定
APP_NAME = "AI Workspace"
VERSION = "0.8.0 (Phase 6: Personas + Advanced Settings)"


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """
    履歴からチャットを復元する際の処理
    過去のメッセージを画面に再表示する
    """
    app_logger.info(f"📂 on_chat_resumeが呼ばれました", 
                   thread_id=thread.get('id', 'None')[:8],
                   thread_name=thread.get('name', 'None'),
                   steps_count=len(thread.get('steps', [])))
    
    print(f"📂 on_chat_resumeが呼ばれました")
    print(f"   Thread ID: {thread.get('id', 'None')}")
    print(f"   Thread Name: {thread.get('name', 'None')}")
    print(f"   Steps count: {len(thread.get('steps', []))}")
    
    # 設定を読み込み
    settings = config_manager.get_all_settings()
    cl.user_session.set("settings", settings)
    cl.user_session.set("system_prompt", "")
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    cl.user_session.set("previous_response_id", None)
    cl.user_session.set("message_history", [])
    cl.user_session.set("thread_id", thread.get("id"))
    cl.user_session.set("previous_response_id", None)
    cl.user_session.set("message_history", [])
    
    # 復元通知メッセージ
    await cl.Message(
        content=f"📂 過去の会話を復元中: {thread.get('name', 'Untitled')}...",
        author="System"
    ).send()
    
    # ステップから過去のメッセージを再構築して表示
    steps = thread.get('steps', [])
    app_logger.debug(f"復元するステップ数: {len(steps)}")
    print(f"   復元するステップ数: {len(steps)}")
    
    # メッセージを順番に復元
    message_count = 0
    messages_to_display = []  # 表示するメッセージを一時保存
    
    # ステップを処理してメッセージを抽出
    for i, step in enumerate(steps):
        step_type = step.get('type')
        step_id = step.get('id')
        created_at = step.get('createdAt')
        
        app_logger.debug(f"ステップ処理 [{i+1}/{len(steps)}]", 
                        step_id=step_id[:8] if step_id else 'None',
                        type=step_type,
                        created_at=created_at,
                        has_input=bool(step.get('input')),
                        has_output=bool(step.get('output')))
        
        # ユーザーメッセージの場合
        if step_type == 'user_message':
            user_input = step.get('input', '')
            if user_input:
                messages_to_display.append({
                    'type': 'user',
                    'content': user_input,
                    'id': step_id,
                    'created_at': created_at,
                    'order': i  # 順序を保持
                })
                app_logger.debug(f"📥 ユーザーメッセージを準備 [{i+1}]", preview=user_input[:50])
                print(f"   📥 ユーザーメッセージを準備 [{i+1}]: {user_input[:50]}...")
        
        # アシスタントメッセージの場合
        elif step_type == 'assistant_message':
            assistant_output = step.get('output', '')
            if assistant_output:
                messages_to_display.append({
                    'type': 'assistant',
                    'content': assistant_output,
                    'id': step_id,
                    'created_at': created_at,
                    'order': i  # 順序を保持
                })
                app_logger.debug(f"🤖 アシスタントメッセージを準備 [{i+1}]", preview=assistant_output[:50])
                print(f"   🤖 アシスタントメッセージを準備 [{i+1}]: {assistant_output[:50]}...")
            else:
                app_logger.warning(f"⚠️ アシスタントメッセージの出力が空です [{i+1}]", step_id=step_id[:8])
                print(f"   ⚠️ アシスタントメッセージの出力が空です [{i+1}]: {step_id[:8]}...")
        
        # runタイプはシステム的なものなのでスキップ
        elif step_type == 'run':
            # runステップにもoutputがある場合がある
            run_output = step.get('output', '')
            if run_output and not run_output.startswith('{'):  # JSONでない場合
                # システムメッセージとして表示
                messages_to_display.append({
                    'type': 'system',
                    'content': run_output,
                    'id': step_id,
                    'created_at': created_at,
                    'order': i  # 順序を保持
                })
                app_logger.debug(f"💻 runステップの出力を準備 [{i+1}]", preview=run_output[:50])
                print(f"   💻 runステップの出力を準備 [{i+1}]: {run_output[:50]}...")
            else:
                app_logger.debug(f"ℹ️ runステップをスキップ [{i+1}]", name=step.get('name', 'N/A'))
                print(f"   ℹ️ runステップをスキップ [{i+1}]: {step.get('name', 'N/A')}")
        
        # その他のタイプ
        else:
            # 必要に応じて他のステップタイプも処理
            app_logger.warning(f"⚠️ 未処理のステップタイプ [{i+1}]: {step_type}")
            print(f"   ⚠️ 未処理のステップタイプ [{i+1}]: {step_type}")
            # outputがあれば表示
            other_output = step.get('output', '')
            if other_output:
                messages_to_display.append({
                    'type': 'system',
                    'content': other_output,
                    'id': step_id,
                    'created_at': created_at,
                    'order': i  # 順序を保持
                })
    
    # messages_to_displayをorderでソートしてから表示（念のため）
    messages_to_display.sort(key=lambda x: x.get('order', 0))
    
    # メッセージを順番に表示
    for msg in messages_to_display:
        if msg['type'] == 'user':
            # ユーザーメッセージを表示
            user_msg = cl.Message(
                content=msg['content'],
                author="User",
                type="user_message"
            )
            user_msg.id = msg['id']  # 元のIDを保持
            await user_msg.send()
            message_count += 1
        elif msg['type'] == 'assistant':
            # アシスタントメッセージを表示
            assistant_msg = cl.Message(
                content=msg['content'],
                author="Assistant"
            )
            assistant_msg.id = msg['id']  # 元のIDを保持
            await assistant_msg.send()
            message_count += 1
        elif msg['type'] == 'system':
            # システムメッセージを表示
            system_msg = cl.Message(
                content=msg['content'],
                author="System"
            )
            system_msg.id = msg['id']  # 元のIDを保持
            await system_msg.send()
            message_count += 1
    
    # 復元完了メッセージ
    await cl.Message(
        content=f"✅ 復元完了: {message_count}件のメッセージを表示しました",
        author="System"
    ).send()
    
    # セッション変数を更新
    cl.user_session.set("message_count", message_count)
    
    app_logger.history_restored(thread.get('id', 'unknown'), message_count)
    print(f"   ✅ 復元完了: {message_count}件のメッセージ")


@cl.on_chat_start
async def on_chat_start():
    """
    新しいチャットセッション開始時の処理
    """
    # 設定を読み込み
    settings = config_manager.get_all_settings()
    cl.user_session.set("settings", settings)
    cl.user_session.set("system_prompt", "")
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    
    # Phase 6: デフォルトペルソナを初期化
    await persona_manager.initialize_default_personas()
    
    # アクティブなペルソナを取得して設定
    active_persona = await persona_manager.get_active_persona()
    if active_persona:
        cl.user_session.set("active_persona", active_persona)
        cl.user_session.set("system_prompt", active_persona.get("system_prompt", ""))
        
        # モデルを更新
        if active_persona.get("model"):
            settings["DEFAULT_MODEL"] = active_persona.get("model")
            cl.user_session.set("settings", settings)
    
    # 現在のユーザー情報を取得
    current_user = cl.user_session.get("user")
    app_logger.info(f"👤 新しいセッション開始", user=current_user.identifier if current_user else "anonymous")
    print(f"👤 現在のユーザー: {current_user}")
    
    # APIキーの確認
    api_status = "✅ 設定済み" if settings.get("OPENAI_API_KEY") and settings["OPENAI_API_KEY"] != "your_api_key_here" else "⚠️ 未設定"
    
    # Tools機能の状態を取得
    tools_status = "✅ 有効" if tools_config.is_enabled() else "❌ 無効"
    enabled_tools = tools_config.get_enabled_tools() if tools_config.is_enabled() else []
    
    welcome_message = f"""
# 🎯 {APP_NAME} へようこそ！

**Version**: {VERSION}

## 📊 現在の状態
- **APIキー**: {api_status}
- **デフォルトモデル**: {settings.get('DEFAULT_MODEL', 'gpt-4o-mini')}
- **データレイヤー**: {data_layer_type or '未設定'}
- **Tools機能**: {tools_status}
  {f"- 有効なツール: {', '.join(enabled_tools)}" if enabled_tools else ""}

## 🔧 利用可能なコマンド
- `/help` - コマンド一覧とヘルプを表示
- `/model [モデル名]` - 使用するモデルを変更
- `/system [プロンプト]` - システムプロンプトを設定
- `/stats` - 統計情報を表示
- `/clear` - 新しい会話を開始
- `/setkey [APIキー]` - OpenAI APIキーを設定
- `/tools` - Tools機能の設定を表示
- `/tools enable [ツール名]` - 特定のツールを有効化
- `/tools disable [ツール名]` - 特定のツールを無効化
- `/persona` - ペルソナ一覧を表示
- `/persona [名前]` - ペルソナを切り替え

💡 **ヒント**: 
- 会話は永続的に保存されます
- 左上の履歴ボタンから過去の会話にアクセスできます
- Tools機能を有効にすると、Web検索やファイル検索が可能になります

## 📝 データレイヤーの状態
- **タイプ**: {data_layer_type or '❌ 未設定'}
- **永続化**: {"✅ SQLiteに永続化" if data_layer_type == "SQLite (Persistent)" else "✅ PostgreSQLに永続化" if data_layer_type == "SQLAlchemy (PostgreSQL)" else "⚠️ インメモリ（再起動で消失）" if data_layer_type == "Simple In-Memory" else "❌ なし"}
- **認証**: {"✅ 有効" if os.getenv("CHAINLIT_AUTH_TYPE") == "credentials" else "❌ 無効"}

---
**AIと会話を始めましょう！** 何でも質問してください。
    """
    
    await cl.Message(content=welcome_message).send()
    
    # APIキーが未設定の場合は警告
    if not settings.get("OPENAI_API_KEY") or settings["OPENAI_API_KEY"] == "your_api_key_here":
        await cl.Message(
            content="⚠️ **APIキーが設定されていません**\n\n`/setkey [あなたのAPIキー]` コマンドで設定してください。",
            author="System"
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    ユーザーメッセージの処理
    コマンドの処理とAI応答の生成・保存
    """
    # メッセージを受信
    user_input = message.content
    current_user = cl.user_session.get("user")
    user_id = current_user.identifier if current_user else "anonymous"
    
    app_logger.message_received(user_input, user_id)
    app_logger.debug(f"📥 メッセージ受信", 
                     user=user_id,
                     length=len(user_input),
                     thread_id=cl.context.session.thread_id[:8] if hasattr(cl.context.session, 'thread_id') else 'None')
    
    # メッセージカウントを増加
    message_count = cl.user_session.get("message_count", 0) + 1
    cl.user_session.set("message_count", message_count)
    
    # コマンド処理
    if user_input.startswith("/"):
        await handle_command(user_input)
        return
    
    # AI応答の生成
    settings = cl.user_session.get("settings", {})
    api_key = settings.get("OPENAI_API_KEY")
    
    if not api_key or api_key == "your_api_key_here":
        await cl.Message(
            content="⚠️ APIキーが設定されていません。\n`/setkey [APIキー]` でAPIキーを設定してください。",
            author="System"
        ).send()
        return
    
    # システムプロンプト
    system_prompt = cl.user_session.get("system_prompt", "")
    model = settings.get("DEFAULT_MODEL", "gpt-4o-mini")
    
    app_logger.debug(f"🤖 AI応答生成開始", model=model, has_system_prompt=bool(system_prompt))
    
    # メッセージ履歴を管理
    message_history = cl.user_session.get("message_history", [])
    
    # Responses APIを使用してAI応答を生成
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # 履歴を追加（最大10メッセージ）
    messages.extend(message_history[-10:])
    messages.append({"role": "user", "content": user_input})
    
    # Tools機能の状態をログに記録
    tools_enabled = tools_config.is_enabled()
    if tools_enabled:
        enabled_tools = tools_config.get_enabled_tools()
        app_logger.debug(f"🔧 Tools機能有効", tools=enabled_tools)
    
    # AIメッセージを先に作成（ストリーミング用）
    ai_message = cl.Message(content="", author="Assistant")
    await ai_message.send()
    
    response_text = ""
    tool_calls = None
    previous_response_id = cl.user_session.get("previous_response_id")
    
    # ============================================================
    # Responses APIを呼び出し（ストリーミング有効）
    # OpenAI SDKはResponses APIを正式にサポートしています
    # 参照: openai responseAPI reference (Text generation).md
    # 参照: openai responseAPI reference (Conversation state).md
    # ============================================================
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
        
        # Responses APIのストリーミングイベント処理
        elif chunk.get("type") == "text_delta":
            # テキストデルタイベント
            if chunk.get("content"):
                response_text += chunk["content"]
                await ai_message.stream_token(chunk["content"])
        
        elif chunk.get("type") == "response_complete":
            # 完了イベント
            if chunk.get("id"):
                cl.user_session.set("previous_response_id", chunk["id"])
            if chunk.get("output_text") and not response_text:
                response_text = chunk["output_text"]
                await ai_message.update(content=response_text)
            break
        
        # Chat Completions APIのフォールバック処理
        elif "choices" in chunk and chunk["choices"]:
            choice = chunk["choices"][0]
            
            # ストリーミングモード（deltaを処理）
            if "delta" in choice:
                delta = choice["delta"]
                
                # テキストコンテンツの処理
                if delta.get("content"):
                    response_text += delta["content"]
                    await ai_message.stream_token(delta["content"])
                
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
            if message_data.get("tool_calls"):
                tool_calls = message_data["tool_calls"]
                app_logger.debug(f"🔧 ツール呼び出しを検出", count=len(tool_calls))
                
                # ツール呼び出しをUIに表示（設定による）
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
                            ).send()
                
                # ツールを実行
                tool_results = await responses_handler.handle_tool_calls(tool_calls, messages)
                
                # ツール結果を表示（設定による）
                if tools_config.get_setting("show_tool_results", True):
                    for result in tool_results:
                        await cl.Message(
                            content=f"📊 **ツール結果**:\n```\n{result['content'][:500]}...\n```",
                            author="System"
                        ).send()
                
                # ツール結果をメッセージに追加
                messages.append(message_data)
                messages.extend(tool_results)
                
                # ツール結果を踏まえて再度APIを呼び出し
                final_msg = cl.Message(content="", author="Assistant")
                await final_msg.send()
                
                async for final_chunk in responses_handler.create_response(
                    messages=messages,
                    model=model,
                    stream=True,
                    use_tools=False,  # ツールは一度だけ使用
                    previous_response_id=previous_response_id
                ):
                    # Responses APIイベント
                    if final_chunk.get("type") == "text_delta":
                        if final_chunk.get("content"):
                            response_text += final_chunk["content"]
                            await final_msg.stream_token(final_chunk["content"])
                    
                    elif final_chunk.get("type") == "response_complete":
                        if final_chunk.get("output_text") and not response_text:
                            response_text = final_chunk["output_text"]
                            await final_msg.update(content=response_text)
                        break
                    
                    # Chat Completions APIフォールバック
                    elif "choices" in final_chunk and final_chunk["choices"]:
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
                            break
            
            # response_idを保存（会話継続用）
            if "id" in chunk:
                cl.user_session.set("previous_response_id", chunk["id"])
            
            break
    
    if response_text:
        # ストリーミング完了時の処理
        await ai_message.update()  # ストリーミング完了を通知
        
        # メッセージ履歴を更新
        message_history.append({"role": "user", "content": user_input})
        message_history.append({"role": "assistant", "content": response_text})
        
        # 履歴を20メッセージに制限
        if len(message_history) > 20:
            message_history = message_history[-20:]
        
        cl.user_session.set("message_history", message_history)
        
        # AI応答をログに記録
        app_logger.ai_response(response_text, model)
        app_logger.debug(f"🤖 AI応答送信完了", 
                        length=len(response_text),
                        message_id=ai_message.id[:8] if ai_message.id else 'None')
        
        # トークン使用量を更新（簡易計算）
        total_tokens = cl.user_session.get("total_tokens", 0)
        estimated_tokens = len(user_input.split()) + len(response_text.split())
        total_tokens += estimated_tokens * 2  # 概算
        cl.user_session.set("total_tokens", total_tokens)
        
        app_logger.debug(f"📊 トークン使用量更新", 
                        estimated_tokens=estimated_tokens,
                        total_tokens=total_tokens)
    else:
        error_msg = "❌ AI応答の生成に失敗しました。"
        await cl.Message(content=error_msg, author="System").send()
        app_logger.error(f"AI応答生成失敗", user_input=user_input[:100])
        await ai_message.update(content="❌ AI応答の生成に失敗しました。")


async def handle_command(user_input: str):
    """コマンドを処理"""
    parts = user_input.split(maxsplit=2)
    cmd = parts[0].lower()
    
    app_logger.debug(f"🎮 コマンド処理", command=cmd)
    
    if cmd == "/help":
        await show_help()
    elif cmd == "/model":
        if len(parts) > 1:
            await change_model(parts[1])
        else:
            await cl.Message(
                content="❌ モデル名を指定してください。\n例: `/model gpt-4o`",
                author="System"
            ).send()
    elif cmd == "/system":
        args = user_input[len("/system"):].strip() if len(user_input) > len("/system") else ""
        await set_system_prompt(args)
    elif cmd == "/stats":
        await show_statistics()
    elif cmd == "/clear":
        await start_new_chat()
    elif cmd == "/setkey":
        if len(parts) > 1:
            await set_api_key(parts[1])
        else:
            await cl.Message(
                content="❌ APIキーを指定してください。\n例: `/setkey sk-...`",
                author="System"
            ).send()
    elif cmd == "/test":
        await test_connection()
    elif cmd == "/status":
        await show_status()
    elif cmd == "/tools":
        if len(parts) == 1:
            await show_tools_status()
        elif len(parts) >= 3:
            await handle_tools_command(parts[1], parts[2])
        else:
            await cl.Message(
                content="❌ コマンド形式が正しくありません。\n例: `/tools enable web_search`",
                author="System"
            ).send()
    elif cmd == "/persona" or cmd == "/personas":
        if len(parts) == 1:
            await show_personas()
        elif len(parts) == 2:
            await switch_persona(parts[1])
        else:
            action = parts[1].lower()
            if action == "create":
                await create_persona_interactive()
            elif action == "delete":
                if len(parts) > 2:
                    await delete_persona(parts[2])
                else:
                    await cl.Message(
                        content="❌ 削除するペルソナ名を指定してください。\n例: `/persona delete creative`",
                        author="System"
                    ).send()
            else:
                await switch_persona(parts[1])
    else:
        await cl.Message(
            content=f"❌ 不明なコマンド: {cmd}\n`/help` でコマンド一覧を確認してください。",
            author="System"
        ).send()


async def show_help():
    """ヘルプメッセージを表示"""
    help_message = """
# 📚 コマンド一覧

## 基本コマンド
- `/help` - このヘルプを表示
- `/clear` - 新しい会話を開始
- `/stats` - 現在のセッションの統計を表示
- `/status` - 設定状態を表示

## 設定コマンド
- `/setkey [APIキー]` - OpenAI APIキーを設定
- `/model [モデル名]` - 使用するモデルを変更
  - 例: `/model gpt-4o-mini`
  - 例: `/model gpt-4o`
- `/system [プロンプト]` - システムプロンプトを設定
  - 例: `/system あなたは親切なアシスタントです`
- `/test` - API接続をテスト

## Tools機能コマンド
- `/tools` - Tools機能の現在の設定を表示
- `/tools enable web_search` - Web検索を有効化
- `/tools disable web_search` - Web検索を無効化
- `/tools enable file_search` - ファイル検索を有効化
- `/tools disable file_search` - ファイル検索を無効化
- `/tools enable all` - すべてのツールを有効化
- `/tools disable all` - すべてのツールを無効化

## 💡 ヒント
- 会話履歴は自動的に保存されます
- 左上の履歴ボタンから過去の会話にアクセスできます
- Tools機能を有効にすると、AIが必要に応じてWeb検索やファイル検索を実行します
"""
    await cl.Message(content=help_message, author="System").send()


async def show_tools_status():
    """Tools機能の状態を表示"""
    status = "✅ 有効" if tools_config.is_enabled() else "❌ 無効"
    enabled_tools = tools_config.get_enabled_tools()
    
    tools_message = f"""
# 🔧 Tools機能の設定

## 全体の状態
- **Tools機能**: {status}

## 個別ツールの状態
- **Web検索**: {"✅ 有効" if tools_config.is_tool_enabled("web_search") else "❌ 無効"}
- **ファイル検索**: {"✅ 有効" if tools_config.is_tool_enabled("file_search") else "❌ 無効"}
- **コードインタープリター**: {"✅ 有効" if tools_config.is_tool_enabled("code_interpreter") else "❌ 無効"}
- **カスタム関数**: {"✅ 有効" if tools_config.is_tool_enabled("custom_functions") else "❌ 無効"}

## 設定
- **ツール選択**: {tools_config.get_setting("tool_choice", "auto")}
- **並列実行**: {"✅ 有効" if tools_config.get_setting("parallel_tool_calls", True) else "❌ 無効"}
- **最大ツール数/呼び出し**: {tools_config.get_setting("max_tools_per_call", 5)}
- **Web検索最大結果数**: {tools_config.get_setting("web_search_max_results", 5)}
- **ファイル検索最大チャンク数**: {tools_config.get_setting("file_search_max_chunks", 20)}
- **ツール呼び出し表示**: {"✅ 有効" if tools_config.get_setting("show_tool_calls", True) else "❌ 無効"}
- **ツール結果表示**: {"✅ 有効" if tools_config.get_setting("show_tool_results", True) else "❌ 無効"}

## 使用方法
- `/tools enable [ツール名]` - ツールを有効化
- `/tools disable [ツール名]` - ツールを無効化
- `/tools enable all` - すべて有効化
- `/tools disable all` - すべて無効化
"""
    
    await cl.Message(content=tools_message, author="System").send()


async def handle_tools_command(action: str, target: str):
    """Tools機能のコマンドを処理"""
    if action == "enable":
        if target == "all":
            tools_config.config["enabled"] = True
            for tool_name in tools_config.config.get("tools", {}):
                tools_config.update_tool_status(tool_name, True)
            await cl.Message(
                content="✅ すべてのツールを有効化しました",
                author="System"
            ).send()
        elif target in tools_config.config.get("tools", {}):
            tools_config.config["enabled"] = True
            tools_config.update_tool_status(target, True)
            await cl.Message(
                content=f"✅ {target}を有効化しました",
                author="System"
            ).send()
        else:
            await cl.Message(
                content=f"❌ 不明なツール: {target}",
                author="System"
            ).send()
    
    elif action == "disable":
        if target == "all":
            tools_config.config["enabled"] = False
            await cl.Message(
                content="✅ すべてのツールを無効化しました",
                author="System"
            ).send()
        elif target in tools_config.config.get("tools", {}):
            tools_config.update_tool_status(target, False)
            await cl.Message(
                content=f"✅ {target}を無効化しました",
                author="System"
            ).send()
        else:
            await cl.Message(
                content=f"❌ 不明なツール: {target}",
                author="System"
            ).send()
    
    else:
        await cl.Message(
            content=f"❌ 不明なアクション: {action}",
            author="System"
            ).send()


async def change_model(model: str):
    """モデルを変更"""
    valid_models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    
    if model not in valid_models:
        await cl.Message(
            content=f"❌ 無効なモデル名です。\n利用可能: {', '.join(valid_models)}",
            author="System"
        ).send()
        return
    
    settings = cl.user_session.get("settings", {})
    settings["DEFAULT_MODEL"] = model
    cl.user_session.set("settings", settings)
    
    config_manager.update_setting("DEFAULT_MODEL", model)
    responses_handler.update_model(model)
    
    app_logger.info(f"モデル変更", model=model)
    
    await cl.Message(
        content=f"✅ モデルを {model} に変更しました",
        author="System"
    ).send()


async def set_system_prompt(prompt: str):
    """システムプロンプトを設定"""
    cl.user_session.set("system_prompt", prompt)
    
    app_logger.info(f"システムプロンプト設定", length=len(prompt))
    
    if prompt:
        await cl.Message(
            content=f"✅ システムプロンプトを設定しました:\n```\n{prompt}\n```",
            author="System"
        ).send()
    else:
        await cl.Message(
            content="✅ システムプロンプトをクリアしました",
            author="System"
        ).send()


async def show_statistics():
    """統計情報を表示"""
    message_count = cl.user_session.get("message_count", 0)
    total_tokens = cl.user_session.get("total_tokens", 0)
    model = cl.user_session.get("settings", {}).get("DEFAULT_MODEL", "gpt-4o-mini")
    
    stats_message = f"""
# 📊 現在のセッションの統計

- **メッセージ数**: {message_count}
- **使用トークン**: {total_tokens:,}
- **使用モデル**: {model}
- **システムプロンプト**: {"設定済み" if cl.user_session.get("system_prompt") else "未設定"}
- **データレイヤー**: {data_layer_type or '未設定'}
- **Tools機能**: {"有効" if tools_config.is_enabled() else "無効"}
  - **有効なツール**: {', '.join(tools_config.get_enabled_tools()) if tools_config.get_enabled_tools() else "なし"}

💡 **ヒント**: {"SQLiteデータレイヤーを使用中。履歴は永続的に保存されます。" if data_layer_type == "SQLite (Persistent)" else "インメモリデータレイヤーを使用中。履歴はアプリ再起動で消失します。"}
"""
    
    await cl.Message(content=stats_message, author="System").send()


async def start_new_chat():
    """新しいチャットを開始"""
    # Chainlitが自動で新しいスレッドを作成するため、
    # ここではセッション変数のリセットのみを行う
    
    app_logger.info("新しいチャット開始")
    
    await cl.Message(
        content=f"""
✅ 新しい会話を開始しました

{"前の会話はSQLiteに永続的に保存されています。" if data_layer_type == "SQLite (Persistent)" else "前の会話はセッション中のみ保存されています。"}
左上の履歴ボタンから過去の会話にアクセスできます。
        """,
        author="System"
    ).send()
    
    # セッション変数をリセット
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    cl.user_session.set("system_prompt", "")
    cl.user_session.set("previous_response_id", None)
    cl.user_session.set("message_history", [])


async def set_api_key(api_key: str):
    """APIキーを設定"""
    success = config_manager.set_api_key(api_key)
    if success:
        new_settings = config_manager.get_all_settings()
        cl.user_session.set("settings", new_settings)
        responses_handler.update_api_key(api_key)
        
        app_logger.info("APIキー設定成功")
        
        await cl.Message(
            content="✅ APIキーを設定しました",
            author="System"
        ).send()
        
        await test_connection()


async def test_connection():
    """API接続テスト"""
    msg = cl.Message(content="🔄 接続テスト中...")
    await msg.send()
    
    success, message, models = await config_manager.test_connection()
    
    if success:
        test_success, test_message = await config_manager.test_simple_completion()
        result = f"✅ 接続成功！\n{test_message if test_success else '応答テスト失敗'}"
        app_logger.info("API接続テスト成功")
    else:
        result = f"❌ 接続失敗: {message}"
        app_logger.error(f"API接続テスト失敗", error=message)
    
    await cl.Message(content=result, author="System").send()


async def show_personas():
    """ペルソナ一覧を表示"""
    personas = await persona_manager.get_all_personas()
    active_persona = cl.user_session.get("active_persona")
    
    message = "# 🎭 ペルソナ一覧\n\n"
    
    for persona in personas:
        is_active = active_persona and persona.get("name") == active_persona.get("name")
        status = "✅ [アクティブ]" if is_active else ""
        
        message += f"## {persona.get('name')} {status}\n"
        message += f"{persona.get('description', 'No description')}\n"
        message += f"- 🤖 Model: {persona.get('model', 'gpt-4o-mini')}\n"
        message += f"- 🌡️ Temperature: {persona.get('temperature', 0.7)}\n"
        
        if persona.get('tags'):
            message += f"- 🏷️ Tags: {', '.join(persona.get('tags', []))}\n"
        message += "\n"
    
    message += "\n💡 **使い方**: `/persona [ペルソナ名]` で切り替え\n"
    message += "💡 **新規作成**: `/persona create` で新しいペルソナを作成\n"
    message += "💡 **削除**: `/persona delete [ペルソナ名]` で削除"
    
    await cl.Message(content=message, author="System").send()


async def switch_persona(persona_name: str):
    """ペルソナを切り替え"""
    personas = await persona_manager.get_all_personas()
    
    # 名前でペルソナを検索
    target_persona = None
    for persona in personas:
        if persona.get("name").lower() == persona_name.lower():
            target_persona = persona
            break
    
    if target_persona:
        # アクティブに設定
        if hasattr(persona_manager, 'set_active_persona'):
            await persona_manager.set_active_persona(target_persona.get("id", target_persona.get("name")))
        
        # セッションを更新
        cl.user_session.set("active_persona", target_persona)
        cl.user_session.set("system_prompt", target_persona.get("system_prompt", ""))
        
        # モデルを更新
        settings = cl.user_session.get("settings", {})
        if target_persona.get("model"):
            settings["DEFAULT_MODEL"] = target_persona.get("model")
            cl.user_session.set("settings", settings)
            
            # responses_handlerのモデルも更新
            responses_handler.update_model(target_persona.get("model"))
        
        # 表示
        info = persona_manager.format_persona_info(target_persona)
        await cl.Message(
            content=f"✅ ペルソナを切り替えました\n\n{info}",
            author="System"
        ).send()
    else:
        await cl.Message(
            content=f"❌ ペルソナ '{persona_name}' が見つかりません。`/persona` で一覧を確認してください。",
            author="System"
        ).send()


async def create_persona_interactive():
    """インタラクティブにペルソナを作成"""
    # 名前を入力
    res = await cl.AskUserMessage(
        content="🎭 新しいペルソナの**名前**を入力してください:",
        timeout=60
    ).send()
    
    if not res:
        await cl.Message(content="❌ キャンセルされました", author="System").send()
        return
    
    name = res["output"]
    
    # 説明を入力
    res = await cl.AskUserMessage(
        content="📝 ペルソナの**説明**を入力してください:",
        timeout=60
    ).send()
    
    if not res:
        await cl.Message(content="❌ キャンセルされました", author="System").send()
        return
    
    description = res["output"]
    
    # システムプロンプトを入力
    res = await cl.AskUserMessage(
        content="🤖 **システムプロンプト**を入力してください (AIの振る舞いを定義):",
        timeout=120
    ).send()
    
    if not res:
        await cl.Message(content="❌ キャンセルされました", author="System").send()
        return
    
    system_prompt = res["output"]
    
    # モデルを選択
    models_list = "\n".join([f"- {model}" for model in persona_manager.AVAILABLE_MODELS])
    res = await cl.AskUserMessage(
        content=f"🤖 使用する**モデル**を選択してください:\n{models_list}\n\n(デフォルト: gpt-4o-mini)",
        timeout=60
    ).send()
    
    model = "gpt-4o-mini"
    if res:
        input_model = res["output"].strip()
        if input_model in persona_manager.AVAILABLE_MODELS:
            model = input_model
    
    # Temperatureを入力
    res = await cl.AskUserMessage(
        content="🌡️ **Temperature** (0.0-2.0, デフォルト: 0.7)\n低い値=より一貫性がある、高い値=より創造的:",
        timeout=60
    ).send()
    
    temperature = 0.7
    if res:
        try:
            temp_value = float(res["output"])
            if 0.0 <= temp_value <= 2.0:
                temperature = temp_value
        except ValueError:
            pass
    
    # タグを入力
    res = await cl.AskUserMessage(
        content="🏷️ **タグ** (カンマ区切り、例: technical, creative, business):",
        timeout=60
    ).send()
    
    tags = []
    if res:
        tags = [tag.strip() for tag in res["output"].split(",") if tag.strip()]
    
    # ペルソナを作成
    persona_data = {
        "name": name,
        "description": description,
        "system_prompt": system_prompt,
        "model": model,
        "temperature": temperature,
        "tags": tags
    }
    
    persona_id = await persona_manager.create_persona(persona_data)
    
    # 確認メッセージ
    info = persona_manager.format_persona_info(persona_data)
    await cl.Message(
        content=f"✅ ペルソナを作成しました\n\n{info}\n\n`/persona {name}` で切り替えできます。",
        author="System"
    ).send()


async def delete_persona(persona_name: str):
    """ペルソナを削除"""
    personas = await persona_manager.get_all_personas()
    
    # 名前でペルソナを検索
    target_persona = None
    for persona in personas:
        if persona.get("name").lower() == persona_name.lower():
            target_persona = persona
            break
    
    if target_persona:
        # デフォルトペルソナは削除できない
        if target_persona.get("name") in ["汎用アシスタント", "プログラミング専門家", "ビジネスアナリスト", "クリエイティブライター", "学習サポーター"]:
            await cl.Message(
                content="❌ デフォルトペルソナは削除できません。",
                author="System"
            ).send()
            return
        
        # 削除実行
        success = await persona_manager.delete_persona(target_persona.get("id", target_persona.get("name")))
        
        if success:
            await cl.Message(
                content=f"✅ ペルソナ '{persona_name}' を削除しました。",
                author="System"
            ).send()
        else:
            await cl.Message(
                content=f"❌ ペルソナ '{persona_name}' の削除に失敗しました。",
                author="System"
            ).send()
    else:
        await cl.Message(
            content=f"❌ ペルソナ '{persona_name}' が見つかりません。",
            author="System"
        ).send()


async def show_status():
    """設定状態を表示"""
    settings = config_manager.get_all_settings()
    
    status_message = f"""
## 📊 現在の設定

- **APIキー**: {settings.get('OPENAI_API_KEY_DISPLAY', '未設定')}
- **モデル**: {cl.user_session.get('settings', {}).get('DEFAULT_MODEL', 'gpt-4o-mini')}
- **メッセージ数**: {cl.user_session.get("message_count", 0)}
- **トークン使用量**: {cl.user_session.get("total_tokens", 0):,}
- **システムプロンプト**: {"設定済み" if cl.user_session.get("system_prompt") else "未設定"}
- **データレイヤー**: {data_layer_type or '未設定'}
- **Tools機能**: {"有効" if tools_config.is_enabled() else "無効"}
"""
    
    await cl.Message(content=status_message, author="System").send()


if __name__ == "__main__":
    app_logger.info(f"Starting {APP_NAME} {VERSION}")
    app_logger.info(f"Working Directory: {os.getcwd()}")
    
    print(f"Starting {APP_NAME} {VERSION}")
    print(f"Working Directory: {os.getcwd()}")
    print("=" * 50)
    print("📌 データレイヤーの状態:")
    print(f"   - タイプ: {data_layer_type or '未設定'}")
    if data_layer_type == "SQLite (Persistent)":
        print("   ✅ SQLite: 履歴は永続的に保存されます")
        print("   📂 保存場所: .chainlit/chainlit.db")
    elif data_layer_type == "Simple In-Memory":
        print("   ⚠️ インメモリ: 履歴はアプリ再起動で消失します")
    elif not data_layer_type:
        print("   ❌ データレイヤーが設定されていません")
        print("   📝 履歴機能が動作しません")
    print("=" * 50)
    print("📌 Tools機能の状態:")
    print(f"   - 全体: {'有効' if tools_config.is_enabled() else '無効'}")
    if tools_config.is_enabled():
        enabled_tools = tools_config.get_enabled_tools()
        print(f"   - 有効なツール: {', '.join(enabled_tools) if enabled_tools else 'なし'}")
    print("=" * 50)
    print("📌 ログイン情報:")
    print("   - ユーザー名: admin")
    print("   - パスワード: admin123 (または.envで設定した値)")
    print("=" * 50)
    
    current_settings = config_manager.get_all_settings()
    print(f"API Key: {current_settings.get('OPENAI_API_KEY_DISPLAY', 'Not set')}")
    print(f"Default Model: {current_settings.get('DEFAULT_MODEL', 'Not set')}")
    
    app_logger.info("アプリケーション起動完了")
