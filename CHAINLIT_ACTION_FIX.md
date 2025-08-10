# Chainlit Action API 修正ガイド

## 問題
Chainlitの新しいバージョンでは、`cl.Action`の引数が変更されています。

## エラー内容
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Action
payload
  Field required [type=missing, input_value=ArgsKwargs((), {'name': '...on': '接続テスト'}), input_type=ArgsKwargs]
```

## 修正内容

### 修正前（古いAPI）
```python
cl.Action(name="test_connection", value="test", description="接続テスト")
```

### 修正後（新しいAPI）
```python
cl.Action(name="test_connection", payload={"value": "test"}, description="接続テスト")
```

## 修正が必要な箇所

`app.py`内のすべての`cl.Action`呼び出し：

1. **on_chat_start関数内のアクションボタン** ✅ 修正済み
   ```python
   actions = [
       cl.Action(name="test_connection", payload={"value": "test"}, description="接続テスト"),
       cl.Action(name="show_status", payload={"value": "status"}, description="設定状態"),
       cl.Action(name="show_sessions", payload={"value": "sessions"}, description="セッション一覧"),
   ]
   ```

## Chainlitバージョンの確認

```bash
uv pip show chainlit
```

## 互換性のあるバージョン

- Chainlit 1.x系: `value`引数を使用
- Chainlit 2.x系: `payload`引数を使用（辞書形式）

## トラブルシューティング

### もし他のAction関連エラーが出た場合

1. すべての`cl.Action`の`value`を`payload`に変更
2. 値を辞書形式でラップ: `payload={"value": "xxx"}`
3. コールバック関数内でも対応:
   ```python
   @cl.action_callback("test_connection")
   async def test_connection_callback(action: cl.Action):
       # action.payloadで値を取得
       value = action.payload.get("value") if action.payload else None
   ```

## 確認済みの動作環境

- ✅ Chainlit 2.6.7以降
- ✅ Python 3.10以降
- ✅ Windows/Mac/Linux

## 今後の対応

Phase 4以降でも`cl.Action`を使用する場合は、必ず`payload`引数を使用してください。