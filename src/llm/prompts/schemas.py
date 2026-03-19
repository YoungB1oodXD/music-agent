# -*- coding: utf-8 -*-
"""
LLM 交互使用的 JSON Schema 定义
"""

# 偏好解析与查询重写 Schema (新版本)
PREFERENCE_PARSE_SCHEMA = {
    "type": "object",
    "properties": {
        "llm_check": {
            "type": "object",
            "properties": {
                "generated_by_llm": {"type": "boolean"},
                "task": {"type": "string"},
                "llm_signature": {"type": "string"}
            },
            "required": ["generated_by_llm", "task", "llm_signature"]
        },
        "updated_preference_state": {
            "type": "object",
            "properties": {
                "scene": {"type": "string"},
                "activity": {"type": "string"},
                "mood": {"type": "array", "items": {"type": "string"}},
                "energy": {"type": "string", "enum": ["high", "medium", "low", ""]},
                "tempo": {"type": "string"},
                "vocal_preference": {"type": "string"},
                "instrument_preference": {"type": "array", "items": {"type": "string"}},
                "genre_preferences": {"type": "array", "items": {"type": "string"}},
                "style_preferences": {"type": "array", "items": {"type": "string"}},
                "avoid": {"type": "array", "items": {"type": "string"}},
                "searchability_preference": {"type": "string"},
                "popularity_preference": {"type": "string"},
                "language_preference": {"type": "string"},
                "diversity_preference": {"type": "string"},
                "feedback_memory": {
                    "type": "object",
                    "properties": {
                        "liked_tracks": {"type": "array", "items": {"type": "string"}},
                        "disliked_tracks": {"type": "array", "items": {"type": "string"}},
                        "rejected_attributes": {"type": "array", "items": {"type": "string"}},
                        "preferred_attributes": {"type": "array", "items": {"type": "string"}}
                    }
                }
            }
        },
        "retrieval_query": {"type": "string"},
        "hard_filters": {
            "type": "object",
            "properties": {
                "vocal_preference": {"type": "string"},
                "searchability_preference": {"type": "string"},
                "language_preference": {"type": "string"}
            }
        },
        "soft_targets": {"type": "array", "items": {"type": "string"}},
        "avoid_terms": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["llm_check", "updated_preference_state", "retrieval_query"]
}

# 意图识别与槽位提取 Schema (保留兼容)
INTENT_AND_SLOTS_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "description": "用户的主要意图",
            "enum": ["recommend_music", "search_music", "refine_preferences", "explain_why", "feedback"]
        },
        "query_text": {
            "type": "string",
            "description": "经过改写或提取的搜索/推荐关键词"
        },
        "mood": {"type": "string", "description": "情感状态"},
        "scene": {"type": "string", "description": "使用场景"},
        "genre": {"type": "string", "description": "音乐流派"},
        "artist": {"type": "string", "description": "艺术家/歌手"},
        "song_name": {"type": "string", "description": "歌曲名称"},
        "energy": {
            "type": "string",
            "description": "音乐能量/强度",
            "enum": ["high", "medium", "low"]
        },
        "vocals": {
            "type": "string",
            "description": "人声类型",
            "enum": ["instrumental", "vocal"]
        },
        "top_k": {
            "type": "integer",
            "description": "返回结果数量限制",
            "default": 5,
            "minimum": 1,
            "maximum": 20
        },
        "feedback": {
            "type": "object",
            "description": "用户反馈信息",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["like", "dislike", "skip"]
                },
                "target_id": {
                    "type": "string",
                    "description": "反馈针对的歌曲 ID"
                }
            },
            "required": ["type"]
        }
    },
    "required": ["intent", "query_text"]
}

# 最终回复生成 Schema
FINAL_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "assistant_text": {
            "type": "string",
            "description": "直接展示给用户的中文回复文本"
        },
        "recommendations": {
            "type": "array",
            "description": "推荐的歌曲列表",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "reason": {"type": "string", "description": "推荐理由"},
                    "citations": {"type": "array", "items": {"type": "string"}, "description": "引用来源"}
                },
                "required": ["id", "name", "reason", "citations"]
            }
        },
        "followup_question": {
            "type": "string",
            "description": "引导用户的后续问题"
        }
    },
    "required": ["assistant_text", "recommendations"]
}

# 推荐解释 Schema (用于 LLM 生成推荐理由)
RECOMMENDATION_EXPLANATION_SCHEMA = {
    "type": "object",
    "properties": {
        "llm_check": {
            "type": "object",
            "properties": {
                "generated_by_llm": {"type": "boolean"},
                "task": {"type": "string"},
                "style_signature": {"type": "string"}
            },
            "required": ["generated_by_llm", "task", "style_signature"]
        },
        "reply_text": {"type": "string"},
        "track_explanations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "track_id": {"type": "string"},
                    "short_reason": {"type": "string"}
                },
                "required": ["track_id", "short_reason"]
            }
        }
    },
    "required": ["llm_check", "reply_text", "track_explanations"]
}

# 反馈自适应 Schema (用于处理用户反馈)
FEEDBACK_ADAPTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "llm_check": {
            "type": "object",
            "properties": {
                "generated_by_llm": {"type": "boolean"},
                "task": {"type": "string"},
                "feedback_signature": {"type": "string"}
            },
            "required": ["generated_by_llm", "task", "feedback_signature"]
        },
        "ack_message": {"type": "string"},
        "updated_preference_state": {
            "type": "object",
            "properties": {
                "scene": {"type": "string"},
                "activity": {"type": "string"},
                "mood": {"type": "array", "items": {"type": "string"}},
                "energy": {"type": "string"},
                "tempo": {"type": "string"},
                "vocal_preference": {"type": "string"},
                "instrument_preference": {"type": "array", "items": {"type": "string"}},
                "genre_preferences": {"type": "array", "items": {"type": "string"}},
                "style_preferences": {"type": "array", "items": {"type": "string"}},
                "avoid": {"type": "array", "items": {"type": "string"}},
                "searchability_preference": {"type": "string"},
                "popularity_preference": {"type": "string"},
                "language_preference": {"type": "string"},
                "diversity_preference": {"type": "string"},
                "feedback_memory": {
                    "type": "object",
                    "properties": {
                        "liked_tracks": {"type": "array", "items": {"type": "string"}},
                        "disliked_tracks": {"type": "array", "items": {"type": "string"}},
                        "rejected_attributes": {"type": "array", "items": {"type": "string"}},
                        "preferred_attributes": {"type": "array", "items": {"type": "string"}}
                    }
                }
            }
        },
        "next_strategy": {
            "type": "object",
            "properties": {
                "keep_core_preferences": {"type": "boolean"},
                "increase_diversity": {"type": "boolean"},
                "prefer_more_searchable": {"type": "boolean"},
                "avoid_recent_attributes": {"type": "array", "items": {"type": "string"}},
                "direction_adjustment": {"type": "string"}
            }
        }
    },
    "required": ["llm_check", "ack_message", "updated_preference_state", "next_strategy"]
}
