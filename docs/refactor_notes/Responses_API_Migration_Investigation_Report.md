# Chat Completions API → Responses API 移行調査報告書

**作成日**: 2025年1月25日  
**作成者**: AI Development Assistant  
**バージョン**: 1.0

---

## 📊 現状調査結果サマリー

### 1. 主要な発見事項

現在のコードベースは **「Responses API」という名前を使用しているが、実際はChat Completions APIを使用している** という混乱した状態になっています。

#### 🔍 重要な事実
1. **ファイル名の誤解**: `responses_handler.py` という名前だが、実際はChat Completions APIを使用
2. **コメントでの明示**: ファイル冒頭で「実際はChat Completions APIのツール機能を管理」と明記
3. **実装の矛盾**: `client.responses.create()` を試すが、AttributeErrorでChat Completions APIにフォールバック

---

## 🔧 修正対象ファイル一覧

### 優先度: 最高（コア機能）

#### 1. `utils/responses_handler.py`
| 行番号 | 現在の実装 | 修正内容 |
|--------|-----------|----------|
| 14行目 | `client.chat.completions.create()メソッドを使用` | コメントを`client.responses.create()`に修正 |
| 231-241行目 | Responses API呼び出しを試みるが失敗 | 正しいResponses API実装に修正 |
| 293行目 | `await self.async_client.chat.completions.create(**chat_params)` | Responses API形式に変更 |
| 831-836行目 | タイトル生成でChat Completions API使用 | Responses API使用に統一 |

#### 2. `app.py`
| 行番号 | 現在の実装 | 修正内容 |
|--------|-----------|----------|
| 99行目 | `from utils.responses_handler import responses_handler` | 新しいハンドラーをインポート |
| 939行目 | `responses_handler.create_response()` | メソッド名は同じだが内部実装変更 |
| 1042行目 | `responses_handler.handle_tool_calls()` | ツール処理ロジックの修正 |

#### 3. `utils/config.py`
| 行番号 | 現在の実装 | 修正内容 |
|--------|-----------|----------|
| 291-292行目 | 接続テストで`client.chat.completions.create` | Responses API形式のテストに変更 |

---

## 🎯 修正方針

### Phase 1: 真のResponses API実装の作成（新規ファイル）

#### 新ファイル: `utils/true_responses_api_handler.py`

```python
"""
真のResponses API実装
OpenAI公式のResponses APIを正しく使用
"""
from openai import AsyncOpenAI
from typing import Optional, Dict, List, Any, AsyncGenerator
import os

class TrueResponsesAPIHandler:
    """正しいResponses API実装"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def create_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        stream: bool = True,
        **kwargs
    ) -> AsyncGenerator[Dict, None]:
        """
        Responses APIを使用した応答生成
        
        重要: これが正しいResponses API実装です
        """
        # メッセージから入力を抽出
        user_input = ""
        system_instructions = ""
        
        for msg in messages:
            if msg["role"] == "user":
                user_input = msg["content"]
            elif msg["role"] == "system":
                system_instructions = msg["content"]
        
        # Responses API呼び出し
        response = await self.client.responses.create(
            model=model,
            input=user_input,
            instructions=system_instructions,
            stream=stream,
            **kwargs
        )
        
        if stream:
            async for chunk in response:
                yield self._process_stream_chunk(chunk)
        else:
            yield self._process_response(response)
```

### Phase 2: 段階的移行計画

#### ステップ1: 並行実装（1-2日）
- 新しい`true_responses_api_handler.py`を作成
- 既存の`responses_handler.py`は一時的に残す
- フィーチャーフラグで切り替え可能にする

#### ステップ2: 機能テスト（1日）
- 基本的なチャット機能
- ストリーミング応答
- ツール使用（Web検索、ファイル検索）
- エラーハンドリング

#### ステップ3: 完全移行（1日）
- `app.py`のインポートを新しいハンドラーに変更
- 古い実装を`docs/archive/`に移動
- ドキュメントの更新

---

## 📝 実装の詳細仕様

### 1. Responses APIの正しいパラメータ構造

```python
# 正しいResponses API呼び出し
response = await client.responses.create(
    model="gpt-4o-mini",           # モデル指定
    input="ユーザーの質問",         # ユーザー入力（必須）
    instructions="システム指示",    # システムプロンプト（オプション）
    previous_response_id="xxx",     # 会話継続用（オプション）
    tools=[                         # ツール設定（オプション）
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
    ],
    stream=True                     # ストリーミング設定
)
```

