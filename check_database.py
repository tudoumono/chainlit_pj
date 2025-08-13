"""
データベースの内容を確認するデバッグスクリプト
"""

import sqlite3
import json
from pathlib import Path

def check_database():
    """データベースの内容を確認"""
    db_path = ".chainlit/chainlit.db"
    
    if not Path(db_path).exists():
        print(f"❌ データベースファイルが存在しません: {db_path}")
        return
    
    print(f"✅ データベースファイルが見つかりました: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # テーブル一覧を取得
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"\n📊 テーブル一覧: {[t[0] for t in tables]}")
    
    # threadsテーブルの内容を確認
    print("\n=== THREADS テーブル ===")
    try:
        cursor.execute("SELECT COUNT(*) FROM threads")
        count = cursor.fetchone()[0]
        print(f"スレッド数: {count}")
        
        if count > 0:
            cursor.execute("SELECT * FROM threads LIMIT 5")
            rows = cursor.fetchall()
            
            # カラム名を取得
            column_names = [description[0] for description in cursor.description]
            print(f"カラム: {column_names}")
            
            for i, row in enumerate(rows, 1):
                print(f"\nスレッド {i}:")
                for col_name, value in zip(column_names, row):
                    if col_name in ['tags', 'metadata'] and value:
                        try:
                            value = json.loads(value)
                        except:
                            pass
                    print(f"  {col_name}: {value}")
    except sqlite3.OperationalError as e:
        print(f"エラー: {e}")
    
    # stepsテーブルの内容を確認
    print("\n=== STEPS テーブル ===")
    try:
        cursor.execute("SELECT COUNT(*) FROM steps")
        count = cursor.fetchone()[0]
        print(f"ステップ数: {count}")
        
        if count > 0:
            cursor.execute("SELECT id, thread_id, name, type FROM steps LIMIT 5")
            rows = cursor.fetchall()
            for row in rows:
                print(f"  ID: {row[0]}, Thread: {row[1]}, Name: {row[2]}, Type: {row[3]}")
    except sqlite3.OperationalError as e:
        print(f"エラー: {e}")
    
    # feedbacksテーブルの内容を確認
    print("\n=== FEEDBACKS テーブル ===")
    try:
        cursor.execute("SELECT COUNT(*) FROM feedbacks")
        count = cursor.fetchone()[0]
        print(f"フィードバック数: {count}")
    except sqlite3.OperationalError as e:
        print(f"エラー: {e}")
    
    # elementsテーブルの内容を確認
    print("\n=== ELEMENTS テーブル ===")
    try:
        cursor.execute("SELECT COUNT(*) FROM elements")
        count = cursor.fetchone()[0]
        print(f"エレメント数: {count}")
    except sqlite3.OperationalError as e:
        print(f"エラー: {e}")
    
    conn.close()
    print("\n✅ データベース確認完了")

if __name__ == "__main__":
    check_database()
