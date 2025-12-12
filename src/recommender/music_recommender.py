#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音乐推荐器封装类
提供基于隐式反馈协同过滤的音乐推荐服务
"""

import json
import pickle
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from collections import defaultdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MusicRecommender:
    """
    音乐推荐器
    
    基于 implicit 库的 ALS 模型，提供：
    1. 歌曲搜索（支持模糊匹配）
    2. 相似歌曲推荐
    """
    
    def __init__(
        self, 
        model_path: Optional[Path] = None,
        mappings_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None
    ):
        """
        初始化推荐器
        
        Args:
            model_path: 模型文件路径 (默认: data/models/implicit_model.pkl)
            mappings_path: ID映射文件路径 (默认: data/models/cf_mappings.pkl)
            metadata_path: 元数据文件路径 (默认: dataset/processed/metadata.json)
        """
        # 项目根目录
        self.project_root = Path(__file__).parent.parent.parent
        
        # 设置默认路径
        self.model_path = model_path or self.project_root / "data" / "models" / "implicit_model.pkl"
        self.mappings_path = mappings_path or self.project_root / "data" / "models" / "cf_mappings.pkl"
        self.metadata_path = metadata_path or self.project_root / "dataset" / "processed" / "metadata.json"
        
        # 加载资源
        self.model = None
        self.item_to_internal = {}  # MSD ID -> 内部索引
        self.internal_to_item = {}  # 内部索引 -> MSD ID
        self.metadata = {}          # MSD ID -> "Artist - Title"
        self.reverse_index = defaultdict(list)  # 歌名(小写) -> [MSD IDs]
        
        self._load_resources()
        self._build_reverse_index()
        
        logger.info(f"✅ MusicRecommender 初始化完成")
        logger.info(f"   - 模型物品数: {len(self.internal_to_item)}")
        logger.info(f"   - 元数据条目: {len(self.metadata)}")
        logger.info(f"   - 反向索引键: {len(self.reverse_index)}")
    
    def _load_resources(self):
        """加载模型、映射和元数据"""
        
        # 1. 加载模型
        if not self.model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")
        
        logger.info(f"📦 加载模型: {self.model_path.name}")
        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)
        
        # 2. 加载ID映射
        if not self.mappings_path.exists():
            raise FileNotFoundError(f"映射文件不存在: {self.mappings_path}")
        
        logger.info(f"📦 加载映射: {self.mappings_path.name}")
        with open(self.mappings_path, 'rb') as f:
            mappings = pickle.load(f)
            # 映射结构: item_mapping (ID -> 内部索引), reverse_items (内部索引 -> ID)
            self.item_to_internal = mappings.get('item_mapping', {})
            self.internal_to_item = mappings.get('reverse_items', {})
        
        # 3. 加载元数据
        if not self.metadata_path.exists():
            logger.warning(f"⚠️ 元数据文件不存在: {self.metadata_path}")
            logger.warning("   歌曲名将显示为原始ID")
        else:
            logger.info(f"📦 加载元数据: {self.metadata_path.name}")
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
    
    def _build_reverse_index(self):
        """
        构建反向索引：歌名 -> [MSD IDs]
        用于快速通过歌名搜索歌曲ID
        """
        logger.info("🔨 构建反向索引...")
        
        for track_id, display_name in self.metadata.items():
            # 只索引模型中存在的歌曲
            if track_id not in self.item_to_internal:
                continue
            
            # 提取歌名（格式: "Artist - Title"）
            if " - " in display_name:
                parts = display_name.split(" - ", 1)
                artist = parts[0].strip().lower()
                title = parts[1].strip().lower()
                full_name = display_name.lower()
                
                # 索引多种形式
                self.reverse_index[title].append(track_id)
                self.reverse_index[artist].append(track_id)
                self.reverse_index[full_name].append(track_id)
            else:
                # 无法解析的格式，直接索引
                self.reverse_index[display_name.lower()].append(track_id)
        
        logger.info(f"   反向索引构建完成: {len(self.reverse_index)} 个键")
    
    def _get_display_name(self, track_id: str) -> str:
        """获取歌曲的显示名称"""
        return self.metadata.get(track_id, track_id)
    
    def search_song(self, query: str, top_k: int = 5) -> List[Tuple[str, str]]:
        """
        搜索歌曲
        
        Args:
            query: 搜索关键词（歌名、歌手或组合）
            top_k: 返回结果数量
            
        Returns:
            List of (track_id, display_name) 元组
        """
        query_lower = query.lower().strip()
        results = []
        seen_ids = set()
        
        # 1. 精确匹配
        if query_lower in self.reverse_index:
            for track_id in self.reverse_index[query_lower]:
                if track_id not in seen_ids:
                    results.append((track_id, self._get_display_name(track_id)))
                    seen_ids.add(track_id)
        
        # 2. 包含匹配（如果精确匹配不足）
        if len(results) < top_k:
            for key, track_ids in self.reverse_index.items():
                if query_lower in key or key in query_lower:
                    for track_id in track_ids:
                        if track_id not in seen_ids:
                            results.append((track_id, self._get_display_name(track_id)))
                            seen_ids.add(track_id)
                            if len(results) >= top_k * 3:  # 取更多候选
                                break
                if len(results) >= top_k * 3:
                    break
        
        # 3. 按匹配度排序（优先完全包含的）
        def match_score(item):
            _, display_name = item
            name_lower = display_name.lower()
            if query_lower == name_lower:
                return 0  # 完全匹配
            elif query_lower in name_lower:
                return 1  # 查询是子串
            elif name_lower in query_lower:
                return 2  # 名称是查询的子串
            else:
                return 3
        
        results.sort(key=match_score)
        
        return results[:top_k]
    
    def recommend_by_song(self, song_name: str, top_k: int = 5) -> Dict:
        """
        根据歌曲名推荐相似歌曲
        
        Args:
            song_name: 歌曲名（支持模糊匹配）
            top_k: 推荐数量
            
        Returns:
            {
                "query": 原始查询,
                "matched_song": 匹配到的歌曲信息,
                "recommendations": [推荐歌曲列表],
                "error": 错误信息(如果有)
            }
        """
        result = {
            "query": song_name,
            "matched_song": None,
            "recommendations": [],
            "error": None
        }
        
        # 1. 搜索歌曲
        search_results = self.search_song(song_name, top_k=3)
        
        if not search_results:
            result["error"] = f"未找到与 '{song_name}' 匹配的歌曲"
            return result
        
        # 2. 取第一个匹配结果
        target_id, target_name = search_results[0]
        result["matched_song"] = {
            "id": target_id,
            "name": target_name
        }
        
        # 3. 获取内部索引
        if target_id not in self.item_to_internal:
            result["error"] = f"歌曲 '{target_name}' 不在推荐模型中"
            return result
        
        internal_id = self.item_to_internal[target_id]
        
        # 4. 调用模型获取相似物品
        try:
            # similar_items 返回 (ids, scores)
            similar_ids, scores = self.model.similar_items(internal_id, N=top_k + 1)
            
            recommendations = []
            for i, (sim_internal_id, score) in enumerate(zip(similar_ids, scores)):
                # 跳过自身
                if sim_internal_id == internal_id:
                    continue
                
                # 转换回原始ID
                if sim_internal_id in self.internal_to_item:
                    rec_track_id = self.internal_to_item[sim_internal_id]
                    rec_name = self._get_display_name(rec_track_id)
                    recommendations.append({
                        "id": rec_track_id,
                        "name": rec_name,
                        "score": float(score)
                    })
                
                if len(recommendations) >= top_k:
                    break
            
            result["recommendations"] = recommendations
            
        except Exception as e:
            result["error"] = f"推荐过程出错: {str(e)}"
            logger.error(f"推荐出错: {e}", exc_info=True)
        
        return result
    
    def recommend_formatted(self, song_name: str, top_k: int = 5) -> str:
        """
        返回格式化的推荐结果字符串（便于Agent输出）
        
        Args:
            song_name: 歌曲名
            top_k: 推荐数量
            
        Returns:
            格式化的推荐结果字符串
        """
        result = self.recommend_by_song(song_name, top_k)
        
        if result["error"]:
            return f"❌ {result['error']}"
        
        lines = []
        matched = result["matched_song"]
        lines.append(f"🎵 基于歌曲: {matched['name']}")
        lines.append(f"   (ID: {matched['id']})")
        lines.append("")
        lines.append("📋 为你推荐:")
        
        for i, rec in enumerate(result["recommendations"], 1):
            lines.append(f"   {i}. {rec['name']} (相似度: {rec['score']:.2f})")
        
        return "\n".join(lines)


# ============================================================
# 测试代码
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("MusicRecommender 测试")
    print("=" * 60)
    
    # 实例化推荐器
    try:
        recommender = MusicRecommender()
    except FileNotFoundError as e:
        print(f"❌ 初始化失败: {e}")
        exit(1)
    
    print("\n" + "=" * 60)
    print("测试 1: 搜索 'Adelitas Way'")
    print("=" * 60)
    
    search_results = recommender.search_song("Adelitas Way", top_k=5)
    if search_results:
        print(f"找到 {len(search_results)} 个结果:")
        for track_id, name in search_results:
            print(f"   - {name} ({track_id})")
    else:
        print("未找到匹配结果")
    
    print("\n" + "=" * 60)
    print("测试 2: 推荐与 'Dirty Little Thing' 相似的歌曲")
    print("=" * 60)
    
    rec_result = recommender.recommend_by_song("Dirty Little Thing", top_k=5)
    if rec_result["error"]:
        print(f"❌ 错误: {rec_result['error']}")
    else:
        print(f"匹配歌曲: {rec_result['matched_song']['name']}")
        print("推荐列表:")
        for rec in rec_result["recommendations"]:
            print(f"   --> {rec['name']} (相似度: {rec['score']:.4f})")
    
    print("\n" + "=" * 60)
    print("测试 3: 格式化输出")
    print("=" * 60)
    
    formatted = recommender.recommend_formatted("Hate Love", top_k=3)
    print(formatted)
    
    print("\n" + "=" * 60)
    print("测试 4: 查询不存在的歌曲")
    print("=" * 60)
    
    result = recommender.recommend_formatted("这首歌肯定不存在12345")
    print(result)
    
    print("\n✅ 测试完成!")
