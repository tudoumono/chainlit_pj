# Chainlit API 修正ガイド (Phase 4)

## 発生したエラーと修正内容

### 1. Message.update()のAPI変更
**エラー**:
```python
TypeError: Message.update() got an unexpected keyword argument 'content'
```

**修正前**:
```python
await msg.update(content="新しい内容")
```

**修正後**:
```python
# ストリーミング完了時は引数なしで更新
await msg.update()

# 新しいメッセージの送信
await cl.Message(content="新しい内容").send()
```

### 2. Message送信時の.send()必須
**エラー**:
```python
TypeError: object Message can't be used in 'await' expression
```

**修正前**:
```python
await cl.Message(content="メッセージ")
```

**修正後**:
```python
await cl.Message(content="メッセージ").send()
```

### 3. stream_tokenに.send()は不要
**エラー**:
```python
RuntimeWarning: coroutine 'stream_token' was never awaited
```

**修正前**:
```python
await ai_message.stream_token(token).send()
```

**修正後**:
```python
await ai_message.stream_token(token)
```

### 4. メッセージの2重表示防止
**問題**: ストリーミング後に同じ内容が2回表示される

**修正前**:
```python
# ストリーミング
ai_message = cl.Message(content="")
await ai_message.send()
for token in response:
    await ai_message.stream_token(token)

# 最終メッセージ（これが2重表示の原因）
await cl.Message(content=full_response).send()
```

**修正後**:
```python
# ストリーミング
ai_message = cl.Message(content="")
await ai_message.send()
for token in response:
    await ai_message.stream_token(token)

# 最終更新（同じメッセージを更新）
await ai_message.update()
```

## Chainlit 2.x系の正しい使い方

### メッセージの基本操作
```python
# 新規メッセージ送信
msg = cl.Message(content="内容")
await msg.send()

# ストリーミング
msg = cl.Message(content="")
await msg.send()
await msg.stream_token("追加テキスト")
await msg.update()  # 完了時

# エラーメッセージ
await cl.Message(content="エラー", author="System").send()
```

### アクションボタン
```python
# payloadを使用（Phase 3で修正済み）
cl.Action(name="action", payload={"key": "value"}, description="説明")
```

## 確認済みバージョン
- Chainlit 2.6.7以降
- OpenAI 1.57.4以降
- Python 3.10以降

## 今後の注意点
Phase 5以降でも同様のAPI使用法を守る必要があります：
1. 必ず`.send()`を付ける
2. `update()`は引数なし
3. `stream_token`は`.send()`不要
4. 1つのメッセージを使い回す（2重送信しない）