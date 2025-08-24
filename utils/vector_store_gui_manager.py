"""
ベクトルストアGUI管理モジュール
層2（個人用）のベクトルストアをGUIで管理
"""

import chainlit as cl
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json


class VectorStoreGUIManager:
    """ベクトルストアのGUI管理クラス"""
    
    # カテゴリ定義
    CATEGORIES = {
        "general": {"name": "一般", "icon": "📄", "description": "分類なし"},
        "technical": {"name": "技術文書", "icon": "💻", "description": "プログラミング・技術資料"},
        "business": {"name": "ビジネス", "icon": "💼", "description": "ビジネス文書・プレゼン"},
        "research": {"name": "研究資料", "icon": "🔬", "description": "研究・論文・学術資料"},
        "personal": {"name": "個人メモ", "icon": "📝", "description": "個人的なメモ・ノート"},
        "project": {"name": "プロジェクト", "icon": "📁", "description": "プロジェクト関連資料"},
        "reference": {"name": "参考資料", "icon": "📚", "description": "リファレンス・マニュアル"},
        "creative": {"name": "クリエイティブ", "icon": "🎨", "description": "創作・デザイン資料"}
    }
    
    def __init__(self, secure_manager):
        """
        初期化
        
        Args:
            secure_manager: SecureVectorStoreManagerインスタンス
        """
        self.secure_manager = secure_manager
        self.user_preferences = {}  # ユーザー設定のキャッシュ
    
    def _get_file_count(self, file_counts) -> int:
        """
        file_countsオブジェクトからファイル数を取得
        
        Args:
            file_counts: file_countsオブジェクト（dict、int、FileCounts オブジェクトなど）
        
        Returns:
            ファイル数
        """
        if file_counts is None:
            return 0
        elif isinstance(file_counts, dict):
            return file_counts.get('total', 0)
        elif isinstance(file_counts, int):
            return file_counts
        elif hasattr(file_counts, 'total'):
            # FileCounts オブジェクトの場合
            return getattr(file_counts, 'total', 0)
        else:
            return 0
    
    async def show_management_panel(self, user_id: str):
        """
        ベクトルストア管理パネルを表示
        
        Args:
            user_id: ユーザーID
        """
        # 現在のベクトルストアを取得
        my_stores = await self.secure_manager.list_my_vector_stores(user_id)
        
        # カテゴリ別に整理
        stores_by_category = self._organize_by_category(my_stores)
        
        # メッセージ構築
        message = "# 📚 ナレッジベース管理パネル\n\n"
        
        # サマリー
        total_count = len(my_stores)
        total_files = sum(
            self._get_file_count(vs.get('file_counts'))
            for vs in my_stores
        )
        
        message += f"""## 📊 統計情報
- **ベクトルストア数**: {total_count}個
- **総ファイル数**: {total_files}個
- **利用カテゴリ**: {len(stores_by_category)}種類

---

"""
        
        # カテゴリ別表示
        message += "## 📁 カテゴリ別ベクトルストア\n\n"
        
        for category_key, stores in stores_by_category.items():
            category_info = self.CATEGORIES.get(category_key, self.CATEGORIES["general"])
            message += f"### {category_info['icon']} {category_info['name']}\n"
            message += f"*{category_info['description']}*\n\n"
            
            for store in stores:
                file_count = self._get_file_count(store.get('file_counts'))
                created_date = datetime.fromtimestamp(store['created_at']).strftime('%Y-%m-%d')
                
                message += f"- **{store['name']}**\n"
                message += f"  - ID: `{store['id'][:8]}...`\n"
                message += f"  - ファイル: {file_count}個 | 作成日: {created_date}\n\n"
        
        # アクションボタン
        actions = [
            cl.Action(
                name="create_vs_with_category",
                payload={"action": "create"},
                label="📁 新規作成",
                description="カテゴリを選んで作成"
            ),
            cl.Action(
                name="manage_vs_category",
                payload={"action": "manage"},
                label="⚙️ カテゴリ変更",
                description="既存VSのカテゴリを変更"
            ),
            cl.Action(
                name="bulk_file_upload",
                payload={"action": "bulk"},
                label="📤 一括アップロード",
                description="複数ファイルを整理"
            ),
            cl.Action(
                name="export_vs_list",
                payload={"action": "export"},
                label="💾 エクスポート",
                description="VS一覧を出力"
            )
        ]
        
        await cl.Message(
            content=message,
            actions=actions,
            author="System"
        ).send()
    
    async def create_with_category_dialog(self, user_id: str):
        """
        カテゴリ選択付きのベクトルストア作成ダイアログ
        
        Args:
            user_id: ユーザーID
        """
        # カテゴリ選択
        category_options = []
        for key, info in self.CATEGORIES.items():
            category_options.append(
                cl.Action(
                    name="select_category",
                    payload={"category": key},
                    label=f"{info['icon']} {info['name']}",
                    description=info['description']
                )
            )
        
        res = await cl.AskActionMessage(
            content="## 📁 新規ベクトルストア作成\n\nカテゴリを選択してください：",
            actions=category_options
        ).send()
        
        if not res:
            return
        
        selected_category = res.get("payload", {}).get("category", "general")
        
        # 名前を入力
        name_res = await cl.AskUserMessage(
            content=f"ベクトルストアの名前を入力してください（省略可）：",
            timeout=60
        ).send()
        
        name = name_res["output"] if name_res else None
        
        # ベクトルストア作成
        await self._create_categorized_vs(user_id, selected_category, name)
    
    async def _create_categorized_vs(self, user_id: str, category: str, name: Optional[str] = None):
        """
        カテゴリ付きベクトルストアを作成
        
        Args:
            user_id: ユーザーID
            category: カテゴリキー
            name: ベクトルストア名
        """
        category_info = self.CATEGORIES.get(category, self.CATEGORIES["general"])
        
        if not name:
            name = f"{category_info['name']} - {datetime.now().strftime('%Y%m%d_%H%M')}"
        
        # メタデータ作成
        metadata = {
            "owner_id": user_id,
            "category": category,
            "category_name": category_info['name'],
            "created_at": datetime.now().isoformat(),
            "type": "personal",  # 個人用VS
            "managed_by_gui": True  # GUI管理フラグ
        }
        
        # ベクトルストア作成
        from utils.vector_store_handler import vector_store_handler
        
        try:
            vector_store = await vector_store_handler.async_client.beta.vector_stores.create(
                name=name,
                metadata=metadata
            )
            
            vs_id = vector_store.id
            
            # 初期ファイルアップロードの提案
            message = f"""✅ **ベクトルストアを作成しました**

{category_info['icon']} **カテゴリ**: {category_info['name']}
📁 **名前**: {name}
🆔 **ID**: `{vs_id}`

### 次のステップ
ファイルをドラッグ&ドロップしてアップロードするか、
以下のコマンドでファイルを追加してください：

`/vs use {vs_id}`"""
            
            await cl.Message(content=message, author="System").send()
            
            # セッションに保存
            cl.user_session.set("personal_vs_id", vs_id)
            
        except Exception as e:
            await cl.Message(
                content=f"❌ ベクトルストア作成エラー: {e}",
                author="System"
            ).send()
    
    async def manage_category_dialog(self, user_id: str):
        """
        カテゴリ変更ダイアログ
        
        Args:
            user_id: ユーザーID
        """
        # 自分のベクトルストア一覧を取得
        my_stores = await self.secure_manager.list_my_vector_stores(user_id)
        
        if not my_stores:
            await cl.Message(
                content="ベクトルストアがありません。先に作成してください。",
                author="System"
            ).send()
            return
        
        # VS選択
        vs_options = []
        for store in my_stores:
            current_category = store.get('category', 'general')
            category_info = self.CATEGORIES.get(current_category, self.CATEGORIES["general"])
            
            vs_options.append(
                cl.Action(
                    name="select_vs_to_manage",
                    payload={"vs_id": store['id'], "current_category": current_category},
                    label=f"{store['name']}",
                    description=f"現在: {category_info['icon']} {category_info['name']}"
                )
            )
        
        res = await cl.AskActionMessage(
            content="## ⚙️ カテゴリ変更\n\n変更するベクトルストアを選択：",
            actions=vs_options
        ).send()
        
        if not res:
            return
        
        vs_id = res.get("payload", {}).get("vs_id")
        current_category = res.get("payload", {}).get("current_category", "general")
        
        # 新しいカテゴリを選択
        category_options = []
        for key, info in self.CATEGORIES.items():
            if key != current_category:  # 現在のカテゴリ以外
                category_options.append(
                    cl.Action(
                        name="update_category",
                        payload={"vs_id": vs_id, "new_category": key},
                        label=f"{info['icon']} {info['name']}",
                        description=info['description']
                    )
                )
        
        res2 = await cl.AskActionMessage(
            content="新しいカテゴリを選択：",
            actions=category_options
        ).send()
        
        if res2:
            await self._update_vs_category(vs_id, user_id, res2.get("payload", {}).get("new_category"))
    
    async def _update_vs_category(self, vs_id: str, user_id: str, new_category: str):
        """
        ベクトルストアのカテゴリを更新
        
        Args:
            vs_id: ベクトルストアID
            user_id: ユーザーID
            new_category: 新しいカテゴリ
        """
        from utils.vector_store_handler import vector_store_handler
        
        try:
            # 現在のメタデータを取得
            vs = await vector_store_handler.async_client.beta.vector_stores.retrieve(vs_id)
            current_metadata = getattr(vs, 'metadata', {}) or {}
            
            # カテゴリを更新
            category_info = self.CATEGORIES.get(new_category, self.CATEGORIES["general"])
            current_metadata['category'] = new_category
            current_metadata['category_name'] = category_info['name']
            current_metadata['updated_at'] = datetime.now().isoformat()
            
            # メタデータを更新
            await vector_store_handler.async_client.beta.vector_stores.update(
                vector_store_id=vs_id,
                metadata=current_metadata
            )
            
            await cl.Message(
                content=f"✅ カテゴリを更新しました\n\n{category_info['icon']} **新カテゴリ**: {category_info['name']}",
                author="System"
            ).send()
            
        except Exception as e:
            await cl.Message(
                content=f"❌ カテゴリ更新エラー: {e}",
                author="System"
            ).send()
    
    async def export_vs_list(self, user_id: str):
        """
        ベクトルストア一覧をエクスポート
        
        Args:
            user_id: ユーザーID
        """
        my_stores = await self.secure_manager.list_my_vector_stores(user_id)
        
        # JSON形式でエクスポート
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "user_id": user_id,
            "total_count": len(my_stores),
            "vector_stores": []
        }
        
        for store in my_stores:
            category = store.get('category', 'general')
            category_info = self.CATEGORIES.get(category, self.CATEGORIES["general"])
            
            export_data["vector_stores"].append({
                "id": store['id'],
                "name": store['name'],
                "category": category,
                "category_name": category_info['name'],
                "file_count": self._get_file_count(store.get('file_counts')),
                "created_at": datetime.fromtimestamp(store['created_at']).isoformat()
            })
        
        # JSON文字列として表示
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        
        message = f"""## 💾 ベクトルストア一覧エクスポート

```json
{json_str}
```

このデータをコピーして保存してください。"""
        
        await cl.Message(content=message, author="System").send()
    
    def _organize_by_category(self, stores: List[Dict]) -> Dict[str, List[Dict]]:
        """
        ベクトルストアをカテゴリ別に整理
        
        Args:
            stores: ベクトルストアリスト
        
        Returns:
            カテゴリ別の辞書
        """
        organized = {}
        
        for store in stores:
            category = store.get('category', 'general')
            if category not in organized:
                organized[category] = []
            organized[category].append(store)
        
        # カテゴリをソート（定義順）
        sorted_organized = {}
        for key in self.CATEGORIES.keys():
            if key in organized:
                sorted_organized[key] = organized[key]
        
        # 未定義のカテゴリがあれば最後に追加
        for key, value in organized.items():
            if key not in sorted_organized:
                sorted_organized[key] = value
        
        return sorted_organized
    
    async def show_category_stats(self, user_id: str):
        """
        カテゴリ別統計を表示
        
        Args:
            user_id: ユーザーID
        """
        my_stores = await self.secure_manager.list_my_vector_stores(user_id)
        stores_by_category = self._organize_by_category(my_stores)
        
        message = "# 📊 カテゴリ別統計\n\n"
        
        for category_key, stores in stores_by_category.items():
            category_info = self.CATEGORIES.get(category_key, self.CATEGORIES["general"])
            total_files = sum(
                self._get_file_count(vs.get('file_counts'))
                for vs in stores
            )
            
            message += f"{category_info['icon']} **{category_info['name']}**\n"
            message += f"- ベクトルストア: {len(stores)}個\n"
            message += f"- ファイル総数: {total_files}個\n\n"
        
        await cl.Message(content=message, author="System").send()


# グローバルインスタンス
gui_manager = None

def initialize_gui_manager(secure_manager):
    """
    GUIマネージャーを初期化
    
    Args:
        secure_manager: SecureVectorStoreManagerインスタンス
    """
    global gui_manager
    gui_manager = VectorStoreGUIManager(secure_manager)
    return gui_manager
