#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量库构建脚本 - BGE-M3 + ChromaDB
基于清洗后的数据构建语义向量索引
"""

import logging
from pathlib import Path
import shutil

import pandas as pd
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 输入输出路径
INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "unified_songs_bge.parquet"
OUTPUT_DIR = PROJECT_ROOT / "index" / "chroma_bge_m3"

# BGE-M3 配置
MODEL_NAME = "BAAI/bge-m3"
BATCH_SIZE = 16
COLLECTION_NAME = "music_bge_collection"


class BGEVectorizer:
    """BGE-M3 向量化器"""
    
    def __init__(self, model_name: str = MODEL_NAME, batch_size: int = BATCH_SIZE):
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = None
        self.model = None
        
        logger.info(f"初始化 BGE-M3 向量化器")
        logger.info(f"  模型: {model_name}")
        logger.info(f"  批大小: {batch_size}")
        
        self._setup_device()
        self._load_model()
    
    def _setup_device(self):
        """配置计算设备"""
        if torch.cuda.is_available():
            self.device = 'cuda'
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"✓ 使用 GPU: {gpu_name}")
            logger.info(f"  显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        else:
            self.device = 'cpu'
            logger.warning("⚠️  未检测到 CUDA，使用 CPU（速度较慢）")
    
    def _load_model(self):
        """加载 BGE-M3 模型"""
        logger.info(f"加载模型: {self.model_name}...")
        
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            
            # 显存优化：使用 float16
            if self.device == 'cuda':
                self.model.half()
                logger.info("✓ 启用 float16 精度（显存优化）")
            
            logger.info("✓ 模型加载成功")
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            raise
    
    def encode_batch(self, texts: list) -> list:
        """批量编码文本"""
        try:
            with torch.no_grad():
                embeddings = self.model.encode(
                    texts,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"编码失败: {e}")
            return None


class ChromaDBBuilder:
    """ChromaDB 向量库构建器"""
    
    def __init__(self, persist_dir: Path, collection_name: str = COLLECTION_NAME):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        
        logger.info(f"初始化 ChromaDB 构建器")
        logger.info(f"  存储路径: {persist_dir}")
        logger.info(f"  集合名: {collection_name}")
        
        self._clean_old_database()
        self._init_database()
    
    def _clean_old_database(self):
        """清空旧的向量库"""
        if self.persist_dir.exists():
            logger.info(f"检测到旧向量库，删除...")
            try:
                shutil.rmtree(self.persist_dir)
                logger.info("✓ 旧向量库已删除")
            except Exception as e:
                logger.error(f"删除失败: {e}")
    
    def _init_database(self):
        """初始化 ChromaDB"""
        if chromadb is None:
            logger.error("❌ ChromaDB 未安装，请运行: pip install chromadb")
            raise ImportError("ChromaDB not installed")
        
        logger.info("初始化 ChromaDB...")
        
        try:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir)
            )
            
            # 创建集合
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "BGE-M3 Music Embeddings"}
            )
            
            logger.info("✓ ChromaDB 初始化成功")
            
        except Exception as e:
            logger.error(f"❌ ChromaDB 初始化失败: {e}")
            raise
    
    def add_vectors(self, df: pd.DataFrame, vectorizer: BGEVectorizer):
        """批量添加向量到数据库"""
        logger.info(f"开始向量化并存储 {len(df)} 条记录...")
        
        total_batches = (len(df) + vectorizer.batch_size - 1) // vectorizer.batch_size
        
        for i in tqdm(range(0, len(df), vectorizer.batch_size), 
                     total=total_batches, 
                     desc="向量化"):
            
            batch_df = df.iloc[i:i+vectorizer.batch_size]
            
            # 准备数据
            texts = batch_df['rich_text'].tolist()
            ids = [f"fma_{row['track_id']}" for _, row in batch_df.iterrows()]
            
            # 元数据
            metadatas = [
                {
                    'title': row['title'],
                    'artist': row['artist'],
                    'genre': row.get('genre', ''),
                    'track_id': row['track_id']
                }
                for _, row in batch_df.iterrows()
            ]
            
            # 编码
            embeddings = vectorizer.encode_batch(texts)
            
            if embeddings is None:
                logger.error(f"批次 {i//vectorizer.batch_size} 编码失败，跳过")
                continue
            
            # 存储
            try:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas
                )
            except Exception as e:
                logger.error(f"批次 {i//vectorizer.batch_size} 存储失败: {e}")
                continue
        
        logger.info(f"✓ 向量存储完成")
        logger.info(f"  集合中的文档数: {self.collection.count()}")


def main():
    """主流程"""
    logger.info("\n" + "=" * 80)
    logger.info("🧬 BGE-M3 向量库构建流程")
    logger.info("=" * 80 + "\n")
    
    # 1. 检查输入文件
    if not INPUT_FILE.exists():
        logger.error(f"❌ 输入文件不存在: {INPUT_FILE}")
        logger.error("   请先运行 data_processor_bge.py")
        return None
    
    logger.info(f"✓ 输入文件: {INPUT_FILE}")
    logger.info(f"  大小: {INPUT_FILE.stat().st_size / 1024:.1f} KB")
    
    # 2. 加载数据
    logger.info("加载清洗后的数据...")
    df = pd.read_parquet(INPUT_FILE)
    logger.info(f"  加载 {len(df)} 条记录")
    logger.info(f"  字段: {df.columns.tolist()}")
    
    # 验证必需字段
    required_fields = ['track_id', 'rich_text', 'title', 'artist']
    missing_fields = [f for f in required_fields if f not in df.columns]
    if missing_fields:
        logger.error(f"❌ 缺少必需字段: {missing_fields}")
        return None
    
    # 3. 初始化向量化器
    vectorizer = BGEVectorizer(MODEL_NAME, BATCH_SIZE)
    
    # 4. 初始化 ChromaDB
    chroma_builder = ChromaDBBuilder(OUTPUT_DIR, COLLECTION_NAME)
    
    # 5. 向量化并存储
    chroma_builder.add_vectors(df, vectorizer)
    
    # 6. 总结
    logger.info("\n" + "=" * 80)
    logger.info("✅ 向量库构建完成！")
    logger.info("=" * 80)
    logger.info(f"  输出路径: {OUTPUT_DIR}")
    logger.info(f"  集合名: {COLLECTION_NAME}")
    logger.info(f"  文档数: {chroma_builder.collection.count()}")
    logger.info(f"  模型: {MODEL_NAME}")
    logger.info(f"  向量维度: 384")
    logger.info("=" * 80 + "\n")
    
    return OUTPUT_DIR


if __name__ == '__main__':
    output_dir = main()
    if output_dir:
        logger.info("🎉 向量库构建流程成功完成！")
