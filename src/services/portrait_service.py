"""
智能用户画像服务

功能：
1. 读取用户偏好和喜欢歌单
2. 组装 Prompt 调用 LLM 生成画像
3. 缓存结果到 DB
"""

import logging
from datetime import datetime
from typing import Optional

from src.models.user_preference import UserPreference
from src.models.playlist import Playlist, PlaylistSong
from src.database.db import Session
from src.llm.clients.base import ChatResponse

logger = logging.getLogger(__name__)

ENERGY_LABEL_MAP = {3: "高能量", 2: "中等能量", 1: "低能量"}
VOCAL_LABEL_MAP = {1: "人声为主", 0: "纯器乐"}

_GENRE_ENERGY_SCORE_MAP: dict[str, int] = {
    "ambient": 1,
    "electronic": 3,
    "instrumental": 2,
    "classical": 2,
    "jazz": 2,
    "rock": 3,
    "pop": 2,
    "folk": 1,
    "hip-hop": 3,
    "lo-fi": 1,
    "chill": 1,
    "experimental": 2,
    "international": 2,
    "country": 2,
    "old-time / historic": 1,
    "spoken": 1,
    "blues": 2,
    "soul-rnb": 2,
    "easy listening": 1,
}


def _calc_energy_label(scores: list[int]) -> str:
    if not scores:
        return "未知"
    avg = sum(scores) / len(scores)
    if avg > 2.5:
        return "高能量"
    elif avg > 1.5:
        return "中等能量"
    return "低能量"


def _calc_vocal_label(scores: list[int]) -> str:
    if not scores:
        return "未知"
    avg = sum(scores) / len(scores)
    if avg > 0.5:
        return "人声为主"
    return "器乐为主"


PORTRAIT_PROMPT_TEMPLATE = """你是一个专业的音乐推荐分析师。请根据以下用户数据，生成一份简洁的用户画像。

【用户偏好】
- 喜欢流派：{liked_genres}
- 不喜欢流派：{disliked_genres}
- 能量偏好：{energy_label}

【最近喜欢的歌曲】（{song_count}首）
{songs_list}

请直接返回以下 JSON 格式（不要加任何其他文字）：
{{"summary": "整体描述（1-2句话，100字以内）", "keywords": ["关键词1", "关键词2", "关键词3"], "scene": "典型听歌场景（20字以内）"}}
"""

DEEP_ANALYSIS_PROMPT_TEMPLATE = """你是一个音乐应用中的"用户音乐画像解读助手"。

输入是用户当前会话中的行为数据，包括：
- 喜欢/不喜欢的歌曲
- 添加到歌单的内容
- 最近的对话记录（如"适合学习""不要人声"等）

你的任务是：
基于这些信息，生成一段"面向用户本人"的趣味音乐画像描述。

【重要约束】
- 这是"当前阶段的偏好解读"，不是年度总结
- 不要提及"今年 / 一年 / 长期数据"
- 不要编造播放次数、时长或统计数据
- 不要假装有完整历史记录

【风格要求】
- 使用第二人称（"你"）
- 语言自然、口语化，有一点情绪感
- 可以有轻微幽默或反差
- 不要使用专业术语（如"推断""模型""动态范围"等）
- 不要写成分析报告或论文

【内容结构建议】
1. 开头一句抓人的总结（类似一句"你是那种…"）
2. 描述你的听歌习惯或偏好特点
3. 结合使用场景或情绪进行解释
4. 用一句有记忆点的话收尾

【输出要求】
100~200字，分段（2~4段），不要一整段

如果信息不足，请基于已有信息做合理、克制的描述，不要扩展不存在的行为。

现在根据以下用户数据生成内容：
{user_data}

直接返回以下 JSON 格式（不要加任何其他文字）：
{{"deep_analysis": "你的分析文字（100~200字，分段）", "scene": "典型场景（5字以内，如：深夜学习）"}}
"""


