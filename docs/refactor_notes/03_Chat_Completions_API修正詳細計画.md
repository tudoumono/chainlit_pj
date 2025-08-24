# Chat Completions API使用箇所の詳細調査結果と修正方針

**作成日**: 2025年1月25日  
**バージョン**: 1.0  
**作成者**: Development Team

---

## 📊 Chat Completions API使用箇所の完全リスト

### 1. 詳細な使用箇所一覧

#### **utils/responses_handler.py**
| 行番号 | 使用内容 | 修正の必要性 |
|--------|---------|------------|
| **14行目** | コメント内: `client.chat.completions.create()メソッドを使用` | コメント修正 |
| **293行目** | `response_stream = await self.async_client.chat.completions.create(**chat_params)` | **最重要修正** |
| **831-836行目** | タイトル生成: `response = await self.async_client.chat.completions.create(...)` | **重要修正** |

#### **utils/config.py**
| 行番号 | 使用内容 | 修正の必要性 |
|--------|---------|------------|
| **291-292行目** | 接続テスト: `response = await asyncio.to_thread(client.chat.completions.create,...)` | **重要修正** |

#### **app.py（間接的使用）**
| 行番号 | 使用内容 | 修正の必要性 |
|--------|---------|------------|
| **99行目** | `from utils.responses_handler import responses_handler` | インポート変更 |
| **939行目** | `async for chunk in responses_handler.create_response(...)` | メソッド呼び出し修正 |
| **1042行目** | `tool_results = await responses_handler.handle_tool_calls(...)` | メソッド呼び出し修正 |
| **1060行目** | `async for final_chunk in responses_handler.create_response(...)` | メソッド呼び出し修正 |

---

## 🔧 修正方針の詳細

### Phase 1: 新しいResponses APIハンドラーの作成

#### 新規ファイル: `utils/true_responses_api_handler.py`

```python
"""
真のResponses API実装
OpenAI公式のResponses APIを正しく使用
"""
from openai import OpenAI, AsyncOpenAI
from typing import Optional, Dict, List, Any, AsyncGenerator
import os
import httpx

class TrueResponsesAPIHandler:
    """本物のResponses API管理クラス"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.default_model = os.getenv("DEFAULT_MODEL", "gpt-5")
        self._init_clients()
    
    def _init_clients(self):
        """クライアント初期化"""
        if not self.api_key:
            return
        
        # プロキシ設定
        http_proxy = os.getenv("HTTP_PROXY", "")
        https_proxy = os.getenv("HTTPS_PROXY", "")
        
        http_client = None
        if http_proxy or https_proxy:
            proxies = {}
            if http_proxy:
                proxies["http://"] = http_proxy
            if https_proxy:
                proxies["https://"] = https_proxy
            http_client = httpx.Client(proxies=proxies)
        
        # 同期クライアント
        self.client = OpenAI(
            api_key=self.api_key,
            http_client=http_client
        )
        
        # 非同期クライアント
        async_http_client = None
        if http_proxy or https_proxy:
            async_http_client = httpx.AsyncClient(proxies=proxies)
        
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            http_client=async_http_client
        )
    
    async def create_response(
        self,
        input_text: str,
        model: str = None,
        instructions: str = None,
        tools: Optional[List[Dict]] = None,
        previous_response_id: str = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncGenerator[Dict, None]:
        """
        正しいResponses API呼び出し
        
        参照: https://platform.openai.com/docs/api-reference/responses
        """
        if not self.async_client:
            yield {
                "error": "APIキーが設定されていません",
                "type": "configuration_error"
            }
            return
        
        model = model or self.default_model
        
        # Responses APIパラメータ構築
        response_params = {
            "model": model,
            "input": input_text,
            "stream": stream,
            **kwargs
        }
        
        # instructions（システムプロンプト相当）
        if instructions:
            response_params["instructions"] = instructions
        
        # 会話継続用のresponse_id
        if previous_response_id:
            response_params["previous_response_id"] = previous_response_id
        
        # Tools設定
        if tools:
            response_params["tools"] = tools
        
        try:
            # 正しいResponses API呼び出し
            response = await self.async_client.responses.create(**response_params)
            
            if stream:
                async for event in response:
                    yield self._process_response_event(event)
            else:
                yield self._process_response_output(response)
                
        except Exception as e:
            yield {
                "error": str(e),
                "type": "api_error"
            }
```

---

### Phase 2: 既存コードの段階的移行

#### ステップ1: Chat Completions APIの直接呼び出しを置換

##### **utils/responses_handler.py - 293行目の修正**
```python
# 修正前
response_stream = await self.async_client.chat.completions.create(**chat_params)

# 修正後（フォールバック削除、Responses APIのみ使用）
response_params = {
    "model": model,
    "input": self._extract_input_from_messages(messages),
    "instructions": self._extract_system_from_messages(messages),
    "stream": stream,
    "tools": tools if use_tools else None,
    **kwargs
}
response = await self.async_client.responses.create(**response_params)
```

