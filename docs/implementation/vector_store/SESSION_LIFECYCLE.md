# ベクトルストア管理システム - セッションVSの仕組み

## 概要
セッションVS（セッション用ベクトルストア）は、各チャットセッション専用の一時的なナレッジベースです。

## 重要な仕様

### 作成タイミング
- ファイルアップロード時に自動的に作成
- 各チャットセッションに1つずつ作成

### 削除タイミング
- **履歴削除時に自動的に削除されます**
- チャット終了時には削除されません
- 履歴は維持したままセッションVSの内容を参照可能

## 実装の詳細

### 1. セッションVSの作成
```python
# auto_vector_store_manager.py
async def get_or_create_session_vs(self, session_id, user_id):
    # セッションVSを作成
    vs_id = await create_vector_store()
    
    # スレッドに紐付け（重要！）
    await data_layer.update_thread_vector_store(thread_id, vs_id)
```

### 2. スレッドとの紐付け
- セッションVS作成時に`thread_id`と`vector_store_id`を紐付け
- データベースの`threads`テーブルに`vector_store_id`カラムとして保存

### 3. 履歴削除時の自動削除
```python
# data_layer.py
async def delete_thread(self, thread_id):
    # スレッドに紐付いたベクトルストアを取得
    thread = await self.get_thread(thread_id)
    if thread and thread.get("vector_store_id"):
        # ベクトルストアを削除
        await vector_store_handler.delete_vector_store(vector_store_id)
    
    # スレッドとその履歴を削除
    await db.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
```

## 利点
1. **履歴の永続性**: チャットを閉じても履歴とVSの内容が保持される
2. **自動クリーンアップ**: 履歴削除時に関連リソースも自動削除
3. **リソース管理**: OpenAI側のベクトルストアも適切に削除

## 注意事項
- セッションVSは履歴と連動して管理されます
- 履歴を残したい場合はセッションVSも残ります
- 履歴を削除するとセッションVSも削除されます
