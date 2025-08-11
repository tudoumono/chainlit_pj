"""
Phase 5: セッション永続化を強化したChainlitアプリケーション
- 会話履歴の完全な管理
- セッション検索機能
- 会話の再開と継続
- タグ機能
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
VERSION = "0.5.0 (Phase 5)"


@cl.on_chat_start
async def on_chat_start():
    """
    チャットセッション開始時の処理
    """
    # 設定を読み込み
    settings = config_manager.get_all_settings()
    
    # 最近のセッションを確認
    recent_sessions = await session_handler.list_sessions(limit=1)
    
    # 新しいセッションを作成するか、最近のセッションを再開するか選択
    if recent_sessions:
        last_session = recent_sessions[0]
        # 最後のセッションが今日で、メッセージが少ない場合は再開を提案
        last_date = datetime.fromisoformat(last_session['created_at'].replace(' ', 'T')) if isinstance(last_session['created_at'], str) else last_session['created_at']
        if isinstance(last_date, str):
            last_date = datetime.fromisoformat(last_date.replace(' ', 'T'))
        
        message_count = await session_handler.get_message_count(last_session['id'])
        
        # 今日のセッションでメッセージが10未満なら再開を提案
        if last_date.date() == datetime.now().date() and message_count < 10:
            session_id = last_session['id']
            await resume_session(session_id, silent=True)
        else:
            # 新しいセッションを作成
            session_id = await create_new_session(settings)
    else:
        # 新しいセッションを作成
        session_id = await create_new_session(settings)
    
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
- `/search [キーワード]` - セッションを検索
- `/recent` - 最近のセッション表示
- `/resume` - 最後のセッションを再開
- `/tag [タグ名]` - セッションにタグを追加
- `/export` - 現在のセッションをエクスポート

💡 **ヒント**: `/recent` で最近の会話を確認できます！

## 📝 Phase 5の新機能
- ✅ **セッション検索機能**
- ✅ **会話の自動再開**
- ✅ **タグ管理**
- ✅ **エクスポート機能（簡易版）**
- ✅ **詳細な履歴管理**

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
        # 最近のセッション情報を表示
        if recent_sessions:
            await show_recent_sessions(limit=3)


async def create_new_session(settings: Dict) -> str:
    """新しいセッションを作成"""
    session_id = await session_handler.create_session(
        title=f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        chat_type="responses",
        model=settings.get('DEFAULT_MODEL', 'gpt-4o-mini'),
        system_prompt=""
    )
    
    # セッション情報の初期化
    cl.user_session.set("phase", "5")
    cl.user_session.set("app_name", APP_NAME)
    cl.user_session.set("settings", settings)
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("message_count", 0)
    cl.user_session.set("total_tokens", 0)
    cl.user_session.set("tags", [])
    
    return session_id


async def resume_session(session_id: str, silent: bool = False):
    """セッションを再開"""
    session = await session_handler.get_session(session_id)
    if not session:
        if not silent:
            await cl.Message(
                content=f"❌ セッション `{session_id}` が見つかりません。",
                author="System"
            ).send()
        return False
    
    # セッション情報を復元
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("message_count", await session_handler.get_message_count(session_id))
    
    # タグを復元
    tags = session.get('tags', '')
    cl.user_session.set("tags", tags.split(',') if tags else [])
    
    # システムプロンプトを復元
    cl.user_session.set("system_prompt", session.get('system_prompt', ''))
    
    # モデル設定を復元
    settings = cl.user_session.get("settings", {})
    settings["DEFAULT_MODEL"] = session.get('model', 'gpt-4o-mini')
    cl.user_session.set("settings", settings)
    
    if not silent:
        # 最近のメッセージを表示
        messages = await session_handler.get_messages(session_id, limit=3)
        
        response = f"""
✅ セッションを再開しました

**タイトル**: {session['title']}
**ID**: `{session_id[:8]}...`
**モデル**: {session.get('model', 'Unknown')}
**タグ**: {', '.join(cl.user_session.get("tags", [])) or 'なし'}