##### **utils/responses_handler.py - 831行目の修正（タイトル生成）**
```python
# 修正前
response = await self.async_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=title_prompt,
    temperature=0.5,
    max_tokens=30,
    stream=False
)

# 修正後
response = await self.async_client.responses.create(
    model="gpt-4o-mini",
    input=self._extract_conversation_summary(messages),
    instructions="この会話の短く簡潔なタイトルを生成してください。20文字以内で。",
    temperature=0.5,
    max_output_tokens=30,
    stream=False
)
```

##### **utils/config.py - 291行目の修正（接続テスト）**
```python
# 修正前
response = await asyncio.to_thread(
    client.chat.completions.create,
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "test"}],
    max_tokens=5
)

# 修正後
response = await asyncio.to_thread(
    client.responses.create,
    model="gpt-4o-mini", 
    input="test",
    max_output_tokens=5
)
```

#### ステップ2: app.pyの修正

```python
# 修正前（99行目）
from utils.responses_handler import responses_handler

# 修正後
from utils.true_responses_api_handler import TrueResponsesAPIHandler
true_responses_handler = TrueResponsesAPIHandler()

# メソッド呼び出しの修正（939行目など）
# 修正前
async for chunk in responses_handler.create_response(
    messages=messages,
    model=model,
    ...
)

# 修正後
# メッセージから入力テキストを抽出
input_text = extract_latest_user_input(messages)
instructions = extract_system_prompt(messages)

async for chunk in true_responses_handler.create_response(
    input_text=input_text,
    instructions=instructions,
    model=model,
    ...
)
```

---

### Phase 3: ヘルパー関数の実装

#### 新規ファイル: `utils/message_converter.py`

```python
"""
Chat Completions形式からResponses API形式への変換ヘルパー
"""
from typing import List, Dict, Optional, Tuple

def extract_input_from_messages(messages: List[Dict[str, str]]) -> str:
    """メッセージ履歴から最新のユーザー入力を抽出"""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""

def extract_system_prompt(messages: List[Dict[str, str]]) -> Optional[str]:
    """メッセージ履歴からシステムプロンプトを抽出"""
    for msg in messages:
        if msg.get("role") == "system":
            return msg.get("content")
    return None

def convert_messages_to_context(messages: List[Dict[str, str]]) -> str:
    """会話履歴を文脈として変換"""
    context = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role != "system":
            context.append(f"{role}: {content}")
    return "\n".join(context)

def prepare_responses_api_params(
    messages: List[Dict[str, str]],
    **kwargs
) -> Dict:
    """Chat Completions形式からResponses API形式へ変換"""
    return {
        "input": extract_input_from_messages(messages),
        "instructions": extract_system_prompt(messages),
        "context": convert_messages_to_context(messages[:-1]),  # 最新以外を文脈として
        **kwargs
    }
```

---

## 📅 段階的移行計画

| 段階 | 作業内容 | 所要時間 | リスク | 優先度 |
|------|---------|----------|--------|---------|
| **Phase 1** | 新しいResponses APIハンドラー作成 | 1-2日 | 低 | 🔴 最高 |
| **Phase 2** | utils/config.py の接続テスト修正 | 0.5日 | 低 | 🟠 高 |
| **Phase 3** | utils/responses_handler.py のタイトル生成修正 | 0.5日 | 低 | 🟠 高 |
| **Phase 4** | utils/responses_handler.py のメイン処理修正 | 2-3日 | **高** | 🔴 最高 |
| **Phase 5** | app.py の全面的な修正 | 2-3日 | **高** | 🔴 最高 |
| **Phase 6** | 統合テストとデバッグ | 2日 | 中 | 🟡 中 |
| **Phase 7** | 古いコードのクリーンアップ | 1日 | 低 | 🟢 低 |

**総所要時間**: 約9-12日（フルタイム開発の場合）

---

## ⚠️ 移行時の注意点

### 重要な変更点

#### 1. パラメータ名の変更
| Chat Completions API | Responses API | 備考 |
|---------------------|---------------|------|
| `messages` | `input` + `instructions` + `context` | 分割が必要 |
| `max_tokens` | `max_output_tokens` | 名称変更 |
| なし | `previous_response_id` | 新規（会話継続用） |

#### 2. ツール設定の変更
```python
# Chat Completions API
tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web",
            "parameters": {...}
        }
    }
]

# Responses API
tools = [
    {"type": "web_search", "enabled": True},
    {"type": "file_search", "file_search": {"vector_store_ids": ["vs_123"]}}
]
```

#### 3. レスポンス形式の変更
```python
# Chat Completions API
content = response.choices[0].message.content

# Responses API
content = response.output_text  # または response.output
```

---

## 🧪 テスト計画

### 単体テスト

