#!/usr/bin/env python3
"""
补全缺失的 genre 数据 (修正版)

核心逻辑：
1. genres.csv 有 top_level 列，表示流派的顶级归属
2. 需要追溯到顶级流派 ID，然后再查 title
3. 最终归一化到 16 种主要流派
"""

import os
import sys
import json
import shutil
from pathlib import Path
from collections import Counter

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd


# 16 种主要流派映射 (基于 data_summary.json 中的 16 种)
MAIN_GENRES = {
    "Rock": "Rock",
    "Experimental": "Experimental",
    "Electronic": "Electronic",
    "Hip-Hop": "Hip-Hop",
    "Folk": "Folk",
    "Pop": "Pop",
    "Instrumental": "Instrumental",
    "International": "International",
    "Classical": "Classical",
    "Jazz": "Jazz",
    "Old-Time / Historic": "Old-Time / Historic",
    "Spoken": "Spoken",
    "Country": "Country",
    "Soul-RnB": "Soul-RnB",
    "Blues": "Blues",
    "Easy Listening": "Easy Listening",
    # 未知/default
    "Unknown": "Instrumental",
}


def load_fma_genre_mapping(genres_csv_path: Path) -> dict[str, str]:
    """读取 FMA genres.csv，建立 genre_id -> 顶级流派 映射"""
    # genre_id -> {title, top_level}
    id_to_info = {}
    id_to_title = {}

    with open(genres_csv_path, "r", encoding="utf-8") as f:
        next(f)  # skip header
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 5:
                genre_id = parts[0].strip()
                title = parts[3].strip()
                top_level = parts[4].strip()
                if genre_id and title:
                    id_to_info[genre_id] = {"title": title, "top_level": top_level}
                    id_to_title[genre_id] = title

    # 建立 genre_id -> 顶级流派名称 的映射
    genre_to_top = {}
    for gid, info in id_to_info.items():
        top = info["top_level"]
        if top == "0" or not top:
            # 自己就是顶级流派
            genre_to_top[gid] = id_to_title.get(gid, "")
        else:
            # 追溯到顶级流派
            top_title = id_to_title.get(top, "")
            genre_to_top[gid] = top_title

    return genre_to_top


def parse_genres_all(genres_all_str: str) -> list[int]:
    """解析 genres_all 字符串"""
    if not genres_all_str or genres_all_str == "nan":
        return []
    try:
        if isinstance(genres_all_str, str):
            genres_all_str = genres_all_str.strip().strip("[]")
            if not genres_all_str:
                return []
            return [int(x.strip()) for x in genres_all_str.split(",") if x.strip()]
        elif isinstance(genres_all_str, list):
            return [int(x) for x in genres_all_str if x]
    except (ValueError, TypeError):
        pass
    return []


def get_top_genre_name(genre_ids: list[int], mapping: dict[str, str]) -> str:
    """从 genres_all 数组获取顶级流派名称"""
    if not genre_ids:
        return ""

    for gid in genre_ids:
        gid_str = str(gid)
        if gid_str in mapping:
            top_genre = mapping[gid_str]
            if top_genre in MAIN_GENRES:
                return top_genre
            # 模糊匹配
            for main_genre in MAIN_GENRES:
                if (
                    main_genre.lower() in top_genre.lower()
                    or top_genre.lower() in main_genre.lower()
                ):
                    return main_genre

    return ""


def normalize_genre(genre: str) -> str:
    """归一化流派名称到 16 种主要流派"""
    if not genre or genre == "nan":
        return ""

    # 直接匹配
    if genre in MAIN_GENRES:
        return genre

    # 模糊匹配
    genre_lower = genre.lower()
    for main_genre in MAIN_GENRES:
        if main_genre.lower() == genre_lower:
            return main_genre
        if main_genre.lower() in genre_lower or genre_lower in main_genre.lower():
            return main_genre

    return "Instrumental"  # 默认


def supplement_genres(
    df: pd.DataFrame, fma_mapping: dict[str, str]
) -> tuple[pd.DataFrame, dict]:
    """补全缺失的 genre 数据"""
    stats = {
        "total_songs": len(df),
        "missing_before": 0,
        "supplemented": 0,
        "still_missing": 0,
        "genre_distribution_after": {},
    }

    # 统计补全前缺失数量
    missing_mask = (df["genre"] == "") | df["genre"].isna()
    stats["missing_before"] = int(missing_mask.sum())

    # 逐行处理
    new_genres = []
    for idx, row in df.iterrows():
        genre = row.get("genre", "")
        if pd.isna(genre) or genre == "" or genre == "nan":
            # 缺失，需要补全
            genres_all = row.get("genres_all", "")
            genre_ids = parse_genres_all(genres_all)

            if genre_ids:
                # 获取顶级流派名称
                top_genre = get_top_genre_name(genre_ids, fma_mapping)
                # 归一化
                final_genre = normalize_genre(top_genre)
                new_genres.append(final_genre if final_genre else "Instrumental")
            else:
                new_genres.append("Instrumental")
        else:
            # 已有流派，归一化
            new_genres.append(normalize_genre(genre))

    df["genre"] = new_genres

    # 统计
    still_missing = (
        (df["genre"] == "") | df["genre"].isna() | (df["genre"] == "nan")
    ).sum()
    stats["supplemented"] = stats["missing_before"] - int(still_missing)
    stats["still_missing"] = int(still_missing)

    # 流派分布
    genre_counts = df["genre"].value_counts().to_dict()
    stats["genre_distribution_after"] = {
        k: int(v) for k, v in genre_counts.items() if k and k != "nan"
    }

    return df, stats