## 最近のメッセージ
"""
        
        for msg in messages[-3:]:
            role_icon = "👤" if msg['role'] == 'user' else "🤖"
            content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            response += f"\n{role_icon} {content_preview}"
        
        await cl.Message(content=response, author="System").send()
    
    return True


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
    
    # メッセージ履歴を取得（コンテキスト管理）
    messages = []
    if session_id:
        # 最大20メッセージまで取得（コンテキストウィンドウ管理）
        db_messages = await session_handler.get_messages(session_id, limit=20)
        
        # 古いメッセージを要約（将来の実装）
        messages = response_handler.format_messages_for_api(
            db_messages[-20:],  # 最新20メッセージ
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
                error_msg = f"❌ エラー: {chunk['error']}"
                ai_message = cl.Message(content=error_msg)
                await ai_message.send()
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
        
        # ストリーミング完了
        await ai_message.update()
        
        # レスポンスをデータベースに保存
        if session_id and full_response:
            await session_handler.add_message(
                session_id=session_id,
                role="assistant",
                content=full_response,
                token_usage=token_usage
            )
        
        # トークン使用量を表示（簡略化）
        if token_usage:
            total_tokens = cl.user_session.get("total_tokens", 0) + token_usage.get("total_tokens", 0)
            cl.user_session.set("total_tokens", total_tokens)
        
        # 最初のメッセージの場合、タイトルを自動生成
        if cl.user_session.get("message_count", 0) == 1:
            asyncio.create_task(auto_generate_title(session_id, messages))
    
    except Exception as e:
        error_msg = f"❌ エラーが発生しました: {str(e)}"
        await cl.Message(content=error_msg, author="System").send()
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
    
    # Phase 5の新コマンド
    if cmd == "/search":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/search [キーワード]`",
                author="System"
            ).send()
            return
        await search_sessions(args)
    
    elif cmd == "/recent":
        await show_recent_sessions()
    
    elif cmd == "/resume":
        await resume_last_session()
    
    elif cmd == "/tag":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/tag [タグ名]` または `/tag` でタグ一覧",
                author="System"
            ).send()
            await show_tags()
            return
        await add_tag(args)
    
    elif cmd == "/export":
        await export_session()
    
    # 既存のコマンド
    elif cmd == "/help":
        await show_help()
    
    elif cmd == "/model":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/model gpt-4o-mini`",
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
    
    # 設定系コマンド
    elif cmd == "/setkey":
        if not args:
            await cl.Message(
                content="❌ 使用方法: `/setkey sk-xxxxxxxxxxxxx`",
                author="System"
            ).send()
            return
        await set_api_key(args)
    
    elif cmd == "/test":
        await test_connection()
    
    elif cmd == "/status":
        await show_status()
    
    else:
        await cl.Message(
            content=f"❓ 不明なコマンド: {cmd}\n\n`/help` で利用可能なコマンドを確認できます。",
            author="System"
        ).send()


# === Phase 5 新機能 ===

async def search_sessions(keyword: str):
    """セッションを検索"""
    sessions = await session_handler.list_sessions(limit=50, search=keyword)
    
    if not sessions:
        await cl.Message(
            content=f"🔍 「{keyword}」に一致するセッションが見つかりません。",
            author="System"
        ).send()
        return
    
    result = f"# 🔍 検索結果: 「{keyword}」\n\n"
    for i, session in enumerate(sessions[:10], 1):
        created = session.get('created_at', 'Unknown')
        tags = session.get('tags', '')
        result += f"""
{i}. **{session['title']}**
   - ID: `{session['id'][:8]}...`
   - タグ: {tags or 'なし'}
   - 作成: {created}
"""
    
    result += f"\n💡 合計 {len(sessions)} 件見つかりました（上位10件表示）"
    result += "\n💡 切り替え: `/session [ID最初の8文字]`"
    
    await cl.Message(content=result, author="System").send()


async def show_recent_sessions(limit: int = 5):
    """最近のセッションを表示"""
    sessions = await session_handler.list_sessions(limit=limit)
    
    if not sessions:
        await cl.Message(
            content="📭 セッションがありません。",
            author="System"
        ).send()
        return
    
    current_id = cl.user_session.get("session_id")
    
    result = f"# 📅 最近のセッション（{limit}件）\n\n"
    for i, session in enumerate(sessions, 1):
        is_current = "⭐ " if session['id'] == current_id else ""
        msg_count = await session_handler.get_message_count(session['id'])
        tags = session.get('tags', '')
        
        result += f"""
{i}. {is_current}**{session['title']}**
   - 💬 {msg_count} メッセージ
   - 🏷️ {tags or 'タグなし'}
   - 📅 {session.get('updated_at', session.get('created_at', 'Unknown'))}
