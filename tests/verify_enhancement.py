#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证增强效果脚本
用于开题答辩展示"规则增强"的实际效果

功能：
1. 读取原始数据和增强后的数据
2. 随机选取3首不同流派的歌曲
3. 并排对比展示Before/After的rich_text
4. 保存对比报告到docs/enhancement_report.txt
"""

import pandas as pd
from pathlib import Path
import random
from typing import List, Tuple


def select_diverse_samples(df: pd.DataFrame, n: int = 3) -> List[int]:
    """
    选择不同流派的样本索引
    
    Args:
        df: 数据框
        n: 需要选择的样本数
    
    Returns:
        样本索引列表
    """
    # 获取所有非空流派
    genre_groups = df[df['genre'] != ''].groupby('genre')
    
    # 优先选择的流派
    preferred_genres = ['Rock', 'Jazz', 'Pop', 'Electronic', 'Classical', 'Hip-Hop']
    
    selected_indices = []
    selected_genres = []
    
    # 优先从preferred_genres中选择
    for genre in preferred_genres:
        if len(selected_indices) >= n:
            break
        if genre in genre_groups.groups:
            # 从该流派中随机选一首
            genre_indices = genre_groups.groups[genre].tolist()
            idx = random.choice(genre_indices)
            selected_indices.append(idx)
            selected_genres.append(genre)
    
    # 如果还不够，从其他流派补充
    if len(selected_indices) < n:
        remaining_genres = set(genre_groups.groups.keys()) - set(selected_genres)
        for genre in remaining_genres:
            if len(selected_indices) >= n:
                break
            genre_indices = genre_groups.groups[genre].tolist()
            idx = random.choice(genre_indices)
            selected_indices.append(idx)
            selected_genres.append(genre)
    
    return selected_indices


def format_comparison(row: pd.Series, index: int) -> str:
    """
    格式化单首歌曲的对比信息
    
    Args:
        row: 歌曲数据行
        index: 序号
    
    Returns:
        格式化的对比文本
    """
    lines = []
    lines.append("=" * 100)
    lines.append(f"歌曲 #{index + 1}: {row['title']} - {row['artist']}")
    lines.append("=" * 100)
    lines.append(f"流派: {row['genre']}")
    lines.append("")
    
    # Before部分
    lines.append("【增强前 - Before】")
    lines.append("-" * 100)
    before_text = row.get('rich_text', 'N/A')
    if before_text and before_text != 'N/A':
        lines.append(before_text)
    else:
        # 如果原始没有rich_text，构造基础文本
        base = f"Song: {row['title']} by {row['artist']}. Genre: {row['genre'] if row['genre'] else 'Unknown'}."
        lines.append(base)
    lines.append("")
    
    # After部分
    lines.append("【增强后 - After】")
    lines.append("-" * 100)
    after_text = row.get('rich_text_enhanced', 'N/A')
    lines.append(after_text)
    lines.append("")
    
    # 对比说明
    lines.append("【增强效果】")
    lines.append("-" * 100)
    if 'Mood:' in after_text:
        mood_part = after_text.split('Mood:')[1].split('.')[0].strip()
        lines.append(f"✅ 添加了情感标签: {mood_part}")
    if 'Scene:' in after_text:
        scene_part = after_text.split('Scene:')[1].split('.')[0].strip()
        lines.append(f"✅ 添加了场景标签: {scene_part}")
    lines.append("")
    
    return '\n'.join(lines)


def main():
    """主函数：执行验证和对比"""
    print("=" * 100)
    print("验证增强效果 - 对比展示")
    print("=" * 100)
    
    # 路径设置
    project_root = Path(__file__).parent.parent
    original_file = project_root / "data" / "processed" / "unified_songs_bge.parquet"
    enhanced_file = project_root / "data" / "processed" / "unified_songs_enhanced.parquet"
    output_file = project_root / "docs" / "enhancement_report.txt"
    
    # 读取数据
    print(f"\n📖 正在读取数据...")
    print(f"   原始文件: {original_file}")
    print(f"   增强文件: {enhanced_file}")
    
    if not enhanced_file.exists():
        print(f"\n❌ 错误: 增强文件不存在，请先运行 apply_enhancement.py")
        return
    
    df_original = pd.read_parquet(original_file)
    df_enhanced = pd.read_parquet(enhanced_file)
    
    print(f"   原始记录数: {len(df_original):,}")
    print(f"   增强记录数: {len(df_enhanced):,}")
    
    # 合并数据（保留原始的rich_text和增强的rich_text_enhanced）
    df = df_enhanced.copy()
    if 'rich_text' in df_original.columns:
        df['rich_text'] = df_original['rich_text']
    
    # 设置随机种子
    random.seed(42)
    
    # 选择样本
    print(f"\n🎯 正在选择不同流派的样本...")
    selected_indices = select_diverse_samples(df, n=3)
    
    # 生成对比报告
    print(f"\n📝 正在生成对比报告...")
    
    report_lines = []
    report_lines.append("╔" + "═" * 98 + "╗")
    report_lines.append("║" + " " * 30 + "增强效果验证报告" + " " * 50 + "║")
    report_lines.append("║" + " " * 20 + "面向多轮交互的智能音乐推荐对话助手" + " " * 36 + "║")
    report_lines.append("╚" + "═" * 98 + "╝")
    report_lines.append("")
    report_lines.append("【说明】")
    report_lines.append("本报告展示基于流派的情感/场景增强效果。")
    report_lines.append("增强前：仅包含歌曲基本信息（标题、艺术家、专辑、流派）")
    report_lines.append("增强后：添加了根据流派推理的情感标签(Mood)和场景标签(Scene)")
    report_lines.append("")
    report_lines.append("")
    
    # 逐个生成对比
    for i, idx in enumerate(selected_indices):
        row = df.iloc[idx]
        comparison = format_comparison(row, i)
        report_lines.append(comparison)
        
        # 同时打印到终端
        print(f"\n{comparison}")
    
    # 添加总结
    report_lines.append("")
    report_lines.append("=" * 100)
    report_lines.append("【总结】")
    report_lines.append("=" * 100)
    report_lines.append("通过基于流派的规则映射，成功为歌曲添加了情感和场景维度的语义信息。")
    report_lines.append("这些增强信息将用于：")
    report_lines.append("  1. 多轮对话中的上下文理解（如\"我想听放松的歌\"）")
    report_lines.append("  2. 场景化推荐（如\"推荐适合运动的音乐\"）")
    report_lines.append("  3. 提升向量检索的语义匹配精度")
    report_lines.append("=" * 100)
    
    # 保存报告
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\n✅ 对比报告已保存: {output_file}")
    print(f"   共对比 {len(selected_indices)} 首不同流派的歌曲")
    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
