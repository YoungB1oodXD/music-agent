import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

BEHAVIOR_FILE = Path(__file__).parent.parent.parent / "data" / "processed" / "user_behaviors.jsonl"


def record_behavior(
    user_id: str,
    song_id: str,
    action: str,
    metadata: dict | None = None,
) -> bool:
    try:
        BEHAVIOR_FILE.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "song_id": song_id,
            "action": action,
            "metadata": metadata or {},
        }
        with open(BEHAVIOR_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        logger.error(f"Failed to record behavior: {e}")
        return False


def get_behavior_stats() -> dict:
    if not BEHAVIOR_FILE.exists():
        return {"total": 0, "by_action": {}}
    counts: dict[str, int] = {}
    total = 0
    try:
        with open(BEHAVIOR_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                try:
                    rec = json.loads(line)
                    action = rec.get("action", "unknown")
                    counts[action] = counts.get(action, 0) + 1
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        logger.error(f"Failed to read behavior stats: {e}")
    return {"total": total, "by_action": counts}