### 2. Chat Completions APIとの違い

| 機能 | Chat Completions API | Responses API |
|------|---------------------|---------------|
| パラメータ名 | `messages` | `input` + `instructions` |
| 会話継続 | メッセージ履歴を送信 | `previous_response_id` |
| ツール指定 | `tools` + `tool_choice` | `tools`のみ |
| 応答形式 | `choices[0].message.content` | `output_text` |
| ストリーミング | デルタ形式 | イベント形式 |

### 3. エラーハンドリング戦略

```python
try:
    # Responses API呼び出し
    response = await client.responses.create(...)
except openai.APIError as e:
    # API固有のエラー
    logger.error(f"Responses API Error: {e}")
    # フォールバック処理
except Exception as e:
    # その他のエラー
    logger.error(f"Unexpected error: {e}")
```

---

## ⚠️ 重要な注意事項

### 1. 既存コードの問題点

現在のコードは以下の混乱した状態にあります：

1. **名前と実装の不一致**: 
   - ファイル名: `responses_handler.py`
   - 実際の実装: Chat Completions API

2. **フォールバック処理の誤解**:
   ```python
   # 現在のコード（問題あり）
   try:
       response = await self.async_client.responses.create(...)  # 存在しないメソッド
   except AttributeError:
       # Chat Completions APIにフォールバック
   ```
   これは「Responses APIが存在しない」という誤解に基づいている

3. **コメントの矛盾**:
   - 「OpenAI SDKはResponses APIを正式にサポート」と記載
   - しかし実際は`AttributeError`でフォールバック

### 2. 修正時の考慮事項

1. **後方互換性**: 既存の機能を壊さないよう段階的に移行
2. **テスト充実**: 各段階で十分なテストを実施
3. **ログ記録**: 移行過程を詳細にログに記録
4. **ロールバック計画**: 問題発生時に即座に戻せる体制

---

## 📅 実装スケジュール案

### 第1週
| 日程 | タスク | 見積時間 |
|------|--------|---------|
| Day 1 | 新しいハンドラー実装 | 4時間 |
| Day 2 | 基本機能テスト | 3時間 |
| Day 3 | ツール機能実装 | 4時間 |
| Day 4 | 統合テスト | 3時間 |
| Day 5 | 移行作業 | 4時間 |

### 第2週
| 日程 | タスク | 見積時間 |
|------|--------|---------|
| Day 6 | エラーハンドリング改善 | 3時間 |
| Day 7 | パフォーマンステスト | 2時間 |
| Day 8 | ドキュメント更新 | 2時間 |
| Day 9 | コードレビュー | 2時間 |
| Day 10 | 本番デプロイ準備 | 3時間 |

---

## ✅ 成功基準

### 必須要件
- [ ] すべての`chat.completions.create()`呼び出しが削除
- [ ] 正しい`client.responses.create()`実装が動作
- [ ] ストリーミング応答が正常動作
- [ ] Web検索ツールが機能
- [ ] ファイル検索ツールが機能

### 品質要件
- [ ] エラー率が1%未満
- [ ] レスポンス時間が既存実装と同等以上
- [ ] メモリ使用量が適切
- [ ] ログが適切に記録される

---

## 🚀 次のアクション

1. **即座に実施**:
   - このドキュメントのレビューと承認
   - 開発環境の準備

2. **Day 1で実施**:
   - `utils/true_responses_api_handler.py`の作成開始
   - 基本的なResponses API呼び出しのテスト

3. **継続的に実施**:
   - 進捗の日次報告
   - 問題発生時の即座のエスカレーション

---

## 📚 参考資料

1. **OpenAI公式ドキュメント**:
   - [Responses API Reference](https://platform.openai.com/docs/api-reference/responses)
   - [Responses API Quickstart](https://platform.openai.com/docs/quickstart?api-mode=responses)
   - [新しいエージェント構築ツール（日本語）](https://openai.com/ja-JP/index/new-tools-for-building-agents/)

2. **内部ドキュメント**:
   - `開発順序計画書.md` - 開発方針
   - `Chainlit_多機能AIワークスペース_アプリケーション仕様書.md` - 全体仕様
   - `docs/implementation_status/02_実装の誤りと修正方針.md` - 問題の詳細

---

**文書の最終更新**: 2025年1月25日
**次回レビュー予定**: Day 3実装完了後