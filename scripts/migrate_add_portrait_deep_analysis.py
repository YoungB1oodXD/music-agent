"""
Migration: Add ai_portrait_deep_analysis column to user_preferences table.
Safe to re-run — uses IF NOT EXISTS.
"""
import sqlite3
import sys
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "music_agent.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check if column already exists
cursor.execute("PRAGMA table_info(user_preferences)")
columns = [row[1] for row in cursor.fetchall()]

if "ai_portrait_deep_analysis" not in columns:
    cursor.execute(
        "ALTER TABLE user_preferences ADD COLUMN ai_portrait_deep_analysis TEXT DEFAULT ''"
    )
    conn.commit()
    print(f"Added ai_portrait_deep_analysis column to {db_path}")
else:
    print("Column already exists, no changes needed.")

conn.close()
