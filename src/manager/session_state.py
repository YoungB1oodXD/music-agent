#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多轮对话会话状态管理
用于开题答辩展示系统架构设计

设计目标：
1. 管理用户当前的情感/场景上下文
2. 追踪对话历史，支持上下文理解
3. 记录推荐历史，避免重复推荐
4. 为后续 LLM 集成提供状态接口
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class RecommendationRecord(BaseModel):
    """
    单次推荐记录
    
    字段说明：
    - timestamp: 推荐时间戳
    - query: 用户查询/请求内容
    - results: 推荐结果列表（歌曲 ID 或歌名）
    - method: 推荐方法（semantic/collaborative/hybrid）
    - feedback: 用户反馈（可选，如 like/dislike/skip）
    """
    timestamp: datetime = Field(default_factory=datetime.now, description="推荐时间")
    query: str = Field(..., description="用户查询内容")
    results: List[str] = Field(default_factory=list, description="推荐结果列表")
    method: str = Field(..., description="推荐方法: semantic/collaborative/hybrid")
    feedback: Optional[str] = Field(None, description="用户反馈: like/dislike/skip")


class DialogueTurn(BaseModel):
    """
    单轮对话记录
    
    字段说明：
    - turn_id: 对话轮次编号
    - user_input: 用户输入文本
    - system_response: 系统回复文本
    - intent: 识别的用户意图（如 search/recommend/feedback）
    - entities: 提取的实体信息（如情感、场景、艺术家名）
    """
    turn_id: int = Field(..., description="对话轮次编号")
    user_input: str = Field(..., description="用户输入")
    system_response: str = Field(..., description="系统回复")
    intent: Optional[str] = Field(None, description="用户意图")
    entities: Dict[str, Any] = Field(default_factory=dict, description="提取的实体")


