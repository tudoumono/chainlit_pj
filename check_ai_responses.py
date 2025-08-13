"""
AIの応答が保存されているか詳細に確認
"""

import sqlite3
import json
from pathlib import Path

db_path = ".chainlit/chainlit.db"

if not Path(db_path).exists():
    print(f"❌ データベースファイルが見つかりません: {db_path}")
    exit(1)

print("=" * 60)
print("📊 AI応答の保存状態確認")
print("=" * 60)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# assistant_messageタイプのステップを確認
cursor.execute("""
    SELECT 
        s.id,
        s.thread_id,
        s.name,
        s.type,
        LENGTH(s.input) as input_len,
        LENGTH(s.output) as output_len,
        SUBSTR(s.input, 1, 100) as input_preview,
        SUBSTR(s.output, 1, 100) as output_preview,
        s.created_at
    FROM steps s
    WHERE s.type = 'assistant_message'
    ORDER BY s.created_at DESC
    LIMIT 10
""")

assistant_messages = cursor.fetchall()

print(f"\n📝 assistant_messageタイプのステップ（最新10件）:")
print("-" * 60)

if not assistant_messages:
    print("❌ assistant_messageが見つかりません")
else:
    for msg in assistant_messages:
        print(f"\nID: {msg[0][:8]}...")
        print(f"  スレッドID: {msg[1][:8]}...")
        print(f"  名前: {msg[2]}")
        print(f"  タイプ: {msg[3]}")
        print(f"  入力長: {msg[4]} bytes")
        print(f"  出力長: {msg[5]} bytes")
        if msg[6]:
            print(f"  入力プレビュー: {msg[6]}")
        if msg[7]:
            print(f"  出力プレビュー: {msg[7]}")
        else:
            print(f"  ⚠️ 出力が空です！")
        print(f"  作成日時: {msg[8]}")

# 全ステップタイプの統計
print("\n" + "=" * 60)
print("📊 ステップタイプ別の統計:")
print("-" * 60)

cursor.execute("""
    SELECT 
        type,
        COUNT(*) as count,
        SUM(CASE WHEN input != '' THEN 1 ELSE 0 END) as with_input,
        SUM(CASE WHEN output != '' THEN 1 ELSE 0 END) as with_output
    FROM steps
    GROUP BY type
    ORDER BY count DESC
""")

stats = cursor.fetchall()
for stat in stats:
    print(f"\nタイプ: {stat[0]}")
    print(f"  総数: {stat[1]}")
    print(f"  入力あり: {stat[2]}")
    print(f"  出力あり: {stat[3]}")
    if stat[0] == 'assistant_message' and stat[3] == 0:
        print(f"  ❌ AIの応答が保存されていません！")

# 最新のスレッドの詳細
print("\n" + "=" * 60)
print("📊 最新スレッドの詳細分析:")
print("-" * 60)

cursor.execute("""
    SELECT id, name FROM threads ORDER BY created_at DESC LIMIT 1
""")
latest_thread = cursor.fetchone()

if latest_thread:
    thread_id = latest_thread[0]
    print(f"スレッド: {latest_thread[1]} ({thread_id[:8]}...)")
    
    cursor.execute("""
        SELECT type, input, output
        FROM steps
        WHERE thread_id = ?
        ORDER BY created_at ASC
    """, (thread_id,))
    
    steps = cursor.fetchall()
    for i, step in enumerate(steps, 1):
        print(f"\n  ステップ{i}: {step[0]}")
        if step[1]:
            print(f"    入力: {step[1][:100]}...")
        if step[2]:
            print(f"    出力: {step[2][:100]}...")
        elif step[0] == 'assistant_message':
            print(f"    ❌ 出力が保存されていません")

conn.close()

print("\n" + "=" * 60)
print("💡 問題の診断:")
print("-" * 60)
print("assistant_messageのoutputフィールドが空の場合、")
print("メッセージハンドラーでAIの応答を適切に保存していない可能性があります。")
print("=" * 60)
