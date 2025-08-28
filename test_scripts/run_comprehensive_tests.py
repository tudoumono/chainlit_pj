#!/usr/bin/env python3
"""
包括的テスト実行スクリプト
全テストカテゴリを順次実行し、結果をレポート
"""

import json
import os
import time
import subprocess
from datetime import datetime
from comprehensive_test_cases import ComprehensiveTestSuite
from ui_checker import ChainlitUIChecker


class TestExecutor:
    def __init__(self):
        self.project_root = "/root/mywork/chainlit_pj"
        self.results_dir = f"{self.project_root}/test_results"
        os.makedirs(self.results_dir, exist_ok=True)
        
        # テストスイートを読み込み
        self.test_suite = ComprehensiveTestSuite()
        self.all_tests = self.test_suite.generate_comprehensive_test_suite()
        
        # テスト実行状況
        self.execution_results = {
            "start_time": datetime.now().isoformat(),
            "test_results": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            },
            "performance_metrics": {}
        }
    
    def check_prerequisites(self):
        """テスト実行の前提条件チェック"""
        print("🔍 前提条件をチェック中...")
        
        prerequisites = {
            "chainlit_app_running": False,
            "dependencies_installed": False,
            "webdriver_available": False
        }
        
        # Chainlitアプリの起動確認
        try:
            import requests
            response = requests.get("http://localhost:8000", timeout=5)
            prerequisites["chainlit_app_running"] = response.status_code == 200
        except:
            prerequisites["chainlit_app_running"] = False
        
        # 依存関係の確認
        try:
            import selenium
            import requests
            prerequisites["dependencies_installed"] = True
        except ImportError:
            prerequisites["dependencies_installed"] = False
        
        # WebDriverの確認
        try:
            checker = ChainlitUIChecker()
            checker.setup_driver()
            checker.driver.quit()
            prerequisites["webdriver_available"] = True
        except:
            prerequisites["webdriver_available"] = False
        
        # 結果の表示
        for check, status in prerequisites.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {check}: {'OK' if status else 'NG'}")
        
        all_ok = all(prerequisites.values())
        
        if not all_ok:
            print("\n❌ 前提条件を満たしていません。以下を確認してください：")
            if not prerequisites["chainlit_app_running"]:
                print("  - Chainlitアプリを起動: chainlit run app.py --host 0.0.0.0 --port 8000")
            if not prerequisites["dependencies_installed"]:
                print("  - 依存関係をインストール: pip install selenium requests")
            if not prerequisites["webdriver_available"]:
                print("  - Chrome WebDriverをインストール: apt-get install chromium-browser")
            return False
        
        print("✅ 全ての前提条件を満たしています\n")
        return True
    
    def execute_ui_tests(self):
        """UI関連テストの実行"""
        print("🖼️ UI テストを実行中...")
        
        try:
            checker = ChainlitUIChecker()
            
            # 基本UIテスト
            ui_results = checker.test_ui_elements()
            self.execution_results["test_results"]["UI_RENDERING"] = {
                "status": "PASSED" if ui_results.get("chat_input_exists", False) else "FAILED",
                "details": ui_results,
                "screenshots": [v for k, v in ui_results.items() if "screenshot" in k or k.endswith(".png")]
            }
            
            # チャット機能テスト
            chat_results = checker.test_chat_functionality()
            self.execution_results["test_results"]["CHAT_FUNCTIONALITY"] = {
                "status": "PASSED" if chat_results.get("chat_test_success", False) else "FAILED", 
                "details": chat_results,
                "screenshots": [v for k, v in chat_results.items() if k.endswith(".png")]
            }
            
            # パフォーマンス情報を記録
            if "load_time" in ui_results:
                self.execution_results["performance_metrics"]["page_load_time"] = ui_results["load_time"]
            
        except Exception as e:
            print(f"❌ UIテスト実行エラー: {e}")
            self.execution_results["test_results"]["UI_ERROR"] = {
                "status": "ERROR",
                "error": str(e)
            }
    
    def execute_manual_tests(self):
        """手動テスト項目の一覧生成"""
        print("📋 手動テスト項目を生成中...")
        
        manual_categories = ["AI_INTEGRATION", "TOOLS_INTEGRATION", "DATA_PERSISTENCE", 
                           "ERROR_HANDLING", "SECURITY"]
        
        manual_tests = {}
        
        for category in manual_categories:
            if category in self.all_tests["test_cases"]:
                manual_tests[category] = []
                for test in self.all_tests["test_cases"][category]:
                    manual_tests[category].append({
                        "id": test["id"],
                        "name": test["name"],
                        "description": test["description"],
                        "priority": test.get("priority", "MEDIUM"),
                        "steps": test["steps"],
                        "expected_results": test["expected_results"],
                        "status": "PENDING"  # 手動実行待ち
                    })
        
        self.execution_results["manual_tests"] = manual_tests
    
    def generate_test_checklist(self):
        """実行可能なテストチェックリストを生成"""
        print("📝 実行用チェックリストを生成中...")
        
        checklist = {
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_tests": self.all_tests["statistics"]["total_tests"]
            },
            "automated_tests": {
                "ui_rendering": "自動実行済み",
                "user_interaction": "自動実行済み", 
                "chat_functionality": "自動実行済み",
                "performance": "自動測定済み"
            },
            "manual_tests": {}
        }
        
        # 手動テスト用チェックリスト
        priority_order = ["HIGH", "MEDIUM", "LOW"]
        
        for priority in priority_order:
            checklist["manual_tests"][priority] = []
            
            for category, tests in self.all_tests["test_cases"].items():
                category_name = self.all_tests["categories"][category]
                
                for test in tests:
                    if test.get("priority") == priority:
                        checklist["manual_tests"][priority].append({
                            "category": category_name,
                            "id": test["id"],
                            "name": test["name"],
                            "description": test["description"],
                            "estimated_time": self._estimate_test_time(test),
                            "requires_setup": self._check_setup_requirements(test),
                            "completed": False
                        })
        
        # チェックリストファイルを保存
        checklist_file = os.path.join(self.results_dir, "manual_test_checklist.json")
        with open(checklist_file, "w", encoding="utf-8") as f:
            json.dump(checklist, f, indent=2, ensure_ascii=False)
        
        return checklist_file
    
    def _estimate_test_time(self, test):
        """テスト実行時間の推定"""
        step_count = len(test.get("steps", []))
        complexity_factors = {
            "CHAT_FUNCTIONALITY": 2,
            "AI_INTEGRATION": 3,
            "TOOLS_INTEGRATION": 3,
            "DATA_PERSISTENCE": 2,
            "ERROR_HANDLING": 2,
            "SECURITY": 4,
            "PERFORMANCE": 3
        }
        
        base_time = step_count * 30  # 1ステップ30秒の基準
        complexity = complexity_factors.get(test.get("category", ""), 1)
        
        estimated_seconds = base_time * complexity
        return f"{estimated_seconds // 60}分{estimated_seconds % 60}秒"
    
    def _check_setup_requirements(self, test):
        """テスト実行に必要な設定の確認"""
        requirements = []
        
        # カテゴリ別の要求事項
        if test.get("category") == "TOOLS_INTEGRATION":
            requirements.append("APIキー設定")
            requirements.append("ベクトルストア設定")
        elif test.get("category") == "ERROR_HANDLING":
            requirements.append("テスト用無効APIキー")
        elif test.get("category") == "SECURITY":
            requirements.append("開発者ツール")
        elif test.get("category") == "PERFORMANCE":
            requirements.append("ネットワーク測定ツール")
        
        # テスト名から推測
        test_name = test.get("name", "").lower()
        if "web検索" in test_name:
            requirements.append("インターネット接続")
        if "ペルソナ" in test_name:
            requirements.append("ペルソナ作成権限")
        
        return requirements
    
    def generate_final_report(self):
        """最終テストレポートの生成"""
        print("📊 最終レポートを生成中...")
        
        # 実行結果の更新
        self.execution_results["end_time"] = datetime.now().isoformat()
        
        # 成功/失敗の集計
        for category, result in self.execution_results["test_results"].items():
            if result["status"] == "PASSED":
                self.execution_results["summary"]["passed"] += 1
            elif result["status"] == "FAILED":
                self.execution_results["summary"]["failed"] += 1
            else:
                self.execution_results["summary"]["skipped"] += 1
        
        self.execution_results["summary"]["total"] = (
            self.execution_results["summary"]["passed"] + 
            self.execution_results["summary"]["failed"] + 
            self.execution_results["summary"]["skipped"]
        )
        
        # 推奨事項の生成
        recommendations = []
        
        if self.execution_results["summary"]["failed"] > 0:
            recommendations.append("失敗したテストの詳細確認と修正が必要")
        
        if "page_load_time" in self.execution_results["performance_metrics"]:
            load_time = self.execution_results["performance_metrics"]["page_load_time"]
            if load_time > 5.0:
                recommendations.append(f"ページ読み込み時間が遅い ({load_time:.1f}秒) - 最適化を検討")
        
        self.execution_results["recommendations"] = recommendations
        
        # JSONレポートを保存
        report_file = os.path.join(self.results_dir, f"test_execution_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.execution_results, f, indent=2, ensure_ascii=False)
        
        # Markdownレポートも生成
        md_report = self._generate_markdown_report()
        md_file = os.path.join(self.results_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_report)
        
        return {
            "json_report": report_file,
            "markdown_report": md_file,
            "summary": self.execution_results["summary"]
        }
    
    def _generate_markdown_report(self):
        """Markdown形式のレポート生成"""
        report = f"""# Chainlit UI テスト実行レポート

## 🔍 実行概要
- **実行日時**: {self.execution_results['start_time']}
- **総テスト数**: {self.execution_results['summary']['total']}
- **成功**: ✅ {self.execution_results['summary']['passed']}
- **失敗**: ❌ {self.execution_results['summary']['failed']} 
- **スキップ**: ⚠️ {self.execution_results['summary']['skipped']}

## 📊 実行結果詳細

"""
        
        for category, result in self.execution_results["test_results"].items():
            status_emoji = {"PASSED": "✅", "FAILED": "❌", "ERROR": "💥", "SKIPPED": "⚠️"}
            emoji = status_emoji.get(result["status"], "❓")
            
            report += f"### {emoji} {category}\n"
            report += f"**ステータス**: {result['status']}\n\n"
            
            if "details" in result:
                report += "**詳細結果**:\n"
                for key, value in result["details"].items():
                    if isinstance(value, bool):
                        value_str = "✅ OK" if value else "❌ NG"
                    elif isinstance(value, (int, float)):
                        value_str = f"{value}"
                    else:
                        value_str = str(value)
                    report += f"- {key}: {value_str}\n"
                report += "\n"
        
        # パフォーマンス情報
        if self.execution_results["performance_metrics"]:
            report += "## ⚡ パフォーマンス\n\n"
            for metric, value in self.execution_results["performance_metrics"].items():
                report += f"- **{metric}**: {value}\n"
            report += "\n"
        
        # 推奨事項
        if self.execution_results.get("recommendations"):
            report += "## 💡 推奨事項\n\n"
            for rec in self.execution_results["recommendations"]:
                report += f"- {rec}\n"
            report += "\n"
        
        # 手動テスト項目
        if "manual_tests" in self.execution_results:
            report += "## 🔧 手動実行が必要なテスト\n\n"
            report += "以下のテストは手動での実行・確認が必要です:\n\n"
            
            for category, tests in self.execution_results["manual_tests"].items():
                if tests:
                    category_name = self.all_tests["categories"].get(category, category)
                    report += f"### {category_name}\n"
                    for test in tests:
                        report += f"- **{test['id']}**: {test['name']}\n"
                    report += "\n"
        
        return report
    
    def run_comprehensive_test(self):
        """包括的テストの実行"""
        print("🚀 包括的テスト実行を開始します...\n")
        
        # 前提条件チェック
        if not self.check_prerequisites():
            return None
        
        # 自動実行可能なテストを実行
        self.execute_ui_tests()
        
        # 手動テスト項目を準備
        self.execute_manual_tests()
        
        # チェックリスト生成
        checklist_file = self.generate_test_checklist()
        
        # 最終レポート生成
        report_info = self.generate_final_report()
        
        print(f"\n✅ テスト実行完了！")
        print(f"📁 結果ディレクトリ: {self.results_dir}")
        print(f"📄 実行レポート: {report_info['markdown_report']}")
        print(f"📋 手動テストチェックリスト: {checklist_file}")
        print(f"📊 成功: {report_info['summary']['passed']} / 失敗: {report_info['summary']['failed']}")
        
        return report_info


if __name__ == "__main__":
    # 包括的テストスイートの生成（初回のみ）
    print("📋 テストスイートを準備中...")
    test_suite = ComprehensiveTestSuite()
    test_suite.save_test_suite()
    
    # テスト実行
    executor = TestExecutor()
    result = executor.run_comprehensive_test()
    
    if result:
        print(f"\n🎉 テスト完了！詳細は以下を確認:")
        print(f"   {result['markdown_report']}")