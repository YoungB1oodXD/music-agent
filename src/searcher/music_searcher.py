#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语义音乐搜索器
基于 BGE-M3 + ChromaDB 实现语义相似度搜索
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

import torch

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import chromadb
except ImportError:
    chromadb = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_MODEL_NAME = "BAAI/bge-m3"
DEFAULT_COLLECTION_NAME = "music_bge_collection"


class MusicSearcher:
    """
    语义音乐搜索器
    
    基于 BGE-M3 向量模型和 ChromaDB 向量数据库，
    提供自然语言查询的音乐语义搜索功能。
    
    Example:
        >>> searcher = MusicSearcher()
        >>> results = searcher.search("relaxing jazz music", top_k=5)
        >>> for r in results:
        ...     print(f"{r['title']} - {r['artist']}")
    """
    
    def __init__(
        self,
        index_path: Optional[Path] = None,
        model_name: str = DEFAULT_MODEL_NAME,
        collection_name: str = DEFAULT_COLLECTION_NAME
    ):
        """
        初始化语义搜索器
        
        Args:
            index_path: ChromaDB 持久化路径 (默认: index/chroma_bge_m3)
            model_name: Sentence Transformer 模型名称 (默认: BAAI/bge-m3)
            collection_name: ChromaDB 集合名称 (默认: music_bge_collection)
        """
        # 项目根目录
        self.project_root = Path(__file__).parent.parent.parent
        
        # 设置默认路径
        self.index_path = index_path or self.project_root / "index" / "chroma_bge_m3"
        self.model_name = model_name
        self.collection_name = collection_name
        
        # 组件
        self.model = None
        self.client = None
        self.collection = None
        self.device = None
        
        # 初始化
        self._check_dependencies()
        self._setup_device()
        self._load_model()
        self._connect_database()
        
        logger.info("✅ MusicSearcher 初始化完成")
        logger.info(f"   - 向量模型: {self.model_name}")
        logger.info(f"   - 向量库文档数: {self.collection.count()}")
    
    def _check_dependencies(self):
        """检查依赖"""
        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers 未安装。"
                "请运行: pip install sentence-transformers"
            )
        
        if chromadb is None:
            raise ImportError(
                "chromadb 未安装。"
                "请运行: pip install chromadb"
            )
    
    def _setup_device(self):
        """配置计算设备"""
        if torch.cuda.is_available():
            self.device = 'cuda'
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"✓ 使用 GPU: {gpu_name}")
        else:
            self.device = 'cpu'
            logger.info("ℹ️  使用 CPU 进行向量编码")
    
    def _load_model(self):
        """加载向量模型"""
        logger.info(f"📦 加载向量模型: {self.model_name}")
        
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            
            # GPU 显存优化
            if self.device == 'cuda':
                self.model.half()
                logger.info("   启用 float16 精度")
            
            logger.info("   模型加载成功")
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            raise
    
    def _connect_database(self):
        """连接 ChromaDB"""
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"向量库不存在: {self.index_path}\n"
                "请先运行: python scripts/vectorizer_bge.py"
            )
        
        logger.info(f"📦 连接向量库: {self.index_path.name}")
        
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.index_path)
            )
            
            # 获取集合
            self.collection = self.client.get_collection(
                name=self.collection_name
            )
            
            logger.info(f"   集合: {self.collection_name}")
            logger.info(f"   文档数: {self.collection.count()}")
            
        except Exception as e:
            logger.error(f"❌ 连接向量库失败: {e}")
            raise
    
    def _encode_query(self, query: str) -> List[float]:
        """将查询文本编码为向量"""
        with torch.no_grad():
            embedding = self.model.encode(
                query,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
        return embedding.tolist()
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        include_metadata: bool = True,
        include_documents: bool = False
    ) -> List[Dict[str, Any]]:
        """
        语义搜索音乐
        
        Args:
            query: 自然语言查询（如 "relaxing jazz music" 或 "欢快的流行歌曲"）
            top_k: 返回结果数量
            include_metadata: 是否包含元数据（title, artist, genre）
            include_documents: 是否包含原始文档文本
            
        Returns:
            搜索结果列表，每个结果包含:
            - id: 文档 ID (格式: fma_{track_id})
            - distance: 与查询的距离（越小越相似）
            - metadata: 元数据字典（如果 include_metadata=True）
            - document: 原始文档文本（如果 include_documents=True）
        """
        # 编码查询
        query_embedding = self._encode_query(query)
        
        # 构建包含字段
        include = ["distances"]
        if include_metadata:
            include.append("metadatas")
        if include_documents:
            include.append("documents")
        
        # 查询 ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=include
        )
        
        # 格式化结果
        formatted_results = []
        
        ids = results['ids'][0] if results['ids'] else []
        distances = results['distances'][0] if results.get('distances') else []
        metadatas = results['metadatas'][0] if results.get('metadatas') else [{}] * len(ids)
        documents = results['documents'][0] if results.get('documents') else [None] * len(ids)
        
        for i, doc_id in enumerate(ids):
            result = {
                'id': doc_id,
                'distance': distances[i] if i < len(distances) else None,
                'similarity': 1 - distances[i] if i < len(distances) else None,  # 转换为相似度
            }
            
            if include_metadata and i < len(metadatas):
                result['title'] = metadatas[i].get('title', 'Unknown')
                result['artist'] = metadatas[i].get('artist', 'Unknown')
                result['genre'] = metadatas[i].get('genre', '')
                result['track_id'] = metadatas[i].get('track_id', '')
            
            if include_documents and i < len(documents):
                result['document'] = documents[i]
            
            formatted_results.append(result)
        
        return formatted_results
    
    def search_formatted(self, query: str, top_k: int = 5) -> str:
        """
        返回格式化的搜索结果字符串（便于 Agent 输出）
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            格式化的结果字符串
        """
        results = self.search(query, top_k=top_k)
        
        if not results:
            return f"❌ 未找到与 '{query}' 相关的音乐"
        
        lines = [
            f"🔍 搜索: \"{query}\"",
            f"",
            f"📋 找到 {len(results)} 首相关音乐:",
        ]
        
        for i, r in enumerate(results, 1):
            title = r.get('title', 'Unknown')
            artist = r.get('artist', 'Unknown')
            similarity = r.get('similarity', 0)
            genre = r.get('genre', '')
            
            genre_str = f" [{genre}]" if genre else ""
            lines.append(f"   {i}. {artist} - {title}{genre_str} (相似度: {similarity:.2f})")
        
        return "\n".join(lines)
    
    def get_collection_info(self) -> Dict[str, Any]:
        """获取向量库信息"""
        return {
            'collection_name': self.collection_name,
            'document_count': self.collection.count(),
            'index_path': str(self.index_path),
            'model_name': self.model_name,
            'device': self.device
        }


