"""
データベースクリーンアップスクリプト
空のスレッドやユーザーメッセージのないスレッドを削除
"""

import sqlite3
import json
from pathlib import Path

db_path = ".chainlit/chainlit.db"

if not Path(db_path).exists():
    print(f"❌ データベースファイルが見つかりません: {db_path}")
    exit(1)

print("=" * 60)
print("🧹 Chainlitデータベースのクリーンアップ")
print("=" * 60)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 空のスレッド（ステップが全くない）を検出
cursor.execute("""
    SELECT t.id, t.name, t.created_at
    FROM threads t
    LEFT JOIN steps s ON t.id = s.thread_id
    WHERE s.id IS NULL
""")
empty_threads = cursor.fetchall()

if empty_threads:
    print(f"\n⚠️ 空のスレッドが{len(empty_threads)}件見つかりました:")
    for thread in empty_threads:
        print(f"  - ID: {thread[0][:8]}... 名前: {thread[1]} 作成: {thread[2]}")
    
    response = input("\nこれらの空のスレッドを削除しますか? (y/n): ")
    if response.lower() == 'y':
        for thread in empty_threads:
            cursor.execute("DELETE FROM threads WHERE id = ?", (thread[0],))
        conn.commit()
        print(f"✅ {len(empty_threads)}件の空のスレッドを削除しました")
else:
    print("✅ 空のスレッドはありません")

# 2. ユーザーメッセージのないスレッドを検出
cursor.execute("""
    SELECT DISTINCT t.id, t.name, t.created_at
    FROM threads t
    INNER JOIN steps s ON t.id = s.thread_id
    LEFT JOIN steps us ON t.id = us.thread_id AND us.type = 'user_message'
    WHERE us.id IS NULL
""")
no_user_msg_threads = cursor.fetchall()

if no_user_msg_threads:
    print(f"\n⚠️ ユーザーメッセージのないスレッドが{len(no_user_msg_threads)}件見つかりました:")
    for thread in no_user_msg_threads:
        # ステップ数を取得
        cursor.execute("SELECT COUNT(*) FROM steps WHERE thread_id = ?", (thread[0],))
        step_count = cursor.fetchone()[0]
        print(f"  - ID: {thread[0][:8]}... 名前: {thread[1]} ステップ数: {step_count}")
    
    response = input("\nこれらのスレッドを削除しますか? (y/n): ")
    if response.lower() == 'y':
        for thread in no_user_msg_threads:
            # 関連するステップも削除
            cursor.execute("DELETE FROM steps WHERE thread_id = ?", (thread[0],))
            cursor.execute("DELETE FROM threads WHERE id = ?", (thread[0],))
        conn.commit()
        print(f"✅ {len(no_user_msg_threads)}件のスレッドとその関連ステップを削除しました")
else:
    print("✅ すべてのスレッドにユーザーメッセージが含まれています")

# 3. 孤立したステップ（スレッドが存在しない）を検出
cursor.execute("""
    SELECT s.thread_id, COUNT(*) as count
    FROM steps s
    LEFT JOIN threads t ON s.thread_id = t.id
    WHERE t.id IS NULL
    GROUP BY s.thread_id
""")
orphan_steps = cursor.fetchall()

if orphan_steps:
    total_orphans = sum(row[1] for row in orphan_steps)
    print(f"\n⚠️ 孤立したステップが{total_orphans}件見つかりました:")
    for thread_id, count in orphan_steps:
        print(f"  - スレッドID: {thread_id[:8]}... ({count}個のステップ)")
    
    response = input("\nこれらの孤立したステップを削除しますか? (y/n): ")
    if response.lower() == 'y':
        cursor.execute("""
            DELETE FROM steps 
            WHERE thread_id NOT IN (SELECT id FROM threads)
        """)
        conn.commit()
        print(f"✅ {total_orphans}件の孤立したステップを削除しました")
else:
    print("✅ 孤立したステップはありません")

# 4. 統計を表示
print("\n" + "=" * 60)
print("📊 クリーンアップ後の統計:")
print("-" * 40)

cursor.execute("SELECT COUNT(*) FROM threads")
thread_count = cursor.fetchone()[0]
print(f"スレッド総数: {thread_count}")

cursor.execute("SELECT COUNT(*) FROM steps")
step_count = cursor.fetchone()[0]
print(f"ステップ総数: {step_count}")

cursor.execute("SELECT COUNT(DISTINCT thread_id) FROM steps WHERE type = 'user_message'")
threads_with_user_msg = cursor.fetchone()[0]
print(f"ユーザーメッセージを含むスレッド数: {threads_with_user_msg}")

conn.close()

print("=" * 60)
print("✅ クリーンアップ完了")
