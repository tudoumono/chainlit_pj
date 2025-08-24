# ベクトルストアセキュリティ実装ガイド

## 概要
他人のベクトルストア操作を防止するための具体的な実装方法です。OpenAI APIキーが共有されている環境でも、アプリケーション層でアクセス制御を実現します。

## 実装の核心

### 1. メタデータによるアクセス制御

```python
# ベクトルストア作成時にメタデータを付与
metadata = {
    "user_id": "user_123",           # 所有者ID
    "access_level": "private",       # アクセスレベル
    "category": "technical_docs",    # カテゴリ
    "created_at": "2025-08-20T10:00:00",
    "ownership_hash": "a1b2c3d4..."  # 所有権検証用ハッシュ
}

vector_store = await client.beta.vector_stores.create(
    name="My Private Knowledge Base",
    metadata=metadata
)
```

### 2. アクセスレベルの実装

| レベル | 説明 | 読み取り | 書き込み | 削除 |
|--------|------|----------|----------|------|
| **private** | 所有者のみ | 所有者 | 所有者 | 所有者 |
| **team** | チーム共有 | チーム全員 | チーム全員 | 所有者のみ |
| **public** | 公開 | 全員 | 所有者 | 所有者 |

### 3. アクセス制御フロー

```
ユーザーがベクトルストア操作を要求
    ↓
ユーザーIDを取得（認証情報から）
    ↓
ベクトルストアのメタデータを取得
    ↓
アクセス権限をチェック
    ├─ 所有者？ → 全権限許可
    ├─ チームメンバー？ → 読み書き許可
    ├─ パブリック？ → 読み取りのみ許可
    └─ その他 → アクセス拒否
    ↓
操作を実行/拒否
    ↓
アクセスログを記録
```

## 具体的な実装

### ファイル構成

```
utils/
├── security/
│   ├── __init__.py
│   ├── vector_store_security.py      # セキュリティ管理
│   ├── secure_vector_store_handler.py # セキュア版ハンドラー
│   └── app_integration_example.py    # 統合例
└── vector_store_handler.py           # 既存のハンドラー（更新必要）
```

### 実装手順

#### Step 1: セキュリティモジュールの導入

```python
# utils/vector_store_handler.py に追加
from utils.security.vector_store_security import security_manager, access_logger

class VectorStoreHandler:
    async def create_vector_store(self, name: str, user_id: str = None, 
                                 file_ids: List[str] = None) -> Optional[str]:
        # ユーザーIDが提供されていれば、メタデータを追加
        metadata = {}
        if user_id:
            metadata = security_manager.create_secure_metadata(
                user_id=user_id,
                api_key=self.api_key
            )
        
        vector_store = await self.async_client.beta.vector_stores.create(
            name=name,
            file_ids=file_ids,
            metadata=metadata  # セキュリティメタデータを追加
        )
        
        # アクセスログを記録
        if user_id:
            access_logger.log_access(
                user_id=user_id,
                vector_store_id=vector_store.id,
                action="create",
                success=True
            )
        
        return vector_store.id
```

#### Step 2: app.pyでの統合

```python
# app.py の修正例
@cl.on_message
async def handle_message(message: cl.Message):
    # ユーザーIDを取得
    user = cl.user_session.get("user")
    user_id = user.identifier if user else f"anon_{cl.user_session.get('session_id')[:8]}"
    
    # コマンド処理
    if message.content.startswith("/vs create"):
        # セキュアなベクトルストア作成
        vs_id = await vector_store_handler.create_vector_store(
            name=f"Personal KB - {user_id}",
            user_id=user_id  # ユーザーIDを渡す
        )
    
    elif message.content.startswith("/vs list"):
        # ユーザーがアクセス可能なもののみ表示
        await show_my_vector_stores()  # セキュア版の一覧表示
    
    elif message.content.startswith("/vs delete"):
        # 所有者のみ削除可能
        parts = message.content.split()
        if len(parts) > 2:
            await delete_my_vector_store(parts[2])  # セキュア版の削除
```

#### Step 3: 一覧表示のフィルタリング

```python
async def list_vector_stores(self, user_id: str = None) -> List[Dict]:
    """ユーザーがアクセス可能なベクトルストアのみ返す"""
    
    # 全てのベクトルストアを取得
    all_stores = await self.async_client.beta.vector_stores.list()
    
    if not user_id:
        # ユーザーIDがない場合は全て返す（後方互換性）
        return [self._format_store(vs) for vs in all_stores.data]
    
    # フィルタリング
    accessible_stores = []
    for vs in all_stores.data:
        vs_detail = await self.async_client.beta.vector_stores.retrieve(vs.id)
        metadata = getattr(vs_detail, 'metadata', {}) or {}
        
        # アクセス権限チェック
        if security_manager.can_access(metadata, user_id, self.api_key, "read"):
            accessible_stores.append(self._format_store(vs_detail))
    
    return accessible_stores
```

## セキュリティ機能の詳細

### 所有権ハッシュ
```python
# ユーザーIDとAPIキーから一意のハッシュを生成
ownership_hash = hashlib.sha256(
    f"{user_id}:{api_key[:8]}...{api_key[-4:]}".encode()
).hexdigest()[:16]
```

### アクセスログ
```json
{
    "timestamp": "2025-08-20T10:30:45",
    "user_id": "user_123",
    "vector_store_id": "vs_abc123",
    "action": "delete",
    "success": false,
    "reason": "Access denied"
}
```

### 共有設定の変更
```python
# チーム共有に変更
await share_my_vector_store(vs_id, "team")

# 公開設定に変更
await share_my_vector_store(vs_id, "public")

# プライベートに戻す
await share_my_vector_store(vs_id, "private")
```

## エラーハンドリング

```python
try:
    # ベクトルストア操作
    result = await delete_secure_vector_store(vs_id, user_id)
    
except PermissionError:
    # アクセス拒否
    await cl.Message(
        content="❌ このベクトルストアを操作する権限がありません",
        author="System"
    ).send()
    
except Exception as e:
    # その他のエラー
    await cl.Message(
        content=f"❌ エラーが発生しました: {e}",
        author="System"
    ).send()
```

## テスト方法

### 1. 異なるユーザーでのテスト
```python
# ユーザーA（所有者）
user_a = "alice@example.com"
vs_id = await create_secure_vector_store("Alice's KB", user_a)

# ユーザーB（他人）
user_b = "bob@example.com"
result = await delete_secure_vector_store(vs_id, user_b)
# → アクセス拒否されるはず
```

### 2. 共有設定のテスト
```python
# プライベート → チーム共有
await share_my_vector_store(vs_id, "team")

# チームメンバーがアクセス
stores = await list_user_vector_stores(team_member_id)
# → 共有されたVSが表示されるはず
```

### 3. ログの確認
```python
# アクセスログを確認
history = access_logger.get_user_access_history(user_id, limit=10)
for entry in history:
    print(f"{entry['timestamp']}: {entry['action']} - {entry['success']}")
```

## まとめ

この実装により、以下のセキュリティ機能が実現されます：

1. **所有者制御** - 各ベクトルストアに所有者を設定
2. **アクセスレベル** - private/team/publicの3段階
3. **操作ログ** - 全ての操作を記録
4. **権限チェック** - 操作前に必ず権限を確認
5. **共有機能** - 必要に応じて他者と共有可能

これらの機能により、同一APIキーを使用する環境でも、安全にベクトルストアを管理できます。
