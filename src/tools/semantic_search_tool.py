import ast
import csv
import json
from pathlib import Path
from typing import Protocol, cast

from src.searcher.music_searcher import MusicSearcher

# Lazy-loaded genres ID→name mapping (loaded once on first use)
_GENRES_ID_TO_NAME: dict[str, str] | None = None


def _get_genres_id_to_name() -> dict[str, str]:
    """Load FMA genres.csv and return {genre_id: genre_title} mapping."""
    global _GENRES_ID_TO_NAME
    if _GENRES_ID_TO_NAME is not None:
        return _GENRES_ID_TO_NAME

    _GENRES_ID_TO_NAME = {}
    genres_csv_path = (
        Path(__file__).parent.parent.parent
        / "dataset"
        / "raw"
        / "fma_metadata"
        / "fma_metadata"
        / "genres.csv"
    )
    if genres_csv_path.exists():
        try:
            with open(genres_csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)  # skip header
                for row in reader:
                    if len(row) >= 4:
                        genre_id = row[0].strip()
                        title = row[3].strip()
                        if genre_id and title:
                            _GENRES_ID_TO_NAME[genre_id] = title
        except Exception:
            pass

    # Fallback for common IDs (best-effort)
    _FALLBACK_GENRES = {
        "15": "Electronic",
        "4": "Jazz",
        "12": "Rock",
        "10": "Pop",
        "17": "Folk",
        "5": "Classical",
        "21": "Hip-Hop",
        "38": "Experimental",
        "2": "International",
        "3": "Blues",
        "9": "Country",
        "14": "Soul-RnB",
        "8": "Old-Time / Historic",
        "20": "Spoken",
        "13": "Easy Listening",
        "1235": "Instrumental",
    }
    for k, v in _FALLBACK_GENRES.items():
        _GENRES_ID_TO_NAME.setdefault(k, v)

    return _GENRES_ID_TO_NAME


def _convert_genre_id_to_name(genre_value: str) -> str:
    """
    Convert a genre value that might be a numeric ID or a name.
    Returns the name if conversion succeeds, otherwise returns the original value.
    """
    genres_map = _get_genres_id_to_name()
    # Try as numeric string key first
    if genre_value in genres_map:
        return genres_map[genre_value]
    # Try as integer key
    try:
        int_key = str(int(genre_value))
        if int_key in genres_map:
            return genres_map[int_key]
    except (ValueError, OverflowError):
        pass
    # Already a name, return as-is
    return genre_value


SEMANTIC_SEARCH_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "query_text": {"type": "string"},
        "top_k": {"type": "integer"},
        "exclude_ids": {"type": "array"},
        "exclude_artists": {"type": "array"},
        "demo_mode": {"type": "boolean"},
    },
    "required": ["query_text", "top_k"],
}


_searcher: MusicSearcher | None = None
_audio_mapping: dict[str, str] | None = None
_SEMANTIC_CANDIDATE_CAP = 40
_SEMANTIC_CANDIDATE_MULTIPLIER = 4
_MIN_SEMANTIC_SIMILARITY = 0.26
_HARD_MIN_SEMANTIC_SIMILARITY = 0.18


_AUDIO_STATIC_ROOT = (
    Path(__file__).parent.parent.parent / "dataset" / "raw" / "fma_small"
)
_MIN_AUDIO_FILE_SIZE = 1000

_GENRE_DESCRIPTIONS: dict[str, str] = {
    "ambient": "氛围音乐弱化节奏与旋律推进，强调空间感与沉浸感，适合独处与思考",
    "electronic": "电子音乐强调合成器音色与节奏编排，风格多变，适合多种场景",
    "instrumental": "器乐作品没有人声，旋律与编曲成为核心，适合专注与放松",
    "classical": "古典音乐结构严谨、层次丰富，适合需要沉浸感的场景",
    "jazz": "爵士乐强调即兴与和声变化，氛围轻松而富有格调",
    "rock": "摇滚乐节奏鲜明、能量充沛，适合需要动力的时刻",
    "pop": "流行音乐旋律上口、结构清晰，易于接受和共鸣",
    "folk": "民谣风格质朴自然，强调叙事与情感表达",
    "hip-hop": "嘻哈音乐节奏感强，强调律动与态度表达",
    "lo-fi": "低保真音乐带有温暖的噪点与松散节拍，适合放松与陪伴",
    "chill": "轻松舒缓的音乐，节奏平稳，适合日常背景",
    "experimental": "实验音乐突破传统结构，探索新声音与表达方式",
}

