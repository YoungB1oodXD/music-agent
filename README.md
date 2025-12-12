# 🎵 Music Agent - 智能音乐推荐系统

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> 基于「双脑架构」的智能音乐推荐系统：结合**语义搜索**与**协同过滤**，提供精准的音乐推荐服务。

---

## 🧠 双脑架构

本项目采用独特的「双脑」设计，模拟人类大脑的左右脑分工：

```
┌─────────────────────────────────────────────────────────────────┐
│                      Music Agent 双脑架构                        │
├─────────────────────────────┬───────────────────────────────────┤
│       🧠 Left Brain         │         🧠 Right Brain            │
│      (语义理解)              │        (行为学习)                  │
├─────────────────────────────┼───────────────────────────────────┤
│  ✦ BGE-M3 向量模型           │  ✦ Implicit ALS 协同过滤           │
│  ✦ ChromaDB 向量数据库       │  ✦ Last.fm 用户行为数据            │
│  ✦ FMA 音乐元数据            │  ✦ 839K+ 歌曲交互数据              │
├─────────────────────────────┼───────────────────────────────────┤
│  📝 "relaxing jazz music"   │  🎧 "喜欢这首歌的人还喜欢..."       │
│  📝 "欢快的流行歌曲"          │  🎧 基于历史听歌行为推荐            │
└─────────────────────────────┴───────────────────────────────────┘
```

| 模块 | 功能 | 数据源 | 技术栈 |
|------|------|--------|--------|
| **Left Brain** | 语义搜索 - 理解用户自然语言描述 | FMA 数据集 (106K 歌曲) | BGE-M3, ChromaDB |
| **Right Brain** | 协同过滤 - 学习用户行为模式 | Last.fm 数据集 (839K 交互) | Implicit ALS |

---

## 📁 项目结构

```
music_agent/
│
├── 📄 README.md                    # 项目文档
├── 📄 requirements.txt             # Python 依赖
├── 📄 .gitignore                   # Git 忽略规则
│
├── 📁 src/                         # 核心模块（可被 import）
│   ├── recommender/                # 协同过滤推荐器 (Right Brain)
│   │   ├── __init__.py
│   │   └── music_recommender.py    # MusicRecommender 类
│   └── searcher/                   # 语义搜索器 (Left Brain)
│       ├── __init__.py
│       └── music_searcher.py       # MusicSearcher 类
│
├── 📁 scripts/                     # 训练与构建脚本
│   ├── train_cf.py                 # 协同过滤模型训练
│   ├── vectorizer_bge.py           # BGE 向量化构建
│   ├── data_processor_bge.py       # FMA 数据清洗
│   ├── build_metadata_from_json.py # 元数据提取
│   ├── eval_model.py               # 模型评估
│   └── run_hybrid_pipeline.py      # 完整流水线
│
├── 📁 data/                        # 模型产物（.gitignore）
│   ├── models/
│   │   ├── implicit_model.pkl      # 协同过滤模型
│   │   └── cf_mappings.pkl         # ID 映射
│   └── processed/
│       └── unified_songs_bge.parquet
│
├── 📁 dataset/                     # 原始数据（.gitignore）
│   ├── raw/
│   │   └── lastfm_train/           # 839K JSON 文件
│   └── processed/
│       └── metadata.json           # ID → 歌名映射
│
├── 📁 index/                       # 向量索引（.gitignore）
│   └── chroma_bge_m3/              # ChromaDB 持久化
│
└── 📁 docs/                        # 历史文档归档
    └── *.md
```

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 创建 Conda 环境
conda create -n music_agent python=3.11 -y
conda activate music_agent

# 安装依赖
pip install -r requirements.txt

# 或使用 conda-forge（推荐 Windows 用户）
conda install -c conda-forge implicit chromadb sentence-transformers
```

### 2. 数据准备

将原始数据放入对应目录：
- `dataset/raw/lastfm_train/` - Last.fm 训练数据 (JSON 格式)
- `dataset/raw/fma_metadata/` - FMA 元数据 (可选)

### 3. 构建系统

```bash
cd scripts/

# Step 1: 训练协同过滤模型 (Right Brain)
python train_cf.py

# Step 2: 提取元数据映射
python build_metadata_from_json.py

