#!/usr/bin/env python
"""
環境チェックと起動
必要な設定を確認してから起動
"""

import os
import sys
import subprocess

def check_environment():
    """環境をチェック"""
    print("🔍 環境チェック中...")
    print()
    
    issues = []
    warnings = []
    
    # 1. simple_data_layer.pyの確認
    if os.path.exists("simple_data_layer.py"):
        print("✅ simple_data_layer.py が存在")
    else:
        issues.append("simple_data_layer.py が見つかりません")
    
    # 2. .envファイルの確認
    if os.path.exists(".env"):
        print("✅ .env ファイルが存在")
        
        # 認証設定を確認
        with open(".env", "r") as f:
            env_content = f.read()
            if "CHAINLIT_AUTH_TYPE" in env_content and not env_content.find("# CHAINLIT_AUTH_TYPE") >= 0:
                print("✅ 認証が有効")
            else:
                warnings.append("認証が無効になっています（履歴UIが表示されない可能性があります）")
    else:
        issues.append(".env ファイルが見つかりません")
    
    # 3. app.pyの確認
    if os.path.exists("app.py"):
        print("✅ app.py が存在")
    else:
        issues.append("app.py が見つかりません")
    
    # 4. utilsディレクトリの確認
    if os.path.exists("utils"):
        print("✅ utils ディレクトリが存在")
    else:
        issues.append("utils ディレクトリが見つかりません")
    
    # 5. auth.pyの確認
    if os.path.exists("auth.py"):
        print("✅ auth.py が存在")
    else:
        warnings.append("auth.py が見つかりません（認証が動作しない可能性があります）")
    
    print()
    
    # 結果を表示
    if issues:
        print("❌ 以下の問題を解決してください:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    if warnings:
        print("⚠️  警告:")
        for warning in warnings:
            print(f"   - {warning}")
        print()
    
    print("✅ 環境チェック完了")
    return True


def install_packages():
    """必要なパッケージをインストール"""
    print("📦 パッケージをチェック中...")
    
    required = ["chainlit", "openai", "python-dotenv", "aiosqlite"]
    missing = []
    
    for package in required:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"📥 不足パッケージをインストール: {', '.join(missing)}")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing)
        print("✅ インストール完了")
    else:
        print("✅ 必要なパッケージはすべてインストール済み")
    
    print()


def main():
    print("=" * 60)
    print("🚀 AI Workspace - 環境チェック & 起動")
    print("=" * 60)
    print()
    
    # パッケージをインストール
    install_packages()
    
    # 環境をチェック
    if not check_environment():
        print()
        print("❌ 環境に問題があります。上記の問題を解決してください。")
        return 1
    
    print()
    print("=" * 60)
    print("📊 起動設定")
    print("=" * 60)
    print()
    print("データレイヤー: インメモリ版（SimpleDataLayer）")
    print("履歴UI: 有効（セッション中のみ保持）")
    print("認証: admin / admin123")
    print()
    print("=" * 60)
    print()
    
    # 起動確認
    response = input("起動しますか？ (y/n): ").lower()
    if response != 'y':
        print("キャンセルしました")
        return 0
    
    print()
    print("🚀 アプリケーションを起動中...")
    print("🌐 ブラウザで http://localhost:8000 を開いてください")
    print()
    
    try:
        subprocess.run(["chainlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("\n👋 アプリケーションを終了しました")
    except Exception as e:
        print(f"❌ エラー: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
