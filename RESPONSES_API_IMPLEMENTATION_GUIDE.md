# OpenAI Responses API + Tools機能 実装ガイド

## 概要
このドキュメントは、OpenAI Responses APIとTools機能（Web検索、ファイル検索）の実装について説明します。

## 実装内容

### 1. Responses API
OpenAIの最新のResponses APIを実装しました。これにより、以下が可能になります：
- 構造化された応答形式
- Tools機能のネイティブサポート
- より効率的なストリーミング処理

### 2. Tools機能

#### 2.1 Web検索
- **機能**: AIが必要に応じてWeb検索を実行
- **有効化**: `/tools enable web_search`
- **無効化**: `/tools disable web_search`
- **設定**:
  - 最大検索結果数: デフォルト5件
  - 検索クエリは自動生成

#### 2.2 ファイル検索
- **機能**: アップロードされたファイルから情報を検索
- **有効化**: `/tools enable file_search`
- **無効化**: `/tools disable file_search`
- **設定**:
  - 最大チャンク数: デフォルト20
  - Vector Storeを使用（要設定）

#### 2.3 コードインタープリター
- **機能**: Pythonコードの実行と分析
- **有効化**: `/tools enable code_interpreter`
- **無効化**: `/tools disable code_interpreter`
- **注意**: デフォルトでは無効

### 3. 設定管理

設定ファイルは `.chainlit/tools_config.json` に保存されます：

```json
{
  "enabled": true,
  "tools": {
    "web_search": {
      "enabled": true,
      "name": "web_search",
      "description": "Search the web for current information",
      "auto_invoke": true
    },
    "file_search": {
      "enabled": true,
      "name": "file_search",
      "description": "Search through uploaded files and documents",
      "auto_invoke": true,
      "file_ids": []
    },
    "code_interpreter": {
      "enabled": false,
      "name": "code_interpreter",
      "description": "Execute Python code for calculations and data analysis",
      "auto_invoke": false
    }
  },
  "settings": {
    "tool_choice": "auto",
    "parallel_tool_calls": true,
    "max_tools_per_call": 5,
    "web_search_max_results": 5,
    "file_search_max_chunks": 20,
    "show_tool_calls": true,
    "show_tool_results": true
  }
}
```

## 使用方法

### 基本的な使い方

1. **アプリケーションの切り替え**
   ```batch
   switch_to_responses_api.bat
   ```

2. **アプリケーションの起動**
   ```batch
   start.bat
   ```

3. **Tools機能の有効化**
   ```
   /tools enable all
   ```
   または個別に：
   ```
   /tools enable web_search
   /tools enable file_search
   ```

### コマンド一覧

#### Tools関連コマンド
- `/tools` - 現在のTools設定を表示
- `/tools enable [ツール名|all]` - ツールを有効化
- `/tools disable [ツール名|all]` - ツールを無効化

#### 利用可能なツール名
- `web_search` - Web検索
- `file_search` - ファイル検索
- `code_interpreter` - コードインタープリター
- `custom_functions` - カスタム関数

### 使用例

#### 例1: Web検索を使った質問
```
User: 最新のAI技術のトレンドについて教えてください。

System: 🔍 Web検索中: latest AI technology trends 2025

System: 📊 ツール結果:
検索結果から最新の情報を取得しました...

Assistant: 最新のAI技術トレンドについて、Web検索の結果を基に以下の情報をお伝えします：
[AIが検索結果を基に回答]
```

#### 例2: ファイル検索を使った質問
```
User: アップロードした資料の中から売上データを探してください。

System: 📁 ファイル検索中

System: 📊 ツール結果:
ファイル検索結果...

Assistant: 資料を検索した結果、以下の売上データが見つかりました：
[検索結果を基にした回答]
```

## 実装詳細

### ファイル構成

```
F:\10_code\AI_Workspace_App_Chainlit\
├── app_responses_api.py       # Responses API版のメインアプリ
├── app.py                      # 現在のアプリ（切り替え可能）
├── app_old_completions.py      # 旧Chat Completions API版（バックアップ）
├── utils/
│   ├── responses_handler.py    # Responses APIハンドラー
│   ├── tools_config.py         # Tools機能の設定管理
│   ├── response_handler.py     # 旧APIハンドラー（バックアップ）
│   ├── config.py              # 一般設定管理
│   └── logger.py              # ログシステム
├── .chainlit/
│   ├── tools_config.json      # Tools設定ファイル
│   └── chainlit.db            # SQLite履歴データベース
└── switch_to_responses_api.bat # API切り替えスクリプト
```

### クラス構成

