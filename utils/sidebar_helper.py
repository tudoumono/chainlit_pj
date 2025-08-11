"""
サイドバー実装の代替案：
チャットプロファイルを使用した履歴表示
"""

import chainlit as cl
from typing import List, Dict
from datetime import datetime
import json


class SessionSidebar:
    """セッション履歴をサイドバー風に表示するヘルパークラス"""
    
    @staticmethod
    async def create_session_buttons(sessions: List[Dict], current_session_id: str) -> List[cl.Action]:
        """セッションリストからアクションボタンを作成"""
        actions = []
        
        for session in sessions[:15]:  # 最大15件表示
            # セッション情報を整形
            is_current = "▶️ " if session['id'] == current_session_id else ""
            title = session.get('title', 'Untitled')
            
            # タイトルが長い場合は短縮
            if len(title) > 25:
                title = title[:22] + "..."
            
            # 更新日時を整形
            updated = session.get('updated_at', session.get('created_at', ''))
            time_str = ""
            if updated:
                try:
                    dt = datetime.fromisoformat(updated.replace(' ', 'T'))
                    if dt.date() == datetime.now().date():
                        time_str = dt.strftime('%H:%M')
                    else:
                        time_str = dt.strftime('%m/%d')
                except:
                    pass
            
            # アクションを作成
            action = cl.Action(
                name=f"load_session_{session['id'][:8]}",
                value=session['id'],
                label=f"{is_current}{title}",
                description=f"{time_str}"
            )
            actions.append(action)
        
        return actions
    
    @staticmethod
    async def show_inline_history(sessions: List[Dict], current_session_id: str) -> str:
        """インライン形式で履歴を表示（メッセージ内）"""
        
        if not sessions:
            return "📭 履歴がありません"
        
        result = "## 📚 セッション履歴\n\n"
        
        for i, session in enumerate(sessions[:10], 1):
            is_current = "▶️" if session['id'] == current_session_id else "　"
            
            # セッション情報
            title = session.get('title', 'Untitled')
            session_id = session['id'][:8]
            
            # タグ
            tags = session.get('tags', '')
            tag_str = f" `{tags}`" if tags else ""
            
            # 日時
            updated = session.get('updated_at', session.get('created_at', ''))
            date_str = ""
            if updated:
                try:
                    dt = datetime.fromisoformat(updated.replace(' ', 'T'))
                    date_str = dt.strftime('%m/%d %H:%M')
                except:
                    pass
            
            result += f"{is_current} **{i}.** [{title}](command:/session {session_id}) {tag_str} - {date_str}\n"
        
        result += "\n💡 クリックまたは `/session [ID]` で切り替え"
        
        return result
    
    @staticmethod
    async def create_floating_panel(sessions: List[Dict], current_session_id: str) -> cl.Text:
        """フローティングパネル風の履歴表示"""
        
        panel_content = """
<div style="
    position: fixed;
    right: 20px;
    top: 100px;
    width: 250px;
    max-height: 500px;
    overflow-y: auto;
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    z-index: 1000;
">
    <h3 style="margin: 0 0 10px 0; font-size: 16px;">📚 セッション履歴</h3>
    <div style="font-size: 14px;">
"""
        
        for session in sessions[:10]:
            is_current = "▶️" if session['id'] == current_session_id else ""
            title = session.get('title', 'Untitled')[:25]
            session_id = session['id'][:8]
            
            panel_content += f"""
        <div style="
            padding: 5px;
            margin: 5px 0;
            cursor: pointer;
            border-radius: 4px;
            background: {'#e3f2fd' if is_current else 'transparent'};
        ">
            {is_current} {title}<br>
            <small style="color: #666;">ID: {session_id}</small>
        </div>
"""
        
        panel_content += """
    </div>
</div>
"""
        
        return cl.Text(
            name="session_panel",
            content=panel_content,
            display="inline",
            language="html"
        )


# 使用例：app.pyに組み込む場合

async def show_session_sidebar():
    """セッション履歴をサイドバー風に表示"""
    from utils.session_handler import session_handler
    
    sessions = await session_handler.list_sessions(limit=15)
    current_session_id = cl.user_session.get("session_id")
    
    # 方法1: アクションボタンとして表示
    actions = await SessionSidebar.create_session_buttons(sessions, current_session_id)
    if actions:
        await cl.Message(
            content="### 📚 セッション履歴",
            actions=actions
        ).send()
    
    # 方法2: インライン履歴として表示
    history_text = await SessionSidebar.show_inline_history(sessions, current_session_id)
    await cl.Message(content=history_text).send()
    
    # 方法3: HTMLパネルとして表示（実験的）
    # panel = await SessionSidebar.create_floating_panel(sessions, current_session_id)
    # await panel.send()


# アクションコールバックの登録
@cl.action_callback(pattern=r"^load_session_.*")
async def on_session_action(action: cl.Action):
    """セッションボタンがクリックされた時の処理"""
    session_id = action.value
    # ここでセッション切り替え処理を実行
    # await resume_session(session_id)
    await cl.Message(f"セッション {session_id[:8]} を読み込みます...").send()
