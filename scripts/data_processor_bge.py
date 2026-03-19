#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能数据处理脚本 - FMA + Last.fm 融合
使用 pathlib.rglob 递归查找所有原始数据文件
"""

import json
import importlib.util
import logging
from pathlib import Path
import re

import pandas as pd
import numpy as np
from tqdm import tqdm

FUZZ_MODULE = 'rapidfuzz' if importlib.util.find_spec('rapidfuzz') else 'fuzzywuzzy'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 输入路径（使用 rglob 递归查找）
RAW_DATA_ROOT = PROJECT_ROOT / "dataset" / "raw"

# 输出路径
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"


class SmartDataLoader:
    """智能数据加载器 - 使用 rglob 递归查找文件"""
    
    def __init__(self, raw_data_root: Path):
        self.raw_data_root = raw_data_root
        logger.info(f"初始化智能数据加载器: {raw_data_root}")
    
    def find_fma_tracks(self) -> Path | None:
        """
        递归查找 FMA tracks.csv 文件
        """
        logger.info("🔍 递归查找 FMA tracks.csv...")
        
        fma_dir = self.raw_data_root / "fma_metadata"
        if not fma_dir.exists():
            logger.error(f"❌ FMA 元数据目录不存在: {fma_dir}")
            return None
        
        # 递归查找 tracks.csv
        matches = list(fma_dir.rglob("tracks.csv"))
        
        if not matches:
            logger.error(f"❌ 未找到 tracks.csv")
            logger.error(f"   扫描目录: {fma_dir}")
            logger.error(f"   目录内容: {list(fma_dir.iterdir())}")
            return None
        
        if len(matches) > 1:
            logger.warning(f"⚠️  找到多个 tracks.csv，使用第一个: {matches[0]}")
        
        logger.info(f"✓ 找到 tracks.csv: {matches[0]}")
        return matches[0]
    
    def find_fma_features(self) -> Path | None:
        """
        递归查找 FMA features.csv 文件
        """
        logger.info("🔍 递归查找 FMA features.csv...")
        
        fma_dir = self.raw_data_root / "fma_metadata"
        if not fma_dir.exists():
            return None
        
        matches = list(fma_dir.rglob("features.csv"))
        
        if not matches:
            logger.warning("⚠️  未找到 features.csv（可选）")
            return None
        
        logger.info(f"✓ 找到 features.csv: {matches[0]}")
        return matches[0]
    
    def find_lastfm_tags(self) -> list[Path]:
        """
        递归查找 Last.fm 标签 JSON 文件
        """
        logger.info("🔍 递归查找 Last.fm 标签数据...")
        
        lastfm_dir = self.raw_data_root / "lastfm_subset"
        if not lastfm_dir.exists():
            logger.error(f"❌ Last.fm subset 目录不存在: {lastfm_dir}")
            return []
        
        # 递归查找所有 JSON 文件
        json_files = list(lastfm_dir.rglob("*.json"))
        
        if not json_files:
            logger.warning(f"⚠️  未找到 JSON 文件")
            logger.warning(f"   扫描目录: {lastfm_dir}")
            # 尝试查找 CSV
            csv_files = list(lastfm_dir.rglob("*.csv"))
            if csv_files:
                logger.info(f"✓ 找到 {len(csv_files)} 个 CSV 文件")
                return csv_files
            return []
        
        logger.info(f"✓ 找到 {len(json_files)} 个 Last.fm JSON 文件")
        return json_files


class FMAProcessor:
    """FMA 数据处理器"""

    def load_tracks(self, tracks_path: Path):
        """加载 FMA tracks.csv"""
        logger.info(f"加载 FMA tracks: {tracks_path}")
        
        try:
            # FMA tracks.csv 通常是多级表头
            df = pd.read_csv(tracks_path, index_col=0, header=[0, 1])
            logger.info(f"  原始形状: {df.shape}")

            def _get_series(df_in: pd.DataFrame, multi_key: tuple[str, str], single_key: str):
                if isinstance(df_in.columns, pd.MultiIndex) and multi_key in df_in.columns:
                    return df_in[multi_key]
                if single_key in df_in.columns:
                    return df_in[single_key]
                return pd.Series(["" for _ in range(len(df_in))], index=df_in.index)

            # 提取需要的列
            tracks_clean = pd.DataFrame({
                'track_id': df.index.astype(str),
                'title': _get_series(df, ('track', 'title'), 'title').fillna('').astype(str),
                'artist': _get_series(df, ('artist', 'name'), 'artist').fillna('').astype(str),
                'genre': _get_series(df, ('track', 'genre_top'), 'genre').fillna('').astype(str),
            })
            
            tracks_clean = tracks_clean[tracks_clean['title'] != '']
            logger.info(f"  清洗后: {len(tracks_clean)} 条记录")
            
            return tracks_clean
            
        except Exception as e:
            logger.error(f"❌ 加载 FMA tracks 失败: {e}")
            # 尝试简单读取
            try:
                df = pd.read_csv(tracks_path)
                logger.info(f"  使用简单模式读取，列: {df.columns.tolist()}")
                return df
            except:
                raise


class LastFMProcessor:
    """Last.fm 数据处理器"""

    def load_tags_from_json(
        self,
        json_files: list[Path],
        max_files: int | None = None,
    ) -> dict[str, dict[str, object]]:
        """
        从 JSON 文件加载 Last.fm 标签
        JSON 格式参考: {"track_id": "xxx", "artist": "xxx", "title": "xxx", "tags": [[tag, count], ...]}
        """
        logger.info(f"加载 Last.fm 标签数据...")
        
        if max_files:
            json_files = json_files[:max_files]
        
        tags_dict: dict[str, dict[str, object]] = {}
        loaded_count = 0
        
        for json_file in tqdm(json_files, desc="加载 JSON"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 提取标签
                track_id = data.get('track_id')
                artist = data.get('artist', '')
                title = data.get('title', '')
                tags = data.get('tags', [])
                
                # 构建查找键
                if artist and title:
                    key = f"{title}|||{artist}"
                    tags_dict[key] = {
                        'track_id': track_id,
                        'tags': [tag[0] for tag in tags if len(tag) > 0]
                    }
                    loaded_count += 1
                    
            except Exception as e:
                logger.debug(f"跳过文件 {json_file.name}: {e}")
                continue
        
        logger.info(f"✓ 成功加载 {loaded_count} 条 Last.fm 标签")
        return tags_dict


class DataMerger:
    """数据融合器 - 二阶段匹配策略"""
    
    def __init__(self):
        self.fuzz_module = FUZZ_MODULE
        logger.info(f"初始化数据融合器，使用模糊匹配库: {self.fuzz_module}")
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """文本规范化"""
        if not text:
            return ""
        # 转小写，移除特殊字符
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def merge_data(self, fma_tracks, lastfm_tags: dict[str, dict[str, object]]):
        """
        融合 FMA 和 Last.fm 数据
        使用二阶段策略：
        1. 精确匹配（大小写不敏感）
        2. 模糊匹配（仅处理未匹配数据）
        """
        logger.info("开始融合 FMA 和 Last.fm 数据...")
        logger.info(f"  FMA 记录数: {len(fma_tracks)}")
        logger.info(f"  Last.fm 标签数: {len(lastfm_tags)}")
        
        if not lastfm_tags:
            logger.warning("Last.fm 数据为空，跳过匹配")
            fma_tracks['tags'] = [[] for _ in range(len(fma_tracks))]
            return fma_tracks
        
        # 构建查找表
        logger.info("构建 Last.fm 查找表...")
        lastfm_lookup = {}
        for key, value in lastfm_tags.items():
            # 规范化键
            parts = key.split('|||')
            if len(parts) == 2:
                title_clean = self.normalize_text(parts[0])
                artist_clean = self.normalize_text(parts[1])
                lookup_key = f"{title_clean}|||{artist_clean}"
                lastfm_lookup[lookup_key] = value
        
        logger.info(f"  查找表大小: {len(lastfm_lookup)}")
        
        # 阶段1: 精确匹配
        logger.info("🚀 阶段1: 精确匹配...")
        fma_tracks['tags'] = None
        matched_exact = 0
        
        for idx, row in tqdm(fma_tracks.iterrows(), total=len(fma_tracks), desc="精确匹配"):
            title_val = row.get('title', '')
            artist_val = row.get('artist', '')
            if not isinstance(title_val, str):
                if title_val is None or (isinstance(title_val, float) and np.isnan(title_val)):
                    title_val = ''
                else:
                    title_val = str(title_val)
            if not isinstance(artist_val, str):
                if artist_val is None or (isinstance(artist_val, float) and np.isnan(artist_val)):
                    artist_val = ''
                else:
                    artist_val = str(artist_val)

            title_clean = self.normalize_text(title_val)
            artist_clean = self.normalize_text(artist_val)
            lookup_key = f"{title_clean}|||{artist_clean}"
            
            if lookup_key in lastfm_lookup:
                fma_tracks.at[idx, 'tags'] = lastfm_lookup[lookup_key]['tags']
                matched_exact += 1
            else:
                fma_tracks.at[idx, 'tags'] = []
        
        logger.info(f"  精确匹配成功: {matched_exact}/{len(fma_tracks)} ({matched_exact/len(fma_tracks)*100:.2f}%)")
        
        return fma_tracks

    @staticmethod
    def _clean_tags(tags: object) -> list[str]:
        if tags is None:
            return []

        if isinstance(tags, str):
            candidates = [tags]
        elif isinstance(tags, (list, tuple, set, np.ndarray, pd.Series)):
            candidates = list(tags)
        else:
            return []

        cleaned: list[str] = []
        seen = set()
        for t in candidates:
            if not isinstance(t, str):
                continue
            s = t.replace('_', ' ').strip()
            s = re.sub(r"\s+", " ", s)
            s = s.lower()
            if not s:
                continue
            if s in seen:
                continue
            seen.add(s)
            cleaned.append(s)
        return cleaned

    @staticmethod
    def _clamp_text(text: str, max_chars: int) -> str:
        if not text:
            return ""
        if max_chars <= 0:
            return ""
        if len(text) <= max_chars:
            return text

        clamped = text[:max_chars]
        return clamped.rstrip(" |.,;\n\t")
    
    def build_rich_text(self, df: pd.DataFrame) -> pd.DataFrame:
        """构建 BGE-M3 Rich Text"""
        logger.info("构建 rich_text 字段...")

        def _safe_text(val: object) -> str:
            if val is None:
                return ""
            try:
                if isinstance(val, float) and np.isnan(val):
                    return ""
                if not isinstance(val, (list, tuple, set, dict)):
                    na = pd.isna(val)
                    if isinstance(na, (bool, np.bool_)) and na:
                        return ""
            except Exception:
                pass
            return str(val).strip()

        def create_rich_text(row) -> str:
            title = _safe_text(row.get('title'))
            artist = _safe_text(row.get('artist'))
            genre = _safe_text(row.get('genre'))

            tags_list = self._clean_tags(row.get('tags'))
            tags_list = tags_list[:10]
            tags_str = ", ".join(tags_list)

            en_parts: list[str] = ["Music track."]
            if title:
                en_parts.append(f"Title: {title}.")
            if artist:
                en_parts.append(f"Artist: {artist}.")
            if title:
                en_parts.append(f"Title: {title}.")
            if artist:
                en_parts.append(f"Artist: {artist}.")
            if genre:
                en_parts.append(f"Genre: {genre}.")
            if tags_str:
                en_parts.append(f"Tags: {tags_str}.")

            zh_parts: list[str] = []
            if title:
                zh_parts.append(f"标题: {title}")
            if artist:
                zh_parts.append(f"歌手: {artist}")
            if genre:
                zh_parts.append(f"风格: {genre}")
            if tags_str:
                zh_parts.append(f"标签: {tags_str}")

            if not zh_parts and en_parts == ["Music track."]:
                return ""

            text = " ".join(en_parts)
            if zh_parts:
                text = f"{text} {' | '.join(zh_parts)}"

            return self._clamp_text(text, max_chars=320)
        
        df['rich_text'] = df.apply(create_rich_text, axis=1)
        
        # 过滤空记录
        df = df.loc[df['rich_text'] != ''].copy()
        logger.info(f"  生成 {len(df)} 条 rich_text")
        
        return df


def main():
    """主流程"""
    logger.info("\n" + "=" * 80)
    logger.info("🎵 智能数据处理流程 - FMA + Last.fm 融合")
    logger.info("=" * 80 + "\n")
    
    # 1. 初始化智能加载器
    loader = SmartDataLoader(RAW_DATA_ROOT)
    
    # 2. 查找 FMA 数据文件
    tracks_path = loader.find_fma_tracks()
    if not tracks_path:
        logger.error("❌ 无法找到 FMA tracks.csv，流程终止")
        return None, 0
    
    # 3. 加载 FMA 数据
    fma_processor = FMAProcessor()
    fma_tracks = fma_processor.load_tracks(tracks_path)
    
    # 4. 查找 Last.fm 标签文件
    lastfm_files = loader.find_lastfm_tags()
    
    # 5. 加载 Last.fm 数据
    lastfm_processor = LastFMProcessor()
    lastfm_tags = {}
    if lastfm_files:
        lastfm_tags = lastfm_processor.load_tags_from_json(lastfm_files)
    
    # 6. 融合数据
    merger = DataMerger()
    merged_data = merger.merge_data(fma_tracks, lastfm_tags)
    
    # 7. 构建 rich_text
    final_data = merger.build_rich_text(merged_data)
    
    # 8. 保存结果
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "unified_songs_bge.parquet"
    
    final_data.to_parquet(output_path, index=False)
    logger.info(f"\n✅ 数据处理完成！")
    logger.info(f"   输出文件: {output_path}")
    logger.info(f"   记录数: {len(final_data)}")
    logger.info(f"   文件大小: {output_path.stat().st_size / 1024:.1f} KB")
    
    return output_path, len(final_data)


if __name__ == '__main__':
    output_path, record_count = main()
    if output_path:
        logger.info("\n" + "=" * 80)
        logger.info("🎉 数据处理流程成功完成！")
        logger.info("=" * 80)