def update_genre_stats(stats: dict, output_path: Path):
    """更新 genre_stats.json"""
    genre_stats = {
        "description": "流派分布统计（补全后）",
        "total_songs": stats["total_songs"],
        "missing_before": stats["missing_before"],
        "supplemented": stats["supplemented"],
        "still_missing": stats["still_missing"],
        "coverage_rate": round(
            (stats["total_songs"] - stats["still_missing"])
            / stats["total_songs"]
            * 100,
            2,
        ),
        "genre_distribution": stats["genre_distribution_after"],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(genre_stats, f, ensure_ascii=False, indent=2)

    return genre_stats


def main():
    print("=" * 60)
    print("Genre 补全脚本 (修正版)")
    print("=" * 60)

    # 路径
    data_dir = project_root / "data" / "processed"
    bge_parquet = data_dir / "unified_songs_bge.parquet"
    enhanced_parquet = data_dir / "unified_songs_enhanced.parquet"
    genres_csv = (
        project_root
        / "dataset"
        / "raw"
        / "fma_metadata"
        / "fma_metadata"
        / "genres.csv"
    )
    genre_stats_path = data_dir / "genre_stats.json"

    # 1. 备份 (使用.bak2避免覆盖之前的备份)
    print("\n[1/5] 备份原始文件...")
    for name in ["bge", "enhanced"]:
        src = bge_parquet if name == "bge" else enhanced_parquet
        dst = src.with_suffix(f".parquet.bak2")
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  已备份: {src.name} -> {dst.name}")

    # 2. 读取 FMA 流派映射
    print("\n[2/5] 读取 FMA 流派映射...")
    fma_mapping = load_fma_genre_mapping(genres_csv)
    print(f"  加载了 {len(fma_mapping)} 个流派映射")
    print(f"  目标流派: {len(MAIN_GENRES)} 种")

    # 3. 处理 bge parquet
    print("\n[3/5] 处理 unified_songs_bge.parquet...")
    df_bge = pd.read_parquet(bge_parquet)
    print(f"  读取了 {len(df_bge)} 条记录")

    df_bge, stats_bge = supplement_genres(df_bge, fma_mapping)
    print(f"  补全前缺失: {stats_bge['missing_before']}")
    print(f"  补全数量: {stats_bge['supplemented']}")
    print(f"  仍缺失: {stats_bge['still_missing']}")

    df_bge.to_parquet(bge_parquet, index=False)
    print(f"  已保存: {bge_parquet.name}")

    # 4. 处理 enhanced parquet
    print("\n[4/5] 处理 unified_songs_enhanced.parquet...")
    if enhanced_parquet.exists():
        df_enhanced = pd.read_parquet(enhanced_parquet)
        print(f"  读取了 {len(df_enhanced)} 条记录")

        if "genre" in df_enhanced.columns:
            df_enhanced, stats_enhanced = supplement_genres(df_enhanced, fma_mapping)
        else:
            print("  没有 genre 列，跳过")
            stats_enhanced = stats_bge

        df_enhanced.to_parquet(enhanced_parquet, index=False)
        print(f"  已保存: {enhanced_parquet.name}")
    else:
        print(f"  文件不存在，跳过")
        stats_enhanced = stats_bge

    # 5. 更新 genre_stats.json
    print("\n[5/5] 更新 genre_stats.json...")
    genre_stats = update_genre_stats(stats_bge, genre_stats_path)
    print(f"  覆盖率: {genre_stats['coverage_rate']}%")
    print(f"  流派种类: {len(genre_stats['genre_distribution'])}")

    # 输出前10个流派
    print("\n  流派分布 Top 10:")
    sorted_genres = sorted(
        genre_stats["genre_distribution"].items(), key=lambda x: x[1], reverse=True
    )[:10]
    for genre, count in sorted_genres:
        print(f"    {genre}: {count}")

    print("\n" + "=" * 60)
    print("Genre 补全完成!")
    print("=" * 60)

    return stats_bge


if __name__ == "__main__":
    main()
