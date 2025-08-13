"""
Chainlit履歴復元問題の詳細診断
"""

import sqlite3
import json
from pathlib import Path

print("=" * 60)
print("📊 Chainlit履歴の詳細診断")
print("=" * 60)

db_path = ".chainlit/chainlit.db"

if not Path(db_path).exists():
    print(f"❌ データベースファイルが見つかりません: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 全スレッドのリスト
print("\n📝 全スレッドの一覧:")
print("-" * 40)
cursor.execute("""
    SELECT id, name, user_id, created_at
    FROM threads
    ORDER BY created_at DESC
""")
threads = cursor.fetchall()
for thread in threads:
    print(f"ID: {thread[0]}")
    print(f"  名前: {thread[1]}")
    print(f"  ユーザー: {thread[2]}")
    print(f"  作成日時: {thread[3]}")
    print()

# 2. 全ステップのサマリー
print("\n📊 ステップのサマリー:")
print("-" * 40)
cursor.execute("""
    SELECT 
        thread_id,
        COUNT(*) as step_count,
        COUNT(CASE WHEN type = 'user_message' THEN 1 END) as user_messages,
        COUNT(CASE WHEN type != 'user_message' THEN 1 END) as other_steps
    FROM steps
    GROUP BY thread_id
    ORDER BY thread_id
""")
step_summaries = cursor.fetchall()
for summary in step_summaries:
    print(f"スレッドID: {summary[0]}")
    print(f"  総ステップ数: {summary[1]}")
    print(f"  ユーザーメッセージ: {summary[2]}")
    print(f"  その他のステップ: {summary[3]}")
    
    # スレッドが存在するかチェック
    cursor.execute("SELECT COUNT(*) FROM threads WHERE id = ?", (summary[0],))
    thread_exists = cursor.fetchone()[0] > 0
    if not thread_exists:
        print(f"  ⚠️ 対応するスレッドが存在しません！")
    print()

# 3. 最新のステップの詳細
print("\n📝 最新のステップの詳細（最大10件）:")
print("-" * 40)
cursor.execute("""
    SELECT id, thread_id, type, name, created_at
    FROM steps
    ORDER BY created_at DESC
    LIMIT 10
""")
steps = cursor.fetchall()
for step in steps:
    print(f"ID: {step[0]}")
    print(f"  スレッドID: {step[1]}")
    print(f"  タイプ: {step[2]}")
    print(f"  名前: {step[3]}")
    print(f"  作成日時: {step[4]}")
    print()

# 4. 問題の診断
print("\n🔍 問題診断:")
print("-" * 40)

# 孤立したステップを検出
cursor.execute("""
    SELECT DISTINCT s.thread_id
    FROM steps s
    LEFT JOIN threads t ON s.thread_id = t.id
    WHERE t.id IS NULL
""")
orphan_thread_ids = [row[0] for row in cursor.fetchall()]

if orphan_thread_ids:
    print(f"❌ 孤立したステップが見つかりました（スレッドが存在しない）:")
    for tid in orphan_thread_ids:
        cursor.execute("SELECT COUNT(*) FROM steps WHERE thread_id = ?", (tid,))
        count = cursor.fetchone()[0]
        print(f"  - スレッドID: {tid} ({count}個のステップ)")
else:
    print("✅ すべてのステップに対応するスレッドが存在します")

# 空のスレッドを検出
cursor.execute("""
    SELECT t.id, t.name
    FROM threads t
    LEFT JOIN steps s ON t.id = s.thread_id
    WHERE s.id IS NULL
""")
empty_threads = cursor.fetchall()

if empty_threads:
    print(f"\n⚠️ 空のスレッドが見つかりました（ステップが存在しない）:")
    for thread in empty_threads:
        print(f"  - ID: {thread[0]}, 名前: {thread[1]}")
else:
    print("\n✅ すべてのスレッドにステップが存在します")

# ユーザーメッセージのないスレッドを検出
cursor.execute("""
    SELECT DISTINCT t.id, t.name
    FROM threads t
    LEFT JOIN steps s ON t.id = s.thread_id AND s.type = 'user_message'
    WHERE s.id IS NULL
""")
no_user_msg_threads = cursor.fetchall()

if no_user_msg_threads:
    print(f"\n⚠️ ユーザーメッセージのないスレッドが見つかりました:")
    for thread in no_user_msg_threads:
        print(f"  - ID: {thread[0]}, 名前: {thread[1]}")

conn.close()

print("\n" + "=" * 60)
print("📋 推奨事項:")
print("-" * 40)
print("1. 孤立したステップがある場合：")
print("   - data_layer.pyのcreate_stepメソッドで自動スレッド作成が機能しています")
print("2. 空のスレッドがある場合：")
print("   - ユーザーがメッセージを送信していない可能性があります")
print("3. 履歴復元でエラーが出る場合：")
print("   - get_threadメソッドでスレッドが正しく返されているか確認")
print("=" * 60)
