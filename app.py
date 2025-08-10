"""
Phase 4: 基本的なチャット機能を含むChainlitアプリケーション
- OpenAI Responses APIの実装
- ストリーミング応答
- メッセージ履歴管理
- 実際のAI応答機能
"""

import chainlit as cl
from dotenv import load_dotenv
import os
from typing import Optional, Dict, List
import asyncio
from pathlib import Path
from datetime import datetime
import json

# utils モジュールをインポート
from utils.config import config_manager
from utils.session_handler import session_handler
from utils.response_handler import response_handler

# .envファイルの読み込み
load_dotenv()

# アプリケーション設定
APP_NAME = "AI Workspace"
VERSION = "0.4.0 (Phase 4)"


@cl.on_chat_start
async def on_chat_start():
    """
    チャットセッション開始時の処理
    """
    # 設定を読み込み
    settings = config_manager.get_all_settings()
    
    # 新しいセッションを作成
    session_id = await session_handler.create_session(
        title=f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        chat_type="responses",
        model=settings.get('DEFAULT_MODEL', 'gpt-4o-mini'),
        system_prompt=""
    )
    
    # セッション情報の初期化
    cl.user_session.set("phase", "4")
    cl.user_session.set("app_name", APP_NAME)
    cl.user_session.set("settings", settings)
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    
    # ウェルカムメッセージの作成
    api_status = "✅ 設定済み" if settings.get("OPENAI_API_KEY") and settings["OPENAI_API_KEY"] != "your_api_key_here" else "⚠️ 未設定"
    
    # データベース統計を取得
    stats = await session_handler.get_statistics()
    
    welcome_message = f"""
# 🎯 {APP_NAME} へようこそ！

**Version**: {VERSION}

## 📊 現在の状態
- **APIキー**: {api_status}
- **デフォルトモデル**: {settings.get('DEFAULT_MODEL', 'gpt-4o-mini')}
- **セッションID**: `{session_id[:8]}...`
- **データベース**: 📁 {stats['session_count']} セッション, 💬 {stats['message_count']} メッセージ

## 🔧 利用可能なコマンド
- `/help` - コマンド一覧とヘルプを表示
- `/model [モデル名]` - このセッションのモデルを変更
- `/system [プロンプト]` - システムプロンプトを設定
- `/clear` - 新しいセッションを開始
- `/sessions` - セッション一覧を表示
- `/stats` - データベース統計を表示

💡 **ヒント**: まずは `/help` でコマンドの詳細を確認してください！

## 📝 Phase 4の新機能
- ✅ **OpenAI Responses API統合**
- ✅ **ストリーミング応答**
- ✅ **実際のAI応答機能**
- ✅ **トークンカウント**
- ✅ **自動タイトル生成**

---
**AIと会話を始めましょう！** 何でも質問してください。
    """
    
    await cl.Message(content=welcome_message).send()
    
    # APIキーが未設定の場合は警告
    if not settings.get("OPENAI_API_KEY") or settings["OPENAI_API_KEY"] == "your_api_key_here":
        await cl.Message(
            content="⚠️ **APIキーが未設定です**\n`/setkey sk-xxxxx` コマンドで設定してください。",
            author="System"
        ).send()
    else:
        # APIキーが設定されている場合は簡単なテストメッセージ
        await cl.Message(
            content="✨ **準備完了！** AIと会話できます。例：「こんにちは」「Pythonについて教えて」",
            author="System"
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    ユーザーメッセージ受信時の処理
    """
    content = message.content.strip()
    settings = cl.user_session.get("settings", {})
    session_id = cl.user_session.get("session_id")
    
    # コマンド処理
    if content.startswith("/"):
        await handle_command(content)
        return
    
    # APIキーの確認
    if not settings.get("OPENAI_API_KEY") or settings["OPENAI_API_KEY"] == "your_api_key_here":
        await cl.Message(
            content="❌ APIキーが設定されていません。`/setkey sk-xxxxx` で設定してください。",
            author="System"
        ).send()
        return
    
    # ユーザーメッセージをデータベースに保存
    if session_id:
        await session_handler.add_message(
            session_id=session_id,
            role="user",
            content=content
        )
        
        # メッセージカウントを更新
        count = cl.user_session.get("message_count", 0) + 1
        cl.user_session.set("message_count", count)
    
    # メッセージ履歴を取得
    messages = []
    if session_id:
        db_messages = await session_handler.get_messages(session_id)
        messages = response_handler.format_messages_for_api(
            db_messages,
            system_prompt=cl.user_session.get("system_prompt", "")
        )
    
    # 最新のユーザーメッセージを追加（まだDBから取得できない場合）
    if not messages or messages[-1]["content"] != content:
        messages.append({"role": "user", "content": content})
    
    # AIレスポンスメッセージを作成
    ai_message = cl.Message(content="")
    await ai_message.send()
    
    # ストリーミング応答を処理
    full_response = ""
    token_usage = {}
    
    try:
        # OpenAI APIを呼び出し
        async for chunk in response_handler.create_chat_completion(
            messages=messages,
            model=settings.get('DEFAULT_MODEL', 'gpt-4o-mini'),
            temperature=0.7,
            stream=True
        ):
            # エラーチェック
            if "error" in chunk:
                await cl.Message(content=f"❌ エラー: {chunk['error']}").send()
                return
            
            # ストリーミングコンテンツを処理
            if chunk.get("choices"):
                for choice in chunk["choices"]:
                    if "delta" in choice:
                        delta = choice["delta"]
                        if "content" in delta:
                            full_response += delta["content"]
                            await ai_message.stream_token(delta["content"])
            
            # トークン使用量を更新
            if "usage" in chunk:
                token_usage = chunk["usage"]
        
        # 最終的なメッセージを更新
        # await cl.Message(content=full_response).send()
        await ai_message.update()

        
        # レスポンスをデータベースに保存
        if session_id and full_response:
            await session_handler.add_message(
                session_id=session_id,
                role="assistant",
                content=full_response,
                token_usage=token_usage
            )
        
        # トークン使用量を表示
        if token_usage:
            usage_text = response_handler.format_token_usage(token_usage)
            total_tokens = cl.user_session.get("total_tokens", 0) + token_usage.get("total_tokens", 0)
            cl.user_session.set("total_tokens", total_tokens)
            
            await cl.Message(
                content=f"{usage_text}\n📈 セッション合計: {total_tokens} トークン",
                author="System"
            ).send()
        
        # 最初のメッセージの場合、タイトルを自動生成
        if cl.user_session.get("message_count", 0) == 1:
            # 非同期でタイトルを生成（UIをブロックしない）
            asyncio.create_task(auto_generate_title(session_id, messages))
    
    except Exception as e:
        await cl.Message(content=f"❌ エラーが発生しました: {str(e)}").send()
        print(f"Error in on_message: {e}")


async def auto_generate_title(session_id: str, messages: List[Dict[str, str]]):
    """セッションタイトルを自動生成"""
    try:
        title = await response_handler.generate_title(messages)
        if title and session_id:
            await session_handler.update_session(session_id, title=title)
    except Exception as e:
        print(f"Error generating title: {e}")


async def handle_command(command: str):
    """
    コマンドを処理
    """
    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    if cmd == "/help":
        await show_help()
    
    elif cmd == "/model":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/model gpt-4o-mini`\n利用可能: gpt-4o-mini, gpt-4o, gpt-4-turbo, gpt-3.5-turbo",
                author="System"
            ).send()
            return
        await change_session_model(args)
    
    elif cmd == "/system":
        await set_system_prompt(args)
    
    elif cmd == "/sessions":
        await show_sessions()
    
    elif cmd == "/session":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/session [セッションID]`",
                author="System"
            ).send()
            return
        await switch_session(args)
    
    elif cmd == "/rename":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/rename [新しいタイトル]`",
                author="System"
            ).send()
            return
        await rename_session(args)
    
    elif cmd == "/stats":
        await show_statistics()
    
    elif cmd == "/clear":
        await start_new_session()
    
    elif cmd == "/setkey":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/setkey sk-xxxxxxxxxxxxx`",
                author="System"
            ).send()
            return
        
        # APIキーを設定
        success = config_manager.set_api_key(args)
        if success:
            # セッション設定を更新
            new_settings = config_manager.get_all_settings()
            cl.user_session.set("settings", new_settings)
            
            # response_handlerのAPIキーも更新
            response_handler.update_api_key(args)
            
            await cl.Message(
                content="✅ APIキーを設定しました",
                author="System"
            ).send()
            
            # 自動で接続テスト
            await test_connection()
        else:
            await cl.Message(
                content="❌ APIキーの設定に失敗しました",
                author="System"
            ).send()
    
    elif cmd == "/setmodel":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/setmodel gpt-4o-mini`\n利用可能: gpt-4o-mini, gpt-4o, gpt-4-turbo, gpt-3.5-turbo",
                author="System"
            ).send()
            return
        
        # デフォルトモデルを変更
        os.environ["DEFAULT_MODEL"] = args
        success = config_manager.save_config({"DEFAULT_MODEL": args})
        if success:
            # 設定を再読み込みしてセッションを更新
            new_settings = config_manager.get_all_settings()
            cl.user_session.set("settings", new_settings)
            
            # response_handlerのモデルも更新
            response_handler.update_model(args)
            
            await cl.Message(
                content=f"✅ デフォルトモデルを {args} に設定しました",
                author="System"
            ).send()
        else:
            await cl.Message(
                content="❌ モデルの設定に失敗しました",
                author="System"
            ).send()
    
    elif cmd == "/test":
        await test_connection()
    
    elif cmd == "/status":
        await show_status()
    
    elif cmd == "/models":
        await list_models()
    
    else:
        await cl.Message(
            content=f"""
❓ 不明なコマンド: {cmd}

`/help` で利用可能なコマンドを確認できます。
            """,
            author="System"
        ).send()


async def change_session_model(model: str):
    """現在のセッションのモデルを変更"""
    session_id = cl.user_session.get("session_id")
    if session_id:
        # セッション設定を更新
        settings = cl.user_session.get("settings", {})
        settings["DEFAULT_MODEL"] = model
        cl.user_session.set("settings", settings)
        
        await cl.Message(
            content=f"✅ このセッションのモデルを {model} に変更しました",
            author="System"
        ).send()
    else:
        await cl.Message(
            content="❌ アクティブなセッションがありません",
            author="System"
        ).send()


async def set_system_prompt(prompt: str):
    """システムプロンプトを設定"""
    cl.user_session.set("system_prompt", prompt)
    
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


async def show_help():
    """コマンドヘルプを表示"""
    help_message = f"""
# 📚 コマンドヘルプ (Phase 4)

## 🤖 AI設定コマンド（新機能）

### `/model [モデル名]`
- **説明**: このセッションで使用するモデルを変更
- **使用例**: `/model gpt-4o`
- **選択肢**: gpt-4o-mini, gpt-4o, gpt-4-turbo, gpt-3.5-turbo

### `/system [プロンプト]`
- **説明**: システムプロンプトを設定（AIの振る舞いを定義）
- **使用例**: `/system あなたは親切なアシスタントです`
- **クリア**: `/system` （引数なしでクリア）

## 🗂️ セッション管理

### `/sessions`
- **説明**: 保存されているセッション一覧を表示
- **使用例**: `/sessions`

### `/session [ID]`
- **説明**: 指定したセッションに切り替え
- **使用例**: `/session abc123def456`

### `/rename [タイトル]`
- **説明**: 現在のセッションのタイトルを変更
- **使用例**: `/rename Python学習`

### `/clear`
- **説明**: 新しいセッションを開始
- **使用例**: `/clear`

### `/stats`
- **説明**: データベースとトークン使用量の統計
- **使用例**: `/stats`

## 🔧 設定管理

### `/help`
- **説明**: このヘルプを表示
- **使用例**: `/help`

### `/test`
- **説明**: OpenAI APIとの接続をテスト
- **使用例**: `/test`

### `/status`
- **説明**: 現在のすべての設定を表示
- **使用例**: `/status`

### `/setkey [APIキー]`
- **説明**: OpenAI APIキーを設定
- **使用例**: `/setkey sk-proj-xxxxxxxxxxxxx`

### `/setmodel [モデル名]`
- **説明**: デフォルトのGPTモデルを変更（全セッション）
- **使用例**: `/setmodel gpt-4o-mini`

### `/models`
- **説明**: 利用可能なGPTモデルの一覧を取得
- **使用例**: `/models`

## 💡 クイックスタート

1️⃣ システムプロンプトを設定: `/system プログラミングの専門家として回答して`
2️⃣ モデルを選択: `/model gpt-4o`
3️⃣ 質問する: 「Pythonでフィボナッチ数列を生成するには？」

## ℹ️ Phase 4の新機能
- 🎯 実際のAI応答機能
- 📊 トークン使用量の追跡
- 🔄 ストリーミング応答
- 🎨 自動タイトル生成
- 💬 システムプロンプトのカスタマイズ
    """
    
    await cl.Message(content=help_message, author="System").send()


async def show_sessions():
    """セッション一覧を表示"""
    sessions = await session_handler.list_sessions(limit=10)
    
    if not sessions:
        await cl.Message(
            content="📭 セッションがありません。新しいチャットを始めてください。",
            author="System"
        ).send()
        return
    
    current_session_id = cl.user_session.get("session_id")
    
    sessions_text = "# 📋 セッション一覧\n\n"
    for i, session in enumerate(sessions, 1):
        is_current = "⭐ " if session['id'] == current_session_id else ""
        created = session.get('created_at', 'Unknown')
        sessions_text += f"""
{i}. {is_current}**{session['title']}**
   - ID: `{session['id'][:8]}...`
   - モデル: {session.get('model', 'Unknown')}
   - 作成日時: {created}
"""
    
    sessions_text += "\n💡 **切り替え方法**: `/session [ID最初の8文字]`"
    
    await cl.Message(content=sessions_text, author="System").send()


async def switch_session(session_id: str):
    """セッションを切り替え"""
    # 短縮IDでも検索可能に
    sessions = await session_handler.list_sessions()
    target_session = None
    
    for session in sessions:
        if session['id'].startswith(session_id):
            target_session = session
            break
    
    if not target_session:
        await cl.Message(
            content=f"❌ セッション `{session_id}` が見つかりません。",
            author="System"
        ).send()
        return
    
    # セッションを切り替え
    cl.user_session.set("session_id", target_session['id'])
    
    # メッセージ履歴を取得
    messages = await session_handler.get_messages(target_session['id'], limit=5)
    message_count = await session_handler.get_message_count(target_session['id'])
    cl.user_session.set("message_count", message_count)
    
    response = f"""
✅ セッションを切り替えました

**タイトル**: {target_session['title']}
**ID**: `{target_session['id'][:8]}...`
**メッセージ数**: {message_count}

## 最近のメッセージ
"""
    
    for msg in messages[-5:]:
        role_icon = "👤" if msg['role'] == 'user' else "🤖"
        content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
        response += f"\n{role_icon} {content_preview}"
    
    await cl.Message(content=response, author="System").send()


async def rename_session(new_title: str):
    """現在のセッションをリネーム"""
    session_id = cl.user_session.get("session_id")
    
    if not session_id:
        await cl.Message(
            content="❌ アクティブなセッションがありません。",
            author="System"
        ).send()
        return
    
    success = await session_handler.update_session(session_id, title=new_title)
    
    if success:
        await cl.Message(
            content=f"✅ セッションタイトルを「{new_title}」に変更しました。",
            author="System"
        ).send()
    else:
        await cl.Message(
            content="❌ タイトルの変更に失敗しました。",
            author="System"
        ).send()


async def show_statistics():
    """データベース統計を表示"""
    stats = await session_handler.get_statistics()
    
    db_size_mb = stats['db_size'] / (1024 * 1024)
    total_tokens = cl.user_session.get("total_tokens", 0)
    
    # 概算コスト計算（GPT-4o-miniベース）
    estimated_cost = total_tokens * 0.00000045  # 平均的な見積もり
    
    stats_message = f"""
# 📊 統計情報

## データベース
- **セッション数**: {stats['session_count']}
- **メッセージ総数**: {stats['message_count']}
- **ペルソナ数**: {stats['persona_count']}
- **データベースサイズ**: {db_size_mb:.2f} MB
- **最終更新**: {stats.get('last_session_date', 'なし')}

## 現在のセッション
- **ID**: `{cl.user_session.get("session_id", "なし")[:8] if cl.user_session.get("session_id") else "なし"}...`
- **メッセージ数**: {cl.user_session.get("message_count", 0)}
- **使用トークン**: {total_tokens}
- **推定コスト**: ${estimated_cost:.4f}

## システムプロンプト
```
{cl.user_session.get("system_prompt", "未設定")}
```
    """
    
    await cl.Message(content=stats_message, author="System").send()


async def start_new_session():
    """新しいセッションを開始"""
    settings = cl.user_session.get("settings", {})
    
    # 新しいセッションを作成
    session_id = await session_handler.create_session(
        title=f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        chat_type="responses",
        model=settings.get('DEFAULT_MODEL', 'gpt-4o-mini'),
        system_prompt=""
    )
    
    # セッション情報を更新
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    cl.user_session.set("system_prompt", "")
    
    await cl.Message(
        content=f"""
✅ 新しいセッションを開始しました

**セッションID**: `{session_id[:8]}...`
**モデル**: {settings.get('DEFAULT_MODEL', 'gpt-4o-mini')}

チャットを始めてください！
        """,
        author="System"
    ).send()


async def test_connection():
    """API接続テストを実行"""
    msg = cl.Message(content="🔄 接続テスト中...", author="System")
    await msg.send()
    
    success, message, models = await config_manager.test_connection()
    
    if success:
        # 簡単なチャットテストも実行
        test_success, test_message = await config_manager.test_simple_completion()
        
        models_text = "\n".join([f"  - {model}" for model in (models[:5] if models else [])])
        result_message = f"""
✅ **接続テスト成功！**

{message}

**チャットテスト**: {test_message if test_success else "失敗"}

**利用可能なモデル（上位5個）:**
{models_text}

詳細なモデル一覧は `/models` コマンドで確認できます。
        """
    else:
        result_message = f"""
❌ **接続テスト失敗**

{message}

**確認事項:**
1. APIキーが正しく入力されているか
2. プロキシ設定が必要な環境かどうか
3. OpenAI APIの利用制限に達していないか
        """
    
    msg.content = result_message
    await msg.update()


async def show_status():
    """現在の設定状態を表示"""
    settings = config_manager.get_all_settings()
    
    status_message = f"""
## 📊 現在の設定状態

**基本設定:**
- **APIキー**: {settings.get('OPENAI_API_KEY_DISPLAY', '未設定')}
- **デフォルトモデル**: {settings.get('DEFAULT_MODEL', 'gpt-4o-mini')}
- **現在のセッションモデル**: {cl.user_session.get('settings', {}).get('DEFAULT_MODEL', 'gpt-4o-mini')}
- **データベース**: {settings.get('DB_PATH', 'chat_history.db')}

**ネットワーク設定:**
- **HTTPプロキシ**: {settings.get('HTTP_PROXY', '未設定') or '未設定'}
- **HTTPSプロキシ**: {settings.get('HTTPS_PROXY', '未設定') or '未設定'}

**ベクトルストア設定:**
- **社内VS ID**: {settings.get('COMPANY_VECTOR_STORE_ID', '未設定') or '未設定'}
- **個人VS ID**: {settings.get('PERSONAL_VECTOR_STORE_ID', '未設定') or '未設定'}

**サーバー設定:**
- **ホスト**: {settings.get('CHAINLIT_HOST', '0.0.0.0')}
- **ポート**: {settings.get('CHAINLIT_PORT', '8000')}
    """
    
    await cl.Message(content=status_message, author="System").send()


async def list_models():
    """利用可能なモデル一覧を取得"""
    msg = cl.Message(content="🔄 モデル一覧を取得中...", author="System")
    await msg.send()
    
    success, message, models = await config_manager.test_connection()
    
    if success and models:
        models_text = "\n".join([f"{i+1}. {model}" for i, model in enumerate(models)])
        result_message = f"""
## 📋 利用可能なGPTモデル

{models_text}

**推奨モデル:**
- `gpt-4o-mini` - 高速で低コスト（推奨）
- `gpt-4o` - 最新の高性能モデル
- `gpt-4-turbo` - バランス型

モデルを変更するには: 
- `/model [モデル名]` - このセッションのみ
- `/setmodel [モデル名]` - デフォルト設定
        """
    else:
        result_message = "❌ モデル一覧の取得に失敗しました。APIキーと接続を確認してください。"
    
    msg.content = result_message
    await msg.update()


if __name__ == "__main__":
    # デバッグ情報の出力
    print(f"Starting {APP_NAME} {VERSION}")
    print(f"Python Path: {os.sys.executable}")
    print(f"Working Directory: {os.getcwd()}")
    
    # 設定の確認
    current_settings = config_manager.get_all_settings()
    print(f"API Key: {current_settings.get('OPENAI_API_KEY_DISPLAY', 'Not set')}")
    print(f"Default Model: {current_settings.get('DEFAULT_MODEL', 'Not set')}")
    print(f"Database Path: {current_settings.get('DB_PATH', 'chat_history.db')}")