class SessionState(BaseModel):
    """
    会话状态类（用于多轮对话管理）
    
    核心设计：
    1. 上下文追踪：记录用户当前的情感/场景偏好
    2. 历史管理：保存对话历史和推荐历史
    3. 状态更新：支持动态更新用户偏好
    4. LLM 接口：为大语言模型提供上下文信息
    
    使用场景：
    - 用户："我想听点放松的音乐"  → 更新 current_mood = "放松"
    - 用户："推荐一些适合跑步的歌" → 更新 current_scene = "跑步"
    - 系统：根据历史推荐避免重复
    """
    
    # ===== 会话基本信息 =====
    session_id: str = Field(..., description="会话唯一标识符")
    user_id: Optional[str] = Field(None, description="用户ID（可选）")
    created_at: datetime = Field(default_factory=datetime.now, description="会话创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    
    # ===== 当前上下文状态 =====
    current_mood: Optional[str] = Field(
        None,
        description="当前情感状态（如：放松、激情、忧郁等）- 从vocab_moods.json提取"
    )
    
    current_scene: Optional[str] = Field(
        None,
        description="当前场景（如：运动、工作、约会等）- 从vocab_scenes.json提取"
    )
    
    current_genre: Optional[str] = Field(
        None,
        description="当前偏好流派（如：Rock、Jazz等）"
    )
    
    # ===== 对话历史 =====
    dialogue_history: List[DialogueTurn] = Field(
        default_factory=list,
        description="完整对话历史记录（用于上下文理解和LLM提示构建）"
    )
    
    # ===== 推荐历史 =====
    recommendation_history: List[RecommendationRecord] = Field(
        default_factory=list,
        description="历史推荐记录（用于去重和个性化）"
    )
    
    last_recommendation: Optional[RecommendationRecord] = Field(
        None,
        description="最近一次推荐结果（用于反馈收集）"
    )
    
    # ===== 用户偏好（动态学习） =====
    liked_songs: List[str] = Field(
        default_factory=list,
        description="用户喜欢的歌曲列表（基于显式反馈）"
    )
    
    disliked_songs: List[str] = Field(
        default_factory=list,
        description="用户不喜欢的歌曲列表（用于过滤）"
    )
    
    preferred_moods: List[str] = Field(
        default_factory=list,
        description="用户偏好的情感标签（频率统计）"
    )
    
    preferred_scenes: List[str] = Field(
        default_factory=list,
        description="用户偏好的场景标签（频率统计）"
    )
    
    # ===== 会话配置 =====
    max_history_turns: int = Field(
        default=10,
        description="保留的最大对话轮次（超出则淘汰最早记录）"
    )
    
    class Config:
        """Pydantic 配置"""
        # 允许字段验证
        validate_assignment = True
        # 允许任意类型（兼容性）
        arbitrary_types_allowed = True
    
    # ===== 核心方法 =====
    
    def add_dialogue_turn(self, user_input: str, system_response: str, 
                         intent: Optional[str] = None, 
                         entities: Optional[Dict[str, Any]] = None):
        """
        添加一轮对话记录
        
        Args:
            user_input: 用户输入
            system_response: 系统回复
            intent: 用户意图
            entities: 提取的实体
        """
        turn = DialogueTurn(
            turn_id=len(self.dialogue_history) + 1,
            user_input=user_input,
            system_response=system_response,
            intent=intent,
            entities=entities or {}
        )
        
        self.dialogue_history.append(turn)
        
        # 限制历史长度
        if len(self.dialogue_history) > self.max_history_turns:
            self.dialogue_history.pop(0)
        
        self.updated_at = datetime.now()
    
    def add_recommendation(self, query: str, results: List[str], 
                          method: str = "hybrid"):
        """
        添加推荐记录
        
        Args:
            query: 用户查询
            results: 推荐结果
            method: 推荐方法
        """
        record = RecommendationRecord(
            query=query,
            results=results,
            method=method
        )
        
        self.recommendation_history.append(record)
        self.last_recommendation = record
        self.updated_at = datetime.now()
    
    def update_mood(self, mood: str):
        """
        更新当前情感状态
        
        Args:
            mood: 情感标签（应从 vocab_moods.json 中选择）
        """
        self.current_mood = mood
        
        # 更新偏好统计
        if mood not in self.preferred_moods:
            self.preferred_moods.append(mood)
        
        self.updated_at = datetime.now()
    
    def update_scene(self, scene: str):
        """
        更新当前场景
        
        Args:
            scene: 场景标签（应从 vocab_scenes.json 中选择）
        """
        self.current_scene = scene
        
        # 更新偏好统计
        if scene not in self.preferred_scenes:
            self.preferred_scenes.append(scene)
        
        self.updated_at = datetime.now()
    
    def add_feedback(self, song_id: str, feedback: str):
        """
        添加用户反馈
        
        Args:
            song_id: 歌曲ID
            feedback: 反馈类型（like/dislike/skip）
        """
        if feedback == "like":
            if song_id not in self.liked_songs:
                self.liked_songs.append(song_id)
        elif feedback == "dislike":
            if song_id not in self.disliked_songs:
                self.disliked_songs.append(song_id)
        
        # 更新最后推荐的反馈
        if self.last_recommendation:
            self.last_recommendation.feedback = feedback
        
        self.updated_at = datetime.now()
    
    def get_context_summary(self) -> Dict[str, Any]:
        """
        获取当前上下文摘要（用于LLM提示构建）
        
        Returns:
            上下文信息字典
        """
        return {
            "current_mood": self.current_mood,
            "current_scene": self.current_scene,
            "current_genre": self.current_genre,
            "recent_dialogues": [
                {
                    "user": turn.user_input,
                    "system": turn.system_response
                }
                for turn in self.dialogue_history[-3:]  # 最近3轮
            ],
            "liked_count": len(self.liked_songs),
            "disliked_count": len(self.disliked_songs),
            "recommendation_count": len(self.recommendation_history)
        }
    
    def reset_context(self):
        """
        重置上下文状态（保留历史记录）
        """
        self.current_mood = None
        self.current_scene = None
        self.current_genre = None
        self.updated_at = datetime.now()


# ============================================================================
# 使用示例（用于开题答辩演示）
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("会话状态管理模块 - 使用示例")
    print("=" * 80)
    
    # 创建会话
    session = SessionState(
        session_id="demo_session_001",
        user_id="user_123"
    )
    
    print("\n【步骤 1】初始化会话")
    print(f"  Session ID: {session.session_id}")
    print(f"  Created at: {session.created_at}")
    
    # 模拟对话
    print("\n【步骤 2】模拟多轮对话")
    session.add_dialogue_turn(
        user_input="我想听点放松的音乐",
        system_response="好的，我为你推荐一些放松的歌曲。你喜欢什么类型的音乐呢？",
        intent="search_by_mood",
        entities={"mood": "放松"}
    )
    session.update_mood("放松")
    
    session.add_dialogue_turn(
        user_input="Jazz 或者轻音乐都可以",
        system_response="明白了，为你推荐 Jazz 风格的放松音乐。",
        intent="refine_genre",
        entities={"genre": "Jazz"}
    )
    
    print(f"  对话轮次: {len(session.dialogue_history)}")
    print(f"  当前情感: {session.current_mood}")
    
    # 添加推荐
    print("\n【步骤 3】记录推荐结果")
    session.add_recommendation(
        query="放松的Jazz音乐",
        results=["Song A", "Song B", "Song C"],
        method="hybrid"
    )
    
    print(f"  推荐歌曲数: {len(session.last_recommendation.results)}")
    print(f"  推荐方法: {session.last_recommendation.method}")
    
    # 用户反馈
    print("\n【步骤 4】收集用户反馈")
    session.add_feedback("Song A", "like")
    session.add_feedback("Song B", "dislike")
    
    print(f"  喜欢的歌曲: {session.liked_songs}")
    print(f"  不喜欢的歌曲: {session.disliked_songs}")
    
    # 上下文摘要
    print("\n【步骤 5】生成上下文摘要（用于LLM）")
    context = session.get_context_summary()
    print(f"  当前情感: {context['current_mood']}")
    print(f"  最近对话轮次: {len(context['recent_dialogues'])}")
    print(f"  喜欢/不喜欢: {context['liked_count']}/{context['disliked_count']}")
    
    # 导出为 JSON
    print("\n【步骤 6】导出会话状态")
    print(session.model_dump_json(indent=2))
    
    print("\n" + "=" * 80)
    print("示例完成！此模块可用于多轮对话状态管理。")
    print("=" * 80)
