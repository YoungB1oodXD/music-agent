import json
import pickle
import numpy as np
from pathlib import Path
import implicit

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
MODEL_PATH = PROJECT_ROOT / "data" / "models" / "implicit_model.pkl"
MAPPINGS_PATH = PROJECT_ROOT / "data" / "models" / "cf_mappings.pkl"
METADATA_PATH = PROJECT_ROOT / "dataset" / "processed" / "metadata.json"

def load_resources():
    print(f"Loading model from {MODEL_PATH}...")
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
        
    print(f"Loading mappings from {MAPPINGS_PATH}...")
    with open(MAPPINGS_PATH, 'rb') as f:
        mappings = pickle.load(f)
        
    return model, mappings

def load_metadata() -> dict:
    """加载元数据映射 (MSD ID -> 歌手 - 歌名)"""
    if not METADATA_PATH.exists():
        print(f"⚠️  元数据文件不存在: {METADATA_PATH}")
        print("   请先运行: python build_metadata_from_json.py")
        return {}
    
    with open(METADATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def resolve_song_name(track_id: str, metadata_dict: dict) -> str:
    """
    将 MSD ID 转换为可读的歌曲名称
    格式: 歌名 (ID) 或 歌手 - 歌名 (ID)
    """
    if track_id in metadata_dict:
        display_name = metadata_dict[track_id]
        return f"{display_name} ({track_id})"
    else:
        # 回退：只显示原始 ID
        return f"[未知] ({track_id})"

def main():
    # 1. 加载资源
    try:
        model, mappings = load_resources()
    except FileNotFoundError:
        print("❌ 找不到模型文件，请先运行训练脚本！")
        return
    
    # 加载元数据映射
    metadata = load_metadata()
    if metadata:
        print(f"✅ 已加载 {len(metadata)} 条元数据映射")
    else:
        print("⚠️  未加载元数据，将只显示原始 ID")

    # 获取反向映射 (从 内部ID -> 原始ID)
    reverse_items = mappings['reverse_items']
    item_mapping = mappings['item_mapping']
    
    # 2. 获取最热门的 5 个物品（根据交互次数或 ID 顺序简单的取几个）
    # 在 implicit 中没有直接存储热门度，我们随机取几个存在的 ID 来测试
    print("\n" + "="*50)
    print("🔍 测试 1: '相似歌曲' (Item-Item Similarity)")
    print("="*50)
    
    # 随机选 3 个物品ID进行测试
    test_internal_ids = list(range(0, min(30, len(reverse_items)), 10)) 
    
    for internal_id in test_internal_ids:
        original_id = reverse_items[internal_id]
        target_name = resolve_song_name(original_id, metadata)
        print(f"\n🎵 目标歌曲: {target_name}")
        
        # 获取最相似的 5 个物品
        # implicit.als 模型使用的是 model.similar_items(itemid, N)
        similar_ids, scores = model.similar_items(internal_id, N=6) # N=6 因为第一个通常是自己
        
        for i in range(len(similar_ids)):
            sim_internal_id = similar_ids[i]
            sim_original_id = reverse_items[sim_internal_id]
            score = scores[i]
            
            if sim_internal_id == internal_id:
                continue # 跳过自己
            
            sim_name = resolve_song_name(sim_original_id, metadata)
            print(f"   --> 相似推荐: {sim_name} (相似度: {score:.4f})")

    # 3. 模拟用户推荐
    print("\n" + "="*50)
    print("👤 测试 2: '猜你喜欢' (User Recommendation)")
    print("="*50)
    
    # 假设一个用户喜欢上面测试的第一个物品
    user_history_internal_ids = [test_internal_ids[0]]
    original_history = [reverse_items[i] for i in user_history_internal_ids]
    
    history_names = [resolve_song_name(tid, metadata) for tid in original_history]
    print(f"假定用户听过: {history_names}")
    
    # implicit >= 0.6 要求传入 user_items CSR 矩阵
    # 这里我们用物品相似度来模拟推荐
    print("\n基于听歌历史的相似推荐:")
    for hist_internal_id in user_history_internal_ids:
        ids, scores = model.similar_items(hist_internal_id, N=6)
        for i in range(len(ids)):
            if ids[i] == hist_internal_id:
                continue
            rec_original_id = reverse_items[ids[i]]
            rec_name = resolve_song_name(rec_original_id, metadata)
            print(f"   --> 推荐: {rec_name} (得分: {scores[i]:.4f})")

if __name__ == "__main__":
    main()