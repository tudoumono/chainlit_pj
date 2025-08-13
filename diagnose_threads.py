"""
履歴復元修正の確認ガイド

問題: "Thread not found" エラーが発生する原因と解決策
"""

import sqlite3
import json
from pathlib import Path

print("=" * 60)
print("📊 Chainlit履歴復元問題の診断")
print("=" * 60)

db_path = ".chainlit/chainlit.db"

if not Path(db_path).exists():
    print(f"❌ データベースファイルが見つかりません: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 問題の診断
print("\n🔍 問題の診断:")
print("-" * 40)

# 1. スレッドIDの一覧
cursor.execute("SELECT DISTINCT id FROM threads ORDER BY created_at DESC LIMIT 10")
thread_ids = [row[0] for row in cursor.fetchall()]
print(f"\n✅ 登録されているスレッドID（最新10件）:")
for tid in thread_ids:
    print(f"   - {tid}")

# 2. ステップに記録されているスレッドIDの一覧
cursor.execute("SELECT DISTINCT thread_id FROM steps ORDER BY created_at DESC LIMIT 10")
step_thread_ids = [row[0] for row in cursor.fetchall()]
print(f"\n📝 ステップに記録されているスレッドID（最新10件）:")
for tid in step_thread_ids:
    print(f"   - {tid}")

# 3. 不一致の確認
print("\n⚠️ スレッドIDの不一致チェック:")
orphan_steps = []
for step_tid in step_thread_ids:
    if step_tid not in thread_ids:
        orphan_steps.append(step_tid)
        print(f"   ❌ ステップのスレッドID {step_tid} に対応するスレッドが存在しません")

if not orphan_steps:
    print("   ✅ すべてのステップに対応するスレッドが存在します")

# 4. 各スレッドの詳細情報
print("\n📊 スレッドとステップの関連性:")
print("-" * 40)
cursor.execute("""
    SELECT 
        t.id,
        t.name,
        t.user_id,
        t.created_at,
        COUNT(s.id) as step_count
    FROM threads t
    LEFT JOIN steps s ON t.id = s.thread_id
    GROUP BY t.id
    ORDER BY t.created_at DESC
    LIMIT 5
""")

for row in cursor.fetchall():
    print(f"\nスレッド: {row[1]}")
    print(f"  ID: {row[0]}")
    print(f"  ユーザー: {row[2]}")
    print(f"  作成日時: {row[3]}")
    print(f"  ステップ数: {row[4]}")

# 5. 孤立したステップの詳細
if orphan_steps:
    print("\n❌ 孤立したステップの詳細:")
    print("-" * 40)
    for orphan_tid in orphan_steps[:5]:  # 最大5件表示
        cursor.execute("""
            SELECT id, name, type, created_at
            FROM steps
            WHERE thread_id = ?
            ORDER BY created_at DESC
            LIMIT 3
        """, (orphan_tid,))
        
        steps = cursor.fetchall()
        if steps:
            print(f"\nスレッドID: {orphan_tid} のステップ:")
            for step in steps:
                print(f"  - {step[1]} ({step[2]}) - {step[3]}")

conn.close()

print("\n" + "=" * 60)
print("📋 解決策:")
print("-" * 40)
print("1. ✅ data_layer.pyのcreate_stepメソッドを修正済み")
print("   - スレッドが存在しない場合は自動的に作成")
print("2. ✅ app.pyのon_chat_resumeハンドラーを追加済み")
print("   - 履歴復元時の処理を適切に行う")
print("3. ✅ ChainlitのスレッドIDを使用するよう修正済み")
print("   - 手動でのスレッドID生成を廃止")
print("\n⚠️ アプリケーションを再起動して、新しいチャットを開始してください")
print("=" * 60)
