#!/usr/bin/env python
"""
Chainlit AIワークスペース 起動スクリプト
"""

import os
import sys
from pathlib import Path

def main():
    """メイン実行関数"""
    print("=" * 60)
    print("🚀 AI Workspace - Phase 5完了版")
    print("=" * 60)
    
    # .envファイルの存在確認
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .envファイルが見つかりません")
        print("📝 .env.exampleをコピーして.envを作成してください")
        return 1
    
    # 認証情報の表示
    from dotenv import load_dotenv
    load_dotenv()
    
    auth_type = os.getenv("CHAINLIT_AUTH_TYPE")
    if auth_type == "credentials":
        print("🔐 認証: 有効")
        print("   ユーザー名: admin")
        print("   パスワード: .envファイルで設定された値")
    else:
        print("🔓 認証: 無効")
    
    print("-" * 60)
    print("📌 実装状況:")
    print("   ✅ Phase 1: 基本環境構築")
    print("   ✅ Phase 2: 設定管理機能")
    print("   ✅ Phase 3: データベース基盤")
    print("   ✅ Phase 4: 基本的なチャット機能")
    print("   ✅ Phase 5: セッション永続化の強化")
    print("-" * 60)
    
    # Chainlitの起動
    print("📡 サーバーを起動中...")
    print("🌐 ブラウザで http://localhost:8000 を開いてください")
    print("-" * 60)
    
    # chainlit runコマンドを実行
    os.system("chainlit run app.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
