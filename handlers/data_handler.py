"""
データエクスポート・インポートハンドラー
会話履歴、ペルソナ、設定、統計データの管理機能
"""

import os
import json
import csv
import sqlite3
import zipfile
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from io import StringIO
import tempfile
from utils.ui_helper import ChainlitHelper as ui
from utils.error_handler import ErrorHandler as error_handler
from utils.logger import app_logger
from utils.analytics_logger import analytics_logger
from utils.persona_manager import persona_manager


class DataHandler:
    """データエクスポート・インポートを統括するクラス"""
    
    def __init__(self):
        """データハンドラーを初期化"""
        self.chainlit_db_path = ".chainlit/chainlit.db"
        self.analytics_db_path = ".chainlit/analytics.db"
        self.personas_path = ".chainlit/personas.json"
        self.export_formats = ["json", "csv", "zip", "backup"]
    
    async def export_workspace_data(
        self,
        user_id: str,
        export_format: str = "json",
        include_conversations: bool = True,
        include_personas: bool = True,
        include_analytics: bool = True,
        date_range_days: int = 30
    ) -> Optional[str]:
        """ワークスペースデータの包括的エクスポート"""
        try:
            loading_msg = await ui.show_loading_message("ワークスペースデータをエクスポート中...")
            
            if export_format not in self.export_formats:
                await ui.update_loading_message(
                    loading_msg,
                    f"❌ サポートされていない形式: {export_format}\n"
                    f"利用可能形式: {', '.join(self.export_formats)}"
                )
                return None
            
            export_data = await self._collect_export_data(
                user_id, include_conversations, include_personas, include_analytics, date_range_days
            )
            
            # フォーマット別エクスポート
            if export_format == "json":
                file_path = await self._export_as_json(export_data, user_id)
            elif export_format == "csv":
                file_path = await self._export_as_csv(export_data, user_id)
            elif export_format == "zip":
                file_path = await self._export_as_zip(export_data, user_id)
            elif export_format == "backup":
                file_path = await self._create_full_backup(user_id)
            else:
                file_path = None
            
            if file_path:
                file_size = os.path.getsize(file_path)
                await ui.update_loading_message(
                    loading_msg,
                    f"✅ エクスポート完了\n\n"
                    f"**ファイル**: {os.path.basename(file_path)}\n"
                    f"**サイズ**: {ui.format_file_size(file_size)}\n"
                    f"**形式**: {export_format.upper()}\n\n"
                    f"ファイルは `.chainlit/exports/` ディレクトリに保存されました。"
                )
                
                app_logger.info("データエクスポート完了", user_id=user_id, format=export_format, file_size=file_size)
                return file_path
            else:
                await ui.update_loading_message(loading_msg, "❌ エクスポートに失敗しました")
                return None
            
        except Exception as e:
            await error_handler.handle_file_error(e, "データエクスポート")
            return None
    
    async def export_conversations_only(
        self,
        user_id: str,
        export_format: str = "json",
        days: int = 30,
        include_metadata: bool = True
    ) -> Optional[str]:
        """会話履歴のみをエクスポート"""
        try:
            loading_msg = await ui.show_loading_message("会話履歴をエクスポート中...")
            
            conversations = await self._get_user_conversations(user_id, days, include_metadata)
            
            if not conversations:
                await ui.update_loading_message(
                    loading_msg,
                    "📝 エクスポート対象の会話履歴がありません。"
                )
                return None
            
            # エクスポートディレクトリの確保
            export_dir = ".chainlit/exports"
            os.makedirs(export_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if export_format == "json":
                filename = f"conversations_{user_id}_{timestamp}.json"
                file_path = os.path.join(export_dir, filename)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "export_info": {
                            "user_id": user_id,
                            "export_date": datetime.now().isoformat(),
                            "days_range": days,
                            "total_conversations": len(conversations)
                        },
                        "conversations": conversations
                    }, f, ensure_ascii=False, indent=2)
                    
            elif export_format == "csv":
                filename = f"conversations_{user_id}_{timestamp}.csv"
                file_path = os.path.join(export_dir, filename)
                
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "ID", "タイムスタンプ", "タイプ", "内容", "ペルソナ", "モデル", "セッションID"
                    ])
                    
                    for conv in conversations:
                        writer.writerow([
                            conv.get("id", ""),
                            conv.get("timestamp", ""),
                            conv.get("type", ""),
                            conv.get("content", "").replace("\n", " "),
                            conv.get("metadata", {}).get("persona", ""),
                            conv.get("metadata", {}).get("model", ""),
                            conv.get("session_id", "")
                        ])
            else:
                await ui.update_loading_message(loading_msg, f"❌ サポートされていない形式: {export_format}")
                return None
            
            file_size = os.path.getsize(file_path)
            await ui.update_loading_message(
                loading_msg,
                f"✅ 会話履歴エクスポート完了\n\n"
                f"**件数**: {len(conversations)}件の会話\n"
                f"**期間**: 直近{days}日間\n"
                f"**ファイル**: {filename}\n"
                f"**サイズ**: {ui.format_file_size(file_size)}"
            )
            
            return file_path
            
        except Exception as e:
            await error_handler.handle_file_error(e, "会話履歴エクスポート")
            return None
    
    async def export_analytics_data(
        self,
        user_id: str = None,
        days: int = 30,
        export_format: str = "json"
    ) -> Optional[str]:
        """統計データをエクスポート"""
        try:
            loading_msg = await ui.show_loading_message("統計データをエクスポート中...")
            
            # 統計データの収集
            usage_summary = analytics_logger.get_usage_summary(user_id, days)
            vs_summary = analytics_logger.get_vector_store_summary(user_id, days)
            
            if not usage_summary and not vs_summary:
                await ui.update_loading_message(
                    loading_msg,
                    "📊 エクスポート対象の統計データがありません。"
                )
                return None
            
            # エクスポートデータの構築
            analytics_data = {
                "export_info": {
                    "user_id": user_id,
                    "export_date": datetime.now().isoformat(),
                    "days_range": days,
                    "data_types": ["usage_summary", "vector_store_summary"]
                },
                "usage_summary": usage_summary,
                "vector_store_summary": vs_summary
            }
            
            # エクスポート実行
            export_dir = ".chainlit/exports"
            os.makedirs(export_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            user_suffix = f"_{user_id}" if user_id else "_all_users"
            filename = f"analytics{user_suffix}_{timestamp}.{export_format}"
            file_path = os.path.join(export_dir, filename)
            
            if export_format == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(analytics_data, f, ensure_ascii=False, indent=2)
            else:
                # CSV形式での統計データエクスポート
                await ui.update_loading_message(loading_msg, "❌ 統計データのCSV形式は現在サポートされていません")
                return None
            
            file_size = os.path.getsize(file_path)
            await ui.update_loading_message(
                loading_msg,
                f"✅ 統計データエクスポート完了\n\n"
                f"**期間**: 直近{days}日間\n"
                f"**対象**: {'指定ユーザー' if user_id else '全ユーザー'}\n"
                f"**ファイル**: {filename}\n"
                f"**サイズ**: {ui.format_file_size(file_size)}"
            )
            
            return file_path
            
        except Exception as e:
            await error_handler.handle_file_error(e, "統計データエクスポート")
            return None
    
    async def import_workspace_data(
        self,
        file_path: str,
        user_id: str,
        merge_mode: bool = True
    ) -> bool:
        """ワークスペースデータのインポート"""
        try:
            if not os.path.exists(file_path):
                await ui.send_error_message(f"ファイルが見つかりません: {file_path}")
                return False
            
            loading_msg = await ui.show_loading_message("データをインポート中...")
            
            # ファイル形式の判定
            if file_path.endswith('.json'):
                success = await self._import_from_json(file_path, user_id, merge_mode)
            elif file_path.endswith('.zip'):
                success = await self._import_from_zip(file_path, user_id, merge_mode)
            else:
                await ui.update_loading_message(
                    loading_msg,
                    "❌ サポートされていないファイル形式です。JSON または ZIP ファイルを使用してください。"
                )
                return False
            
            if success:
                await ui.update_loading_message(
                    loading_msg,
                    f"✅ データインポート完了\n\n"
                    f"**ファイル**: {os.path.basename(file_path)}\n"
                    f"**モード**: {'マージ' if merge_mode else '置換'}\n\n"
                    f"インポートしたデータは既存のデータと統合されました。"
                )
                
                app_logger.info("データインポート完了", user_id=user_id, file_path=file_path)
            else:
                await ui.update_loading_message(loading_msg, "❌ データインポートに失敗しました")
            
            return success
            
        except Exception as e:
            await error_handler.handle_file_error(e, "データインポート", os.path.basename(file_path))
            return False
    
    async def create_backup(self, user_id: str = None) -> Optional[str]:
        """完全バックアップの作成"""
        try:
            loading_msg = await ui.show_loading_message("完全バックアップを作成中...")
            
            backup_path = await self._create_full_backup(user_id)
            
            if backup_path:
                file_size = os.path.getsize(backup_path)
                await ui.update_loading_message(
                    loading_msg,
                    f"✅ バックアップ作成完了\n\n"
                    f"**ファイル**: {os.path.basename(backup_path)}\n"
                    f"**サイズ**: {ui.format_file_size(file_size)}\n\n"
                    f"バックアップファイルには以下が含まれています:\n"
                    f"- 会話履歴データベース\n"
                    f"- 統計データベース\n"
                    f"- ペルソナ設定\n"
                    f"- エクスポートメタデータ"
                )
                return backup_path
            else:
                await ui.update_loading_message(loading_msg, "❌ バックアップ作成に失敗しました")
                return None
                
        except Exception as e:
            await error_handler.handle_file_error(e, "バックアップ作成")
            return None
    
    async def _collect_export_data(
        self,
        user_id: str,
        include_conversations: bool,
        include_personas: bool,
        include_analytics: bool,
        date_range_days: int
    ) -> Dict[str, Any]:
        """エクスポート用データの収集"""
        export_data = {
            "export_info": {
                "user_id": user_id,
                "export_date": datetime.now().isoformat(),
                "date_range_days": date_range_days,
                "included_data": []
            }
        }
        
        if include_conversations:
            conversations = await self._get_user_conversations(user_id, date_range_days)
            export_data["conversations"] = conversations
            export_data["export_info"]["included_data"].append("conversations")
        
        if include_personas:
            personas = await persona_manager.get_all_personas()
            export_data["personas"] = personas
            export_data["export_info"]["included_data"].append("personas")
        
        if include_analytics:
            usage_summary = analytics_logger.get_usage_summary(user_id, date_range_days)
            vs_summary = analytics_logger.get_vector_store_summary(user_id, date_range_days)
            export_data["analytics"] = {
                "usage_summary": usage_summary,
                "vector_store_summary": vs_summary
            }
            export_data["export_info"]["included_data"].append("analytics")
        
        return export_data
    
    async def _get_user_conversations(
        self,
        user_id: str,
        days: int,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """ユーザーの会話履歴を取得"""
        try:
            conversations = []
            
            # 日付範囲の計算
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            with sqlite3.connect(self.chainlit_db_path) as conn:
                cursor = conn.cursor()
                
                sql = """
                SELECT e.id, e.type, e.content, e.created_at, s.id as session_id, s.metadata
                FROM element e
                LEFT JOIN step s ON e.step_id = s.id
                WHERE s.user_id = ? 
                AND e.created_at >= ? 
                AND e.created_at <= ?
                AND e.content IS NOT NULL
                ORDER BY e.created_at DESC
                """
                
                cursor.execute(sql, [user_id, start_date.isoformat(), end_date.isoformat()])
                rows = cursor.fetchall()
                
                for row in rows:
                    element_id, element_type, content, created_at, session_id, session_metadata = row
                    
                    conversation = {
                        "id": element_id,
                        "type": element_type,
                        "content": content,
                        "timestamp": created_at,
                        "session_id": session_id
                    }
                    
                    if include_metadata and session_metadata:
                        try:
                            metadata = json.loads(session_metadata)
                            conversation["metadata"] = {
                                "persona": metadata.get("active_persona", {}).get("name"),
                                "model": metadata.get("model"),
                                "settings": metadata.get("settings", {})
                            }
                        except (json.JSONDecodeError, AttributeError):
                            pass
                    
                    conversations.append(conversation)
            
            return conversations
            
        except Exception as e:
            app_logger.error(f"会話履歴取得エラー: {e}")
            return []
    
    async def _export_as_json(self, export_data: Dict[str, Any], user_id: str) -> str:
        """JSON形式でエクスポート"""
        export_dir = ".chainlit/exports"
        os.makedirs(export_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"workspace_{user_id}_{timestamp}.json"
        file_path = os.path.join(export_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return file_path
    
    async def _export_as_csv(self, export_data: Dict[str, Any], user_id: str) -> str:
        """CSV形式でエクスポート（複数ファイル）"""
        export_dir = ".chainlit/exports"
        os.makedirs(export_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 会話履歴CSV
        if "conversations" in export_data:
            conv_filename = f"conversations_{user_id}_{timestamp}.csv"
            conv_path = os.path.join(export_dir, conv_filename)
            
            with open(conv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "タイプ", "内容", "タイムスタンプ", "セッションID"])
                
                for conv in export_data["conversations"]:
                    writer.writerow([
                        conv.get("id", ""),
                        conv.get("type", ""),
                        conv.get("content", "").replace("\n", " "),
                        conv.get("timestamp", ""),
                        conv.get("session_id", "")
                    ])
        
        # ペルソナCSV
        if "personas" in export_data:
            persona_filename = f"personas_{user_id}_{timestamp}.csv"
            persona_path = os.path.join(export_dir, persona_filename)
            
            with open(persona_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["名前", "説明", "モデル", "Temperature", "タグ"])
                
                for persona in export_data["personas"]:
                    writer.writerow([
                        persona.get("name", ""),
                        persona.get("description", ""),
                        persona.get("model", ""),
                        persona.get("temperature", ""),
                        ",".join(persona.get("tags", []))
                    ])
        
        # 主要なファイルパスを返す（会話履歴を優先）
        return conv_path if "conversations" in export_data else persona_path
    
    async def _export_as_zip(self, export_data: Dict[str, Any], user_id: str) -> str:
        """ZIP形式で包括的エクスポート"""
        export_dir = ".chainlit/exports"
        os.makedirs(export_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"workspace_{user_id}_{timestamp}.zip"
        zip_path = os.path.join(export_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # メタデータ
            zipf.writestr("export_info.json", json.dumps(export_data["export_info"], indent=2))
            
            # 会話履歴
            if "conversations" in export_data:
                zipf.writestr("conversations.json", 
                            json.dumps(export_data["conversations"], ensure_ascii=False, indent=2))
            
            # ペルソナ
            if "personas" in export_data:
                zipf.writestr("personas.json",
                            json.dumps(export_data["personas"], ensure_ascii=False, indent=2))
            
            # 統計データ
            if "analytics" in export_data:
                zipf.writestr("analytics.json",
                            json.dumps(export_data["analytics"], ensure_ascii=False, indent=2))
        
        return zip_path
    
    async def _create_full_backup(self, user_id: str = None) -> str:
        """完全バックアップファイルの作成"""
        export_dir = ".chainlit/exports"
        os.makedirs(export_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_suffix = f"_{user_id}" if user_id else "_full"
        backup_filename = f"backup{user_suffix}_{timestamp}.zip"
        backup_path = os.path.join(export_dir, backup_filename)
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # データベースファイルのバックアップ
            if os.path.exists(self.chainlit_db_path):
                zipf.write(self.chainlit_db_path, "chainlit.db")
            
            if os.path.exists(self.analytics_db_path):
                zipf.write(self.analytics_db_path, "analytics.db")
            
            # ペルソナファイル
            if os.path.exists(self.personas_path):
                zipf.write(self.personas_path, "personas.json")
            
            # バックアップ情報
            backup_info = {
                "backup_date": datetime.now().isoformat(),
                "user_id": user_id,
                "backup_type": "full_backup",
                "included_files": ["chainlit.db", "analytics.db", "personas.json"]
            }
            zipf.writestr("backup_info.json", json.dumps(backup_info, indent=2))
        
        return backup_path
    
    async def _import_from_json(self, file_path: str, user_id: str, merge_mode: bool) -> bool:
        """JSONファイルからのインポート"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # データの妥当性チェック
            if "export_info" not in import_data:
                await ui.send_error_message("無効なエクスポートファイル形式です。")
                return False
            
            # ペルソナのインポート
            if "personas" in import_data:
                await self._import_personas(import_data["personas"], merge_mode)
            
            # 会話履歴のインポート（簡易実装）
            if "conversations" in import_data:
                app_logger.info(f"会話履歴 {len(import_data['conversations'])} 件のインポートをスキップ")
                # 注意: 会話履歴の直接インポートは複雑なため、現在は未実装
            
            return True
            
        except Exception as e:
            app_logger.error(f"JSONインポートエラー: {e}")
            return False
    
    async def _import_from_zip(self, file_path: str, user_id: str, merge_mode: bool) -> bool:
        """ZIPファイルからのインポート"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(file_path, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                # ペルソナのインポート
                personas_path = os.path.join(temp_dir, "personas.json")
                if os.path.exists(personas_path):
                    with open(personas_path, 'r', encoding='utf-8') as f:
                        personas_data = json.load(f)
                    await self._import_personas(personas_data, merge_mode)
                
                return True
                
        except Exception as e:
            app_logger.error(f"ZIPインポートエラー: {e}")
            return False
    
    async def _import_personas(self, personas_data: List[Dict], merge_mode: bool):
        """ペルソナデータのインポート"""
        try:
            imported_count = 0
            
            for persona_data in personas_data:
                persona_name = persona_data.get("name", "")
                
                if merge_mode:
                    # 既存チェック
                    existing_personas = await persona_manager.get_all_personas()
                    exists = any(p.get("name") == persona_name for p in existing_personas)
                    
                    if not exists:
                        await persona_manager.create_persona(persona_data)
                        imported_count += 1
                else:
                    # 強制インポート（名前重複時は新しい名前生成）
                    await persona_manager.create_persona(persona_data)
                    imported_count += 1
            
            app_logger.info(f"ペルソナインポート完了: {imported_count}件")
            
        except Exception as e:
            app_logger.error(f"ペルソナインポートエラー: {e}")


# グローバルインスタンス
data_handler = DataHandler()