# ============================================================
# 测试代码
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("MusicSearcher 测试")
    print("=" * 60)
    
    # 实例化搜索器
    try:
        searcher = MusicSearcher()
    except (FileNotFoundError, ImportError) as e:
        print(f"❌ 初始化失败: {e}")
        exit(1)
    
    # 测试 1: 基础搜索
    print("\n" + "=" * 60)
    print("测试 1: 搜索 'relaxing jazz music'")
    print("=" * 60)
    
    results = searcher.search("relaxing jazz music", top_k=5)
    for r in results:
        print(f"   {r['artist']} - {r['title']} (相似度: {r['similarity']:.2f})")
    
    # 测试 2: 格式化输出
    print("\n" + "=" * 60)
    print("测试 2: 格式化搜索 'upbeat pop song'")
    print("=" * 60)
    
    formatted = searcher.search_formatted("upbeat pop song", top_k=3)
    print(formatted)
    
    # 测试 3: 中文查询
    print("\n" + "=" * 60)
    print("测试 3: 中文查询 '轻松的背景音乐'")
    print("=" * 60)
    
    formatted_cn = searcher.search_formatted("轻松的背景音乐", top_k=3)
    print(formatted_cn)
    
    # 测试 4: 集合信息
    print("\n" + "=" * 60)
    print("测试 4: 向量库信息")
    print("=" * 60)
    
    info = searcher.get_collection_info()
    for k, v in info.items():
        print(f"   {k}: {v}")
    
    print("\n✅ 测试完成!")
