#!/usr/bin/env python3
"""
包括的テストケース定義
Chainlit多機能AIワークスペースの全機能を網羅的にテスト
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any


class ComprehensiveTestSuite:
    def __init__(self):
        self.test_categories = {
            "UI_RENDERING": "UI表示・レンダリング",
            "USER_INTERACTION": "ユーザー操作",
            "CHAT_FUNCTIONALITY": "チャット機能",
            "AI_INTEGRATION": "AI統合機能", 
            "DATA_PERSISTENCE": "データ永続化",
            "SETTINGS_MANAGEMENT": "設定管理",
            "TOOLS_INTEGRATION": "ツール統合",
            "ERROR_HANDLING": "エラーハンドリング",
            "PERFORMANCE": "パフォーマンス",
            "SECURITY": "セキュリティ",
            "ACCESSIBILITY": "アクセシビリティ",
            "CROSS_BROWSER": "クロスブラウザ対応"
        }

    def get_ui_rendering_tests(self) -> List[Dict[str, Any]]:
        """UI表示・レンダリングテスト"""
        return [
            {
                "id": "UI_001",
                "name": "初期画面表示テスト",
                "category": "UI_RENDERING",
                "priority": "HIGH",
                "description": "アプリ起動時の基本UI要素の表示確認",
                "preconditions": ["Chainlitアプリが起動済み", "認証済み"],
                "steps": [
                    "1. ブラウザでアプリにアクセス",
                    "2. 3秒間読み込み待機",
                    "3. スクリーンショット撮影"
                ],
                "expected_results": [
                    "ヘッダーが表示される",
                    "サイドバー（履歴）が表示される", 
                    "メインチャット画面が表示される",
                    "チャット入力欄が表示される",
                    "送信ボタンが表示される",
                    "設定パネルが表示される"
                ],
                "test_data": {},
                "assertions": [
                    "header_exists",
                    "sidebar_exists", 
                    "chat_input_exists",
                    "send_button_exists",
                    "settings_panel_exists"
                ]
            },
            {
                "id": "UI_002", 
                "name": "設定パネル表示テスト",
                "category": "UI_RENDERING",
                "priority": "HIGH",
                "description": "設定パネルの全項目表示確認",
                "steps": [
                    "1. 設定パネルエリアの確認",
                    "2. 各設定項目のラベル確認",
                    "3. 設定値の初期表示確認"
                ],
                "expected_results": [
                    "「OpenAI - Model」ドロップダウンが表示",
                    "「Tools機能 - 有効/無効」スイッチが表示",
                    "「Web検索 - 有効/無効」スイッチが表示", 
                    "「ファイル検索 - 有効/無効」スイッチが表示",
                    "ベクトルストア設定項目群が表示",
                    "温度設定スライダーが表示",
                    "プロキシ設定項目群が表示"
                ]
            },
            {
                "id": "UI_003",
                "name": "レスポンシブデザインテスト", 
                "category": "UI_RENDERING",
                "priority": "MEDIUM",
                "description": "画面サイズ変更時のUI適応確認",
                "steps": [
                    "1. 画面サイズ 1920x1080 で表示確認",
                    "2. 画面サイズ 1366x768 で表示確認", 
                    "3. 画面サイズ 768x1024 で表示確認（タブレット）",
                    "4. 各サイズでスクリーンショット撮影"
                ],
                "expected_results": [
                    "全サイズでUIが崩れない",
                    "設定パネルが適切にリサイズ", 
                    "チャット入力欄が使用可能",
                    "スクロールが正常動作"
                ]
            }
        ]

    def get_user_interaction_tests(self) -> List[Dict[str, Any]]:
        """ユーザー操作テスト"""
        return [
            {
                "id": "INT_001",
                "name": "基本チャット入力テスト",
                "category": "USER_INTERACTION", 
                "priority": "HIGH",
                "description": "チャット入力欄での基本操作確認",
                "steps": [
                    "1. チャット入力欄をクリック",
                    "2. テストメッセージを入力: 'こんにちは、テストです'",
                    "3. Enterキーで送信",
                    "4. 送信後の状態確認"
                ],
                "expected_results": [
                    "入力欄にフォーカスが当たる",
                    "入力文字が正しく表示される",
                    "Enterキーで送信される", 
                    "送信後に入力欄がクリアされる",
                    "ユーザーメッセージがチャット画面に表示される"
                ],
                "test_data": {
                    "message": "こんにちは、テストです"
                }
            },
            {
                "id": "INT_002",
                "name": "設定項目操作テスト",
                "category": "USER_INTERACTION",
                "priority": "HIGH", 
                "description": "各設定項目の操作確認",
                "steps": [
                    "1. モデル選択ドロップダウンをクリック",
                    "2. 'gpt-4o'を選択",
                    "3. Toolsスイッチをオン/オフ切り替え",
                    "4. Web検索スイッチをオン/オフ切り替え",
                    "5. 温度スライダーを0.5に設定",
                    "6. 設定変更の反映確認"
                ],
                "expected_results": [
                    "ドロップダウンが開く",
                    "選択したモデルが反映される",
                    "スイッチ状態が視覚的に変わる",
                    "スライダー値が更新される",
                    "設定変更通知が表示される"
                ]
            },
            {
                "id": "INT_003",
                "name": "アクションボタンテスト",
                "category": "USER_INTERACTION",
                "priority": "HIGH",
                "description": "ウェルカムメッセージのアクションボタン操作",
                "steps": [
                    "1. 「🎭 新しいペルソナ作成」ボタンクリック",
                    "2. ペルソナ作成フォーム表示確認",
                    "3. 「📊 統計ダッシュボード」ボタンクリック",
                    "4. ダッシュボード表示確認",
                    "5. 「🔍 ワークスペース検索」ボタンクリック",
                    "6. 検索画面表示確認"
                ],
                "expected_results": [
                    "各ボタンクリック時に対応画面が表示される",
                    "フォームやダッシュボードが正しく描画される",
                    "戻る機能が正常動作する"
                ]
            }
        ]

    def get_chat_functionality_tests(self) -> List[Dict[str, Any]]:
        """チャット機能テスト"""
        return [
            {
                "id": "CHAT_001",
                "name": "基本応答テスト",
                "category": "CHAT_FUNCTIONALITY",
                "priority": "HIGH",
                "description": "シンプルなメッセージに対する基本応答",
                "steps": [
                    "1. 「こんにちは」と送信",
                    "2. 応答待機（最大30秒）",
                    "3. 応答内容確認",
                    "4. ストリーミング表示確認"
                ],
                "expected_results": [
                    "30秒以内に応答が開始される",
                    "ストリーミング形式で文字が表示される", 
                    "完全な文章が表示される",
                    "エラーが発生しない"
                ],
                "test_data": {
                    "message": "こんにちは"
                }
            },
            {
                "id": "CHAT_002", 
                "name": "会話継続テスト",
                "category": "CHAT_FUNCTIONALITY",
                "priority": "HIGH",
                "description": "OpenAI Responses APIのprevious_response_id機能確認",
                "steps": [
                    "1. '私の名前はテスト太郎です'と送信",
                    "2. 応答確認",
                    "3. '私の名前は何ですか？'と送信",
                    "4. 前の会話を踏まえた応答確認"
                ],
                "expected_results": [
                    "2回目の質問で「テスト太郎」と正しく回答される",
                    "会話コンテキストが保持されている"
                ],
                "test_data": {
                    "messages": [
                        "私の名前はテスト太郎です",
                        "私の名前は何ですか？"
                    ]
                }
            },
            {
                "id": "CHAT_003",
                "name": "長文応答テスト",
                "category": "CHAT_FUNCTIONALITY", 
                "priority": "MEDIUM",
                "description": "長文応答時のストリーミング表示確認",
                "steps": [
                    "1. '人工知能について詳しく説明してください'と送信",
                    "2. 長文応答のストリーミング確認",
                    "3. 全文表示完了確認"
                ],
                "expected_results": [
                    "長文がスムーズにストリーミング表示される",
                    "表示が途切れない",
                    "最終的に完全な応答が表示される"
                ]
            }
        ]

    def get_ai_integration_tests(self) -> List[Dict[str, Any]]:
        """AI統合機能テスト"""
        return [
            {
                "id": "AI_001",
                "name": "OpenAI APIキー認証テスト",
                "category": "AI_INTEGRATION",
                "priority": "HIGH", 
                "description": "APIキー設定と認証状態確認",
                "steps": [
                    "1. 設定からAPIキー状態確認",
                    "2. テストメッセージで応答確認",
                    "3. 認証エラーの有無確認"
                ],
                "expected_results": [
                    "APIキーが正しく設定されている",
                    "認証エラーが発生しない",
                    "正常な応答が得られる"
                ]
            },
            {
                "id": "AI_002",
                "name": "モデル切り替えテスト", 
                "category": "AI_INTEGRATION",
                "priority": "HIGH",
                "description": "異なるOpenAIモデル間の切り替え確認",
                "steps": [
                    "1. gpt-4o-miniを選択してテストメッセージ送信",
                    "2. gpt-4oに切り替えてテストメッセージ送信",
                    "3. 応答の違いや速度差確認"
                ],
                "expected_results": [
                    "各モデルで正常に応答される",
                    "モデル切り替えがエラーなく実行される",
                    "設定変更が即座に反映される"
                ]
            },
            {
                "id": "AI_003",
                "name": "システムプロンプト機能テスト",
                "category": "AI_INTEGRATION",
                "priority": "MEDIUM",
                "description": "ペルソナ機能でのシステムプロンプト適用確認",
                "steps": [
                    "1. ペルソナ作成画面を開く",
                    "2. '関西弁で話すアシスタント'ペルソナを作成",
                    "3. ペルソナ選択後にテストメッセージ送信",
                    "4. 関西弁での応答確認"
                ],
                "expected_results": [
                    "ペルソナが正しく作成される",
                    "システムプロンプトが適用される",
                    "指定された口調で応答される"
                ]
            }
        ]

    def get_tools_integration_tests(self) -> List[Dict[str, Any]]:
        """ツール統合テスト"""
        return [
            {
                "id": "TOOLS_001",
                "name": "Web検索機能テスト",
                "category": "TOOLS_INTEGRATION",
                "priority": "HIGH",
                "description": "Web検索ツールの動作確認",
                "steps": [
                    "1. Web検索をONに設定",
                    "2. '今日の天気は？'と質問",
                    "3. Web検索実行確認",
                    "4. 検索結果を含む応答確認"
                ],
                "expected_results": [
                    "Web検索が実行される",
                    "最新の天気情報が含まれた応答",
                    "検索ソース情報が表示される"
                ]
            },
            {
                "id": "TOOLS_002", 
                "name": "ファイル検索機能テスト",
                "category": "TOOLS_INTEGRATION",
                "priority": "HIGH",
                "description": "ベクトルストア検索機能確認",
                "steps": [
                    "1. ファイル検索をONに設定",
                    "2. ベクトルストアIDを設定",
                    "3. ドキュメント関連の質問を送信",
                    "4. ベクトル検索結果確認"
                ],
                "expected_results": [
                    "ベクトル検索が実行される",
                    "関連ドキュメント情報が含まれた応答",
                    "検索チャンク情報が表示される"
                ]
            },
            {
                "id": "TOOLS_003",
                "name": "ツール設定永続化テスト",
                "category": "TOOLS_INTEGRATION", 
                "priority": "MEDIUM",
                "description": "ツール設定の保存・復元確認",
                "steps": [
                    "1. 各ツール設定を変更",
                    "2. ブラウザをリロード",
                    "3. 設定値の復元確認",
                    "4. 新しいチャットでの設定確認"
                ],
                "expected_results": [
                    "設定がセッション間で保持される",
                    "チャット再開時も設定が維持される"
                ]
            }
        ]

    def get_data_persistence_tests(self) -> List[Dict[str, Any]]:
        """データ永続化テスト"""
        return [
            {
                "id": "DATA_001",
                "name": "チャット履歴保存テスト",
                "category": "DATA_PERSISTENCE",
                "priority": "HIGH",
                "description": "会話履歴のSQLite保存確認",
                "steps": [
                    "1. 複数のメッセージを送信",
                    "2. ブラウザタブを閉じる",
                    "3. 新しいタブでアクセス",
                    "4. 履歴の表示確認"
                ],
                "expected_results": [
                    "サイドバーに会話履歴が表示される",
                    "過去の会話が正しく復元される",
                    "メッセージの順序が保持される"
                ]
            },
            {
                "id": "DATA_002",
                "name": "設定データ永続化テスト",
                "category": "DATA_PERSISTENCE",
                "priority": "HIGH", 
                "description": "ユーザー設定の永続化確認",
                "steps": [
                    "1. 全設定項目をデフォルト以外に変更",
                    "2. アプリを再起動",
                    "3. 設定値の復元確認"
                ],
                "expected_results": [
                    "全設定項目が変更値で復元される",
                    "ベクトルストアIDが保持される",
                    "モデル選択が保持される"
                ]
            },
            {
                "id": "DATA_003",
                "name": "会話再開機能テスト",
                "category": "DATA_PERSISTENCE",
                "priority": "HIGH",
                "description": "OpenAI previous_response_id機能との連携",
                "steps": [
                    "1. 会話を開始して複数やり取り",
                    "2. 一度ブラウザを閉じる", 
                    "3. 同じスレッドを再開",
                    "4. 会話継続の確認"
                ],
                "expected_results": [
                    "過去の会話コンテキストが保持される",
                    "OpenAI側でも会話が継続される",
                    "previous_response_idが正しく復元される"
                ]
            }
        ]

    def get_error_handling_tests(self) -> List[Dict[str, Any]]:
        """エラーハンドリングテスト"""
        return [
            {
                "id": "ERROR_001",
                "name": "APIエラーハンドリングテスト",
                "category": "ERROR_HANDLING",
                "priority": "HIGH",
                "description": "OpenAI APIエラー時の適切な処理確認",
                "steps": [
                    "1. 無効なAPIキーを設定",
                    "2. メッセージを送信",
                    "3. エラーメッセージの表示確認",
                    "4. 正常なAPIキーに戻して回復確認"
                ],
                "expected_results": [
                    "わかりやすいエラーメッセージが表示",
                    "アプリがクラッシュしない",
                    "設定修正後に正常動作に戻る"
                ]
            },
            {
                "id": "ERROR_002",
                "name": "ネットワークエラーテスト",
                "category": "ERROR_HANDLING", 
                "priority": "MEDIUM",
                "description": "ネットワーク切断時の挙動確認",
                "steps": [
                    "1. ネットワークを切断",
                    "2. メッセージ送信を試行",
                    "3. 接続エラーメッセージ確認",
                    "4. ネットワーク復旧後の自動回復確認"
                ],
                "expected_results": [
                    "接続エラーが適切に表示される",
                    "ユーザーに再試行を促す",
                    "復旧後は正常動作する"
                ]
            }
        ]

    def get_performance_tests(self) -> List[Dict[str, Any]]:
        """パフォーマンステスト"""
        return [
            {
                "id": "PERF_001", 
                "name": "初期読み込み速度テスト",
                "category": "PERFORMANCE",
                "priority": "MEDIUM",
                "description": "アプリ初期読み込み時間測定",
                "steps": [
                    "1. ブラウザキャッシュをクリア",
                    "2. アプリにアクセス開始時刻記録",
                    "3. 完全読み込み完了時刻記録", 
                    "4. 読み込み時間算出"
                ],
                "expected_results": [
                    "初期読み込み時間が5秒以内",
                    "UIが段階的に表示される",
                    "ローディング表示が適切に動作"
                ],
                "performance_criteria": {
                    "max_load_time": 5.0,
                    "acceptable_load_time": 3.0
                }
            },
            {
                "id": "PERF_002",
                "name": "応答速度テスト",
                "category": "PERFORMANCE",
                "priority": "HIGH",
                "description": "AI応答の開始時間測定",
                "steps": [
                    "1. メッセージ送信時刻記録",
                    "2. 応答開始時刻記録",
                    "3. 応答完了時刻記録",
                    "4. 各時間を算出"
                ],
                "expected_results": [
                    "応答開始まで3秒以内",
                    "ストリーミング表示が滑らか", 
                    "完了まで30秒以内"
                ],
                "performance_criteria": {
                    "max_response_start": 3.0,
                    "max_response_complete": 30.0
                }
            }
        ]

    def get_security_tests(self) -> List[Dict[str, Any]]:
        """セキュリティテスト"""
        return [
            {
                "id": "SEC_001",
                "name": "APIキー保護テスト",
                "category": "SECURITY", 
                "priority": "HIGH",
                "description": "APIキーの適切な保護確認",
                "steps": [
                    "1. ブラウザ開発者ツールでNetwork監視",
                    "2. メッセージを送信",
                    "3. APIキーが平文で送信されていないか確認",
                    "4. ローカルストレージでの保存状態確認"
                ],
                "expected_results": [
                    "APIキーが適切に隠蔽されている",
                    "HTTPSで暗号化通信されている",
                    "ブラウザに平文保存されていない"
                ]
            },
            {
                "id": "SEC_002",
                "name": "入力サニタイゼーションテスト",
                "category": "SECURITY",
                "priority": "MEDIUM",
                "description": "悪意のある入力に対する防御確認",
                "steps": [
                    "1. HTMLタグを含む入力: '<script>alert(1)</script>'",
                    "2. SQL特殊文字: '; DROP TABLE--'",
                    "3. 極端に長い文字列入力",
                    "4. 特殊文字・絵文字入力"
                ],
                "expected_results": [
                    "スクリプト実行されない",
                    "SQLインジェクションが防御される",
                    "長い入力でクラッシュしない",
                    "特殊文字が適切に処理される"
                ]
            }
        ]

    def generate_comprehensive_test_suite(self) -> Dict[str, Any]:
        """包括的テストスイートを生成"""
        test_suite = {
            "metadata": {
                "name": "Chainlit多機能AIワークスペース 包括的テストスイート",
                "version": "1.0.0",
                "created": datetime.now().isoformat(),
                "total_categories": len(self.test_categories),
                "description": "Chainlitアプリケーションの全機能を網羅的にテストするためのテストスイート"
            },
            "categories": self.test_categories,
            "test_cases": {}
        }
        
        # 各カテゴリのテストケースを追加
        all_tests = []
        all_tests.extend(self.get_ui_rendering_tests())
        all_tests.extend(self.get_user_interaction_tests())
        all_tests.extend(self.get_chat_functionality_tests()) 
        all_tests.extend(self.get_ai_integration_tests())
        all_tests.extend(self.get_tools_integration_tests())
        all_tests.extend(self.get_data_persistence_tests())
        all_tests.extend(self.get_error_handling_tests())
        all_tests.extend(self.get_performance_tests())
        all_tests.extend(self.get_security_tests())
        
        # カテゴリ別に整理
        for test in all_tests:
            category = test["category"]
            if category not in test_suite["test_cases"]:
                test_suite["test_cases"][category] = []
            test_suite["test_cases"][category].append(test)
        
        # 統計情報を追加
        test_suite["statistics"] = {
            "total_tests": len(all_tests),
            "high_priority": len([t for t in all_tests if t.get("priority") == "HIGH"]),
            "medium_priority": len([t for t in all_tests if t.get("priority") == "MEDIUM"]),
            "low_priority": len([t for t in all_tests if t.get("priority") == "LOW"]),
            "by_category": {cat: len(test_suite["test_cases"][cat]) for cat in test_suite["test_cases"]}
        }
        
        return test_suite

    def save_test_suite(self, output_dir: str = "/root/mywork/chainlit_pj/test_scripts"):
        """テストスイートをファイルに保存"""
        os.makedirs(output_dir, exist_ok=True)
        
        test_suite = self.generate_comprehensive_test_suite()
        
        # JSONファイルに保存
        json_file = os.path.join(output_dir, "comprehensive_test_suite.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(test_suite, f, indent=2, ensure_ascii=False)
        
        # Markdown形式のレポートも生成
        md_file = os.path.join(output_dir, "test_suite_report.md")
        self._generate_markdown_report(test_suite, md_file)
        
        return {
            "json_file": json_file,
            "markdown_file": md_file,
            "total_tests": test_suite["statistics"]["total_tests"]
        }

    def _generate_markdown_report(self, test_suite: Dict[str, Any], output_file: str):
        """Markdown形式のテストレポートを生成"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# {test_suite['metadata']['name']}\n\n")
            f.write(f"**バージョン**: {test_suite['metadata']['version']}  \n")
            f.write(f"**作成日**: {test_suite['metadata']['created']}  \n")
            f.write(f"**総テスト数**: {test_suite['statistics']['total_tests']}  \n\n")
            
            # 統計情報
            f.write("## 📊 テスト統計\n\n")
            f.write("| 優先度 | テスト数 |\n")
            f.write("|--------|----------|\n")
            f.write(f"| HIGH | {test_suite['statistics']['high_priority']} |\n")
            f.write(f"| MEDIUM | {test_suite['statistics']['medium_priority']} |\n")
            f.write(f"| LOW | {test_suite['statistics']['low_priority']} |\n\n")
            
            # カテゴリ別統計
            f.write("## 📋 カテゴリ別テスト数\n\n")
            for cat, count in test_suite['statistics']['by_category'].items():
                cat_name = test_suite['categories'][cat]
                f.write(f"- **{cat_name}**: {count}テスト\n")
            f.write("\n")
            
            # 各カテゴリの詳細
            for category, tests in test_suite["test_cases"].items():
                category_name = test_suite["categories"][category]
                f.write(f"## 🧪 {category_name}\n\n")
                
                for test in tests:
                    priority_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
                    emoji = priority_emoji.get(test.get("priority", "LOW"), "⚪")
                    
                    f.write(f"### {emoji} {test['id']}: {test['name']}\n\n")
                    f.write(f"**説明**: {test['description']}  \n")
                    f.write(f"**優先度**: {test.get('priority', 'LOW')}  \n\n")
                    
                    # 前提条件
                    if 'preconditions' in test:
                        f.write("**前提条件**:\n")
                        for cond in test['preconditions']:
                            f.write(f"- {cond}\n")
                        f.write("\n")
                    
                    # テスト手順
                    f.write("**テスト手順**:\n")
                    for step in test['steps']:
                        f.write(f"{step}  \n")
                    f.write("\n")
                    
                    # 期待結果
                    f.write("**期待結果**:\n")
                    for result in test['expected_results']:
                        f.write(f"- {result}\n")
                    f.write("\n")
                    
                    # テストデータ
                    if 'test_data' in test and test['test_data']:
                        f.write("**テストデータ**:\n")
                        f.write("```json\n")
                        f.write(json.dumps(test['test_data'], indent=2, ensure_ascii=False))
                        f.write("\n```\n\n")
                    
                    f.write("---\n\n")


if __name__ == "__main__":
    test_suite = ComprehensiveTestSuite()
    result = test_suite.save_test_suite()
    
    print("✅ 包括的テストスイートを生成しました！")
    print(f"📁 JSONファイル: {result['json_file']}")
    print(f"📄 Markdownレポート: {result['markdown_file']}")  
    print(f"🧪 総テスト数: {result['total_tests']}")