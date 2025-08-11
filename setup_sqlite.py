"""
SQLiteデータベースのテーブルを作成するスクリプト
ChainlitのSQLAlchemyDataLayerで必要なテーブルを作成
"""

import sqlite3
import os
from pathlib import Path

def create_tables():
    """ChainlitのSQLAlchemyDataLayerに必要なテーブルを作成"""
    
    # データベースパスを作成
    db_dir = Path(".chainlit")
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / "chainlit.db"
    
    print(f"📁 データベースパス: {db_path}")
    
    # SQLiteに接続
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # users テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            identifier TEXT UNIQUE NOT NULL,
            createdAt TEXT,
            metadata TEXT
        )
    """)
    print("✅ users テーブルを作成")
    
    # threads テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            id TEXT PRIMARY KEY,
            createdAt TEXT,
            name TEXT,
            userId TEXT,
            userIdentifier TEXT,
            tags TEXT,
            metadata TEXT,
            FOREIGN KEY (userId) REFERENCES users(id)
        )
    """)
    print("✅ threads テーブルを作成")
    
    # steps テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS steps (
            id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            threadId TEXT,
            parentId TEXT,
            disableFeedback INTEGER DEFAULT 0,
            streaming INTEGER DEFAULT 0,
            waitForAnswer INTEGER DEFAULT 0,
            isError INTEGER DEFAULT 0,
            metadata TEXT,
            tags TEXT,
            input TEXT,
            output TEXT,
            createdAt TEXT,
            start TEXT,
            end TEXT,
            generation TEXT,
            showInput TEXT,
            language TEXT,
            indent INTEGER DEFAULT 0,
            FOREIGN KEY (threadId) REFERENCES threads(id),
            FOREIGN KEY (parentId) REFERENCES steps(id)
        )
    """)
    print("✅ steps テーブルを作成")
    
    # elements テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS elements (
            id TEXT PRIMARY KEY,
            threadId TEXT,
            type TEXT,
            chainlitKey TEXT,
            url TEXT,
            objectKey TEXT,
            name TEXT,
            display TEXT,
            size TEXT,
            language TEXT,
            page INTEGER DEFAULT 0,
            forId TEXT,
            mime TEXT,
            FOREIGN KEY (threadId) REFERENCES threads(id)
        )
    """)
    print("✅ elements テーブルを作成")
    
    # feedbacks テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id TEXT PRIMARY KEY,
            forId TEXT,
            threadId TEXT,
            value INTEGER,
            comment TEXT,
            FOREIGN KEY (threadId) REFERENCES threads(id)
        )
    """)
    print("✅ feedbacks テーブルを作成")
    
    # インデックスを作成
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_threads_userId ON threads(userId)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_threads_createdAt ON threads(createdAt DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_steps_threadId ON steps(threadId)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_elements_threadId ON elements(threadId)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedbacks_threadId ON feedbacks(threadId)")
    print("✅ インデックスを作成")
    
    # コミットして閉じる
    conn.commit()
    conn.close()
    
    print("\n✅ すべてのテーブルが正常に作成されました！")
    print("📝 アプリケーションを起動できます: chainlit run app.py")


if __name__ == "__main__":
    print("=" * 50)
    print("SQLiteデータベースのセットアップ")
    print("=" * 50)
    
    try:
        create_tables()
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        print("📝 既存のデータベースファイルを削除してから再実行してください")
