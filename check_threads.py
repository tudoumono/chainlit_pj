"""
スレッドとステップの保存状態を確認するスクリプト
"""

import sqlite3
import json
from pathlib import Path

db_path = ".chainlit/chainlit.db"

if not Path(db_path).exists():
    print(f"❌ データベースファイルが見つかりません: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 60)
print("📊 データベース状態チェック")
print("=" * 60)

# スレッド数を確認
cursor.execute("SELECT COUNT(*) FROM threads")
thread_count = cursor.fetchone()[0]
print(f"\n✅ スレッド総数: {thread_count}")

if thread_count > 0:
    print("\n📝 最新のスレッド（最大5件）:")
    cursor.execute("""
        SELECT id, name, user_id, created_at 
        FROM threads 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"  - ID: {row[0][:8]}...")
        print(f"    名前: {row[1]}")
        print(f"    ユーザー: {row[2]}")
        print(f"    作成日時: {row[3]}")
        print()

# ステップ数を確認
cursor.execute("SELECT COUNT(*) FROM steps")
step_count = cursor.fetchone()[0]
print(f"✅ ステップ総数: {step_count}")

if step_count > 0:
    print("\n📝 最新のステップ（最大5件）:")
    cursor.execute("""
        SELECT s.id, s.thread_id, s.name, s.type, s.created_at
        FROM steps s
        ORDER BY s.created_at DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"  - ID: {row[0][:8]}...")
        print(f"    スレッドID: {row[1][:8]}...")
        print(f"    名前: {row[2]}")
        print(f"    タイプ: {row[3]}")
        print(f"    作成日時: {row[4]}")
        print()

# スレッドごとのステップ数
print("\n📊 スレッドごとのステップ数:")
cursor.execute("""
    SELECT t.id, t.name, COUNT(s.id) as step_count
    FROM threads t
    LEFT JOIN steps s ON t.id = s.thread_id
    GROUP BY t.id
    ORDER BY t.created_at DESC
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  - スレッド: {row[1]} ({row[0][:8]}...)")
    print(f"    ステップ数: {row[2]}")

conn.close()

print("\n" + "=" * 60)
print("✅ チェック完了")
print("=" * 60)