class PortraitService:
    def __init__(self, llm_client=None):
        """
        初始化画像服务
        Args:
            llm_client: LLM 客户端（MockLLMClient 或 QwenClient）
        """
        self._llm = llm_client

    @property
    def llm(self):
        if self._llm is None:
            from src.agent.mock_llm import MockLLMClient

            self._llm = MockLLMClient()
        return self._llm

    def generate_portrait(
        self, db: Session, user_id: int, session_id: str | None = None
    ) -> dict:
        """
        生成用户画像

        Args:
            db: 数据库会话
            user_id: 用户 ID
            session_id: 当前会话 ID（用于获取对话历史和场景偏好）

        Returns:
            dict: 画像结果 {"summary": ..., "keywords": [...], "scene": ..., "deep_analysis": ...}
        """
        prefs = UserPreference.get_or_create(db, user_id)

        liked_songs = self._get_liked_songs(db, user_id, limit=20)

        if liked_songs and not prefs.liked_genre_counts:
            from collections import Counter

            genre_counts: dict[str, int] = Counter(
                s.get("genre", "") for s in liked_songs if s.get("genre")
            )
            if genre_counts:
                prefs.liked_genre_counts = dict(genre_counts)
        if liked_songs and (
            not prefs.energy_scores.get("scores")
            or prefs.energy_scores.get("count", 0) == 0
        ):
            energy_vals = [
                _GENRE_ENERGY_SCORE_MAP.get(s.get("genre", "").lower(), 2)
                for s in liked_songs
                if s.get("genre")
            ]
            if energy_vals:
                prefs.energy_scores = {"scores": energy_vals, "count": len(energy_vals)}
        if liked_songs or prefs.liked_genre_counts:
            prefs.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(prefs)

        portrait = self._build_portrait_from_data(prefs, liked_songs)

        dialogue_history = ""
        preferred_scenes: list[str] = []
        if session_id:
            dialogue_history = self._get_dialogue_history(db, session_id)
            preferred_scenes = self._get_preferred_scenes(db, session_id)

        if self._llm is not None:
            try:
                llm_portrait = self._call_llm(prefs, liked_songs)
                if llm_portrait:
                    portrait = llm_portrait
                deep = self._call_llm_deep_analysis(
                    prefs, liked_songs, dialogue_history, preferred_scenes
                )
                if deep:
                    portrait["deep_analysis"] = deep.get("deep_analysis", "")
                    if deep.get("scene"):
                        portrait["scene"] = deep["scene"]
            except Exception as e:
                logger.warning(f"[Portrait] LLM 调用失败: {e}")

        prefs.save_portrait(
            db=db,
            summary=portrait["summary"],
            keywords=portrait["keywords"],
            scene=portrait["scene"],
            deep_analysis=portrait.get("deep_analysis", ""),
        )

        return portrait

    def get_cached_portrait(self, db: Session, user_id: int) -> Optional[dict]:
        """获取缓存的画像"""
        prefs = UserPreference.get_or_create(db, user_id)
        if prefs.ai_portrait_summary:
            return prefs.get_portrait()
        return None

    def _get_dialogue_history(self, db: Session, session_id: str) -> str:
        """获取最近一轮对话历史（最近10轮）"""
        try:
            from src.models.chat_history import ChatHistory

            turns = (
                db.query(ChatHistory)
                .filter(ChatHistory.session_id == session_id)
                .order_by(ChatHistory.turn_id.desc())
                .limit(10)
                .all()
            )
            turns = list(reversed(turns))
            lines = []
            for t in turns:
                lines.append(f"用户：{t.user_input}")
                resp = t.system_response[:200] if t.system_response else ""
                lines.append(f"系统：{resp}")
            return "\n".join(lines) if lines else "暂无对话记录"
        except Exception as e:
            logger.warning(f"[Portrait] 获取对话历史失败: {e}")
            return "暂无对话记录"

    def _get_preferred_scenes(self, db: Session, session_id: str) -> list[str]:
        """获取用户偏好的场景列表"""
        try:
            from src.models.session_persistence import SessionPersistence

            record = (
                db.query(SessionPersistence)
                .filter(SessionPersistence.session_id == session_id)
                .first()
            )
            if record:
                scenes = record.preferred_scenes or []
                current = record.current_scene
                if current and current not in scenes:
                    scenes = [current] + scenes
                return scenes[:5]
            return []
        except Exception as e:
            logger.warning(f"[Portrait] 获取场景偏好失败: {e}")
            return []

    def _call_llm_deep_analysis(
        self,
        prefs: UserPreference,
        songs: list[dict],
        dialogue_history: str,
        preferred_scenes: list[str],
    ) -> Optional[dict]:
        """调用 LLM 生成深度画像分析"""
        liked = prefs.liked_genre_counts or {}
        disliked = prefs.disliked_genre_counts or {}

        liked_str = (
            "、".join(
                [f"{g}({c}次)" for g, c in sorted(liked.items(), key=lambda x: -x[1])]
            )
            if liked
            else "暂无"
        )
        disliked_str = (
            "、".join(
                [
                    f"{g}({c}次)"
                    for g, c in sorted(disliked.items(), key=lambda x: -x[1])
                ]
            )
            if disliked
            else "无明确不喜欢"
        )

        energy_data = prefs.energy_scores or {}
        energy_scores = energy_data.get("scores", [])
        if not energy_scores and songs:
            energy_scores = [
                _GENRE_ENERGY_SCORE_MAP.get(s.get("genre", "").lower(), 2)
                for s in songs
                if s.get("genre")
            ]
        energy_label = _calc_energy_label(energy_scores)

        songs_list = []
        for s in songs[:15]:
            title = s.get("title", "?")
            artist = s.get("artist", "?")
            genre = s.get("genre", "") or "未知"
            songs_list.append(f"{title} - {artist}（{genre}）")
        songs_str = (
            "\n".join(f"{i + 1}. {s}" for i, s in enumerate(songs_list))
            or "暂无歌曲记录"
        )

        scene_str = (
            "、".join(preferred_scenes) if preferred_scenes else "暂无明确场景偏好"
        )

        user_data = (
            f"喜欢流派：{liked_str}\n"
            f"不喜欢流派：{disliked_str}\n"
            f"能量偏好：{energy_label}\n"
            f"歌曲总数：{len(songs)}首"
        )

        prompt = DEEP_ANALYSIS_PROMPT_TEMPLATE.format(
            user_data=user_data,
            dialogue_history=dialogue_history,
        )

        logger.info("[Portrait] 调用 LLM 生成深度分析")
        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}], json_output=True
        )

        if response.content:
            import json

            try:
                result = json.loads(response.content)
                if isinstance(result, dict) and result.get("deep_analysis"):
                    logger.info("[Portrait] 深度分析生成成功")
                    return result
            except json.JSONDecodeError as e:
                logger.warning(f"[Portrait] 深度分析 JSON 解析失败: {e}")

        return None

    def _get_liked_songs(
        self, db: Session, user_id: int, limit: int = 20
    ) -> list[dict]:
        """获取用户喜欢的歌曲列表"""
        try:
            liked_playlist = (
                db.query(Playlist)
                .filter(
                    Playlist.user_id == user_id,
                    Playlist.is_system == True,
                )
                .first()
            )
            if not liked_playlist:
                return []

            songs = (
                db.query(PlaylistSong)
                .filter(PlaylistSong.playlist_id == liked_playlist.id)
                .limit(limit)
                .all()
            )

            song_list = [
                {
                    "track_id": s.track_id,
                    "title": s.title or "",
                    "artist": s.artist or "未知艺术家",
                    "tags": s.tags if isinstance(s.tags, list) else [],
                }
                for s in songs
                if s.track_id
            ]

            if song_list:
                track_genres = self._fetch_track_genres(
                    [s["track_id"] for s in song_list]
                )
                for song in song_list:
                    song["genre"] = track_genres.get(song["track_id"], "")

            return song_list
        except Exception as e:
            logger.warning(f"[Portrait] 获取喜欢歌单失败: {e}")
            return []

    def _fetch_track_genres(self, track_ids: list[str]) -> dict[str, str]:
        """从 ChromaDB 批量获取歌曲流派"""
        if not track_ids:
            return {}
        try:
            import chromadb
            from pathlib import Path

            project_root = Path(__file__).parent.parent
            client = chromadb.PersistentClient(
                path=str(project_root / "index" / "chroma_bge_m3")
            )
            collection = client.get_collection(name="music_bge_collection")
            chroma_ids = [f"fma_{tid}" for tid in track_ids]
            results = collection.get(ids=chroma_ids, include=["metadatas"])
            genre_map: dict[str, str] = {}
            for i, cid in enumerate(results.get("ids", [])):
                if cid.startswith("fma_"):
                    tid = cid[4:]
                    metadata = (
                        results.get("metadatas", [{}])[i]
                        if i < len(results.get("metadatas", []))
                        else {}
                    )
                    genre_map[tid] = metadata.get("genre", "")
            return genre_map
        except Exception as e:
            logger.warning(f"[Portrait] ChromaDB 查询失败: {e}")
            return {}

    def _build_portrait_from_data(
        self, prefs: UserPreference, songs: list[dict]
    ) -> dict:
        """基于数据本地构建简单画像（无 LLM 调用时使用）"""
        from collections import Counter

        liked_genres_list = prefs.get_preferred_genres(top_n=5)

        if not liked_genres_list and songs:
            genre_counts: dict[str, int] = {}
            for s in songs:
                g = s.get("genre", "")
                if g:
                    genre_counts[g] = genre_counts.get(g, 0) + 1
            if genre_counts:
                liked_genres_list = [
                    t
                    for t, _ in sorted(
                        genre_counts.items(), key=lambda x: x[1], reverse=True
                    )[:5]
                ]

        liked_genres_str = (
            "、".join(liked_genres_list) if liked_genres_list else "暂无偏好"
        )

        disliked = prefs.get_disliked_genres()
        disliked_genres_str = "、".join(disliked.keys()) if disliked else "无明确不喜欢"

        energy_data = prefs.energy_scores or {}
        energy_scores = energy_data.get("scores", [])
        if not energy_scores and songs:
            energy_scores = [
                _GENRE_ENERGY_SCORE_MAP.get(s.get("genre", "").lower(), 2)
                for s in songs
                if s.get("genre")
            ]
        energy_label = _calc_energy_label(energy_scores)

        songs_list = [
            f"{s.get('title', '?')} - {s.get('artist', '?')} ({s.get('genre', '')})"
            for s in songs[:10]
        ]
        songs_str = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(songs_list) if s)

        summary = f"偏爱{liked_genres_str}，能量偏好{energy_label}"
        keywords = liked_genres_list[:3] if liked_genres_list else ["流行音乐"]
        scene = (
            "日常聆听"
            if energy_label == "中等能量"
            else ("动感场景" if energy_label == "高能量" else "安静场景")
        )

        return {
            "summary": summary,
            "keywords": keywords,
            "scene": scene,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _call_llm(self, prefs: UserPreference, songs: list[dict]) -> Optional[dict]:
        """调用 LLM 生成画像"""
        liked_genres_list = prefs.get_preferred_genres(top_n=5)
        if not liked_genres_list and songs:
            genre_counts: dict[str, int] = {}
            for s in songs:
                g = s.get("genre", "")
                if g:
                    genre_counts[g] = genre_counts.get(g, 0) + 1
            if genre_counts:
                liked_genres_list = [
                    t
                    for t, _ in sorted(
                        genre_counts.items(), key=lambda x: x[1], reverse=True
                    )[:5]
                ]
        liked_genres_str = (
            "、".join(liked_genres_list) if liked_genres_list else "暂无偏好"
        )

        disliked = prefs.get_disliked_genres()
        disliked_genres_str = "、".join(disliked.keys()) if disliked else "无明确不喜欢"

        energy_data = prefs.energy_scores or {}
        energy_scores = energy_data.get("scores", [])
        if not energy_scores and songs:
            energy_scores = [
                _GENRE_ENERGY_SCORE_MAP.get(s.get("genre", "").lower(), 2)
                for s in songs
                if s.get("genre")
            ]
        energy_label = _calc_energy_label(energy_scores)

        songs_list = []
        for s in songs[:20]:
            title = s.get("title", "?")
            artist = s.get("artist", "?")
            genre = s.get("genre", "") or "未知"
            songs_list.append(f"{title} - {artist} - {genre}")

        songs_str = (
            "\n".join(f"{i + 1}. {s}" for i, s in enumerate(songs_list))
            if songs_list
            else "暂无歌曲记录"
        )

        prompt = PORTRAIT_PROMPT_TEMPLATE.format(
            liked_genres=liked_genres_str,
            disliked_genres=disliked_genres_str,
            energy_label=energy_label,
            song_count=len(songs),
            songs_list=songs_str,
        )

        logger.info(f"[Portrait] 调用 LLM 生成画像，歌曲数: {len(songs)}")
        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}], json_output=True
        )

        if response.content:
            import json

            try:
                portrait = json.loads(response.content)
                if isinstance(portrait, dict) and "summary" in portrait:
                    portrait["generated_at"] = datetime.utcnow().isoformat()
                    logger.info("[Portrait] LLM 画像生成成功")
                    return portrait
            except json.JSONDecodeError as e:
                logger.warning(f"[Portrait] JSON 解析失败: {e}")

        logger.warning("[Portrait] LLM 返回无效，使用本地画像")
        return None
