# Chainlit Action API ガイド

## ⚠️ 重要な注意事項

**ChainlitのAction APIでは、`payload`パラメータは必ず辞書型（dict）である必要があります。**

## ❌ よくある間違い

```python
# 間違い1: 文字列を使用
cl.Action(name="action", payload="yes", label="はい")  # ❌ エラー

# 間違い2: valueパラメータを使用（古いAPI）
cl.Action(name="action", value="yes", label="はい")  # ❌ エラー
```

## ✅ 正しい使い方

### 1. 基本的な使い方

```python
# 正しい: payloadは辞書型
cl.Action(
    name="action_name",
    payload={"action": "yes"},  # ✅ 辞書型
    label="はい"
)
```

### 2. 複数の値を含む場合

```python
cl.Action(
    name="edit_action",
    payload={
        "action": "edit",
        "target": "model",
        "value": "gpt-4"
    },
    label="編集"
)
```

### 3. レスポンスの処理

```python
# アクションメッセージを送信
res = await cl.AskActionMessage(
    content="選択してください",
    actions=[
        cl.Action(name="yes", payload={"action": "yes"}, label="はい"),
        cl.Action(name="no", payload={"action": "no"}, label="いいえ")
    ]
).send()

# レスポンスの確認（必ずデフォルト値を設定）
if res and res.get("payload", {}).get("action") == "yes":
    # はいが選択された場合の処理
    pass
```

## 📋 チェックリスト

新しいActionを実装する際は、以下を確認してください：

- [ ] `payload`パラメータを使用している（`value`ではない）
- [ ] `payload`の値は辞書型である
- [ ] レスポンス処理で`get("payload", {})`を使用している
- [ ] ネストした値には`.get("key")`でアクセスしている

## 🔍 デバッグ方法

エラーが発生した場合：

1. エラーメッセージを確認
   ```
   Input should be a valid dictionary [type=dict_type, input_value='yes', input_type=str]
   ```
   → payloadが文字列になっている

2. payloadの型を確認
   ```python
   print(type(action.payload))  # <class 'dict'>であるべき
   ```

3. レスポンスの構造を確認
   ```python
   print(res)  # {'name': 'action_name', 'payload': {'action': 'yes'}}
   ```

## 📝 実装例

### 確認ダイアログ

```python
async def ask_confirmation(message: str) -> bool:
    """確認ダイアログを表示"""
    res = await cl.AskActionMessage(
        content=message,
        actions=[
            cl.Action(name="confirm", payload={"confirmed": True}, label="確認"),
            cl.Action(name="cancel", payload={"confirmed": False}, label="キャンセル")
        ]
    ).send()
    
    return res and res.get("payload", {}).get("confirmed", False)
```

### 選択メニュー

```python
async def show_menu():
    """選択メニューを表示"""
    res = await cl.AskActionMessage(
        content="オプションを選択してください",
        actions=[
            cl.Action(name="opt1", payload={"option": "create"}, label="作成"),
            cl.Action(name="opt2", payload={"option": "edit"}, label="編集"),
            cl.Action(name="opt3", payload={"option": "delete"}, label="削除"),
            cl.Action(name="opt4", payload={"option": "cancel"}, label="キャンセル")
        ]
    ).send()
    
    if res:
        option = res.get("payload", {}).get("option")
        if option == "create":
            await handle_create()
        elif option == "edit":
            await handle_edit()
        elif option == "delete":
            await handle_delete()
        # cancelの場合は何もしない
```

## 🚨 エラー回避のベストプラクティス

1. **常に辞書型を使用**
   ```python
   payload={"key": "value"}  # ✅
   ```

2. **デフォルト値を設定**
   ```python
   res.get("payload", {}).get("action", "default")
   ```

3. **型ヒントを活用**
   ```python
   from typing import Dict, Any
   
   def create_action(name: str, payload: Dict[str, Any], label: str):
       return cl.Action(name=name, payload=payload, label=label)
   ```

4. **定数を使用**
   ```python
   # アクション定数を定義
   ACTION_YES = {"action": "yes"}
   ACTION_NO = {"action": "no"}
   ACTION_CANCEL = {"action": "cancel"}
   
   # 使用時
   cl.Action(name="confirm", payload=ACTION_YES, label="はい")
   ```

## 📚 参考リンク

- [Chainlit公式ドキュメント](https://docs.chainlit.io/)
- [Action API Reference](https://docs.chainlit.io/api-reference/action)

---

最終更新: 2025-08-18
