# -*- coding: utf-8 -*-
"""
LLM 交互使用的 JSON Schema 定义
"""

# 意图识别与槽位提取 Schema
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
