# 快速开始指南（重构后）

## 5秒快速执行

```bash
# 激活环境
conda activate lightfm_py311

# 进入脚本目录
cd e:\Workspace\music_agent\scripts

# 运行完整管道（自动处理所有路径）
python run_hybrid_pipeline.py
```

---

## 核心改进

### 前后对比

#### 原来（v1.0）
```python
# 需要手动指定每个路径
processor = DataProcessorBGE(output_dir=Path("../data/processed"))
output_path, records = processor.process(
    fma_root=Path("../data/raw/fma_metadata"),          # 错误路径！
    lastfm_root=Path("../data/raw/lastfm_subset")       # 不存在！
)
```

#### 现在（v2.0）
```python
# 自动使用正确的路径
processor = DataProcessorBGE()
output_path, records = processor.process()  # 完成！
```

---

## 路径自动映射

所有脚本自动执行以下映射：

### 输入（原始数据）
```
你的数据 ← 来自 ../dataset/ 目录（不动）
├── ../dataset/fma/metadata/          [FMA元数据]
│   ├── tracks.csv
│   └── features.csv
├── ../dataset/lastfm/                [Last.fm标签]
│   └── *.json
└── ../dataset/lastfm/train/          [Last.fm交互]
    └── *.csv/.txt
```

### 输出（生成的产物）
```
生成的文件 → 存储到 ./data/ 和 ./index/（整洁）
├── ./data/processed/
│   └── unified_songs_bge.parquet     [清洗数据]
├── ./data/models/
│   ├── lightfm_model.pkl             [LightFM模型]
│   └── cf_mappings.pkl               [ID映射]
└── ./index/chroma_bge_m3/            [向量索引]
    └── [ChromaDB数据库]
```

---

## 运行方式

### 方式1：完整管道（推荐）

```bash
python run_hybrid_pipeline.py
```

**执行内容**：
1. ✅ 数据处理（FMA + Last.fm融合）
2. ✅ BGE-M3向量化（ChromaDB存储）
3. ✅ LightFM协同过滤（模型训练）

**输出**：
```
================================================================================
混合推荐系统管道完成总结
================================================================================
[输入数据位置]:
  FMA元数据: E:\Workspace\dataset\fma\metadata
  Last.fm标签: E:\Workspace\dataset\lastfm
  Last.fm训练: E:\Workspace\dataset\lastfm\train

[输出文件位置]:
  清洗数据: E:\Workspace\music_agent\data\processed/unified_songs_bge.parquet
  ChromaDB向量库: E:\Workspace\music_agent\index\chroma_bge_m3/
  LightFM模型: E:\Workspace\music_agent\data\models/lightfm_model.pkl
  ID映射: E:\Workspace\music_agent\data\models/cf_mappings.pkl
================================================================================
```

---

### 方式2：分步骤运行

```bash
# 步骤1：数据清洗
python data_processor_bge.py
# 输出: ./data/processed/unified_songs_bge.parquet

# 步骤2：向量化
python vectorizer_bge.py
# 输出: ./index/chroma_bge_m3/

# 步骤3：模型训练
python train_cf.py
# 输出: ./data/models/*.pkl
```

---

### 方式3：检查路径配置

```bash
python check_paths.py
```

**验证内容**：
- ✓ 输入数据是否存在
- ✓ 输出目录是否可创建
- ✓ Python依赖是否完整

---

## 环境要求

### 虚拟环境
```bash
conda activate lightfm_py311
```

### 依赖库（已安装在lightfm_py311中）
```
pandas >= 2.3.3
numpy >= 1.26.4
sentence-transformers >= 5.1.2  (BGE-M3)
chromadb >= 1.3.5              (向量数据库)
lightfm >= 1.17                (协同过滤)
torch >= 2.9.1                 (深度学习)
```

---

## 常见问题

### Q1: 脚本找不到数据怎么办？

检查数据是否在正确位置：
```bash
dir ..\dataset\fma\metadata
dir ..\dataset\lastfm
```

或运行诊断脚本：
```bash
python check_paths.py
```

### Q2: 能否修改输入/输出路径？

可以！在脚本顶部修改常量：
```python
# 如果数据在其他位置
RAW_FMA_PATH = Path("/your/custom/path/fma")

# 如果想输出到其他位置
OUTPUT_PROCESSED_PATH = Path("/your/output/path")
```

### Q3: 脚本会覆盖现有数据吗？

**不会**！脚本使用 `exist_ok=True` 创建目录，不会删除现有文件。

### Q4: 如何只运行某个步骤？

直接运行对应脚本：
```bash
# 只运行数据处理
python data_processor_bge.py

# 只运行向量化
python vectorizer_bge.py
```

### Q5: 如何在不同项目间重复使用脚本？

相对路径设计使得脚本可以直接复制到其他项目的 `scripts/` 目录：
```
新项目/
├── scripts/
│   ├── data_processor_bge.py   ← 复制来的（自动识别路径）
│   ├── vectorizer_bge.py       ← 复制来的
│   ├── train_cf.py             ← 复制来的
│   └── run_hybrid_pipeline.py  ← 复制来的
├── data/
│   ├── processed/
│   └── models/
└── index/
```

---

## 文件目录结构

```
e:\Workspace\
├── dataset/                          ← 原始数据（不动）
│   ├── fma/
│   │   └── metadata/
│   │       ├── tracks.csv
│   │       └── features.csv
│   └── lastfm/
│       ├── *.json
│       └── train/
│           └── *.csv
│
└── music_agent/                      ← 项目目录
    ├── scripts/                      ← 脚本目录
    │   ├── data_processor_bge.py     ← 已重构
    │   ├── vectorizer_bge.py         ← 已重构
    │   ├── train_cf.py               ← 已重构
    │   ├── run_hybrid_pipeline.py    ← 已重构
    │   ├── check_paths.py            ← 新增
    │   └── PATH_MAPPING.md           ← 新增
    │
    ├── data/                         ← 生成的数据（整洁）
    │   ├── processed/
    │   │   └── unified_songs_bge.parquet
    │   └── models/
    │       ├── lightfm_model.pkl
    │       └── cf_mappings.pkl
    │
    ├── index/                        ← 向量索引（整洁）
    │   └── chroma_bge_m3/
    │       └── [ChromaDB files]
    │
    ├── RECONSTRUCTION_SUMMARY.md     ← 新增
    └── README.md
```

---

## 验证完成

运行以下命令验证所有设置正确：

```bash
cd e:\Workspace\music_agent\scripts

# 检查路径和依赖
python check_paths.py

# 若以上检查通过，运行完整管道
python run_hybrid_pipeline.py

# 验证输出
dir ..\data\processed
dir ..\data\models  
dir ..\index
```

---

## 技术细节（可选阅读）

详见以下文档：
- [`PATH_MAPPING.md`](scripts/PATH_MAPPING.md) - 详细的路径配置指南
- [`RECONSTRUCTION_SUMMARY.md`](RECONSTRUCTION_SUMMARY.md) - 重构改动详情

---

## 更新日志

| 版本 | 日期 | 改动 |
|------|------|------|
| **v2.0** | **2025-12-02** | **路径映射重构** ✨ |
| v1.0 | 2025-11-xx | 初始版本 |

---

**立即开始**：
```bash
cd e:\Workspace\music_agent\scripts
python run_hybrid_pipeline.py
```
