#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音乐推荐器封装类（稳定版）
提供基于 implicit ALS 的音乐推荐服务
【已规避 Windows + similar_items 卡死问题】
"""

import os
# ===== Windows 兼容性设置（必须在 import implicit 前）=====
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import json
import pickle
import logging
import numpy as np
from scipy.sparse import csr_matrix
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from collections import defaultdict

# ================= 日志配置 =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MusicRecommender:
    """
    音乐推荐器

    基于 implicit ALS 模型，提供：
    1. 歌曲搜索（模糊匹配）
    2. 基于歌曲的相似歌曲推荐（recommend 稳定实现）
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        mappings_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None
    ):
        """
        初始化推荐器
        """
        self.project_root = Path(__file__).parent.parent.parent

        self.model_path = model_path or self.project_root / "data" / "models" / "implicit_model.pkl"
        self.mappings_path = mappings_path or self.project_root / "data" / "models" / "cf_mappings.pkl"
        self.metadata_path = metadata_path or self.project_root / "dataset" / "processed" / "metadata.json"

        self.model = None
        self.item_to_internal: Dict[str, int] = {}
        self.internal_to_item: Dict[int, str] = {}
        self.metadata: Dict[str, str] = {}
        self.reverse_index = defaultdict(list)

        self._load_resources()
        self._build_reverse_index()

        logger.info("✅ MusicRecommender 初始化完成")
        logger.info(f"   - 模型物品数: {len(self.internal_to_item)}")
        logger.info(f"   - 元数据条目: {len(self.metadata)}")

    # ================= 资源加载 =================
    def _load_resources(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")

        with open(self.model_path, "rb") as f:
            self.model = pickle.load(f)

        if not self.mappings_path.exists():
            raise FileNotFoundError(f"映射文件不存在: {self.mappings_path}")

        with open(self.mappings_path, "rb") as f:
            mappings = pickle.load(f)
            self.item_to_internal = mappings.get("item_mapping", {})
            self.internal_to_item = mappings.get("reverse_items", {})

        if self.metadata_path.exists():
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        else:
            logger.warning("⚠️ 未找到元数据文件，歌曲将显示为 ID")

    # ================= 索引构建 =================
    def _build_reverse_index(self):
        logger.info("🔨 构建歌曲反向索引...")
        for track_id, display_name in self.metadata.items():
            if track_id not in self.item_to_internal:
                continue

            name = display_name.lower()
            self.reverse_index[name].append(track_id)

            if " - " in name:
                artist, title = name.split(" - ", 1)
                self.reverse_index[artist.strip()].append(track_id)
                self.reverse_index[title.strip()].append(track_id)

    def _get_display_name(self, track_id: str) -> str:
        return self.metadata.get(track_id, track_id)

    # ================= 搜索功能 =================
    def search_song(self, query: str, top_k: int = 5) -> List[Tuple[str, str]]:
        query = query.lower().strip()
        results = []
        seen = set()

        if query in self.reverse_index:
            for tid in self.reverse_index[query]:
                if tid not in seen:
                    results.append((tid, self._get_display_name(tid)))
                    seen.add(tid)

        if len(results) < top_k:
            for key, tids in self.reverse_index.items():
                if query in key:
                    for tid in tids:
                        if tid not in seen:
                            results.append((tid, self._get_display_name(tid)))
                            seen.add(tid)
                if len(results) >= top_k * 2:
                    break

        return results[:top_k]

    # ================= 推荐核心（稳定版） =================
    def recommend_by_song(self, song_name: str, top_k: int = 5) -> Dict:
        """
        根据歌曲名推荐相似歌曲
        【使用 recommend()，Windows 稳定】
        """
        result = {
            "query": song_name,
            "matched_song": None,
            "recommendations": [],
            "error": None
        }

        search_results = self.search_song(song_name, top_k=3)
        if not search_results:
            result["error"] = f"未找到与 '{song_name}' 匹配的歌曲"
            return result

        target_id, target_name = search_results[0]
        result["matched_song"] = {"id": target_id, "name": target_name}

        if target_id not in self.item_to_internal:
            result["error"] = f"歌曲 '{target_name}' 不在模型中"
            return result

        target_internal_id = self.item_to_internal[target_id]

        try:
            if hasattr(self.model, "item_factors") and self.model.item_factors is not None:
                n_items = self.model.item_factors.shape[0]
            else:
                n_items = max(self.internal_to_item.keys()) + 1 if self.internal_to_item else 0

            user_items = csr_matrix(
                ([1.0], ([0], [target_internal_id])),
                shape=(1, n_items)
            )

            rec_ids, scores = self.model.recommend(
                userid=0,
                user_items=user_items,
                N=top_k,
                filter_already_liked_items=True,
                recalculate_user=True
            )

            for iid, score in zip(rec_ids, scores):
                if iid in self.internal_to_item:
                    tid = self.internal_to_item[iid]
                    result["recommendations"].append({
                        "id": tid,
                        "name": self._get_display_name(tid),
                        "score": float(score)
                    })

        except Exception as e:
            logger.error("推荐过程异常", exc_info=True)
            result["error"] = str(e)

        return result

    # ================= Agent 输出友好 =================
    def recommend_formatted(self, song_name: str, top_k: int = 5) -> str:
        result = self.recommend_by_song(song_name, top_k)

        if result["error"]:
            return f"❌ {result['error']}"

        lines = [
            f"🎵 基于歌曲: {result['matched_song']['name']}",
            "📋 推荐结果："
        ]

        for i, rec in enumerate(result["recommendations"], 1):
            lines.append(f"{i}. {rec['name']}（得分: {rec['score']:.3f}）")

        return "\n".join(lines)


# ================= 本地测试 =================
if __name__ == "__main__":
    print("=" * 60)
    print("MusicRecommender 稳定版测试")
    print("=" * 60)

    recommender = MusicRecommender()

    print("\n🔍 搜索测试：Adelitas Way")
    for tid, name in recommender.search_song("Adelitas Way"):
        print("-", name, tid)

    print("\n🎧 推荐测试：Dirty Little Thing")
    print(recommender.recommend_formatted("Dirty Little Thing", top_k=5))

    print("\n🎧 推荐测试：不存在的歌曲")
    print(recommender.recommend_formatted("不存在的歌123"))
