#!/usr/bin/env python3
"""
Chainlit UI機能チェックスクリプト
MCP連携でClaude Codeによる自動UI分析
"""

import time
import subprocess
import requests
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime


class ChainlitUIChecker:
    def __init__(self, chainlit_url="http://localhost:8000"):
        self.chainlit_url = chainlit_url
        self.screenshot_dir = "/root/mywork/chainlit_pj/screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
    def setup_driver(self):
        """Selenium WebDriverを設定"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
    def check_app_status(self):
        """Chainlitアプリの起動状況確認"""
        try:
            response = requests.get(self.chainlit_url, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def capture_screenshot(self, filename_suffix=""):
        """スクリーンショットを撮影"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chainlit_ui_{timestamp}{filename_suffix}.png"
        filepath = os.path.join(self.screenshot_dir, filename)
        
        self.driver.save_screenshot(filepath)
        return filepath
    
    def test_ui_elements(self):
        """包括的UI要素テスト"""
        test_results = {}
        
        # 1. 基本UIの読み込み
        start_time = time.time()
        self.driver.get(self.chainlit_url)
        time.sleep(5)  # 読み込み待機
        load_time = time.time() - start_time
        test_results["load_time"] = load_time
        
        # 初期画面のスクリーンショット
        test_results["initial_load"] = self.capture_screenshot("_initial")
        
        # 2. 基本UI要素の詳細チェック
        ui_elements = {
            "chat_input": ["input[placeholder*='メッセージ'], textarea[placeholder*='メッセージ'], input, textarea"],
            "send_button": ["button[type='submit'], button:contains('送信'), [aria-label*='送信']"],
            "header": ["header, .header, [role='banner']"],
            "sidebar": [".sidebar, [role='complementary'], .chat-history"],
            "settings_panel": [".settings, .chat-settings, [data-testid*='settings']"],
            "model_selector": ["select, .select, [role='combobox']"],
            "tools_switches": ["input[type='checkbox'], .switch, [role='switch']"],
            "action_buttons": ["button:contains('ペルソナ'), button:contains('統計'), button:contains('検索')"]
        }
        
        for element_name, selectors in ui_elements.items():
            found = False
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        found = True
                        test_results[f"{element_name}_count"] = len(elements)
                        break
                except:
                    continue
            test_results[f"{element_name}_exists"] = found
        
        # 3. 設定項目の詳細確認
        settings_items = [
            "Model", "Tools", "Web検索", "ファイル検索", 
            "ベクトル", "温度", "プロキシ"
        ]
        
        for item in settings_items:
            try:
                # テキスト、ラベル、プレースホルダーで検索
                elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{item}')]")
                test_results[f"settings_{item}_exists"] = len(elements) > 0
            except:
                test_results[f"settings_{item}_exists"] = False
        
        # 4. レスポンシブデザインテスト
        window_sizes = [
            {"name": "desktop", "size": (1920, 1080)},
            {"name": "laptop", "size": (1366, 768)},
            {"name": "tablet", "size": (768, 1024)}
        ]
        
        for window in window_sizes:
            try:
                self.driver.set_window_size(*window["size"])
                time.sleep(2)
                test_results[f"responsive_{window['name']}"] = self.capture_screenshot(f"_{window['name']}")
            except Exception as e:
                test_results[f"responsive_{window['name']}_error"] = str(e)
        
        # 元の画面サイズに戻す
        self.driver.set_window_size(1920, 1080)
        
        return test_results
    
    def test_chat_functionality(self):
        """チャット機能のテスト"""
        test_results = {}
        
        # テストメッセージを送信
        try:
            # 入力欄を見つける
            chat_input = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input, textarea"))
            )
            
            # テストメッセージを入力
            test_message = "UIテスト: 機能チェック中"
            chat_input.send_keys(test_message)
            
            # 送信前のスクリーンショット
            test_results["before_send"] = self.capture_screenshot("_before_send")
            
            # Enterキーまたは送信ボタンを押す
            chat_input.send_keys("\n")
            time.sleep(2)
            
            # 送信後のスクリーンショット
            test_results["after_send"] = self.capture_screenshot("_after_send")
            
            # レスポンス待機
            time.sleep(10)
            
            # レスポンス後のスクリーンショット
            test_results["with_response"] = self.capture_screenshot("_with_response")
            
            test_results["chat_test_success"] = True
            
        except Exception as e:
            test_results["chat_test_success"] = False
            test_results["error"] = str(e)
            test_results["error_screenshot"] = self.capture_screenshot("_error")
        
        return test_results
    
    def generate_report(self, ui_results, chat_results):
        """テストレポート生成"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "chainlit_url": self.chainlit_url,
            "app_status": self.check_app_status(),
            "ui_tests": ui_results,
            "chat_tests": chat_results,
            "screenshots_location": self.screenshot_dir
        }
        
        # JSONレポートを保存
        report_file = os.path.join(self.screenshot_dir, "test_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report
    
    def run_full_test(self):
        """完全なUIテストを実行"""
        print("🔧 Chainlit UIテスト開始...")
        
        if not self.check_app_status():
            print("❌ Chainlitアプリが起動していません")
            return None
        
        try:
            self.setup_driver()
            
            print("📸 UI要素のテスト...")
            ui_results = self.test_ui_elements()
            
            print("💬 チャット機能のテスト...")
            chat_results = self.test_chat_functionality()
            
            print("📋 レポート生成...")
            report = self.generate_report(ui_results, chat_results)
            
            return report
            
        finally:
            if hasattr(self, 'driver'):
                self.driver.quit()


if __name__ == "__main__":
    checker = ChainlitUIChecker()
    result = checker.run_full_test()
    
    if result:
        print("✅ UIテスト完了")
        print(f"📁 スクリーンショット: {checker.screenshot_dir}")
        print(f"📄 レポート: {os.path.join(checker.screenshot_dir, 'test_report.json')}")
    else:
        print("❌ UIテスト失敗")