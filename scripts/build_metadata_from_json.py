#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 Last.fm 训练数据 JSON 文件中提取元数据映射
生成 MSD ID -> "歌手 - 歌名" 的映射文件
"""

import json
import logging
from pathlib import Path
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 输入输出路径
RAW_TRAIN_DIR = PROJECT_ROOT / "dataset" / "raw" / "lastfm_train"
OUTPUT_DIR = PROJECT_ROOT / "dataset" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "metadata.json"


def find_json_files(train_dir: Path) -> list:
    """递归查找所有 JSON 文件"""
    logger.info(f"🔍 递归查找 JSON 文件: {train_dir}")
    
    if not train_dir.exists():
        logger.error(f"❌ 目录不存在: {train_dir}")
        return []
    
    json_files = list(train_dir.rglob("*.json"))
    logger.info(f"✓ 找到 {len(json_files)} 个 JSON 文件")
    return json_files


def extract_metadata(json_files: list) -> dict:
    """从 JSON 文件中提取元数据"""
    logger.info("📖 开始提取元数据...")
    
    metadata = {}
    success_count = 0
    missing_fields_count = 0
    error_count = 0
    
    for json_file in tqdm(json_files, desc="提取元数据"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取字段
            track_id = data.get('track_id')
            if not track_id:
                # 尝试从文件名获取 track_id
                track_id = json_file.stem
            
            title = data.get('title', 'Unknown')
            artist = data.get('artist', 'Unknown')
            
            # 处理缺失值
            if not title or title.strip() == '':
                title = 'Unknown'
            if not artist or artist.strip() == '':
                artist = 'Unknown'
            
            # 构建映射值
            display_name = f"{artist} - {title}"
            metadata[track_id] = display_name
            
            if title == 'Unknown' or artist == 'Unknown':
                missing_fields_count += 1
            else:
                success_count += 1
                
        except json.JSONDecodeError as e:
            logger.debug(f"JSON 解析错误 {json_file.name}: {e}")
            error_count += 1
        except Exception as e:
            logger.debug(f"处理错误 {json_file.name}: {e}")
            error_count += 1
    
    logger.info(f"✓ 提取完成:")
    logger.info(f"  完整记录: {success_count}")
    logger.info(f"  部分缺失: {missing_fields_count}")
    logger.info(f"  解析错误: {error_count}")
    logger.info(f"  总计映射: {len(metadata)}")
    
    return metadata


def save_metadata(metadata: dict, output_path: Path):
    """保存元数据到 JSON 文件"""
    logger.info(f"💾 保存元数据到: {output_path}")
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    file_size = output_path.stat().st_size / 1024
    logger.info(f"✓ 保存成功: {file_size:.1f} KB")


def main():
    logger.info("=" * 60)
    logger.info("🎵 从 Last.fm JSON 构建元数据映射")
    logger.info("=" * 60)
    
    # 1. 查找 JSON 文件
    json_files = find_json_files(RAW_TRAIN_DIR)
    if not json_files:
        logger.error("❌ 未找到任何 JSON 文件，流程终止")
        return
    
    # 2. 提取元数据
    metadata = extract_metadata(json_files)
    if not metadata:
        logger.error("❌ 未提取到任何元数据，流程终止")
        return
    
    # 3. 保存结果
    save_metadata(metadata, OUTPUT_FILE)
    
    # 4. 打印示例
    logger.info("\n📋 示例数据（前 5 条）:")
    for i, (track_id, display_name) in enumerate(list(metadata.items())[:5]):
        logger.info(f"  {track_id}: {display_name}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"🎉 完成！共提取 {len(metadata)} 首歌曲的元数据")
    logger.info(f"   输出文件: {OUTPUT_FILE}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
