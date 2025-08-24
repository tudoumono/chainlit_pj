# ベクトルストアAPI移行ガイド

## 背景

OpenAIの`beta.vector_stores` APIは廃止予定（deprecated）となりました。
- 参考: [GitHub Issue #2451](https://github.com/openai/openai-python/issues/2451)
- 参考: [公式移行ガイド](https://platform.openai.com/docs/guides/migrate-to-responses)

## 現在の状況

### 現在の実装（vector_store_handler.py）
- `beta.vector_stores` APIを使用
- **すでにフォールバック処理が実装済み**
- AttributeError時は自動的にローカルJSON管理に切り替わる
- 短期的には現状のままでも動作する


## 移行方法

### 方法1: 即座に移行（推奨）

```python
# app.pyの変更
# 変更前:
from utils.vector_store_handler import vector_store_handler

# 変更後:
from utils.vector_store_handler_v2 import vector_store_handler
```



## データ構造

### ベクトルストア情報（.chainlit/vector_stores/）
```json
{
  "id": "vs_xxxxxxxxxxxx",
  "name": "Personal Knowledge Base",
  "file_ids": ["file-xxx", "file-yyy"],
  "created_at": "2025-08-20T10:00:00",
  "status": "completed",
  "file_counts": {
    "total": 2,
    "in_progress": 0,
    "completed": 2,
    "failed": 0
  }
}
```

### ファイル情報（.chainlit/vector_store_files/）
```json
{
  "id": "file-xxxxxxxxxxxx",
  "filename": "document.pdf",
  "size": 1024000,
  "purpose": "assistants",
  "created_at": "2025-08-20T10:00:00"
}
```

## 注意事項

### 制限事項
- **実際のベクトルサーチ機能は提供されません**
  - ローカル管理のため、実際の意味検索は動作しない
  - ファイルの管理とメタデータの保存のみ
  
### 利点
- OpenAI APIの変更に影響されない
- ローカルで完結するため高速
- コストがかからない

### 今後の対応
- OpenAIが新しいベクトルストアAPIを提供した場合は、その実装に移行
- 独自のベクトル検索実装（ChromaDB、Pinecone等）への移行も検討可能

## テスト方法

```bash
# 1. バックアップを作成
cp utils/vector_store_handler.py utils/vector_store_handler.backup.py

# 2. v2をメインファイルに置き換え
cp utils/vector_store_handler_v2.py utils/vector_store_handler.py

# 3. アプリケーションを起動してテスト
python run.py

# 4. 問題があれば元に戻す
cp utils/vector_store_handler.backup.py utils/vector_store_handler.py
```

## まとめ

- **短期的対応**: 現在のコードのフォールバック処理で対応可能
- **中長期的対応**: vector_store_handler_v2.pyへの移行を推奨
- **将来的対応**: OpenAIの新APIまたは他のベクトル検索サービスへの移行

## 関連ファイル

- `utils/vector_store_handler.py` - 現在の実装（フォールバック付き）
- `utils/vector_store_handler_v2.py` - 新しい実装（完全ローカル管理）
- `utils/vector_store_sync.py` - 同期管理（両方に対応）
- `create_history.md` - 修正履歴
