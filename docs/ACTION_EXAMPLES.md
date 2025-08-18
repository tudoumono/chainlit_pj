# Chainlit Action API 実装例

このファイルは、`utils/action_helper.py`を使用した実装例を示します。

## 1. 基本的な使い方

```python
from utils.action_helper import ask_confirmation, ask_choice, create_action

# 確認ダイアログ（シンプル）
async def delete_file(file_id: str):
    if await ask_confirmation(f"ファイル {file_id} を削除しますか？"):
        # 削除処理
        await perform_delete(file_id)
        await cl.Message(content="✅ 削除しました").send()
    else:
        await cl.Message(content="❌ キャンセルしました").send()

# 選択メニュー
async def select_model():
    model = await ask_choice(
        "使用するモデルを選択してください",
        {
            "gpt-4o": "GPT-4 Optimized",
            "gpt-4o-mini": "GPT-4 Mini",
            "gpt-3.5-turbo": "GPT-3.5 Turbo"
        }
    )
    
    if model:
        await cl.Message(content=f"✅ {model}を選択しました").send()
```

## 2. カスタムアクション

```python
from utils.action_helper import create_action, get_action_value

async def custom_menu():
    # カスタムアクションを作成
    actions = [
        create_action("save", "save", "💾 保存", format="json"),
        create_action("export", "export", "📤 エクスポート", format="csv"),
        create_action("cancel", "cancel", "❌ キャンセル")
    ]
    
    res = await cl.AskActionMessage(
        content="アクションを選択してください",
        actions=actions
    ).send()
    
    # レスポンス処理
    action = get_action_value(res, "action")
    format_type = get_action_value(res, "format")
    
    if action == "save":
        await save_data(format_type)
    elif action == "export":
        await export_data(format_type)
```

## 3. 複雑な確認ダイアログ

```python
async def complex_confirmation():
    res = await cl.AskActionMessage(
        content="この操作は元に戻せません。本当に実行しますか？",
        actions=[
            cl.Action(
                name="confirm",
                payload={
                    "confirmed": True,
                    "backup": True,
                    "notify": False
                },
                label="バックアップを作成して実行"
            ),
            cl.Action(
                name="confirm_notify",
                payload={
                    "confirmed": True,
                    "backup": True,
                    "notify": True
                },
                label="バックアップ作成＆通知して実行"
            ),
            cl.Action(
                name="cancel",
                payload={"confirmed": False},
                label="キャンセル"
            )
        ]
    ).send()
    
    if res:
        payload = res.get("payload", {})
        if payload.get("confirmed"):
            if payload.get("backup"):
                await create_backup()
            if payload.get("notify"):
                await send_notification()
            await execute_action()
```

## 4. エラー処理を含む実装

```python
from utils.action_helper import validate_payload

async def safe_action():
    try:
        res = await cl.AskActionMessage(
            content="選択してください",
            actions=[
                cl.Action(name="a", payload={"action": "a"}, label="A"),
                cl.Action(name="b", payload={"action": "b"}, label="B")
            ],
            timeout=30
        ).send()
        
        if res:
            payload = res.get("payload")
            
            # ペイロードの検証
            if not validate_payload(payload):
                raise ValueError("Invalid payload format")
            
            action = payload.get("action")
            # 処理を実行
            
    except TimeoutError:
        await cl.Message(content="⏱️ タイムアウトしました").send()
    except ValueError as e:
        await cl.Message(content=f"❌ エラー: {e}").send()
```

## 5. 定数を使った実装

```python
# 定数定義
class Actions:
    CONFIRM = {"action": "confirm"}
    CANCEL = {"action": "cancel"}
    YES = {"action": "yes"}
    NO = {"action": "no"}
    
    CREATE = {"action": "create", "type": "new"}
    UPDATE = {"action": "update", "type": "modify"}
    DELETE = {"action": "delete", "type": "remove"}

# 使用例
async def use_constants():
    res = await cl.AskActionMessage(
        content="操作を選択してください",
        actions=[
            cl.Action(name="create", payload=Actions.CREATE, label="新規作成"),
            cl.Action(name="update", payload=Actions.UPDATE, label="更新"),
            cl.Action(name="delete", payload=Actions.DELETE, label="削除"),
            cl.Action(name="cancel", payload=Actions.CANCEL, label="キャンセル")
        ]
    ).send()
    
    if res:
        payload = res.get("payload", {})
        action = payload.get("action")
        action_type = payload.get("type")
        
        print(f"Action: {action}, Type: {action_type}")
```

## 6. 型ヒント付き実装

```python
from typing import Optional, Dict, Any

async def typed_action() -> Optional[str]:
    """型ヒント付きのアクション処理"""
    
    res: Optional[Dict[str, Any]] = await cl.AskActionMessage(
        content="選択してください",
        actions=[
            cl.Action(name="opt1", payload={"value": "option1"}, label="オプション1"),
            cl.Action(name="opt2", payload={"value": "option2"}, label="オプション2")
        ]
    ).send()
    
    if res:
        payload: Dict[str, Any] = res.get("payload", {})
        value: Optional[str] = payload.get("value")
        return value
    
    return None
```

## まとめ

1. **常に`payload`は辞書型で定義する**
2. **`get("payload", {})`でデフォルト値を設定する**
3. **ヘルパー関数を活用してコードを簡潔にする**
4. **エラー処理を適切に実装する**
5. **型ヒントで安全性を高める**