```python
# tests/test_responses_api.py
import pytest
from utils.true_responses_api_handler import TrueResponsesAPIHandler

@pytest.mark.asyncio
async def test_basic_response():
    """基本的な応答テスト"""
    handler = TrueResponsesAPIHandler()
    response = await handler.create_response(
        input_text="Hello, world!",
        model="gpt-5",
        stream=False
    )
    assert response is not None
    assert "error" not in response

@pytest.mark.asyncio
async def test_with_tools():
    """ツール使用時のテスト"""
    handler = TrueResponsesAPIHandler()
    tools = [
        {"type": "web_search", "enabled": True},
        {"type": "file_search", "file_search": {"vector_store_ids": ["vs_123"]}}
    ]
    response = await handler.create_response(
        input_text="Search for information",
        tools=tools,
        stream=False
    )
    assert response is not None

@pytest.mark.asyncio
async def test_streaming():
    """ストリーミング応答のテスト"""
    handler = TrueResponsesAPIHandler()
    chunks = []
    async for chunk in handler.create_response(
        input_text="Tell me a story",
        stream=True
    ):
        chunks.append(chunk)
    assert len(chunks) > 0

@pytest.mark.asyncio
async def test_conversation_continuation():
    """会話継続のテスト"""
    handler = TrueResponsesAPIHandler()
    # 最初の応答
    first_response = await handler.create_response(
        input_text="Hello",
        stream=False
    )
    response_id = first_response.get("id")
    
    # 継続応答
    second_response = await handler.create_response(
        input_text="What did I just say?",
        previous_response_id=response_id,
        stream=False
    )
    assert second_response is not None
```

### 統合テスト

```python
# tests/test_integration.py
import pytest
from app import handle_message

@pytest.mark.asyncio
async def test_end_to_end_conversation():
    """エンドツーエンドの会話テスト"""
    # ユーザーメッセージ送信
    response = await handle_message("Hello, AI!")
    assert response is not None
    
    # ツール使用
    response = await handle_message("Search for latest news")
    assert "web_search" in str(response)
    
    # ベクトルストア参照
    response = await handle_message("What's in my documents?")
    assert "file_search" in str(response)
```

---

## 🔄 互換性の維持

### 互換性レイヤーの実装

```python
# utils/responses_compatibility.py
class ResponsesCompatibilityLayer:
    """既存コードとの互換性を保つためのレイヤー"""
    
    def __init__(self, handler: TrueResponsesAPIHandler):
        self.handler = handler
    
    def convert_chat_to_responses(self, chat_params: Dict) -> Dict:
        """Chat Completions形式をResponses API形式に変換"""
        messages = chat_params.pop("messages", [])
        return {
            "input": self.extract_input(messages),
            "instructions": self.extract_instructions(messages),
            "model": chat_params.get("model"),
            "max_output_tokens": chat_params.pop("max_tokens", None),
            **chat_params
        }
    
    async def create_response_compat(self, **chat_params):
        """互換性のあるcreate_response メソッド"""
        responses_params = self.convert_chat_to_responses(chat_params)
        return await self.handler.create_response(**responses_params)
```

---

## 📁 最終的なファイル構成

```
utils/
├── true_responses_api_handler.py  # ✨ 新しいResponses API実装
├── message_converter.py           # ✨ 変換ヘルパー
├── responses_compatibility.py     # ✨ 互換性レイヤー
├── archive/                       # 📦 アーカイブ
│   └── old_chat_completions/      
│       ├── responses_handler.py   # 旧実装
│       └── config.py              # 旧実装の該当部分
└── tests/                         # 🧪 テスト
    ├── test_responses_api.py
    └── test_integration.py
```

---

## ✅ 修正完了時のチェックリスト

### API移行
- [ ] すべての`chat.completions`参照が削除された
- [ ] `client.responses.create()`が正しく実装された
- [ ] パラメータ変換が正しく動作する
- [ ] レスポンス形式の変換が正しく動作する

### 機能確認
- [ ] 基本的なチャット機能が動作する
- [ ] Web検索機能が動作する
- [ ] ファイル検索機能が動作する
- [ ] ストリーミング応答が正常に動作する
- [ ] 会話継続（previous_response_id）が動作する

### コード品質
- [ ] エラーハンドリングが適切に実装された
- [ ] ログが適切に記録される
- [ ] テストがすべてパスする
- [ ] ドキュメントが更新された

### クリーンアップ
- [ ] 古いコードがアーカイブされた
- [ ] 不要なインポートが削除された
- [ ] コメントが更新された
- [ ] リファクタリング完了の記録が残された

---

## 🎯 期待される成果

### 技術的成果
1. **最新API活用**: Responses APIの全機能を活用可能に
2. **パフォーマンス向上**: より効率的なAPI呼び出し
3. **機能拡張**: Web検索、ステートフル会話の実現

### ビジネス価値
1. **競争力向上**: 最新技術の活用
2. **保守性向上**: クリーンなコードベース
3. **拡張性向上**: 将来の機能追加が容易に

---

## 📝 関連ドキュメント

- `開発順序計画書.md` - 開発方針と優先順位
- `docs/implementation_status/02_実装の誤りと修正方針.md` - 全体的な修正方針
- `docs/api_notes/Responses_API_誤解の経緯と対策.md` - API混乱の詳細
- `Chainlit_多機能AIワークスペース_アプリケーション仕様書.md` - アプリケーション仕様

---

**最終更新日**: 2025年1月25日  
**次回レビュー予定**: Phase 1完了時