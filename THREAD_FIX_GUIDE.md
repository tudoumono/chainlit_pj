# Chainlit履歴保存修正ガイド

## 問題の原因
ログとコードの分析により、以下の問題が判明しました：
- ✅ `create_step`は呼ばれており、ステップは保存されている
- ❌ `create_thread`が一度も呼ばれていない
- ❌ そのため`list_threads`で常に「スレッド総数: 0」となる

**根本原因：** app.pyでスレッド（Thread）を明示的に作成していないこと

## 修正内容

### 1. 必要なインポートの追加
```python
import uuid  # スレッドID生成用
import chainlit.data as cl_data  # データレイヤーアクセス用
```

### 2. on_chat_start関数の修正
新しいチャットセッション開始時にスレッドを作成：
```python
@cl.on_chat_start
async def on_chat_start():
    # ... 既存のコード ...
    
    # 新しいスレッドを作成（履歴保存のため必須）
    thread_id = str(uuid.uuid4())
    thread = ThreadDict(
        id=thread_id,
        name=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        userId=current_user.identifier if current_user else "anonymous",
        user_identifier=current_user.identifier if current_user else "anonymous",
        tags=[],
        metadata={},
        createdAt=datetime.now().isoformat()
    )
    
    # データレイヤーにスレッドを作成
    if hasattr(cl_data, '_data_layer') and cl_data._data_layer:
        try:
            await cl_data._data_layer.create_thread(thread)
            print(f"✅ 新しいスレッドを作成しました: {thread_id}")
        except Exception as e:
            print(f"⚠️ スレッド作成エラー: {e}")
    
    # セッションにスレッドIDを保存
    cl.user_session.set("thread_id", thread_id)
```

### 3. start_new_chat関数の修正
新しいチャットを開始する際にも同様にスレッドを作成

## 確認方法

### 1. アプリケーションを再起動
```bash
# Ctrl+C で現在のプロセスを停止後
chainlit run app.py --headless
```

### 2. チャットでメッセージを送信
通常通りチャットを行い、複数のメッセージをやり取りします。

### 3. データベースの確認
```bash
python check_threads.py
```

### 4. 期待される結果
- `create_thread`がログに表示される
- `list_threads`で実際のスレッド数が表示される
- 左上の履歴ボタンから過去の会話が確認できる

## トラブルシューティング

### データベースをリセットする場合
```bash
# データベースファイルを削除
rm .chainlit/chainlit.db

# アプリケーションを再起動
chainlit run app.py --headless
```

### ログで確認すべき内容
成功時のログ例：
```
🔧 SQLite: create_threadが呼ばれました - ID: xxxxx
   ✅ スレッドをSQLiteに保存しました
🔧 SQLite: list_threadsが呼ばれました
   スレッド総数: 1
   取得したスレッド数: 1
```

## まとめ
この修正により、Chainlitアプリケーションで履歴が正しく保存されるようになります。
スレッドとステップの両方が適切にデータベースに保存され、
アプリケーションを再起動しても履歴が永続的に保持されます。
