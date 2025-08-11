#!/usr/bin/env python
"""
データレイヤーの状態を確認して起動するスクリプト
"""

import os
import sys
import subprocess


def check_packages():
    """パッケージの状態を確認"""
    packages_status = {}
    
    # 必須パッケージ
    required = ["chainlit", "openai", "aiosqlite", "python-dotenv"]
    # オプションパッケージ
    optional = ["chainlit-sqlalchemy"]
    
    for package in required + optional:
        try:
            __import__(package.replace("-", "_"))
            packages_status[package] = "✅"
        except ImportError:
            packages_status[package] = "❌"
    
    return packages_status


def check_data_layer():
    """データレイヤーの状態を確認"""
    print("\n📊 データレイヤーの確認...")
    
    # SQLAlchemyデータレイヤーを確認
    try:
        from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
        print("✅ SQLAlchemyデータレイヤーが利用可能")
        return "sqlalchemy"
    except ImportError:
        print("⚠️ SQLAlchemyデータレイヤーが利用できません")
    
    # シンプルデータレイヤーを確認
    try:
        import simple_data_layer
        print("✅ シンプルなインメモリデータレイヤーが利用可能")
        return "simple"
    except ImportError:
        print("⚠️ シンプルデータレイヤーが利用できません")
    
    return None


def install_missing_packages():
    """不足しているパッケージをインストール"""
    print("\n📦 不足しているパッケージをインストールしますか？")
    
    response = input("インストールする場合は 'y' を入力: ").lower()
    if response == 'y':
        print("\n📥 chainlit-sqlalchemyをインストール中...")
        subprocess.run([sys.executable, "-m", "pip", "install", "chainlit-sqlalchemy[sqlite]"])
        print("✅ インストール完了")
        return True
    return False


def main():
    """メイン処理"""
    print("=" * 60)
    print("🚀 AI Workspace 起動前チェック")
    print("=" * 60)
    
    # パッケージの状態を確認
    print("\n📋 パッケージの状態:")
    packages = check_packages()
    for package, status in packages.items():
        print(f"  {status} {package}")
    
    # データレイヤーを確認
    data_layer = check_data_layer()
    
    if data_layer is None:
        print("\n⚠️ データレイヤーが設定されていません")
        print("履歴機能を有効にするには、以下のいずれかが必要です：")
        print("  1. pip install chainlit-sqlalchemy[sqlite] （推奨）")
        print("  2. simple_data_layer.py を使用（インメモリ、再起動で消える）")
        
        if install_missing_packages():
            data_layer = check_data_layer()
    
    # 起動確認
    print("\n" + "=" * 60)
    if data_layer:
        print("✅ 準備完了！")
        if data_layer == "sqlalchemy":
            print("📊 SQLAlchemyデータレイヤーを使用（永続化あり）")
        else:
            print("📊 シンプルデータレイヤーを使用（インメモリ）")
        
        print("\n🚀 アプリケーションを起動します...")
        print("=" * 60)
        
        # Chainlitを起動
        subprocess.run(["chainlit", "run", "app.py"])
    else:
        print("❌ データレイヤーが設定されていないため、起動できません")
        print("上記の手順でパッケージをインストールしてください")
        sys.exit(1)


if __name__ == "__main__":
    main()
