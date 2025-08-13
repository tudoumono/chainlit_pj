"""
ステップの詳細内容を確認するスクリプト
"""

import sqlite3
import json
from pathlib import Path

db_path = ".chainlit/chainlit.db"

if not Path(db_path).exists():
    print(f"❌ データベースファイルが見つかりません: {db_path}")
    exit(1)

print("=" * 60)
print("📊 ステップの詳細内容確認")
print("=" * 60)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 最新のスレッドを取得
cursor.execute("""
    SELECT id, name, created_at
    FROM threads
    ORDER BY created_at DESC
    LIMIT 1
""")
thread = cursor.fetchone()

if not thread:
    print("❌ スレッドが見つかりません")
    conn.close()
    exit(1)

thread_id = thread[0]
print(f"\n📝 最新のスレッド:")
print(f"  ID: {thread_id}")
print(f"  名前: {thread[1]}")
print(f"  作成日時: {thread[2]}")

# このスレッドのステップを詳細に取得
cursor.execute("""
    SELECT id, type, name, input, output, created_at
    FROM steps
    WHERE thread_id = ?
    ORDER BY created_at ASC
""", (thread_id,))

steps = cursor.fetchall()
print(f"\n📊 ステップ数: {len(steps)}")
print("=" * 60)

for i, step in enumerate(steps, 1):
    step_id, step_type, step_name, step_input, step_output, created_at = step
    
    print(f"\n【ステップ {i}】")
    print(f"  ID: {step_id[:8]}...")
    print(f"  タイプ: {step_type}")
    print(f"  名前: {step_name}")
    print(f"  作成日時: {created_at}")
    
    # input内容
    if step_input:
        print(f"  入力:")
        if len(step_input) > 200:
            print(f"    {step_input[:200]}...")
        else:
            print(f"    {step_input}")
    
    # output内容
    if step_output:
        print(f"  出力:")
        if len(step_output) > 200:
            print(f"    {step_output[:200]}...")
        else:
            print(f"    {step_output}")
    
    print("-" * 40)

# メッセージの分析
print("\n📊 メッセージの分析:")
print("=" * 60)

# ユーザーメッセージ
cursor.execute("""
    SELECT COUNT(*), COUNT(CASE WHEN input != '' THEN 1 END)
    FROM steps
    WHERE thread_id = ? AND type = 'user_message'
""", (thread_id,))
user_stats = cursor.fetchone()
print(f"ユーザーメッセージ: {user_stats[0]}件 (入力あり: {user_stats[1]}件)")

# アシスタントメッセージ
cursor.execute("""
    SELECT COUNT(*), COUNT(CASE WHEN output != '' THEN 1 END)
    FROM steps
    WHERE thread_id = ? AND type = 'assistant_message'
""", (thread_id,))
assistant_stats = cursor.fetchone()
print(f"アシスタントメッセージ: {assistant_stats[0]}件 (出力あり: {assistant_stats[1]}件)")

# runステップ
cursor.execute("""
    SELECT COUNT(*), COUNT(CASE WHEN output != '' THEN 1 END)
    FROM steps
    WHERE thread_id = ? AND type = 'run'
""", (thread_id,))
run_stats = cursor.fetchone()
print(f"runステップ: {run_stats[0]}件 (出力あり: {run_stats[1]}件)")

conn.close()

print("\n" + "=" * 60)
print("✅ 分析完了")
print("\n💡 ヒント:")
print("  - user_messageのinputフィールドにユーザーの入力が保存される")
print("  - assistant_messageのoutputフィールドにAIの回答が保存される")
print("  - runステップは処理の記録で、通常は表示不要")
print("=" * 60)
