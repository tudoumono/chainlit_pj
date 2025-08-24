# セキュアなベクトルストア管理実装ガイド

## 概要
所有者のベクトルストアのみ表示・変更可能、他人のVSはIDを知っていれば読み取り専用で使用可能な実装です。

## 主な仕様

### 1. プライバシー保護
- `/vs`コマンドで表示されるのは**自分が作成したもののみ**
- 他人のベクトルストアは一覧に表示されない
- プライバシーを保護しつつ、明示的な共有を可能にする

### 2. アクセス制御

| 操作 | 所有者 | IDを知っている他人 |
|------|--------|-------------------|
| **一覧表示** | ✅ 表示される | ❌ 表示されない |
| **詳細確認** | ✅ 可能 | ✅ 可能（IDで） |
| **使用（読み取り）** | ✅ 可能 | ✅ 可能（IDで） |
| **名前変更** | ✅ 可能 | ❌ 不可 |
| **削除** | ✅ 可能 | ❌ 不可 |
| **ファイル追加** | ✅ 可能 | ❌ 不可 |

### 3. メタデータ構造
```python
metadata = {
    "owner_id": "user_123",      # 所有者ID（必須）
    "created_at": "2025-08-20",  # 作成日時
    "category": "general",       # カテゴリ
    "visibility": "private"      # 可視性（将来の拡張用）
}
```

## 実装ファイル

### 1. `utils/secure_vector_store_manager.py`
セキュアなベクトルストア管理の中核モジュール

主なクラス：
- `SecureVectorStoreManager` - セキュア管理クラス

主なメソッド：
- `create_personal_vector_store()` - 所有者情報付きでVS作成
- `list_my_vector_stores()` - 自分のVSのみ取得
- `can_modify()` - 変更権限チェック
- `can_read()` - 読み取り権限チェック
- `use_vector_store()` - IDでVSを使用

### 2. `utils/secure_vs_commands.py`
app.py統合用のコマンドハンドラー

主な関数：
- `handle_vs_command_secure()` - /vsコマンドの処理
- `show_my_vector_stores_only()` - 自分のVSのみ表示
- `use_vector_store_by_id()` - IDでVS使用（他人のも可）

## app.pyへの統合方法

### Step 1: インポート追加
```python
# app.pyの先頭に追加
from utils.secure_vector_store_manager import initialize_secure_manager
from utils.secure_vs_commands import (
    handle_vs_command_secure,
    handle_file_upload_to_vector_store,
    validate_and_use_vector_stores
)
```

### Step 2: 初期化
```python
@cl.on_chat_start
async def on_chat_start():
    # ... 既存のコード ...
    
    # セキュアマネージャーを初期化
    from utils.vector_store_handler import vector_store_handler
    initialize_secure_manager(vector_store_handler)
    
    # ... 既存のコード ...
```

### Step 3: /vsコマンドの置き換え
```python
@cl.on_message
async def on_message(message: cl.Message):
    # ... 既存のコード ...
    
    # /vsコマンドの処理をセキュア版に置き換え
    if message_content.startswith("/vs") or message_content.startswith("/vector"):
        await handle_vs_command_secure(message_content)
        return
    
    # ... 既存のコード ...
```

### Step 4: ファイルアップロード処理の修正
```python
# ファイルアップロード時の処理
if message.elements:
    # セキュア版のファイルアップロード処理
    await handle_file_upload_to_vector_store(message.elements)
```

### Step 5: ベクトルストアID設定の修正
```python
@cl.on_settings_update
async def on_settings_update(settings):
    # ... 既存のコード ...
    
    # ベクトルストアIDの検証と使用設定
    if "Vector_Store_IDs" in settings:
        vs_ids_string = settings["Vector_Store_IDs"]
        valid_ids = await validate_and_use_vector_stores(vs_ids_string)
        
        # 有効なIDのみ設定
        tools_config.set_vector_store_ids(valid_ids)
    
    # ... 既存のコード ...
```

## 使用例

### 1. 自分のベクトルストア作成
```
ユーザーA: /vs create "技術文書" programming
システム: ✅ ベクトルストアを作成しました
         ID: vs_abc123
         所有者: あなた
```

### 2. 自分のベクトルストア一覧
```
ユーザーA: /vs
システム: # マイベクトルストア
         - vs_abc123 (技術文書) [所有]
         - vs_def456 (プロジェクト) [所有]
         
         注意: 表示されるのはあなたが所有するもののみです
```

### 3. 他人のベクトルストアを使用
```
ユーザーB: /vs use vs_abc123
システム: ✅ ベクトルストアを使用設定しました（読み取り専用）
         ID: vs_abc123
         所有者: 他のユーザー
         注意: 読み取り専用です。変更はできません。
```

### 4. 他人のベクトルストアを変更しようとした場合
```
ユーザーB: /vs delete vs_abc123
システム: ❌ このベクトルストアを削除する権限がありません
         （所有者のみ削除可能）
```

### 5. IDを共有して協力
```
ユーザーA: 「私のナレッジベースを使ってください: vs_abc123」
ユーザーB: /vs use vs_abc123
システム: ✅ 読み取り専用で使用可能になりました
```

## セキュリティ上の利点

1. **プライバシー保護**
   - 他人のVSは見えない
   - 所有者情報は保護される

2. **明示的な共有**
   - IDを知っている人だけがアクセス可能
   - URLのように共有できる

3. **権限の明確化**
   - 所有者のみが変更可能
   - 他人は読み取りのみ

4. **誤操作防止**
   - 他人のVSを誤って削除・変更できない
   - 権限チェックが自動的に行われる

## トラブルシューティング

### Q: 他人のVSが見えない
A: 仕様です。IDを直接教えてもらってください。

### Q: 他人のVSを変更したい
A: 不可能です。所有者に依頼してください。

### Q: 共有したVSを取り消したい
A: VSを削除するか、新しいVSを作成してください。

### Q: 誰がVSの所有者か確認したい
A: セキュリティ上、所有者情報は表示されません。

## 今後の拡張案

1. **共有レベルの追加**
   - read-only / read-write の選択
   - グループ共有機能

2. **有効期限付き共有**
   - 一時的なアクセス権限
   - 自動失効機能

3. **アクセスログ**
   - 誰がいつアクセスしたか記録
   - 監査機能

4. **招待機能**
   - メールやリンクで招待
   - アクセストークン方式
