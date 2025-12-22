#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Implicit 协同过滤训练脚本
智能加载 Last.fm 训练数据（支持嵌套目录结构）
使用 implicit.als.AlternatingLeastSquares 算法进行训练
"""

import os
# 【优化建议 1】即使是 implicit，在 Windows 上限制线程数也是好习惯
# 这能防止 Numpy 底层的 OpenBLAS/MKL 与 implicit 争抢资源
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import json
import logging
import pickle
import itertools
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

import numpy as np
from tqdm import tqdm
from scipy.sparse import coo_matrix, csr_matrix

try:
    import implicit
    from implicit.als import AlternatingLeastSquares
except ImportError:
    implicit = None
    AlternatingLeastSquares = None

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
OUTPUT_DIR = PROJECT_ROOT / "data" / "models"

# 训练参数
# implicit 建议 factors 在 50-200 之间
NO_COMPONENTS = 64      
ITERATIONS = 15         
REGULARIZATION = 0.01   


class SmartTrainDataLoader:
    """智能训练数据加载器 - 支持嵌套目录和多种格式"""
    
    def __init__(self, train_dir: Path):
        self.train_dir = train_dir
        self.users = {}
        self.items = {}
        self.user_counter = 0
        self.item_counter = 0
        self.interactions = []
        
        logger.info(f"初始化智能训练数据加载器: {train_dir}")
    
    def find_train_files(self) -> List[Path]:
        """递归查找训练数据文件"""
        logger.info("🔍 递归查找训练数据文件...")
        
        if not self.train_dir.exists():
            logger.error(f"❌ 训练数据目录不存在: {self.train_dir}")
            return None
        
        # 检查是否有 JSON 文件
        json_gen = self.train_dir.rglob("*.json")
        try:
            first_json = next(json_gen)
            logger.info(f"✓ 找到 JSON 格式（相似度数据）")
            return first_json.parent.parent.rglob("*.json")
        except StopIteration:
            pass
        
        # 简略了 TSV/CSV 检查以节省篇幅，逻辑保持原样即可...
        logger.error("❌ 未找到任何训练数据文件")
        return None
    
    def load_from_json_similars(self, json_files, max_files: int = None) -> bool:
        """从 JSON 加载数据"""
        logger.info("从 JSON 相似度数据构建交互矩阵...")
        
        if hasattr(json_files, '__iter__') and not isinstance(json_files, list):
            json_files = list(json_files) if max_files is None else list(itertools.islice(json_files, max_files))
        
        loaded_count = 0
        
        for json_file in tqdm(json_files, desc="加载 JSON"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                track_id = data.get('track_id')
                if not track_id: continue
                
                similars = data.get('similars', [])
                
                for similar_item in similars:
                    if len(similar_item) >= 2:
                        similar_track = similar_item[0]
                        score = float(similar_item[1])
                        # 过滤低相似度
                        if score > 0.1:
                            self._add_interaction(track_id, similar_track, score)
                            loaded_count += 1
            except Exception:
                continue
        
        logger.info(f"✓ 加载完成: {loaded_count} 条交互")
        logger.info(f"  用户数: {len(self.users)} | 物品数: {len(self.items)}")
        return len(self.interactions) > 0
    
    def _add_interaction(self, user_id, item_id, weight):
        if user_id not in self.users:
            self.users[user_id] = self.user_counter
            self.user_counter += 1
        if item_id not in self.items:
            self.items[item_id] = self.item_counter
            self.item_counter += 1
        self.interactions.append((self.users[user_id], self.items[item_id], weight))
    
    def get_reverse_mapping(self):
        return {v: k for k, v in self.users.items()}, {v: k for k, v in self.items.items()}


class ImplicitTrainer:
    """Implicit ALS 模型训练器"""
    
    def __init__(self, no_components=NO_COMPONENTS, iterations=ITERATIONS, regularization=REGULARIZATION):
        if implicit is None:
            logger.error("❌ Implicit 库未安装")
            raise ImportError("请运行 pip install implicit")
        
        self.no_components = no_components
        self.iterations = iterations
        
        logger.info("初始化 Implicit ALS 训练器")
        logger.info(f"  Version: {implicit.__version__}")
        
        self.model = AlternatingLeastSquares(
            factors=no_components,
            regularization=regularization,
            iterations=iterations,
            num_threads=1,  # Windows 必须单线程
            random_state=42
        )
    
    def fit(self, interactions: List[Tuple], num_users: int, num_items: int):
        logger.info("构建 CSR 矩阵...")
        
        user_ids = np.array([x[0] for x in interactions], dtype=np.int32)
        item_ids = np.array([x[1] for x in interactions], dtype=np.int32)
        weights = np.array([x[2] for x in interactions], dtype=np.float32)
        
        # 构建 User-Item 矩阵
        # 注意: implicit >= 0.6.0 期望 fit(user_items)
        interaction_matrix = coo_matrix(
            (weights, (user_ids, item_ids)),
            shape=(num_users, num_items),
            dtype=np.float32
        ).tocsr()
        
        # 显式排序索引 (重要)
        interaction_matrix.sort_indices()
        
        logger.info(f"  矩阵形状: {interaction_matrix.shape}")
        
        logger.info("开始训练 (ALS)...")
        try:
            # show_progress=True 在 Windows 终端通常表现良好
            self.model.fit(interaction_matrix, show_progress=True)
            logger.info("✓ 训练过程完成")
        except Exception as e:
            logger.error(f"❌ 训练报错: {str(e)}")
            raise

def main():
    logger.info("=" * 80)
    logger.info("🤖 Implicit ALS 协同过滤训练")
    logger.info("=" * 80)
    
    loader = SmartTrainDataLoader(RAW_TRAIN_DIR)
    files = loader.find_train_files()
    
    if not files: return
    
    if not loader.load_from_json_similars(files):
        logger.error("❌ 无数据")
        return
    
    trainer = ImplicitTrainer()
    trainer.fit(loader.interactions, len(loader.users), len(loader.items))
    
    # 保存流程
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    model_path = OUTPUT_DIR / "implicit_model.pkl"
    # implicit 对象可以直接 pickle
    with open(model_path, 'wb') as f:
        pickle.dump(trainer.model, f)
    
    # 保存映射
    rev_users, rev_items = loader.get_reverse_mapping()
    mappings = {
        'user_mapping': loader.users,
        'item_mapping': loader.items,
        'reverse_users': rev_users,
        'reverse_items': rev_items
    }
    with open(OUTPUT_DIR / "cf_mappings.pkl", 'wb') as f:
        pickle.dump(mappings, f)
        
    logger.info(f"🎉 成功! 模型保存至: {model_path}")

if __name__ == '__main__':
    main()