"""
一次性迁移脚本：为 user_preferences 表追加 portrait 字段
仅在缺失时才添加，安全可重复执行
"""

from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).parent.parent / "data" / "music_agent.db"

ADD_COLUMNS = [
    ("ai_portrait_summary", "TEXT DEFAULT ''"),
    ("ai_portrait_keywords", "TEXT DEFAULT '[]'"),
    ("ai_portrait_scene", "TEXT DEFAULT ''"),
    ("ai_portrait_generated_at", "TEXT"),
]


def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 获取现有列
    cursor.execute("PRAGMA table_info(user_preferences)")
    existing = {row[1] for row in cursor.fetchall()}

    for col_name, col_def in ADD_COLUMNS:
        if col_name not in existing:
            cursor.execute(
                f"ALTER TABLE user_preferences ADD COLUMN {col_name} {col_def}"
            )
            print(f"Added column: {col_name}")
        else:
            print(f"Column already exists: {col_name}")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate()
