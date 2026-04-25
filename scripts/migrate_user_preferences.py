#!/usr/bin/env python3
"""
用户偏好表迁移脚本

将旧的 user_preferences 表结构迁移到新的 Counter 模式

旧结构：
- preferred_genres (JSON) - 列表
- preferred_energy (String) - 单值

新结构：
- liked_genre_counts (JSON) - dict
- disliked_genre_counts (JSON) - dict
- energy_scores (JSON) - {"scores": [], "count": 0}
- vocal_scores (JSON) - {"scores": [], "count": 0}
"""

import sqlite3
import json
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "music_agent.db"


def migrate_user_preferences():
    """迁移用户偏好表"""

    # 1. 备份数据库
    backup_path = DB_PATH.with_suffix(".db.preference_migration_backup")
    shutil.copy2(DB_PATH, backup_path)
    print(f"[MIGRATION] 数据库已备份到: {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 2. 检查旧数据
    cursor.execute(
        "SELECT user_id, preferred_genres, preferred_energy FROM user_preferences"
    )
    old_data = cursor.fetchall()
    print(f"[MIGRATION] 找到 {len(old_data)} 条旧记录")

    # 3. 创建新表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences_new (
            user_id INTEGER PRIMARY KEY,
            liked_genre_counts TEXT DEFAULT '{}',
            disliked_genre_counts TEXT DEFAULT '{}',
            energy_scores TEXT DEFAULT '{"scores": [], "count": 0}',
            vocal_scores TEXT DEFAULT '{"scores": [], "count": 0}',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 4. 迁移数据
    migrated = 0
    for user_id, preferred_genres_json, preferred_energy in old_data:
        # 解析旧数据
        preferred_genres = []
        if preferred_genres_json:
            try:
                if isinstance(preferred_genres_json, str):
                    preferred_genres = json.loads(preferred_genres_json)
                elif isinstance(preferred_genres_json, list):
                    preferred_genres = preferred_genres_json
            except:
                preferred_genres = []

        # 构建 liked_genre_counts
        liked_genre_counts = {}
        for genre in preferred_genres:
            if genre:
                liked_genre_counts[str(genre)] = (
                    liked_genre_counts.get(str(genre), 0) + 1
                )

        # 构建 energy_scores
        energy_map = {"high": 3, "medium": 2, "low": 1, "none": 0}
        energy_scores = {"scores": [], "count": 0}
        if preferred_energy and preferred_energy in energy_map:
            energy_scores["scores"] = [energy_map[preferred_energy]]
            energy_scores["count"] = 1

        # 插入新记录
        cursor.execute(
            """
            INSERT OR REPLACE INTO user_preferences_new 
            (user_id, liked_genre_counts, energy_scores, updated_at)
            VALUES (?, ?, ?, ?)
        """,
            (
                user_id,
                json.dumps(liked_genre_counts),
                json.dumps(energy_scores),
                datetime.now().isoformat(),
            ),
        )
        migrated += 1

    conn.commit()
    print(f"[MIGRATION] 已迁移 {migrated} 条记录")

    # 5. 替换表
    cursor.execute("DROP TABLE user_preferences")
    cursor.execute("ALTER TABLE user_preferences_new RENAME TO user_preferences")
    conn.commit()

    # 6. 验证
    cursor.execute("PRAGMA table_info(user_preferences)")
    new_schema = cursor.fetchall()
    print(f"[MIGRATION] 新表结构:")
    for col in new_schema:
        print(f"  - {col[1]}: {col[2]}")

    conn.close()
    print("[MIGRATION] 迁移完成!")


if __name__ == "__main__":
    migrate_user_preferences()
