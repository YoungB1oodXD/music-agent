#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
from pathlib import Path
import re
import ast

import pandas as pd
import numpy as np
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
RAW_DATA_ROOT = PROJECT_ROOT / "dataset" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"


class FMADataLoader:
    def __init__(self, raw_data_root: Path):
        self.raw_data_root = raw_data_root
        logger.info(f"Initializing FMA data loader: {raw_data_root}")
    
    def find_fma_tracks(self) -> Path | None:
        logger.info("Searching for FMA tracks.csv...")
        fma_dir = self.raw_data_root / "fma_metadata"
        if not fma_dir.exists():
            logger.error(f"FMA metadata directory not found: {fma_dir}")
            return None
        matches = list(fma_dir.rglob("tracks.csv"))
        if not matches:
            logger.error("tracks.csv not found")
            return None
        if len(matches) > 1:
            logger.warning(f"Multiple tracks.csv found, using first: {matches[0]}")
        logger.info(f"Found tracks.csv: {matches[0]}")
        return matches[0]


class FMAProcessor:
    def load_tracks(self, tracks_path: Path):
        logger.info(f"Loading FMA tracks: {tracks_path}")
        try:
            df = pd.read_csv(tracks_path, index_col=0, header=[0, 1])
            logger.info(f"  Raw shape: {df.shape}")

            def _get_series(df_in: pd.DataFrame, multi_key: tuple[str, str], single_key: str):
                if isinstance(df_in.columns, pd.MultiIndex) and multi_key in df_in.columns:
                    return df_in[multi_key]
                if single_key in df_in.columns:
                    return df_in[single_key]
                return pd.Series(["" for _ in range(len(df_in))], index=df_in.index)

            tracks_clean = pd.DataFrame({
                'track_id': df.index.astype(str),
                'title': _get_series(df, ('track', 'title'), 'title').fillna('').astype(str),
                'artist': _get_series(df, ('artist', 'name'), 'artist').fillna('').astype(str),
                'genre': _get_series(df, ('track', 'genre_top'), 'genre').fillna('').astype(str),
                'artist_tags': _get_series(df, ('artist', 'tags'), 'artist_tags').fillna('').astype(str),
                'track_tags': _get_series(df, ('track', 'tags'), 'track_tags').fillna('').astype(str),
                'genres_all': _get_series(df, ('track', 'genres_all'), 'genres_all').fillna('').astype(str),
                'duration': _get_series(df, ('track', 'duration'), 'duration').fillna(0).astype(float),
            })
            
            tracks_clean = tracks_clean[tracks_clean['title'] != '']
            logger.info(f"  After cleaning: {len(tracks_clean)} records")
            return tracks_clean
            
        except Exception as e:
            logger.error(f"Failed to load FMA tracks: {e}")
            raise

    @staticmethod
    def _parse_fma_tags(tags_str: str) -> list[str]:
        if not tags_str or tags_str == 'nan':
            return []
        try:
            parsed = ast.literal_eval(tags_str)
            if isinstance(parsed, list):
                return [str(t).lower().replace('_', ' ').strip() for t in parsed if t]
            return []
        except:
            tags = re.findall(r"'([^']+)'", tags_str)
            return [t.lower().replace('_', ' ').strip() for t in tags if t]


class DataProcessor:
    @staticmethod
    def _parse_fma_tags(tags_str: str) -> list[str]:
        return FMAProcessor._parse_fma_tags(tags_str)
    
    def process_tags(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Processing tags from FMA...")
        
        def extract_tags(row) -> list[str]:
            all_tags = []
            for col in ['artist_tags', 'track_tags']:
                tag_val = row.get(col, '')
                if tag_val and tag_val != 'nan':
                    all_tags.extend(self._parse_fma_tags(tag_val))
            return list(dict.fromkeys(all_tags))[:10]
        
        df['tags'] = df.apply(extract_tags, axis=1)
        tags_cover = (df['tags'].apply(len) > 0).sum()
        logger.info(f"  Tags coverage: {tags_cover}/{len(df)} ({tags_cover/len(df)*100:.1f}%)")
        return df

    @staticmethod
    def _clamp_text(text: str, max_chars: int) -> str:
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip(" |.,;\n\t")
    
    def build_rich_text(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("构建 rich_text 字段...")

        def _safe_text(val: object) -> str:
            if val is None:
                return ""
            try:
                if isinstance(val, float) and np.isnan(val):
                    return ""
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
            tags = row.get('tags', [])
            tags_str = ", ".join(tags[:10]) if tags else ""

            en_parts: list[str] = ["Music track."]
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
                text = f"{text} | {' | '.join(zh_parts)}"
            return self._clamp_text(text, max_chars=320)
        
        df['rich_text'] = df.apply(create_rich_text, axis=1)
        df = df.loc[df['rich_text'] != ''].copy()
        logger.info(f"  生成 {len(df)} 条 rich_text")
        return df


def main():
    logger.info("\n" + "=" * 80)
    logger.info("FMA Single-Source Data Processing Pipeline")
    logger.info("=" * 80 + "\n")
    
    loader = FMADataLoader(RAW_DATA_ROOT)
    tracks_path = loader.find_fma_tracks()
    if not tracks_path:
        logger.error("FMA tracks.csv not found, exiting")
        return None, 0
    
    fma_processor = FMAProcessor()
    fma_tracks = fma_processor.load_tracks(tracks_path)
    
    data_processor = DataProcessor()
    fma_tracks = data_processor.process_tags(fma_tracks)
    final_data = data_processor.build_rich_text(fma_tracks)
    
    metadata = {}
    for _, row in final_data.iterrows():
        track_id = str(row.get('track_id', ''))
        title = str(row.get('title', '') or 'Unknown')
        artist = str(row.get('artist', '') or 'Unknown')
        if track_id:
            metadata[track_id] = f"{artist} - {title}"
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "unified_songs_bge.parquet"
    final_data.to_parquet(output_path, index=False)
    
    metadata_path = PROJECT_ROOT / "dataset" / "processed" / "metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    tags_cover = (final_data['tags'].apply(len) > 0).sum()
    genre_cover = (final_data['genre'] != '').sum()
    
    logger.info(f"\nData processing complete!")
    logger.info(f"   Output: {output_path}")
    logger.info(f"   Records: {len(final_data)}")
    logger.info(f"   Tags coverage: {tags_cover}/{len(final_data)} ({tags_cover/len(final_data)*100:.1f}%)")
    logger.info(f"   Genre coverage: {genre_cover}/{len(final_data)} ({genre_cover/len(final_data)*100:.1f}%)")
    logger.info(f"   Metadata: {metadata_path}")
    
    return output_path, len(final_data)


if __name__ == '__main__':
    output_path, record_count = main()
    if output_path:
        logger.info("\n" + "=" * 80)
        logger.info("FMA single-source pipeline completed successfully!")
        logger.info("=" * 80)