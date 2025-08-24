# フェーズ2・フェーズ3実装ガイド

## 概要
三層ベクトルストア管理の自動化とGUI化を実装しました。

## フェーズ2：層3の自動化（チャット単位）

### 実装内容
ファイルアップロード時にセッション用ベクトルストアを自動作成・管理

### 主な機能
1. **自動VS作成**
   - ファイルアップロード時に自動的にセッションVSを作成
   - メタデータで`type: "session"`として識別

2. **自動ファイル追加**
   - アップロードされたファイルを自動的にVSに追加
   - セッション内で共有される一時的なナレッジベース

3. **自動クリーンアップ**
   - チャット終了時に自動削除（オプション）
   - 一時的なVSとして管理

### 実装ファイル
- `utils/auto_vector_store_manager.py` - 自動管理クラス

### 使用例
```python
# ファイルアップロード時（自動）
ユーザー: [ファイルをドラッグ&ドロップ]
システム: ✅ ファイルを自動的にナレッジベースに追加しました
         セッションベクトルストア: vs_session_xxx
         このチャット内で検索対象になります

# セッション情報確認
ユーザー: /vs session
システム: セッションベクトルストア
         ファイル数: 3個
         作成時刻: 14:30
```

## フェーズ3：層2のGUI化（個人用）

### 実装内容
カテゴリ管理機能とGUIベースの管理パネル

### カテゴリ定義
| カテゴリ | アイコン | 説明 |
|---------|---------|------|
| general | 📄 | 一般・分類なし |
| technical | 💻 | 技術文書・プログラミング |
| business | 💼 | ビジネス文書 |
| research | 🔬 | 研究・論文 |
| personal | 📝 | 個人メモ |
| project | 📁 | プロジェクト資料 |
| reference | 📚 | リファレンス |
| creative | 🎨 | クリエイティブ |

### 主な機能

#### 1. 管理パネル
```bash
/vs gui
```
- カテゴリ別にベクトルストアを表示
- 統計情報（VS数、ファイル数）
- アクションボタンでインタラクティブ操作

#### 2. カテゴリ付き作成
```python
# GUIダイアログで作成
1. カテゴリ選択（8種類から選択）
2. 名前入力（オプション）
3. 自動的にメタデータに記録
```

#### 3. カテゴリ変更
```python
# 既存VSのカテゴリを変更
1. 変更するVSを選択
2. 新しいカテゴリを選択
3. メタデータを更新
```

#### 4. エクスポート機能
```python
# VS一覧をJSON形式でエクスポート
{
  "exported_at": "2025-08-20T15:00:00",
  "user_id": "user_123",
  "vector_stores": [
    {
      "id": "vs_xxx",
      "name": "技術文書",
      "category": "technical",
      "file_count": 10
    }
  ]
}
```

### 実装ファイル
- `utils/vector_store_gui_manager.py` - GUI管理クラス

## 統合実装

### 実装ファイル
- `utils/integrated_vs_commands.py` - 統合コマンドハンドラー

### 新しいコマンド
| コマンド | 説明 |
|---------|------|
| `/vs gui` | 管理パネル表示 |
| `/vs stats` | カテゴリ別統計 |
| `/vs session` | セッションVS情報 |
| `/vs auto` | 自動化設定確認 |

## app.pyへの統合方法

### 1. インポート追加
```python
from utils.integrated_vs_commands import (
    handle_integrated_vs_commands,
    handle_integrated_file_upload,
    handle_gui_action,
    on_chat_start_integrated,
    on_chat_end_integrated
)
```

### 2. on_chat_start修正
```python
@cl.on_chat_start
async def on_chat_start():
    # ... 既存のコード ...
    
    # 統合初期化
    await on_chat_start_integrated()
```

### 3. on_message修正
```python
@cl.on_message
async def on_message(message: cl.Message):
    # /vsコマンド処理を統合版に置き換え
    if message.content.startswith("/vs"):
        await handle_integrated_vs_commands(message.content)
        return
    
    # ファイルアップロード処理を統合版に
    if message.elements:
        await handle_integrated_file_upload(message.elements)
        return
```

### 4. アクション処理追加
```python
@cl.on_action
async def on_action(action: cl.Action):
    # GUI関連のアクション処理
    if action.name in ["create_vs_with_category", "manage_vs_category", 
                       "bulk_file_upload", "export_vs_list"]:
        await handle_gui_action(action)
```

### 5. クリーンアップ（オプション）
```python
@cl.on_chat_end
async def on_chat_end():
    # セッションVSのクリーンアップ
    await on_chat_end_integrated()
```

## 動作フロー

### ファイルアップロード時の自動処理
```
1. ユーザーがファイルをアップロード
    ↓
2. セッションVSが存在しない場合は自動作成
    ↓
3. ファイルを自動的にVSに追加
    ↓
4. メッセージで通知
    ↓
5. 以後の会話で自動的に参照
```

### GUI管理フロー
```
1. /vs gui で管理パネルを開く
    ↓
2. カテゴリ別にVSを確認
    ↓
3. アクションボタンで操作
    ├─ 新規作成（カテゴリ選択）
    ├─ カテゴリ変更
    ├─ 一括アップロード
    └─ エクスポート
```

## 三層の役割分担

| 層 | 管理方法 | 作成 | 削除 | 特徴 |
|----|---------|------|------|------|
| **層1（会社）** | 環境変数 | 管理者 | 不可 | 読み取り専用、共有知識 |
| **層2（個人）** | GUI/コマンド | ユーザー | ユーザー | カテゴリ管理、永続的 |
| **層3（セッション）** | 自動 | 自動 | 自動 | 一時的、チャット単位 |

## 使用シナリオ

### シナリオ1：技術文書の管理
```
1. /vs gui で管理パネルを開く
2. 「新規作成」→「技術文書」カテゴリを選択
3. ファイルをアップロード
4. 永続的な技術ナレッジベースとして利用
```

### シナリオ2：一時的な分析作業
```
1. 分析用ファイルをアップロード（自動でセッションVS作成）
2. ファイル内容について質問
3. チャット終了時に自動削除
```

### シナリオ3：プロジェクト資料の整理
```
1. /vs gui で「プロジェクト」カテゴリのVSを作成
2. 関連資料を一括アップロード
3. カテゴリ別統計で管理状況を確認
```

## まとめ

フェーズ2とフェーズ3の実装により：

1. **自動化** - ファイルアップロードの手間を削減
2. **組織化** - カテゴリによる体系的な管理
3. **可視化** - GUI管理パネルで直感的操作
4. **効率化** - 三層構造で適切な知識管理

これにより、エンジニアでないユーザーでも簡単にナレッジベースを管理できるようになりました。
