# File Search API 実装ガイド

## 重要なリンク
- **最新のFile Search APIガイド**: https://platform.openai.com/docs/guides/tools-file-search
- **Responses API リファレンス**: https://platform.openai.com/docs/api-reference/responses
- **Vector Stores API**: https://platform.openai.com/docs/api-reference/vector-stores

## 実装の変遷と判断基準

### 2025年8月20日の議論

#### 1. 初期の問題
- **エラー**: `'AsyncBeta' object has no attribute 'vector_stores'`
- **原因**: OpenAI SDK v1.57+でAPIパスが変更された可能性を疑った

#### 2. 試みた解決策
1. **最初の試み**: beta.vector_stores と beta.assistants.vector_stores の両方に対応
2. **第二の試み**: Assistants API経由でFile Searchを実装（vector_store_handler_v2.py）
3. **最終的な解決**: Responses APIでFile Searchを正しく実装

#### 3. 正しい実装方法

##### Responses APIでのFile Search使用方法

```python
# 1. ベクトルストアを作成
vector_store = await client.beta.vector_stores.create(
    name="My Vector Store"
)

# 2. ファイルをアップロード
file = await client.files.create(
    file=open("document.pdf", "rb"),
    purpose="assistants"
)

# 3. ファイルをベクトルストアに追加
await client.beta.vector_stores.files.create(
    vector_store_id=vector_store.id,
    file_id=file.id
)

# 4. Responses APIでFile Searchを使用
response = await client.beta.responses.create(
    model="gpt-4-turbo",
    messages=[{"role": "user", "content": "質問"}],
    tools=[{"type": "file_search"}],
    tool_resources={
        "file_search": {
            "vector_store_ids": [vector_store.id]
        }
    }
)
```

##### Chat Completions APIでのFile Search（非推奨）

Chat Completions APIではFile Searchは直接サポートされていません。
代わりにAssistants APIを使用する必要があります。

## APIパスの違い

### OpenAI SDK バージョンによる違い

| SDKバージョン | Vector Stores APIパス |
|-------------|---------------------|
| < v1.12.0 | 利用不可 |
| v1.12.0 - v1.56.x | `client.beta.vector_stores` |
| v1.57.0+ | `client.beta.vector_stores` または `client.beta.assistants.vector_stores` |

### 実装の選択基準

1. **Responses API使用時**: 
   - `client.beta.vector_stores`を直接使用
   - toolsパラメータでfile_searchを指定
   - tool_resourcesでvector_store_idsを指定

2. **Chat Completions API使用時**:
   - File Searchは利用不可
   - Assistants APIに切り替える必要がある

3. **Assistants API使用時**:
   - Assistant作成時にtoolsでfile_searchを指定
   - メッセージ送信時にfile_idsを指定可能

## エラーと対処法

### よくあるエラー

1. **`'AsyncBeta' object has no attribute 'vector_stores'`**
   - 原因: SDKのバージョンが古い、またはインポートエラー
   - 対処: `pip install --upgrade openai` でSDKを更新

2. **`Invalid 'tools[1].vector_store_ids': empty array`**
   - 原因: file_searchツールにvector_store_idsが空
   - 対処: vector_store_idsが空の場合はfile_searchツールを含めない

3. **`Missing required parameter: 'tools[1].vector_store_ids'`**
   - 原因: file_searchツールの設定が不完全
   - 対処: tool_resourcesで正しくvector_store_idsを指定

## 実装のベストプラクティス

1. **ベクトルストア管理**
   - ユーザーごとに個別のベクトルストアを作成
   - セッション用の一時的なベクトルストアと永続的なベクトルストアを分離
   - 不要になったベクトルストアは定期的にクリーンアップ

2. **ファイルアップロード**
   - サポートされるファイル形式を事前にチェック
   - 大きなファイルは分割してアップロード
   - アップロード後は必ずベクトル化の完了を待つ

3. **エラーハンドリング**
   - APIエラーは適切にキャッチしてユーザーに通知
   - フォールバック機能を実装（ローカル管理など）
   - リトライ機能を実装

## 参考実装

- `utils/vector_store_handler_responses.py` - Responses API対応版
- `utils/vector_store_handler_v2.py` - Assistants API対応版（フォールバック用）
- `utils/vector_store_handler.py` - 旧実装（互換性のため保持）