# Step 3: 构建向量索引 (Left Brain, 需要 GPU 加速)
python vectorizer_bge.py
```

---

## 💡 使用方法

### 🧠 Right Brain: 协同过滤推荐

```python
from src.recommender import MusicRecommender

# 初始化推荐器
recommender = MusicRecommender()

# 搜索歌曲
results = recommender.search_song("Dirty Little Thing")
print(results)  # [('TRZNRZF...', 'Adelitas Way - Dirty Little Thing'), ...]

# 获取推荐
rec = recommender.recommend_by_song("Hate Love", top_k=5)
print(rec['recommendations'])
# [{'name': 'Adelitas Way - Dirty Little Thing', 'score': 0.99}, ...]

# 格式化输出（适合 Agent）
print(recommender.recommend_formatted("Survive", top_k=3))
# 🎵 基于歌曲: Sick Puppies - Survive
# 📋 为你推荐:
#    1. Adelitas Way - Hate Love (相似度: 0.98)
#    ...
```

### 🧠 Left Brain: 语义搜索

```python
from src.searcher import MusicSearcher

# 初始化搜索器（首次加载模型较慢）
searcher = MusicSearcher()

# 自然语言搜索
results = searcher.search("relaxing jazz music", top_k=5)
for r in results:
    print(f"{r['artist']} - {r['title']} (相似度: {r['similarity']:.2f})")

# 支持中文查询
results_cn = searcher.search("欢快的流行歌曲", top_k=3)

# 格式化输出
print(searcher.search_formatted("sad piano ballad", top_k=3))
# 🔍 搜索: "sad piano ballad"
# 📋 找到 3 首相关音乐:
#    1. Artist - Title [Genre] (相似度: 0.85)
#    ...
```

### 🔀 混合推荐（双脑协作）

```python
from src.recommender import MusicRecommender
from src.searcher import MusicSearcher

# 初始化双脑
recommender = MusicRecommender()
searcher = MusicSearcher()

# 场景：用户说「我想听类似 Coldplay 的轻松音乐」
# Step 1: 语义搜索理解「轻松音乐」
semantic_results = searcher.search("relaxing Coldplay style", top_k=3)

# Step 2: 协同过滤找相似歌曲
for r in semantic_results:
    cf_results = recommender.recommend_by_song(r['title'], top_k=2)
    print(f"基于 {r['title']} 推荐: {cf_results['recommendations']}")
```

---

## 📊 模型参数

### 协同过滤 (Implicit ALS)

| 参数 | 值 | 说明 |
|------|-----|------|
| factors | 64 | 隐向量维度 |
| regularization | 0.01 | L2 正则化 |
| iterations | 15 | 训练迭代次数 |
| 训练数据 | 839K | Last.fm 交互记录 |

### 语义向量 (BGE-M3)

| 参数 | 值 | 说明 |
|------|-----|------|
| model | BAAI/bge-m3 | 多语言向量模型 |
| dimension | 1024 | 向量维度 |
| batch_size | 16 | 批处理大小 |
| 索引数据 | 106K | FMA 音乐元数据 |

---

## 🛠️ 开发指南

### 运行测试

```bash
# 测试推荐器
python src/recommender/music_recommender.py

# 测试搜索器
python src/searcher/music_searcher.py

# 模型评估
python scripts/eval_model.py
```

### 环境变量

```bash
# 禁用 BLAS 多线程（Windows 兼容性）
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
```

---

## 📝 注意事项

1. **Windows 用户**：建议使用 `conda-forge` 安装 `implicit`，避免 C++ 编译问题
2. **GPU 加速**：向量化过程支持 CUDA，建议使用 GPU 加速（RTX 3060 约需 2 小时）
3. **内存要求**：加载完整模型约需 2-4 GB 内存

---

## 📜 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [FMA Dataset](https://github.com/mdeff/fma) - Free Music Archive 数据集
- [Last.fm Dataset](http://ocelma.net/MusicRecommendationDataset/) - 音乐推荐数据集
- [Implicit](https://github.com/benfred/implicit) - 隐式反馈推荐库
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [BGE-M3](https://huggingface.co/BAAI/bge-m3) - 多语言向量模型