"""
    
    result += "\n💡 再開: `/resume` または `/session [ID]`"
    
    await cl.Message(content=result, author="System").send()


async def resume_last_session():
    """最後のセッションを再開"""
    sessions = await session_handler.list_sessions(limit=1)
    
    if not sessions:
        await cl.Message(
            content="📭 再開できるセッションがありません。",
            author="System"
        ).send()
        return
    
    last_session = sessions[0]
    await resume_session(last_session['id'])


async def add_tag(tag: str):
    """セッションにタグを追加"""
    session_id = cl.user_session.get("session_id")
    if not session_id:
        await cl.Message(
            content="❌ アクティブなセッションがありません。",
            author="System"
        ).send()
        return
    
    # 現在のタグを取得
    tags = cl.user_session.get("tags", [])
    
    # タグを追加（重複チェック）
    if tag not in tags:
        tags.append(tag)
        cl.user_session.set("tags", tags)
        
        # データベースに保存
        await session_handler.update_session(session_id, tags=tags)
        
        await cl.Message(
            content=f"✅ タグ「{tag}」を追加しました。\n現在のタグ: {', '.join(tags)}",
            author="System"
        ).send()
    else:
        await cl.Message(
            content=f"ℹ️ タグ「{tag}」は既に追加されています。\n現在のタグ: {', '.join(tags)}",
            author="System"
        ).send()


async def show_tags():
    """現在のタグを表示"""
    tags = cl.user_session.get("tags", [])
    if tags:
        await cl.Message(
            content=f"🏷️ 現在のタグ: {', '.join(tags)}",
            author="System"
        ).send()
    else:
        await cl.Message(
            content="🏷️ タグが設定されていません。",
            author="System"
        ).send()


async def export_session():
    """セッションをエクスポート（簡易版）"""
    session_id = cl.user_session.get("session_id")
    if not session_id:
        await cl.Message(
            content="❌ アクティブなセッションがありません。",
            author="System"
        ).send()
        return
    
    # セッション情報を取得
    session = await session_handler.get_session(session_id)
    messages = await session_handler.get_messages(session_id)
    
    # JSON形式でエクスポート
    export_data = {
        "session": {
            "id": session['id'],
            "title": session['title'],
            "model": session.get('model', 'unknown'),
            "created_at": str(session.get('created_at', '')),
            "tags": session.get('tags', '').split(',') if session.get('tags') else []
        },
        "messages": [
            {
                "role": msg['role'],
                "content": msg['content'],
                "created_at": str(msg.get('created_at', ''))
            }
            for msg in messages
        ],
        "statistics": {
            "message_count": len(messages),
            "total_tokens": cl.user_session.get("total_tokens", 0)
        }
    }
    
    # JSON文字列に変換
    json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
    
    # 結果を表示
    result = f"""
# 📤 セッションエクスポート

**タイトル**: {session['title']}
**メッセージ数**: {len(messages)}
**形式**: JSON

## エクスポートデータ（最初の500文字）
```json
{json_str[:500]}...
```

💡 **Phase 11で完全なエクスポート機能を実装予定**
- PDF形式
- HTML形式
- ファイルダウンロード
"""
    
    await cl.Message(content=result, author="System").send()


# === 既存機能の改善 ===

async def show_help():
    """コマンドヘルプを表示（Phase 5対応）"""
    help_message = f"""
# 📚 コマンドヘルプ (Phase 5)

## 🔍 検索・履歴機能（新機能）

### `/search [キーワード]`
- **説明**: セッションをキーワードで検索
- **使用例**: `/search Python`
- **検索対象**: タイトル、タグ

### `/recent`
- **説明**: 最近のセッション5件を表示
- **使用例**: `/recent`

### `/resume`
- **説明**: 最後のセッションを再開
- **使用例**: `/resume`

### `/tag [タグ名]`
- **説明**: 現在のセッションにタグを追加
- **使用例**: `/tag 重要`
- **一覧表示**: `/tag` （引数なし）

### `/export`
- **説明**: セッションをJSON形式でエクスポート（簡易版）
- **使用例**: `/export`

## 🤖 AI設定コマンド

### `/model [モデル名]`
- **説明**: このセッションで使用するモデルを変更
- **使用例**: `/model gpt-4o`

### `/system [プロンプト]`
- **説明**: システムプロンプトを設定
- **使用例**: `/system プログラミングの専門家として`

## 🗂️ セッション管理

### `/sessions`
- **説明**: セッション一覧を表示
- **使用例**: `/sessions`

### `/session [ID]`
- **説明**: 特定のセッションに切り替え
- **使用例**: `/session abc123de`

### `/rename [タイトル]`
- **説明**: セッションのタイトルを変更
- **使用例**: `/rename AI学習ノート`

### `/clear`
- **説明**: 新しいセッションを開始
- **使用例**: `/clear`

### `/stats`
- **説明**: 統計情報を表示
- **使用例**: `/stats`

## 💡 Phase 5のポイント

**効率的な会話管理**:
1. `/recent` で最近の会話を確認
2. `/resume` ですぐに前回の続きから
3. `/search Python` で過去の学習内容を検索
4. `/tag 重要` でセッションを分類

