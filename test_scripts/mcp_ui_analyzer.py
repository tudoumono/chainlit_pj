#!/usr/bin/env python3
"""
MCP連携UI分析スクリプト
MCPのCipherエージェントを使ってUI分析結果を記録・検索
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


class MCPUIAnalyzer:
    def __init__(self):
        self.project_root = "/root/mywork/chainlit_pj"
        self.screenshots_dir = f"{self.project_root}/screenshots"
        self.analysis_dir = f"{self.project_root}/ui_analysis"
        os.makedirs(self.analysis_dir, exist_ok=True)
        
    def analyze_screenshot_with_claude(self, screenshot_path, context=""):
        """
        スクリーンショットをClaude（この会話内）で分析
        実際の実行時は、このファイルのパスを教えて手動で分析を依頼
        """
        analysis_prompt = f"""
        ## UIスクリーンショット分析依頼
        
        **スクリーンショット**: {screenshot_path}
        **コンテキスト**: {context}
        
        以下の観点でChainlit UIを分析してください：
        
        1. **基本UI要素**:
           - ヘッダー、サイドバー、メイン画面の表示状態
           - チャット入力欄の存在と配置
           - ボタン、アイコンの表示状態
        
        2. **設定UI**:
           - 右側の設定パネルの表示状態
           - 設定項目（モデル選択、Tools、ベクトルストア等）
           - スライダー、スイッチ、テキスト入力の動作状態
        
        3. **チャット機能**:
           - メッセージの表示形式
           - ストリーミング表示の状態
           - エラー表示の有無
        
        4. **全体的な問題点**:
           - レイアウトの崩れ
           - 文字化け
           - 色やスタイリングの問題
           - 機能的な問題の兆候
        
        5. **改善提案**:
           - UIの改善点
           - ユーザビリティの向上案
        """
        
        # 分析プロンプトをファイルに保存（手動分析用）
        analysis_file = f"{self.analysis_dir}/analysis_prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(analysis_file, "w", encoding="utf-8") as f:
            f.write(analysis_prompt)
        
        return analysis_file
    
    def create_test_checklist(self):
        """UI機能チェックリストを作成"""
        checklist = {
            "基本UI要素": {
                "ヘッダー表示": "未確認",
                "サイドバー表示": "未確認", 
                "チャット入力欄": "未確認",
                "送信ボタン": "未確認",
                "履歴表示": "未確認"
            },
            "設定UI": {
                "設定パネル表示": "未確認",
                "モデル選択": "未確認",
                "Tools機能スイッチ": "未確認",
                "Web検索設定": "未確認",
                "ファイル検索設定": "未確認",
                "ベクトルストア設定": "未確認",
                "温度設定": "未確認",
                "プロキシ設定": "未確認"
            },
            "チャット機能": {
                "メッセージ送信": "未確認",
                "ストリーミング表示": "未確認",
                "会話継続": "未確認",
                "Tools使用": "未確認",
                "エラーハンドリング": "未確認"
            },
            "アクション機能": {
                "ペルソナ作成": "未確認",
                "統計ダッシュボード": "未確認",
                "ワークスペース検索": "未確認"
            },
            "データ永続化": {
                "チャット履歴保存": "未確認",
                "設定保存": "未確認",
                "セッション復元": "未確認"
            }
        }
        
        checklist_file = f"{self.analysis_dir}/ui_checklist.json"
        with open(checklist_file, "w", encoding="utf-8") as f:
            json.dump(checklist, f, indent=2, ensure_ascii=False)
        
        return checklist_file
    
    def create_test_scenarios(self):
        """テストシナリオを作成"""
        scenarios = [
            {
                "name": "基本チャット機能テスト",
                "steps": [
                    "1. アプリにアクセス",
                    "2. 初期画面の確認",
                    "3. 「こんにちは」と入力",
                    "4. 送信ボタンクリック",
                    "5. レスポンス表示確認",
                    "6. スクリーンショット撮影"
                ],
                "expected": "正常なチャット応答とストリーミング表示"
            },
            {
                "name": "設定UI操作テスト", 
                "steps": [
                    "1. 設定パネルの表示確認",
                    "2. モデル選択ドロップダウン操作",
                    "3. Toolsスイッチの切り替え",
                    "4. 各設定項目の動作確認",
                    "5. 設定変更後のテストメッセージ送信",
                    "6. スクリーンショット撮影"
                ],
                "expected": "全設定項目の正常動作"
            },
            {
                "name": "会話継続テスト",
                "steps": [
                    "1. 「生成AIとは？」と質問",
                    "2. 回答確認",
                    "3. 「具体例を教えて」と続けて質問", 
                    "4. 前の会話を踏まえた回答確認",
                    "5. スクリーンショット撮影"
                ],
                "expected": "会話コンテキストを保持した応答"
            },
            {
                "name": "Tools機能テスト",
                "steps": [
                    "1. Web検索を有効化",
                    "2. 「今日のニュース」と質問",
                    "3. Web検索実行確認",
                    "4. 検索結果を含む回答確認",
                    "5. スクリーンショット撮影"
                ],
                "expected": "Web検索結果を含む応答"
            },
            {
                "name": "アクションボタンテスト",
                "steps": [
                    "1. アクションボタンの表示確認",
                    "2. 統計ダッシュボードボタンクリック",
                    "3. ダッシュボード表示確認",
                    "4. ペルソナ作成ボタンクリック",
                    "5. フォーム表示確認",
                    "6. スクリーンショット撮影"
                ],
                "expected": "全アクションボタンの正常動作"
            }
        ]
        
        scenarios_file = f"{self.analysis_dir}/test_scenarios.json"
        with open(scenarios_file, "w", encoding="utf-8") as f:
            json.dump(scenarios, f, indent=2, ensure_ascii=False)
        
        return scenarios_file
    
    def create_mcp_integration_guide(self):
        """MCP連携の使用ガイドを作成"""
        guide = """# MCP連携UI分析ガイド