_GENRE_MOOD_TAGS: dict[str, list[str]] = {
    "ambient": ["calm", "dreamy", "introspective"],
    "electronic": ["energetic", "modern", "urban"],
    "instrumental": ["peaceful", "focused", "serene"],
    "classical": ["elegant", "emotional", "timeless"],
    "jazz": ["sophisticated", "relaxed", "soulful"],
    "rock": ["energetic", "bold", "expressive"],
    "pop": ["uplifting", "catchy", "accessible"],
    "folk": ["warm", "nostalgic", "sincere"],
    "hip-hop": ["confident", "rhythmic", "urban"],
    "lo-fi": ["cozy", "nostalgic", "relaxed"],
    "chill": ["relaxed", "easygoing", "mellow"],
    "experimental": ["curious", "unconventional", "exploratory"],
}

_GENRE_SCENE_TAGS: dict[str, list[str]] = {
    "ambient": ["late-night", "study", "solo-walk"],
    "electronic": ["workout", "commute", "party"],
    "instrumental": ["study", "work", "relaxation"],
    "classical": ["dinner", "reflection", "evening"],
    "jazz": ["cafe", "evening", "social"],
    "rock": ["workout", "drive", "energy-boost"],
    "pop": ["commute", "social", "anytime"],
    "folk": ["morning", "nature", "reflection"],
    "hip-hop": ["workout", "urban", "night-out"],
    "lo-fi": ["study", "late-night", "chill"],
    "chill": ["anytime", "background", "relaxation"],
    "experimental": ["focus", "creative-work", "discovery"],
}

_GENRE_INSTRUMENTATION: dict[str, list[str]] = {
    "ambient": ["synth pads", "reverb", "minimal percussion"],
    "electronic": ["synthesizer", "drum machine", "bass"],
    "instrumental": ["piano", "strings", "guitar"],
    "classical": ["orchestra", "piano", "strings"],
    "jazz": ["piano", "saxophone", "double bass", "drums"],
    "rock": ["electric guitar", "bass", "drums"],
    "pop": ["varied instruments", "electronic elements", "vocals"],
    "folk": ["acoustic guitar", "folk instruments", "soft percussion"],
    "hip-hop": ["beats", "bass", "samples"],
    "lo-fi": ["soft drums", "piano", "vinyl crackle"],
    "chill": ["soft keys", "gentle beats", "ambient textures"],
    "experimental": ["varied and unconventional", "found sounds", "synthesis"],
}

_GENRE_ENERGY: dict[str, str] = {
    "ambient": "低能量，适合安静与沉浸",
    "electronic": "中高能量，节奏感强",
    "instrumental": "中低能量，平稳舒缓",
    "classical": "能量多变，情绪跨度大",
    "jazz": "中等能量，轻松有格调",
    "rock": "高能量，充满动力",
    "pop": "中等能量，易于接受",
    "folk": "中低能量，温暖自然",
    "hip-hop": "中高能量，律动感强",
    "lo-fi": "低能量，适合放松陪伴",
    "chill": "低能量，轻松舒适",
    "experimental": "能量不定，探索性强",
}


def _derive_explanation_fields(genre: str | None) -> dict[str, object]:
    if not genre:
        return {}

    genre_lower = genre.lower().strip()
    matched_key = None
    for key in _GENRE_DESCRIPTIONS:
        if key in genre_lower or genre_lower in key:
            matched_key = key
            break

    if not matched_key:
        return {}

    fields: dict[str, object] = {}

    if matched_key in _GENRE_DESCRIPTIONS:
        fields["genre_description"] = _GENRE_DESCRIPTIONS[matched_key]
    if matched_key in _GENRE_MOOD_TAGS:
        fields["mood_tags"] = _GENRE_MOOD_TAGS[matched_key]
    if matched_key in _GENRE_SCENE_TAGS:
        fields["scene_tags"] = _GENRE_SCENE_TAGS[matched_key]
    if matched_key in _GENRE_INSTRUMENTATION:
        fields["instrumentation"] = _GENRE_INSTRUMENTATION[matched_key]
    if matched_key in _GENRE_ENERGY:
        fields["energy_note"] = _GENRE_ENERGY[matched_key]

    return fields


