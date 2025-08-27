# 🏗️ Modular Handler Architecture実装ガイド

本ドキュメントは、多機能AIワークスペースアプリケーションの**Modular Handler Architecture**の実装指針とベストプラクティスを説明します。

## 📋 目次

- [アーキテクチャ概要](#-アーキテクチャ概要)
- [設計原則](#-設計原則)
- [ファイル構造](#-ファイル構造)
- [各ハンドラーの責任範囲](#-各ハンドラーの責任範囲)
- [実装パターン](#-実装パターン)
- [新機能追加ガイド](#-新機能追加ガイド)
- [ベストプラクティス](#-ベストプラクティス)
- [トラブルシューティング](#-トラブルシューティング)

## 🏗️ アーキテクチャ概要

### 構造図

```
app.py (440行) - Chainlitコアイベント処理のみ
├── handlers/                    # 機能別ハンドラー（1,313行）
│   ├── command_handler.py       # コマンドルーティング (234行)
│   ├── persona_handler.py       # ペルソナ管理 (183行)
│   ├── settings_handler.py      # 設定・統計・テスト (280行)
│   └── vector_store_commands.py # ベクトルストア管理 (316行)
├── utils/                       # 共通ユーティリティ
│   ├── ui_helper.py            # UI操作統一化 (107行)
│   ├── error_handler.py        # エラー処理統一化 (209行)
│   ├── responses_handler.py    # Responses API処理
│   ├── config.py              # 設定管理
│   ├── persona_manager.py     # ペルソナエンジン
│   └── vector_store_handler.py # ベクトルストアエンジン
└── .chainlit/                  # データ永続化
    ├── chainlit.db            # SQLiteデータベース
    ├── personas.json          # ペルソナデータ
    └── vector_stores/         # ベクトルストア管理
```

### リファクタリング効果

| 指標 | Before | After | 改善率 |
|-----|--------|-------|--------|
| **app.py行数** | 2,468行 | 440行 | **82%削減** |
| **機能分離** | 1つのモノリシック | 6つのモジュラーハンドラー | **6倍の粒度向上** |
| **責任範囲** | 複数責任混在 | 単一責任原則 | **明確化** |
| **テスト容易性** | 困難 | 容易 | **大幅改善** |

## 🎯 設計原則

### 1. 単一責任原則（SRP）
各ハンドラーは**1つの明確な責任**のみを持つ：
- `CommandHandler`: コマンドルーティングのみ
- `PersonaHandler`: ペルソナ管理のみ
- `SettingsHandler`: 設定・統計管理のみ
- `VectorStoreHandler`: ベクトルストア管理のみ

### 2. DRY原則（Don't Repeat Yourself）
共通処理の統一化：
- **UI処理**: `ui_helper.py`で統一
- **エラー処理**: `error_handler.py`で統一
- **ログ処理**: `logger.py`で統一

### 3. 疎結合設計
- **遅延インポート**で循環参照を回避
- **インターフェースの統一化**で依存関係を最小化
- **独立性の確保**で個別テストを可能に

### 4. 高凝集設計
関連機能を論理的にグループ化：
- ペルソナ関連：作成・編集・削除・切り替え
- 設定関連：API設定・モデル設定・統計表示
- ベクトルストア関連：CRUD操作・ファイル管理

## 📂 ファイル構造

### コアファイル

#### `app.py` (440行)
```python
# 責任：Chainlitコアイベント処理のみ
- @cl.on_chat_start    # セッション初期化
- @cl.on_message       # メッセージルーティング  
- @cl.on_file_upload   # ファイル処理ルーティング
- @cl.on_settings_update # 設定更新処理
- @cl.on_action        # アクション処理ルーティング
- @cl.on_chat_resume   # チャット再開処理
- @cl.on_chat_end      # チャット終了処理
```

### ハンドラーファイル

#### `handlers/command_handler.py` (234行)
```python
class CommandHandler:
    """コマンドルーティング専用クラス"""
    
    def __init__(self):
        self.commands = {
            "/help": self._handle_help,
            "/stats": self._handle_stats,
            # ... 全コマンドのルーティング
        }
    
    async def handle_command(self, user_input: str):
        """統一コマンド処理エントリーポイント"""
        
    def _get_settings_handler(self):
        """遅延インポートによる依存関係管理"""
```

#### `handlers/persona_handler.py` (183行)
```python
class PersonaHandler:
    """ペルソナ管理専用クラス"""
    
    async def show_personas(self):
        """ペルソナ一覧表示"""
        
    async def switch_persona(self, persona_name: str):
        """ペルソナ切り替え"""
        
    async def create_persona_interactive(self):
        """インタラクティブペルソナ作成"""
        
    async def delete_persona(self, persona_name: str):
        """ペルソナ削除"""
```

### 共通ユーティリティ

#### `utils/ui_helper.py` (107行)
```python
class ChainlitHelper:
    """Chainlit UI操作の統一化"""
    
    @staticmethod
    async def send_system_message(content: str):
        """システムメッセージ統一送信"""
        
    @staticmethod
    async def send_error_message(content: str):
        """エラーメッセージ統一送信"""
        
    @staticmethod
    def get_session(key: str, default=None):
        """セッション取得の統一インターフェース"""
```

#### `utils/error_handler.py` (209行)
```python
class ErrorHandler:
    """統一エラーハンドリング"""
    
    @staticmethod
    async def handle_api_error(error: Exception, operation: str):
        """API関連エラーの専用処理"""
        
    @staticmethod
    async def handle_file_error(error: Exception, operation: str):
        """ファイル関連エラーの専用処理"""
        
    @staticmethod
    async def handle_vector_store_error(error: Exception, operation: str):
        """ベクトルストア関連エラーの専用処理"""
```

## 🎛️ 各ハンドラーの責任範囲

### CommandHandler
**責任**: コマンド文字列の解析とルーティング
- コマンド文字列の分割・検証
- 適切なハンドラーメソッドへの転送
- ヘルプ表示・基本コマンド処理
- **❌ やらないこと**: 具体的な機能実装（他ハンドラーに委譲）

### PersonaHandler  
**責任**: ペルソナの全ライフサイクル管理
- ペルソナ一覧表示・検索
- ペルソナ作成・編集・削除
- ペルソナ切り替えとセッション適用
- **❌ やらないこと**: ペルソナデータの永続化（persona_managerに委譲）

### SettingsHandler
**責任**: アプリケーション設定と統計情報
- API設定・接続テスト
- モデル変更・システムプロンプト設定
- 統計情報表示・システム状態監視
- **❌ やらないこと**: 実際の設定保存（config_managerに委譲）

### VectorStoreHandler
**責任**: ベクトルストアの管理とファイル処理
- ベクトルストアのCRUD操作
- ファイルアップロード処理
- 3層構造の維持管理
- **❌ やらないこと**: OpenAI APIの直接呼び出し（vector_store_handlerに委譲）

## 🔧 実装パターン

### 1. 遅延インポートパターン

```python
class CommandHandler:
    def _get_settings_handler(self):
        """循環参照を避ける遅延インポート"""
        global settings_handler_instance
        if settings_handler_instance is None:
            from handlers.settings_handler import SettingsHandler
            settings_handler_instance = SettingsHandler()
        return settings_handler_instance
```

### 2. 統一UI処理パターン

```python
# ❌ 避けるべきパターン
await cl.Message(content="✅ 成功しました", author="System").send()

# ✅ 推奨パターン
from utils.ui_helper import ChainlitHelper as ui
await ui.send_success_message("成功しました")
```

### 3. 統一エラーハンドリングパターン

```python
# ❌ 避けるべきパターン  
try:
    # 処理
    pass
except Exception as e:
    await cl.Message(content=f"エラー: {str(e)}", author="System").send()

# ✅ 推奨パターン
from utils.error_handler import ErrorHandler as error_handler
try:
    # 処理
    pass
except Exception as e:
    await error_handler.handle_api_error(e, "API呼び出し")
```

### 4. セッション管理パターン

```python
# ❌ 避けるべきパターン
user_id = cl.user_session.get("user_id", "anonymous")

# ✅ 推奨パターン
from utils.ui_helper import ChainlitHelper as ui
user_id = ui.get_session("user_id", "anonymous")
```

## ➕ 新機能追加ガイド

### ステップ1: 責任の特定
新機能がどの責任範囲に属するかを決定：

| 機能カテゴリ | 追加先ハンドラー | 例 |
|------------|----------------|-----|
| **新しいコマンド** | CommandHandler | `/export`, `/import` |
| **ペルソナ機能** | PersonaHandler | ペルソナ共有、テンプレート |
| **設定・統計** | SettingsHandler | 新しい設定項目、レポート機能 |
| **ベクトルストア** | VectorStoreHandler | 検索機能、同期機能 |
| **UI処理** | ui_helper.py | 新しいメッセージタイプ |
| **エラー処理** | error_handler.py | 新しいエラー種別 |

### ステップ2: 実装パターンの適用

#### 新しいコマンドの追加例

```python
# 1. CommandHandlerにルーティング追加
class CommandHandler:
    def __init__(self):
        self.commands = {
            # 既存のコマンド...
            "/export": self._handle_export,  # 新しいコマンド
        }
    
    async def _handle_export(self, parts: List[str]):
        """エクスポートコマンドの処理"""
        settings_handler = self._get_settings_handler()
        await settings_handler.export_settings()

# 2. SettingsHandlerに実装追加
class SettingsHandler:
    async def export_settings(self):
        """設定エクスポート機能"""
        try:
            # エクスポート処理...
            await ui.send_success_message("設定をエクスポートしました")
        except Exception as e:
            await error_handler.handle_file_error(e, "設定エクスポート")
```

#### 新しいUI処理の追加例

```python
# utils/ui_helper.py
class ChainlitHelper:
    @staticmethod
    async def send_progress_message(content: str, progress: int):
        """進捗表示の新しいパターン"""
        formatted_content = f"⏳ {content} ({progress}%完了)"
        await cl.Message(content=formatted_content, author="System").send()

# 使用例
await ui.send_progress_message("処理中", 75)
```

### ステップ3: テストとドキュメント更新

1. **単体テスト**: 新しいハンドラーメソッドのテスト
2. **統合テスト**: 他ハンドラーとの連携テスト  
3. **ドキュメント更新**: README.md、本ガイドの更新

## ⭐ ベストプラクティス

### 🎯 DO（推奨事項）

1. **統一インターフェース使用**
   ```python
   # UI処理
   await ui.send_system_message("メッセージ")
   
   # エラー処理
   await error_handler.handle_api_error(e, "操作名")
   
   # セッション管理
   value = ui.get_session("key", default_value)
   ```

2. **適切なログ記録**
   ```python
   from utils.logger import app_logger
   app_logger.info("操作開始", operation="ペルソナ作成")
   app_logger.error("エラー発生", error=str(e))
   ```

3. **例外の適切な処理**
   ```python
   try:
       result = await some_operation()
   except SpecificException as e:
       await error_handler.handle_specific_error(e, "操作名")
   except Exception as e:
       await error_handler.handle_unexpected_error(e, "操作名")
   ```

4. **遅延インポート使用**
   ```python
   def _get_handler(self):
       if not hasattr(self, '_handler'):
           from handlers.some_handler import SomeHandler
           self._handler = SomeHandler()
       return self._handler
   ```

### ❌ DON'T（避けるべき事項）

1. **直接的なChainlit API呼び出し**
   ```python
   # ❌ 避ける
   await cl.Message(content="メッセージ", author="System").send()
   
   # ✅ 推奨
   await ui.send_system_message("メッセージ")
   ```

2. **ハードコードされたエラーメッセージ**
   ```python
   # ❌ 避ける
   await cl.Message(content="エラーが発生しました", author="System").send()
   
   # ✅ 推奨  
   await error_handler.handle_unexpected_error(e, "操作名")
   ```

3. **複数責任の混在**
   ```python
   # ❌ 避ける：ペルソナハンドラーでベクトルストア操作
   class PersonaHandler:
       async def create_persona_with_vector_store(self):
           # ペルソナ作成 + ベクトルストア作成
   
   # ✅ 推奨：責任を分離
   class PersonaHandler:
       async def create_persona(self):
           # ペルソナ作成のみ
           
   class VectorStoreHandler:
       async def create_persona_vector_store(self):
           # ベクトルストア作成のみ
   ```

4. **循環インポート**
   ```python
   # ❌ 避ける
   from handlers.settings_handler import settings_handler
   
   # ✅ 推奨
   def _get_settings_handler(self):
       # 遅延インポート
   ```

## 🔍 トラブルシューティング

### よくある問題と解決策

#### 1. 循環インポートエラー
**症状**: `ImportError: cannot import name 'X' from 'Y'`

**解決策**: 遅延インポートの使用
```python
# 問題のあるコード
from handlers.settings_handler import SettingsHandler

# 解決策
def get_settings_handler():
    from handlers.settings_handler import SettingsHandler
    return SettingsHandler()
```

#### 2. セッション値の不整合
**症状**: セッション値が期待と異なる

**解決策**: ui_helper.pyの統一インターフェース使用
```python
# 問題のあるコード
value = cl.user_session.get("key")

# 解決策
from utils.ui_helper import ChainlitHelper as ui
value = ui.get_session("key", default_value)
```

#### 3. エラーメッセージの不統一
**症状**: エラー表示が統一されていない

**解決策**: error_handler.pyの専用メソッド使用
```python
# 問題のあるコード
await cl.Message(content=f"エラー: {str(e)}").send()

# 解決策
await error_handler.handle_api_error(e, "操作名")
```

#### 4. ハンドラー間の依存関係
**症状**: あるハンドラーが他のハンドラーに強く依存

**解決策**: インターフェースの統一と疎結合設計
```python
# 問題のあるコード
persona_handler = PersonaHandler()
settings_handler = SettingsHandler()
settings_handler.persona_handler = persona_handler

# 解決策
# 共通インターフェースを通じた疎結合な連携
await ui.send_system_message("連携完了")
```

## 📚 参考資料

- [README.md](../README.md) - プロジェクト概要
- [create_history.md](../create_history.md) - リファクタリング履歴  
- [app.py](../app.py) - メインアプリケーション
- [handlers/](../handlers/) - モジュラーハンドラー
- [utils/](../utils/) - 共通ユーティリティ

---

## 📝 更新履歴

- **2024-08-27**: 初版作成（Modular Handler Architecture導入）

本ドキュメントは、新しいModular Handler Architectureの理解と実装支援を目的としています。不明な点がある場合は、具体的なファイルやコード例を参照してください。