## 概要
このガイドでは、MCPのCipherエージェントを活用してChainlit UIの機能チェックを効率的に行う方法を説明します。

## 分析手順

### 1. スクリーンショット撮影
```bash
# Chainlitアプリが起動中であることを確認
curl http://localhost:8000

# UIチェッカーでスクリーンショット撮影
python test_scripts/ui_checker.py
```

### 2. MCPエージェントでの分析
以下のようにClaude Code（この会話）で分析を依頼：

```
このスクリーンショットを分析してください: /root/mywork/chainlit_pj/screenshots/[ファイル名]

以下の観点で確認：
- UI要素の表示状態
- 設定パネルの機能
- チャット機能の動作
- 全体的な問題点
```

### 3. 結果の記録
分析結果をCipherエージェントで記録：

```python
# mcp_ui_analyzerを使って結果を構造化
analyzer = MCPUIAnalyzer()
analyzer.record_analysis_result(screenshot_path, analysis_result)
```

## 自動化されたテストシナリオ

### 基本チェック項目
- [ ] 初期画面の正常表示
- [ ] チャット入力・送信機能  
- [ ] 設定UIの表示・操作
- [ ] ストリーミング応答
- [ ] 会話継続機能
- [ ] Tools機能（Web検索・ファイル検索）
- [ ] アクションボタン
- [ ] エラーハンドリング

### 高度なテスト
- [ ] 複数ブラウザでの表示確認
- [ ] レスポンシブデザイン
- [ ] パフォーマンス測定
- [ ] セキュリティ確認

## トラブルシューティング

### よくある問題
1. **設定UIが表示されない**
   - `@cl.on_chat_resume`で`_create_settings_ui()`が呼ばれているか確認

2. **会話が継続しない**  
   - `previous_response_id`の保存・復元確認
   - OpenAI Responses APIの`store: true`設定確認

3. **Tools機能が動作しない**
   - tools_config.jsonの設定確認
   - APIキーの設定確認

## MCPエージェント活用のメリット

1. **自動記録**: 分析結果を自動でCipherに記録
2. **過去分析の検索**: 以前の分析結果を簡単に参照
3. **パターン認識**: 類似問題の自動検出
4. **継続的改善**: 分析履歴からUI改善傾向を把握
"""

        guide_file = f"{self.analysis_dir}/mcp_integration_guide.md"
        with open(guide_file, "w", encoding="utf-8") as f:
            f.write(guide)
            
        return guide_file

    def record_analysis_result(self, screenshot_path, analysis_result, test_scenario=""):
        """分析結果を記録（MCP Cipherエージェント用）"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "screenshot_path": screenshot_path,
            "test_scenario": test_scenario,
            "analysis_result": analysis_result,
            "issues_found": [],
            "recommendations": []
        }
        
        # JSON形式で記録
        record_file = f"{self.analysis_dir}/analysis_record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(record_file, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        
        return record_file

    def setup_analysis_environment(self):
        """分析環境のセットアップ"""
        print("🔧 MCP UI分析環境をセットアップしています...")
        
        # 必要なディレクトリを作成
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.analysis_dir, exist_ok=True)
        
        # チェックリスト作成
        checklist_file = self.create_test_checklist()
        print(f"✅ チェックリスト作成: {checklist_file}")
        
        # テストシナリオ作成
        scenarios_file = self.create_test_scenarios()
        print(f"✅ テストシナリオ作成: {scenarios_file}")
        
        # MCP連携ガイド作成
        guide_file = self.create_mcp_integration_guide()
        print(f"✅ MCPガイド作成: {guide_file}")
        
        print("\n🚀 セットアップ完了！以下の手順で分析を開始してください：")
        print("1. Chainlitアプリを起動")
        print("2. python test_scripts/ui_checker.py でスクリーンショット撮影")
        print("3. Claude Codeでスクリーンショットを分析依頼")
        print("4. 分析結果をCipherエージェントで記録")
        
        return {
            "checklist": checklist_file,
            "scenarios": scenarios_file, 
            "guide": guide_file
        }


if __name__ == "__main__":
    analyzer = MCPUIAnalyzer()
    result = analyzer.setup_analysis_environment()
    print(f"\n📁 分析ファイル: {analyzer.analysis_dir}")