def _get_audio_mapping() -> dict[str, str]:
    global _audio_mapping
    if _audio_mapping is None:
        mapping_path = (
            Path(__file__).parent.parent.parent
            / "data"
            / "processed"
            / "audio_mapping.json"
        )
        if mapping_path.exists():
            with open(mapping_path, "r", encoding="utf-8") as f:
                _audio_mapping = json.load(f)
        else:
            _audio_mapping = {}
    return _audio_mapping or {}


def _get_audio_info(track_id: str) -> dict[str, object]:
    mapping = _get_audio_mapping()
    track_id_str = str(track_id)
    if track_id_str not in mapping:
        return {"is_playable": False, "audio_url": None}

    raw_path = mapping[track_id_str]
    if raw_path.startswith("fma_small/"):
        audio_path = raw_path[len("fma_small/") :]
    else:
        audio_path = raw_path

    full_file_path = _AUDIO_STATIC_ROOT / audio_path
    if not full_file_path.exists():
        return {"is_playable": False, "audio_url": None}

    file_size = full_file_path.stat().st_size
    if file_size < _MIN_AUDIO_FILE_SIZE:
        return {"is_playable": False, "audio_url": None}

    return {"is_playable": True, "audio_url": f"/audio/{audio_path}"}


class _SearcherProtocol(Protocol):
    def search(self, query: str, top_k: int = 5) -> list[dict[str, object]]: ...


def _get_searcher() -> MusicSearcher:
    global _searcher
    if _searcher is None:
        _searcher = MusicSearcher()
    return _searcher


def _parse_exclude_ids(args: dict[str, object]) -> set[str]:
    raw_obj = args.get("exclude_ids")
    if not isinstance(raw_obj, list):
        return set()

    raw = cast(list[object], raw_obj)
    parsed: set[str] = set()
    for value_obj in raw:
        if not isinstance(value_obj, str):
            continue
        normalized = value_obj.strip()
        if normalized:
            parsed.add(normalized)
    return parsed


def _parse_exclude_artists(args: dict[str, object]) -> set[str]:
    raw_obj = args.get("exclude_artists")
    if not isinstance(raw_obj, list):
        return set()

    raw = cast(list[object], raw_obj)
    parsed: set[str] = set()
    for value_obj in raw:
        if not isinstance(value_obj, str):
            continue
        normalized = value_obj.strip().lower()
        if normalized:
            parsed.add(normalized)
    return parsed


def _collect_result_ids(item: dict[str, object]) -> set[str]:
    comparable_ids: set[str] = set()
    for key in ("track_id", "id"):
        value = item.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (str, int, float)):
            normalized = str(value).strip()
            if normalized:
                comparable_ids.add(normalized)
    return comparable_ids


def _expand_query_text(query_text: str) -> str:
    """
    Low-risk bilingual query expansion for Chinese scene/mood queries.
    Appends English keywords to improve retrieval in English-heavy metadata.
    """
    expansion_map = {
        ("学习", "复习", "专注"): "study learning focus",
        ("轻音乐", "纯音乐", "器乐"): "instrumental calm ambient",
        ("emo", "难过", "伤心", "安静"): "calm quiet sad",
        ("夜跑", "跑步", "运动", "健身"): "run runner running workout",
        ("高能量", "动感", "燃", "节奏"): "energy energetic upbeat",
        ("夜", "深夜"): "night",
    }

    added_words: list[str] = []
    query_lower = query_text.lower()

    for triggers, expansion in expansion_map.items():
        if any(trigger in query_lower for trigger in triggers):
            for word in expansion.split():
                if word not in query_lower and word not in added_words:
                    added_words.append(word)

    if not added_words:
        return query_text

    # Cap at 12 extra words
    final_expansion = " ".join(added_words[:12])
    return f"{query_text} {final_expansion}".strip()


