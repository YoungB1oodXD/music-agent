#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时数据检查脚本"""

import pandas as pd
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "processed" / "unified_songs_bge.parquet"

# 加载数据
print("=== 加载数据 ===")
print(f"数据文件: {DATA_FILE}")
df = pd.read_parquet(DATA_FILE)

# 基本信息
print("\n=== 数据集基本信息 ===")
print(f"总记录数: {len(df):,}")
print(f"字段列表: {list(df.columns)}")
print(f"文件大小: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")

# 数据类型
print("\n=== 数据类型 ===")
print(df.dtypes)

# 前5条记录
print("\n=== 前5条记录 ===")
print(df.head())

# rich_text 示例
print("\n=== rich_text 示例（前3条）===")
for i in range(min(3, len(df))):
    print(f"\n[{i+1}] {df['rich_text'].iloc[i]}")

# 统计信息
print("\n=== 标签统计 ===")
has_tags = df['tags'].apply(lambda x: len(x) > 0 if isinstance(x, list) else False).sum()
no_tags = len(df) - has_tags
print(f"有标签的记录: {has_tags:,} ({has_tags/len(df)*100:.2f}%)")
print(f"无标签的记录: {no_tags:,} ({no_tags/len(df)*100:.2f}%)")

# 字段完整性
print("\n=== 字段完整性 ===")
for col in df.columns:
    null_count = df[col].isnull().sum()
    if col == 'tags':  # tags 是列表类型
        empty_count = df[col].apply(lambda x: len(x) == 0 if isinstance(x, list) else True).sum()
    elif df[col].dtype == 'object':
        empty_count = (df[col] == '').sum()
    else:
        empty_count = 0
    print(f"{col:15s}: 空值={null_count:6,}, 空/空列表={empty_count:6,}")

# Genre 分布
print("\n=== Genre 分布（Top 10）===")
genre_counts = df['genre'].value_counts().head(10)
for genre, count in genre_counts.items():
    print(f"  {genre:20s}: {count:6,} ({count/len(df)*100:.2f}%)")

print("\n✅ 数据检查完成！")
