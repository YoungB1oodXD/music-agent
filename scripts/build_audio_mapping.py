#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import json
import logging
from pathlib import Path
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
FMA_SMALL_DIR = PROJECT_ROOT / "dataset" / "raw" / "fma_small" / "fma_small"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "audio_mapping.json"


def build_audio_mapping():
    logger.info(f"Scanning FMA_small directory: {FMA_SMALL_DIR}")
    
    if not FMA_SMALL_DIR.exists():
        logger.error(f"FMA_small directory not found: {FMA_SMALL_DIR}")
        return {}
    
    audio_mapping = {}
    mp3_files = list(FMA_SMALL_DIR.rglob("*.mp3"))
    
    logger.info(f"Found {len(mp3_files)} MP3 files")
    
    for mp3_file in tqdm(mp3_files, desc="Building mapping"):
        filename = mp3_file.stem
        try:
            track_id = str(int(filename))
            relative_path = str(mp3_file.relative_to(FMA_SMALL_DIR.parent.parent))
            audio_mapping[track_id] = relative_path.replace("\\", "/")
        except ValueError:
            logger.warning(f"Invalid filename: {filename}")
            continue
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(audio_mapping, f, indent=2)
    
    logger.info(f"Saved {len(audio_mapping)} mappings to {OUTPUT_FILE}")
    return audio_mapping


if __name__ == '__main__':
    mapping = build_audio_mapping()
    print(f"\nSample mappings:")
    for track_id, path in list(mapping.items())[:5]:
        print(f"  {track_id}: {path}")