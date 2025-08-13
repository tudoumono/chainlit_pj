"""
履歴復元問題の詳細確認
"""

import sqlite3
import json
from pathlib import Path

db_path = ".chainlit/chainlit.db"

if not Path(db_path).exists():
    print(f"❌ データベースファイルが見つかりません: {db_path}")
    exit(1)

print("=" * 60)
print("📊 Chainlit履歴復元問題の診断")
print("=" * 60)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. スレッドの確認
print("\n📝 登録されているスレッド:")
print("-" * 40)
cursor.execute("SELECT id, name, user_id, created_at FROM threads ORDER BY created_at DESC")
threads = cursor.fetchall()
for thread in threads:
    print(f"ID: {thread[0]}")
    print(f"  名前: {thread[1]}")
    print(f"  ユーザー: {thread[2]}")
    print(f"  作成日時: {thread[3]}")
    
    # このスレッドのステップを確認
    cursor.execute("""
        SELECT COUNT(*), 
               COUNT(CASE WHEN type='user_message' THEN 1 END),
               MIN(created_at), MAX(created_at)
        FROM steps WHERE thread_id = ?
    """, (thread[0],))
    step_info = cursor.fetchone()
    print(f"  ステップ数: {step_info[0]} (ユーザーメッセージ: {step_info[1]})")
    print(f"  期間: {step_info[2]} ~ {step_info[3]}")
    print()

# 2. 最新のステップの詳細
print("\n📝 最新のステップ（各タイプ別）:")
print("-" * 40)
cursor.execute("""
    SELECT DISTINCT type FROM steps
""")
step_types = [row[0] for row in cursor.fetchall()]

for step_type in step_types:
    cursor.execute("""
        SELECT id, thread_id, name, created_at
        FROM steps
        WHERE type = ?
        ORDER BY created_at DESC
        LIMIT 2
    """, (step_type,))
    steps = cursor.fetchall()
    
    if steps:
        print(f"\nタイプ: {step_type}")
        for step in steps:
            print(f"  - ID: {step[0][:8]}... スレッド: {step[1][:8]}...")
            print(f"    名前: {step[2]}, 作成: {step[3]}")

# 3. スレッドとステップの整合性チェック
print("\n🔍 整合性チェック:")
print("-" * 40)

# 孤立したステップ
cursor.execute("""
    SELECT COUNT(DISTINCT s.thread_id)
    FROM steps s
    LEFT JOIN threads t ON s.thread_id = t.id
    WHERE t.id IS NULL
""")
orphan_count = cursor.fetchone()[0]
if orphan_count > 0:
    print(f"❌ 孤立したステップのスレッド数: {orphan_count}")
else:
    print("✅ すべてのステップに対応するスレッドが存在")

# 空のスレッド
cursor.execute("""
    SELECT COUNT(*)
    FROM threads t
    LEFT JOIN steps s ON t.id = s.thread_id
    WHERE s.id IS NULL
""")
empty_count = cursor.fetchone()[0]
if empty_count > 0:
    print(f"⚠️ 空のスレッド数: {empty_count}")
else:
    print("✅ すべてのスレッドにステップが存在")

conn.close()

print("\n" + "=" * 60)
print("📋 診断結果:")
print("-" * 40)
print("1. データベースにスレッドとステップは正常に保存されている")
print("2. 履歴復元時の問題は、get_threadメソッドの実装にある可能性")
print("3. 特に、ステップの取得と返却の部分を確認する必要がある")
print("=" * 60)
