#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话流转模拟脚本
用于开题答辩展示多轮对话状态管理

模拟场景：
- Turn 1: 用户请求推荐适合学习的歌
- Turn 2: 系统推荐歌曲
- Turn 3: 用户反馈并请求调整
"""

import sys
from pathlib import Path
import json
from datetime import datetime
from typing import Protocol


# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.manager.session_state import SessionState


def print_separator(title: str = ""):
    """打印分隔线"""
    print("\n" + "=" * 100)
    if title:
        print(f"  {title}")
        print("=" * 100)


def print_state_snapshot(state: SessionState, turn_num: int, description: str):
    """打印状态快照"""
    print_separator(f"【Turn {turn_num}】 {description}")
    
    # 获取上下文摘要
    context = state.get_context_summary()
    
    print("\n📊 当前状态快照:")
    print("-" * 100)
    print(f"  Session ID: {state.session_id}")
    print(f"  User ID: {state.user_id}")
    print(f"  创建时间: {state.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  更新时间: {state.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n🎯 上下文状态:")
    print("-" * 100)
    print(f"  当前情感: {state.current_mood or 'None'}")
    print(f"  当前场景: {state.current_scene or 'None'}")
    print(f"  当前流派: {state.current_genre or 'None'}")
    
    print("\n💬 对话历史:")
    print("-" * 100)
    if state.dialogue_history:
        for turn in state.dialogue_history:
            print(f"  Turn {turn.turn_id}:")
            print(f"    用户: {turn.user_input}")
            print(f"    系统: {turn.system_response}")
            if turn.intent:
                print(f"    意图: {turn.intent}")
            if turn.entities:
                print(f"    实体: {turn.entities}")
            print()
    else:
        print("  （空）")
    
    print("\n🎵 推荐历史:")
    print("-" * 100)
    if state.last_recommendation:
        rec = state.last_recommendation
        print(f"  最近推荐:")
        print(f"    时间: {rec.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"    查询: {rec.query}")
        print(f"    结果: {rec.results}")
        print(f"    方法: {rec.method}")
        if rec.feedback:
            print(f"    用户反馈: {rec.feedback}")
    else:
        print("  （空）")
    
    print("\n❤️ 用户偏好:")
    print("-" * 100)
    print(f"  喜欢的歌曲: {len(state.liked_songs)} 首")
    if state.liked_songs:
        print(f"    {state.liked_songs[:5]}")
    print(f"  不喜欢的歌曲: {len(state.disliked_songs)} 首")
    if state.disliked_songs:
        print(f"    {state.disliked_songs[:5]}")
    
    print("\n📋 完整 JSON 快照:")
    print("-" * 100)
    # 转换为 JSON（处理 datetime）
    state_dict = state.model_dump()
    # 将 datetime 转为字符串
    for key in ['created_at', 'updated_at']:
        if key in state_dict and isinstance(state_dict[key], datetime):
            state_dict[key] = state_dict[key].isoformat()
    
    for turn in state_dict.get('dialogue_history', []):
        if 'timestamp' in turn and isinstance(turn['timestamp'], datetime):
            turn['timestamp'] = turn['timestamp'].isoformat()
    
    for rec in state_dict.get('recommendation_history', []):
        if 'timestamp' in rec and isinstance(rec['timestamp'], datetime):
            rec['timestamp'] = rec['timestamp'].isoformat()
    
    if state_dict.get('last_recommendation') and 'timestamp' in state_dict['last_recommendation']:
        if isinstance(state_dict['last_recommendation']['timestamp'], datetime):
            state_dict['last_recommendation']['timestamp'] = state_dict['last_recommendation']['timestamp'].isoformat()
    
    print(json.dumps(state_dict, ensure_ascii=False, indent=2))
    print("\n")


def main():
    """主函数：模拟完整会话流程"""
    print_separator("会话流转模拟 - 多轮对话状态管理演示")
    print("\n🎬 场景：用户寻找适合学习的音乐")
    print("\n")
    
    # ============================================================================
    # Turn 1: 初始化会话，用户发起请求
    # ============================================================================
    state = SessionState(
        session_id="session_demo_001",
        user_id="user_12345",
        current_mood=None,
        current_scene=None,
        current_genre=None,
        last_recommendation=None,
        dialogue_history=[],
        recommendation_history=[],
        liked_songs=[],
        disliked_songs=[],
        preferred_moods=[],
        preferred_scenes=[],
    )
    
    # 用户输入
    user_input_1 = "推荐点适合学习的歌"
    
    # 系统处理（模拟意图识别和槽位提取）
    intent_1 = "recommend"
    entities_1 = {
        "scene": "学习",
        "original_query": user_input_1
    }
    
    # 更新状态
    state.update_scene("学习")
    
    # 系统响应
    system_response_1 = "好的，我为您推荐一些适合学习的歌曲。正在搜索..."
    
    # 添加对话记录
    state.add_dialogue_turn(
        user_input=user_input_1,
        system_response=system_response_1,
        intent=intent_1,
        entities=entities_1
    )
    
    # 打印快照
    print_state_snapshot(state, 1, "用户发起推荐请求")
    
    # ============================================================================
    # Turn 2: 系统推荐歌曲
    # ============================================================================
    
    # 模拟推荐结果
    recommended_songs = ["TR_001", "TR_002", "TR_003"]
    
    # 更新推荐历史
    state.add_recommendation(
        query="适合学习的歌",
        results=recommended_songs,
        method="scene_based_retrieval"
    )
    
    # 系统响应
    system_response_2 = f"为您推荐了 {len(recommended_songs)} 首适合学习的歌曲：\n"
    system_response_2 += "  1. Classical Piano Study Music (TR_001)\n"
    system_response_2 += "  2. Ambient Focus Soundscape (TR_002)\n"
    system_response_2 += "  3. Instrumental Jazz for Concentration (TR_003)\n"
    system_response_2 += "请问您喜欢吗？"
    
    # 添加对话记录
    state.add_dialogue_turn(
        user_input="[系统内部：执行推荐]",
        system_response=system_response_2,
        intent="show_recommendation",
        entities={"song_count": len(recommended_songs)}
    )
    
    # 打印快照
    print_state_snapshot(state, 2, "系统推荐歌曲")
    
    # ============================================================================
    # Turn 3: 用户反馈并请求调整
    # ============================================================================
    
    # 用户输入
    user_input_3 = "换一首，不要太吵的"
    
    # 系统处理
    intent_3 = "refine_recommendation"
    entities_3 = {
        "feedback": "negative",
        "constraint": "不要太吵",
        "mood_hint": "平静"
    }
    
    # 更新状态
    state.update_mood("平静")
    
    # 记录负向反馈（假设用户不喜欢 TR_003）
    state.disliked_songs.append("TR_003")
    
    # 更新推荐记录的反馈
    if state.last_recommendation:
        state.last_recommendation.feedback = "negative: 太吵"
    
    # 系统响应
    system_response_3 = "明白了，我会为您推荐更安静、更平静的音乐。"
    
    # 添加对话记录
    state.add_dialogue_turn(
        user_input=user_input_3,
        system_response=system_response_3,
        intent=intent_3,
        entities=entities_3
    )
    
    # 打印快照
    print_state_snapshot(state, 3, "用户反馈并请求调整")
    
    # ============================================================================
    # 总结
    # ============================================================================
    print_separator("【模拟完成】")
    print("\n✅ 成功模拟了 3 轮对话的状态流转")
    print("\n📊 关键状态变化:")
    print("  - Turn 1: 初始化会话，识别场景='学习'")
    print("  - Turn 2: 执行推荐，记录推荐历史")
    print("  - Turn 3: 收集反馈，更新情感='平静'，记录负向反馈")
    print("\n💡 展示价值:")
    print("  1. 完整的对话历史追踪")
    print("  2. 动态的上下文状态更新（场景、情感）")
    print("  3. 推荐历史与用户反馈管理")
    print("  4. 用户偏好学习（liked/disliked songs）")
    print("\n" + "=" * 100)
    print()


if __name__ == "__main__":
    # 重定向输出到文件
    output_file = Path(__file__).parent.parent / "data" / "logs" / "session_simulation_log.txt"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 使用 tee 方式：同时输出到控制台和文件
    import io
    
    # 保存原始 stdout
    original_stdout = sys.stdout
    
    # 创建字符串缓冲区
    output_buffer = io.StringIO()
    
    # 创建一个同时写入控制台和缓冲区的类
    class _TeeTarget(Protocol):
        @property
        def encoding(self) -> str | None:
            ...

        def write(self, s: str, /) -> int:
            ...

        def flush(self) -> None:
            ...

    class TeeOutput:
        def __init__(self, *files: _TeeTarget):
            self.files: tuple[_TeeTarget, ...] = files

        def write(self, data: str) -> int:
            for f in self.files:
                try:
                    _ = f.write(data)
                except UnicodeEncodeError:
                    enc = getattr(f, "encoding", None) or "utf-8"
                    safe = data.encode(enc, errors="replace").decode(enc, errors="replace")
                    try:
                        _ = f.write(safe)
                    except Exception:
                        pass
                except Exception:
                    pass

                try:
                    f.flush()
                except Exception:
                    pass
            return len(data)

        def flush(self) -> None:
            for f in self.files:
                try:
                    f.flush()
                except Exception:
                    pass
    
    # 设置 tee 输出
    sys.stdout = TeeOutput(original_stdout, output_buffer)
    
    try:
        # 执行主函数
        main()
    finally:
        # 恢复原始 stdout
        sys.stdout = original_stdout
        
        # 保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            _ = f.write(output_buffer.getvalue())
        
        try:
            print(f"\n[ok] 会话日志已保存到: {output_file}")
        except UnicodeEncodeError:
            # 最后的保险，如果连 [ok] 这种 ASCII 都出问题（极罕见）
            pass
