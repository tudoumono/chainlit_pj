# **多機能AIワークスペース アプリケーション仕様書（更新版）**

バージョン: 1.3  
更新日: 2025年8月24日  
初版作成日: 2025年8月6日  
概要: OpenAIの最新Responses APIを活用した、プロフェッショナル向けのChainlitベースAIアプリケーションの技術仕様

---

## **🎯 最重要：OpenAI Responses APIの実装について**

### ✨ **Responses API - 新世代のAIエージェント構築API**

OpenAIは2024年12月に革新的な**Responses API**を正式発表しました。これは**Chat Completions APIのシンプルさとAssistant APIのツール使用機能を統合**した、全く新しいAPIです。

### 📌 **公式リファレンス**
- [OpenAI Quickstart - Responses API](https://platform.openai.com/docs/quickstart?api-mode=responses)
- [新しいエージェント構築ツールの発表（日本語）](https://openai.com/ja-JP/index/new-tools-for-building-agents/)
- [Web Search and States with Responses API Cookbook](https://cookbook.openai.com/examples/responses_api/responses_example)

### 🚀 **Responses APIの特徴**

| 機能 | 説明 | 実装状態 |
|------|------|----------|
| **ステートフルな会話** | 会話状態を自動管理 | ✅ **利用可能** |
| **Web Search** | ウェブ検索機能内蔵 | ✅ **利用可能** |
| **File Search** | ファイル検索機能 | ✅ **利用可能** |
| **Code Interpreter** | コード実行機能 | ✅ **利用可能** |
| **Custom Tools** | カスタムツール定義 | ✅ **利用可能** |

### 📝 **実装方法（公式ドキュメント準拠）**

```python
# ✅ 正しい実装：Responses APIの使用
from openai import OpenAI
client = OpenAI()

# Responses APIを使用した実装例
response = client.responses.create(
    model="gpt-5",  # または "gpt-4o-mini", "gpt-4o" など
    input="Write a one-sentence bedtime story about a unicorn.",
    # ツールの設定も可能
    tools=[
        {
            "type": "web_search",
            "enabled": True
        },
        {
            "type": "file_search",
            "file_search": {
                "vector_store_ids": ["vs_xxx"]
            }
        }
    ]
)

print(response.output_text)
```

### ⚠️ **重要な変更点**

以前の誤った記載：
- ❌ 「client.responses.create()は存在しない」
- ❌ 「Responses APIは独立したAPIではない」
- ❌ 「Chat Completions APIのツール機能として実装」

**正しい理解：**
- ✅ **Responses APIは独立した新しいAPI**
- ✅ **client.responses.create()メソッドが正式に存在**
- ✅ **本プロジェクトの中核となる最重要API**

### 🚫 **実装上の厳格なルール**

#### ❌ **使用禁止**
```python
# 絶対に使用してはいけない実装
response = client.chat.completions.create(...)  # ❌ 使用禁止
```

#### ✅ **必須実装**
```python
# 必ず使用すべき実装
response = client.responses.create(...)  # ✅ Responses API必須
```

**理由：**
- Responses APIは新世代のエージェント構築に特化
- Web Search機能がネイティブで統合
- ステートフル会話管理が標準装備
- Chat Completions APIは旧世代のAPIであり、本プロジェクトでは一切使用しない

### 🔗 **必須参照ドキュメント**
- [Responses API Quickstart](https://platform.openai.com/docs/quickstart?api-mode=responses)
- [OpenAI公式発表 - 新しいエージェント構築ツール](https://openai.com/ja-JP/index/new-tools-for-building-agents/)
- [Responses API Cookbook Example](https://cookbook.openai.com/examples/responses_api/responses_example)
- [Web Search Integration Guide](https://platform.openai.com/docs/guides/web-search)
- [File Search with Responses API](https://platform.openai.com/docs/guides/file-search)

---

## **1. システム概要**

### 1.1 現在の実装状態

本アプリケーションは、Chainlitフレームワークを基盤とした多機能AIワークスペースです。当初の設計から進化し、現在は以下の構成で動作しています：

- **フレームワーク**: Chainlit 2.6.8以上
- **AI API**: OpenAI Responses API（**Chat Completions APIは使用禁止**）
- **データベース**: SQLite3（永続化）
- **認証**: Chainlit内蔵認証（credentials）

### 1.2 実装状況（Responses API移行前）

| Phase | 機能 | 状態 | 説明 |
|-------|------|------|------|
| 1 | 基本環境構築 | ✅ 完了 | Chainlit起動、ウェルカム画面 |
| **新** | **Responses API統合** | **🔴 最優先** | **Chat Completions API使用禁止、Responses API必須** |
| 2 | 設定管理 | ✅ 完了 | APIキー管理、接続テスト |
| 3 | データベース基盤 | ✅ 完了 | SQLite3による履歴永続化 |
| 4 | 基本チャット | ✅ 完了 | ストリーミング応答、エラーハンドリング |
| 5 | セッション永続化 | ✅ 完了 | 会話履歴の保存と復元 |
| 6 | 高度な設定 | ✅ 完了 | ペルソナ機能、モデル選択 |
| 7 | ベクトルストア基礎 | ✅ 完了 | 3階層ナレッジベース管理 |

### 1.3 未実装機能（Phase 8-12）

| Phase | 機能 | 状態 | 説明 |
|-------|------|------|------|
| 8 | 3階層ベクトルストア完全実装 | ⚠️ 部分完了 | 自動削除機能が未完成 |
| 9 | マルチモーダル入力 | ❌ 未実装 | 画像・PDF直接入力 |
| 10 | Agents SDK | ❌ 未実装 | 高レベルエージェント機能 |
| 11 | エクスポート機能 | ❌ 未実装 | JSON/HTML/PDF出力 |
| 12 | UI/UX改善 | ❌ 未実装 | レスポンシブデザイン |

---

## **2. アーキテクチャ**
### 2.2 推奨アーキテクチャ（リファクタリング後）

```
├── app.py                          # エントリーポイントのみ（100行以内）
├── modules/
│   ├── auth/                       # 認証モジュール
│   ├── chat/                       # チャット機能
│   ├── settings/                   # 設定管理
│   ├── database/                   # データベース
│   ├── vector_store/               # ベクトルストア（統一）
│   └── ui/                         # UI コンポーネント
└── config/                         # 設定ファイル
```

---

## **3. 主要機能仕様**

### 3.1 チャット機能（現在の実装）

#### API呼び出し方法

```python
# utils/responses_handler.py での実装（Responses API対応版）
async def create_response(self, input_text, model, **kwargs):
    """
    OpenAI Responses APIを使用した実装
    公式ドキュメント: https://platform.openai.com/docs/quickstart?api-mode=responses
    """
    # ツール設定
    tools = []
    
    # Web検索機能（Responses API内蔵）
    if self.tools_config.is_tool_enabled("web_search"):
        tools.append({
            "type": "web_search",
            "enabled": True
        })
    
    # ファイル検索機能
    if self.tools_config.is_tool_enabled("file_search"):
        tools.append({
            "type": "file_search",
            "file_search": {
                "vector_store_ids": self.get_active_vector_stores()
            }
        })
    
    # Responses APIを呼び出し（新しいメソッド）
    response = await self.async_client.responses.create(
        model=model,
        input=input_text,
        tools=tools if tools else None,
        stream=True  # ストリーミング対応
    )
    
    # ストリーミング処理
    async for chunk in response:
        yield self._process_stream_chunk(chunk)
```

### 3.2 ベクトルストア管理（3階層構造）

#### 現在の実装

| 階層 | 名称 | 管理方法 | 永続性 | 用途 |
|------|------|----------|--------|------|
| 1層目 | 会社全体 | .env設定 | 永続 | 組織共有ナレッジ |
| 2層目 | 個人ユーザー | DB保存 | 永続 | 個人ナレッジ |
| 3層目 | セッション | メモリ | 一時的 | チャット内ファイル |

#### ベクトルストア作成

```python
# OpenAI Beta APIを使用（正式版）
vector_store = await client.beta.vector_stores.create(
    name="Knowledge Base",
    metadata={"user_id": user_id, "category": "personal"}
)

# ファイルアップロード
file = await client.files.create(
    file=open("document.pdf", "rb"),
    purpose="assistants"
)

# ベクトルストアにファイルを追加
await client.beta.vector_stores.file_batches.create(
    vector_store_id=vector_store.id,
    file_ids=[file.id]
)
```

### 3.3 設定管理

#### ChatSettingsウィジェット（現在15項目）

```python
# 推奨：基本設定と詳細設定に分離
basic_settings = [
    Select("Model", values=["gpt-4o-mini", "gpt-4o"]),
    Switch("File_Search", label="ファイル検索"),
    Slider("Temperature", min=0, max=2, step=0.1)
]

advanced_settings = [
    # ベクトルストア設定
    # プロキシ設定
    # システムプロンプト
]
```

---

## **4. 技術的課題と改善計画**

### 4.1 即座に対応すべき課題

| 課題 | 現状 | 対策 | 優先度 |
|------|------|------|--------|
| **Responses API未実装** | **Chat Completions使用中（禁止）** | **即座に完全移行必須** | **🔴 最高** |
| app.py肥大化 | 2000行超 | モジュール分割 | 🔴 高 |
| VS関連ファイル重複 | 11個のファイル | 統一版に一本化 | 🔴 高 |
| エラーハンドリング | 不統一 | 共通エラーハンドラー | 🔴 高 |

### 4.2 短期的改善項目

| 項目 | 現状 | 改善案 | 優先度 |
|------|------|--------|--------|
| UI複雑化 | 設定項目15個 | 基本/詳細に分離 | 🟡 中 |
| コマンド体系 | 重複・混乱 | 統一コマンド設計 | 🟡 中 |
| ログ過多 | WebSocket頻繁 | ログレベル制御 | 🟡 中 |

### 4.3 中長期的実装項目

| 項目 | 内容 | 期待効果 | 優先度 |
|------|------|----------|--------|
| Phase 9 | マルチモーダル | 画像・PDF直接処理 | 🟢 低 |
| Phase 10 | Agents SDK | 高度なエージェント | 🟢 低 |
| Phase 11-12 | エクスポート・UI | UX向上 | 🟢 低 |

---

## **5. 開発ガイドライン**

### 5.1 コーディング規約

#### 🚫 **API使用に関する絶対的ルール**

```python
# ❌❌❌ 絶対禁止：Chat Completions APIの使用
def create_chat_response():
    # 以下のコードは絶対に書いてはいけない
    response = client.chat.completions.create(...)  # ❌ 使用禁止
    
# ✅✅✅ 必須：Responses APIの使用
def create_response():
    # 必ずResponses APIを使用する
    response = client.responses.create(...)  # ✅ 必須
```

**違反時の対応：**
- コードレビューで即座に差し戻し
- Chat Completions APIを使用したコードは一切マージしない
- 既存コードも発見次第、Responses APIに書き換える

```python
# ✅ 良い例：明確な関数名と型ヒント
async def create_vector_store(
    self,
    name: str,
    user_id: str,
    category: str = "general"
) -> Optional[str]:
    """
    ベクトルストアを作成
    
    Args:
        name: ベクトルストア名
        user_id: ユーザーID
        category: カテゴリー
    
    Returns:
        作成されたベクトルストアID、失敗時はNone
    """
    pass

# ❌ 悪い例：不明確な名前と型情報なし
async def create_vs(n, u, c=None):
    pass
```

### 5.2 エラーハンドリング標準

```python
# 統一エラーハンドラー
class AppError(Exception):
    """アプリケーション基底例外"""
    pass

class VectorStoreError(AppError):
    """ベクトルストア関連エラー"""
    pass

# 使用例
try:
    vector_store = await create_vector_store(...)
except VectorStoreError as e:
    logger.error(f"VS作成エラー: {e}")
    await cl.Message(
        content=f"❌ ベクトルストア作成に失敗しました: {e}",
        author="System"
    ).send()
```

### 5.3 ログレベル管理

```python
# .env設定
LOG_LEVEL=INFO  # 本番環境
LOG_LEVEL=DEBUG  # 開発環境

# ログ使用
logger.debug("詳細デバッグ情報")  # 開発時のみ
logger.info("通常情報")            # 本番でも記録
logger.warning("警告")              # 問題の可能性
logger.error("エラー")              # エラー発生
```

---

## **6. デプロイメント**

### 6.1 環境要件

```ini
# requirements.in
chainlit>=2.6.8
openai>=1.57.4  # Beta APIサポート必須
python-dotenv>=1.0.1
aiosqlite>=0.20.0
sqlalchemy>=2.0.43
```

### 6.2 環境変数

```bash
# .env.example
# OpenAI設定
OPENAI_API_KEY=sk-xxx
DEFAULT_MODEL=gpt-4o-mini

# Chainlit設定
CHAINLIT_AUTH_TYPE=credentials
CHAINLIT_USERNAME=admin
CHAINLIT_PASSWORD=secure_password

# ベクトルストア
COMPANY_VECTOR_STORE_ID=vs_company_xxx

# ログ設定
LOG_LEVEL=INFO
```

---

## **7. 保守とドキュメント**

### 7.1 ドキュメント構成

```
docs/
├── API_CLARIFICATION.md           # API名称の明確化（新規作成）
├── ARCHITECTURE.md                 # アーキテクチャ設計
├── DEVELOPMENT_GUIDE.md           # 開発ガイド
├── DEPLOYMENT.md                  # デプロイメント手順
└── TROUBLESHOOTING.md            # トラブルシューティング
```

### 7.2 バージョン管理

- **Gitフロー**: main/develop/feature ブランチ戦略
- **セマンティックバージョニング**: v1.2.0 形式
- **変更履歴**: CHANGELOG.md形式で管理（create_history.md置き換え）

---

## **8. 今後のロードマップ**

### Phase 0: Responses API移行（2025年8月 - 最優先）
- [ ] **Responses APIへの完全移行**
- [ ] **Web Search機能の実装**
- [ ] **ステートフル会話管理の実装**

### Phase 1: 技術的負債の解消（2025年9月）
- [ ] app.pyのモジュール分割
- [ ] ベクトルストア関連コードの統一
- [ ] エラーハンドリングの標準化

### Phase 2: 機能改善（2025年9月）
- [ ] UI/UXの簡素化
- [ ] コマンド体系の再設計
- [ ] パフォーマンス最適化

### Phase 3: 新機能実装（2025年10月以降）
- [ ] マルチモーダル対応
- [ ] Agents SDK統合
- [ ] 高度なエクスポート機能

---

## **付録A: API名称の混乱防止ガイド**

### ❌ 過去の誤った理解
- 「Responses APIは存在しない」
- 「Chat Completions APIのツール機能で代替」
- 「client.responses.create()は使えない」

### ✅ 正しい理解と実装
- **「Responses APIは2024年12月に正式発表された新しいAPI」**
- **「client.responses.create()メソッドが正式に利用可能」**
- **「Web Search機能がネイティブで利用可能」**
- **「本プロジェクトの中核技術として採用」**

### 📚 公式リファレンス
- [OpenAI Tools Documentation](https://platform.openai.com/docs/guides/tools)
- [File Search Guide](https://platform.openai.com/docs/guides/tools-file-search)
- [Assistants API](https://platform.openai.com/docs/assistants/overview)

---

## **付録B: 緊急対応手順**

### エラー発生時のチェックリスト
1. ログレベルをDEBUGに変更して詳細確認
2. `.chainlit/chainlit.db`の整合性確認
3. ベクトルストアIDの有効性確認
4. APIキーとクォータの確認
5. WebSocket接続状態の確認

### リカバリー手順
```bash
# データベースバックアップ
cp .chainlit/chainlit.db .chainlit/chainlit.db.backup

# ベクトルストアクリーンアップ
python utils/vector_store_sync.py --cleanup

# アプリケーション再起動
chainlit run app.py -w
```

---

**本仕様書は生きた文書として、実装の進捗に応じて継続的に更新されます。**

最終更新: 2025年8月24日
次回レビュー予定: 2025年9月1日