def _coerce_similarity_to_float(value: object) -> float:
    """
    Safely converts a similarity value to float.
    Treats bool as non-numeric (0.0).
    """
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def semantic_search(args: dict[str, object]) -> dict[str, object]:
    query_text = str(args["query_text"])
    expanded_query = _expand_query_text(query_text)
    top_k = max(1, int(cast(int | float | str, args["top_k"])))
    candidate_k = min(_SEMANTIC_CANDIDATE_CAP, top_k * _SEMANTIC_CANDIDATE_MULTIPLIER)
    exclude_ids = _parse_exclude_ids(args)
    exclude_artists = _parse_exclude_artists(args)

    try:
        searcher = cast(_SearcherProtocol, _get_searcher())
        if expanded_query != query_text:
            results_orig = searcher.search(query_text, top_k=candidate_k)
            results_expanded = searcher.search(expanded_query, top_k=candidate_k)

            merged: dict[str, dict[str, object]] = {}
            for item in results_orig + results_expanded:
                item_ids = _collect_result_ids(item)
                if not item_ids:
                    continue
                key = sorted(list(item_ids))[0]
                if key not in merged:
                    merged[key] = item
                else:
                    existing_sim = _coerce_similarity_to_float(
                        merged[key].get("similarity")
                    )
                    current_sim = _coerce_similarity_to_float(item.get("similarity"))
                    if current_sim > existing_sim:
                        merged[key] = item

            results = sorted(
                merged.values(),
                key=lambda x: _coerce_similarity_to_float(x.get("similarity")),
                reverse=True,
            )
        else:
            results = searcher.search(query_text, top_k=candidate_k)
    except FileNotFoundError as exc:
        return {"ok": False, "data": [], "error": str(exc)}
    except ImportError as exc:
        return {"ok": False, "data": [], "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "data": [], "error": f"Semantic search failed: {exc}"}

    data: list[dict[str, object]] = []
    for item in results:
        if exclude_ids:
            comparable_ids = _collect_result_ids(item)
            if comparable_ids and comparable_ids.intersection(exclude_ids):
                continue

        if exclude_artists:
            artist = str(item.get("artist", "")).strip().lower()
            if artist and artist in exclude_artists:
                continue

        track_id = str(item.get("track_id", ""))
        audio_info = _get_audio_info(track_id)
        genre = str(item.get("genre", ""))
        if not genre:
            genres_all_str = str(item.get("genres_all", ""))
            if genres_all_str and genres_all_str != "nan":
                try:
                    genres_list = ast.literal_eval(genres_all_str)
                    if isinstance(genres_list, list) and genres_list:
                        raw_genre = str(genres_list[0])
                        genre = _convert_genre_id_to_name(raw_genre)
                except Exception:
                    pass
        explanation_fields = _derive_explanation_fields(genre)

        result_item: dict[str, object] = {
            "id": cast(object, item.get("id")),
            "title": cast(object, item.get("title")),
            "artist": cast(object, item.get("artist")),
            "genre": cast(object, genre),
            "track_id": cast(object, track_id),
            "similarity": cast(object, item.get("similarity")),
            "distance": cast(object, item.get("distance")),
            "is_playable": audio_info["is_playable"],
            "audio_url": cast(object, audio_info["audio_url"]),
        }
        result_item.update(explanation_fields)
        data.append(result_item)

    preferred: list[dict[str, object]] = []
    floor_passed: list[dict[str, object]] = []
    for row in data:
        similarity_obj = row.get("similarity")
        if isinstance(similarity_obj, bool):
            continue
        if not isinstance(similarity_obj, (int, float)):
            continue
        similarity = float(similarity_obj)
        if similarity >= _MIN_SEMANTIC_SIMILARITY:
            preferred.append(row)
        elif similarity >= _HARD_MIN_SEMANTIC_SIMILARITY:
            floor_passed.append(row)

    selected: list[dict[str, object]] = preferred[:top_k]
    if len(selected) < top_k:
        for row in floor_passed:
            selected.append(row)
            if len(selected) >= top_k:
                break

    if not selected and data:
        selected = [data[0]]

    return {"ok": True, "data": selected}