#### ResponsesAPIHandler
- **場所**: `utils/responses_handler.py`
- **責務**: Responses APIの呼び出しとレスポンス処理
- **主要メソッド**:
  - `create_response()` - API呼び出し（Tools対応）
  - `handle_tool_calls()` - ツール呼び出しの処理
  - `_handle_web_search()` - Web検索の実行
  - `_handle_file_search()` - ファイル検索の実行

#### ToolsConfig
- **場所**: `utils/tools_config.py`
- **責務**: Tools機能の設定管理
- **主要メソッド**:
  - `is_enabled()` - Tools機能の有効状態確認
  - `is_tool_enabled()` - 個別ツールの有効状態確認
  - `update_tool_status()` - ツールの有効/無効切り替え
  - `build_tools_parameter()` - API用パラメータ構築

## カスタマイズ方法

### Web検索の実装

現在はデモ実装となっています。実際のWeb検索APIを統合するには：

1. **Bing Search APIの場合**:
```python
# utils/responses_handler.py の _handle_web_search メソッドを修正

import requests

async def _handle_web_search(self, query: str) -> str:
    # Bing Search API
    subscription_key = os.getenv("BING_SEARCH_API_KEY")
    endpoint = "https://api.bing.microsoft.com/v7.0/search"
    
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}
    params = {"q": query, "count": self.tools_config.get_setting("web_search_max_results", 5)}
    
    response = requests.get(endpoint, headers=headers, params=params)
    results = response.json()
    
    # 結果をフォーマット
    formatted_results = []
    for item in results.get("webPages", {}).get("value", []):
        formatted_results.append(f"- {item['name']}: {item['snippet']}")
    
    return "\n".join(formatted_results)
```

2. **Google Custom Search APIの場合**:
```python
# 同様にGoogle APIを統合
from googleapiclient.discovery import build

async def _handle_web_search(self, query: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    
    service = build("customsearch", "v1", developerKey=api_key)
    result = service.cse().list(q=query, cx=cse_id, num=5).execute()
    
    # 結果をフォーマット
    # ...
```

### ファイル検索の実装

Vector Store APIを使用する場合：

```python
# utils/responses_handler.py の _handle_file_search メソッドを修正

async def _handle_file_search(self, messages: List[Dict[str, Any]]) -> str:
    file_ids = self.tools_config.get_search_file_ids()
    
    # OpenAI Vector Store APIを使用
    vector_store = await self.async_client.beta.vector_stores.create(
        name="File Search Store"
    )
    
    # ファイルを追加
    for file_id in file_ids:
        await self.async_client.beta.vector_stores.files.create(
            vector_store_id=vector_store.id,
            file_id=file_id
        )
    
    # 検索を実行
    # ...
```

## トラブルシューティング

### 問題: Tools機能が動作しない

1. **設定を確認**:
   ```
   /tools
   ```

2. **Tools機能を有効化**:
   ```
   /tools enable all
   ```

3. **設定ファイルを確認**:
   `.chainlit/tools_config.json` が正しく作成されているか確認

### 問題: Web検索が実行されない

1. **APIキーを確認**:
   実際のWeb検索APIキーが設定されているか確認

2. **ログを確認**:
   `.chainlit/app.log` でエラーメッセージを確認

### 問題: 旧バージョンに戻したい

```batch
copy /Y app_old_completions.py app.py
```

## 今後の拡張計画

1. **実際のWeb検索API統合**
   - Bing Search API
   - Google Custom Search API
   - DuckDuckGo API

2. **ファイル検索の強化**
   - Vector Store統合
   - ローカルファイル検索
   - PDF/Word文書の解析

3. **カスタム関数の追加**
   - データベース検索
   - 外部API呼び出し
   - カスタムビジネスロジック

4. **UI/UXの改善**
   - ツール実行状況のリアルタイム表示
   - 検索結果のリッチな表示
   - ツール設定のGUI

## まとめ

OpenAI Responses APIとTools機能の実装により、以下が実現されました：

✅ **構造化されたAPI応答**
- より効率的なエラーハンドリング
- 明確なツール呼び出しフロー

✅ **拡張可能なTools機能**
- Web検索、ファイル検索の基盤実装
- 簡単な有効/無効切り替え
- カスタマイズ可能な設定

✅ **ユーザーフレンドリーな操作**
- コマンドによる簡単な設定変更
- 視覚的なツール実行状況表示
- 詳細な統計情報

## 参考リンク

- [OpenAI API Reference - Responses](https://platform.openai.com/docs/api-reference/responses)
- [OpenAI Tools - Web Search Guide](https://platform.openai.com/docs/guides/tools-web-search?api-mode=responses)
- [OpenAI Tools - File Search Guide](https://platform.openai.com/docs/guides/tools-file-search)
- [Chainlit Documentation](https://docs.chainlit.io/)