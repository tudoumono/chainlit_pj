#!/usr/bin/env python
"""
安全な起動スクリプト
インメモリデータレイヤーで確実に起動
"""

import subprocess
import sys
import os

def main():
    print("=" * 60)
    print("🚀 AI Workspace - 安全モードで起動")
    print("=" * 60)
    print()
    print("📊 データレイヤー: インメモリ版")
    print("✅ 履歴UIが表示されます")
    print("⚠️  履歴はアプリ再起動で消失します")
    print()
    print("📌 ログイン情報:")
    print("   ユーザー名: admin")
    print("   パスワード: admin123")
    print()
    print("=" * 60)
    print()
    
    # simple_data_layer.pyが存在するか確認
    if not os.path.exists("simple_data_layer.py"):
        print("❌ simple_data_layer.pyが見つかりません")
        print("📝 ファイルが存在することを確認してください")
        return 1
    
    print("✅ インメモリデータレイヤーを検出")
    print("🌐 ブラウザで http://localhost:8000 を開いてください")
    print()
    
    # Chainlitを起動
    try:
        subprocess.run(["chainlit", "run", "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 アプリケーションを終了しました")
    except Exception as e:
        print(f"❌ エラー: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
