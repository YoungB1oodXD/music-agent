from __future__ import annotations
import random
from typing import List, Dict

TEST_USERS = [f"user_{i}" for i in range(1, 11)]

TEST_QUERIES = [
    "推荐一些适合学习的歌",
    "来点欢快的流行音乐",
    "安静的爵士乐",
    "跑步时听的动感歌曲",
    "睡前放松的音乐",
    "工作专注时听的歌",
    "周末派对音乐",
    "悲伤的情歌",
    "早晨唤醒音乐",
    "开车兜风听的歌",
    "瑜伽冥想音乐",
    "下午茶时间听的歌",
    "深夜独处时的音乐",
    "健身房运动音乐",
    "古典音乐推荐",
    "电子音乐推荐",
    "民谣歌曲推荐",
    "hip-hop音乐",
    "古典摇滚",
    "轻音乐推荐",
]

SCENES = ["学习", "工作", "运动", "休息", "派对", "通勤", "瑜伽", "睡眠"]
MOODS = ["欢快", "平静", "悲伤", "兴奋", "浪漫", "专注", "放松", "激烈"]
GENRES = ["Pop", "Rock", "Jazz", "Classical", "Electronic", "Hip-Hop", "Folk", "R&B"]
ENERGY_LEVELS = ["high", "medium", "low"]
VOCAL_PREFERENCES = ["有歌词", "纯音乐", "人声", "器乐"]

TRACK_POOL = [f"track_{i:04d}" for i in range(1, 101)]


def generate_test_user_preferences(user_id: str) -> Dict:
    """Generate random preferences for a test user"""
    return {
        "user_id": user_id,
        "scenes": random.sample(SCENES, k=random.randint(1, 3)),
        "moods": random.sample(MOODS, k=random.randint(1, 3)),
        "genres": random.sample(GENRES, k=random.randint(1, 2)),
        "energy": random.choice(ENERGY_LEVELS),
        "vocal": random.choice(VOCAL_PREFERENCES),
    }


def generate_test_behavior_log(user_id: str, num_actions: int = 20) -> List[Dict]:
    """Generate simulated user behavior log"""
    log = []
    for _ in range(num_actions):
        action_type = random.choice(["like", "play", "dislike", "skip"])
        track_id = random.choice(TRACK_POOL)
        log.append(
            {
                "user_id": user_id,
                "track_id": track_id,
                "action": action_type,
                "timestamp": f"2026-04-{random.randint(1, 8):02d}T{random.randint(0, 23):02d}:00:00",
            }
        )
    return log


def get_test_queries() -> List[str]:
    """Return test query set"""
    return TEST_QUERIES


def get_test_users() -> List[str]:
    """Return test user list"""
    return TEST_USERS


def get_track_pool() -> List[str]:
    """Return available track pool"""
    return TRACK_POOL.copy()