**コンテキスト管理**:
- 最大20メッセージまで記憶
- 古いメッセージは自動的に要約（今後実装）
- セッション間の切り替えが高速化
"""
    
    await cl.Message(content=help_message, author="System").send()


async def show_statistics():
    """統計情報を表示（改善版）"""
    stats = await session_handler.get_statistics()
    session_id = cl.user_session.get("session_id")
    
    db_size_mb = stats['db_size'] / (1024 * 1024)
    total_tokens = cl.user_session.get("total_tokens", 0)
    
    # タグ統計を計算
    all_sessions = await session_handler.list_sessions(limit=100)
    tag_counts = {}
    for session in all_sessions:
        tags = session.get('tags', '').split(',') if session.get('tags') else []
        for tag in tags:
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # 人気タグTop5
    popular_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    stats_message = f"""
# 📊 統計情報

## データベース
- **総セッション数**: {stats['session_count']}
- **総メッセージ数**: {stats['message_count']}
- **データベースサイズ**: {db_size_mb:.2f} MB
- **最終更新**: {stats.get('last_session_date', 'なし')}

## 現在のセッション
- **ID**: `{session_id[:8] if session_id else 'なし'}...`
- **メッセージ数**: {cl.user_session.get("message_count", 0)}
- **使用トークン**: {total_tokens:,}
- **タグ**: {', '.join(cl.user_session.get("tags", [])) or 'なし'}

## タグ統計
**人気タグ Top5**:
"""
    
    for i, (tag, count) in enumerate(popular_tags, 1):
        stats_message += f"\n{i}. {tag} ({count}回)"
    
    if not popular_tags:
        stats_message += "\nまだタグが使用されていません"
    
    await cl.Message(content=stats_message, author="System").send()


# === 既存機能（簡略化） ===

async def change_session_model(model: str):
    """セッションモデルを変更"""
    settings = cl.user_session.get("settings", {})
    settings["DEFAULT_MODEL"] = model
    cl.user_session.set("settings", settings)
    
    session_id = cl.user_session.get("session_id")
    if session_id:
        await session_handler.update_session(session_id, model=model)
    
    await cl.Message(
        content=f"✅ このセッションのモデルを {model} に変更しました",
        author="System"
    ).send()


async def set_system_prompt(prompt: str):
    """システムプロンプトを設定"""
    cl.user_session.set("system_prompt", prompt)
    
    session_id = cl.user_session.get("session_id")
    if session_id:
        await session_handler.update_session(session_id, system_prompt=prompt)
    
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


async def show_sessions():
    """セッション一覧を表示"""
    await show_recent_sessions(10)


async def switch_session(session_id: str):
    """セッションを切り替え"""
    sessions = await session_handler.list_sessions()
    target_session = None
    
    for session in sessions:
        if session['id'].startswith(session_id):
            target_session = session
            break
    
    if target_session:
        await resume_session(target_session['id'])
    else:
        await cl.Message(
            content=f"❌ セッション `{session_id}` が見つかりません。",
            author="System"
        ).send()


async def rename_session(new_title: str):
    """セッションをリネーム"""
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


async def start_new_session():
    """新しいセッションを開始"""
    settings = cl.user_session.get("settings", {})
    session_id = await create_new_session(settings)
    
    await cl.Message(
        content=f"""
✅ 新しいセッションを開始しました

**セッションID**: `{session_id[:8]}...`
**モデル**: {settings.get('DEFAULT_MODEL', 'gpt-4o-mini')}

チャットを始めてください！
        """,
        author="System"
    ).send()


async def set_api_key(api_key: str):
    """APIキーを設定"""
    success = config_manager.set_api_key(api_key)
    if success:
        new_settings = config_manager.get_all_settings()
        cl.user_session.set("settings", new_settings)
        response_handler.update_api_key(api_key)
        
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
    else:
        result = f"❌ 接続失敗: {message}"
    
    await cl.Message(content=result, author="System").send()


async def show_status():
    """設定状態を表示"""
    settings = config_manager.get_all_settings()
    
    status_message = f"""
## 📊 現在の設定

- **APIキー**: {settings.get('OPENAI_API_KEY_DISPLAY', '未設定')}
- **モデル**: {cl.user_session.get('settings', {}).get('DEFAULT_MODEL', 'gpt-4o-mini')}
- **セッション**: `{cl.user_session.get('session_id', 'なし')[:8] if cl.user_session.get('session_id') else 'なし'}...`
- **タグ**: {', '.join(cl.user_session.get("tags", [])) or 'なし'}
"""
    
    await cl.Message(content=status_message, author="System").send()


if __name__ == "__main__":
    print(f"Starting {APP_NAME} {VERSION}")
    print(f"Working Directory: {os.getcwd()}")
    
    current_settings = config_manager.get_all_settings()
    print(f"API Key: {current_settings.get('OPENAI_API_KEY_DISPLAY', 'Not set')}")
    print(f"Default Model: {current_settings.get('DEFAULT_MODEL', 'Not set')}")
