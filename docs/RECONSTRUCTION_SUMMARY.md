# 数据处理脚本重构总结

## 重构目标

实现 **原地读取，异地输出** 的数据工程最佳实践：
- ✅ **原始数据不动**：保留在 `../dataset/` 目录（项目上级）
- ✅ **产物整洁**：输出到 `./data/` 和 `./index/` 目录（项目内部）
- ✅ **路径统一**：所有脚本使用相同的常量定义

---

## 重构内容

### 1. **data_processor_bge.py**

#### 变更点
```python
# 【新增】路径常量定义（顶部）
RAW_FMA_PATH = Path(__file__).parent.parent.parent / "dataset" / "fma" / "metadata"
RAW_LASTFM_PATH = Path(__file__).parent.parent.parent / "dataset" / "lastfm"
OUTPUT_PROCESSED_PATH = Path(__file__).parent.parent / "data" / "processed"

# 【修改】__init__ 方法
# 旧: def __init__(self, output_dir: Path = Path("../data/processed"))
# 新: def __init__(self, output_dir: Path = None)
#     if output_dir is None: output_dir = OUTPUT_PROCESSED_PATH

# 【修改】process() 方法默认参数
# 旧: fma_root=Path("../data/raw/fma_metadata")
# 新: fma_root=None (自动使用 RAW_FMA_PATH)

# 【修改】__main__ 脚本（移除硬编码路径）
# 旧: processor.process(fma_root=Path(...), lastfm_root=Path(...))
# 新: processor.process()  # 自动使用配置的路径
```

#### 关键改进
- ✅ 自动识别原始数据位置
- ✅ 自动创建输出目录
- ✅ 相对路径更便携

---

### 2. **vectorizer_bge.py**

#### 变更点
```python
# 【新增】路径常量定义
RAW_FMA_PATH = ...
RAW_LASTFM_PATH = ...
OUTPUT_PROCESSED_PATH = Path(__file__).parent.parent / "data" / "processed"
OUTPUT_INDEX_PATH = Path(__file__).parent.parent / "index" / "chroma_bge_m3"

# 【修改】ChromaVectorDBBGE.__init__
# 旧: persist_dir: Path = Path("../index/chroma_bge_m3")
# 新: persist_dir: Path = None
#     if persist_dir is None: persist_dir = OUTPUT_INDEX_PATH

# 【修改】StoragePipelineBGE.__init__
# 旧: output_dir: Path = Path("../index")
# 新: output_dir: Path = None
#     if output_dir is None: output_dir = OUTPUT_INDEX_PATH.parent

# 【修改】__main__ 脚本
# 旧: parquet_file = Path("../data/processed/unified_songs_bge.parquet")
# 新: parquet_file = OUTPUT_PROCESSED_PATH / "unified_songs_bge.parquet"
```

#### 关键改进
- ✅ 自动查找处理后的数据
- ✅ 自动创建ChromaDB目录
- ✅ 消除魔术字符串

---

### 3. **train_cf.py**

#### 变更点
```python
# 【新增】路径常量定义
RAW_FMA_PATH = ...
RAW_LASTFM_TRAIN_PATH = Path(...) / "dataset" / "lastfm" / "train"
OUTPUT_MODELS_PATH = Path(__file__).parent.parent / "data" / "models"

# 【修改】CFPipeline.__init__
# 旧: output_dir: Path = Path("../data/models")
# 新: output_dir: Path = None
#     if output_dir is None: output_dir = OUTPUT_MODELS_PATH

# 【修改】process() 方法
# 旧: data_dir: Path = Path("../data/raw/lastfm_train")
# 新: data_dir: Path = None
#     if data_dir is None: data_dir = RAW_LASTFM_TRAIN_PATH

# 【修改】__main__ 脚本
# 旧: pipeline.process(data_dir=Path(...), triplet_file=None, ...)
# 新: pipeline.process(no_components=64, epochs=30)  # 使用默认路径
```

#### 关键改进
- ✅ 自动识别训练数据位置
- ✅ 自动创建模型输出目录
- ✅ 更干净的调用接口

---

### 4. **run_hybrid_pipeline.py**

#### 变更点
```python
# 【新增】路径常量定义（全局）
RAW_FMA_PATH = ...
RAW_LASTFM_PATH = ...
RAW_LASTFM_TRAIN_PATH = ...
OUTPUT_PROCESSED_PATH = ...
OUTPUT_MODELS_PATH = ...
OUTPUT_INDEX_PATH = ...

# 【修改】run_pipeline() 函数
# 旧: fma_root = Path("../data/raw/fma_metadata")
# 新: fma_root = RAW_FMA_PATH

# 【修改】各步骤的类初始化
# 旧: processor = DataProcessorBGE(output_dir=Path("../data/processed"))
# 新: processor = DataProcessorBGE()  # 自动使用配置

# 【修改】最终输出信息
# 新增: 打印实际使用的路径，便于用户核对
```

#### 关键改进
- ✅ 统一的路径配置
- ✅ 清晰的路径检查
- ✅ 用户友好的输出信息

---

### 5. **新增辅助文件**

#### PATH_MAPPING.md
- 详细的路径配置指南
- 常量定义和使用示例
- 常见问题解答

#### check_paths.py
- 路径映射检查脚本
- 验证输入数据存在性
- 验证依赖库完整性
- 生成详细的配置报告

---

## 使用示例

### 场景1：标准使用（推荐）

```bash
# 运行完整管道
cd e:\Workspace\music_agent\scripts
python run_hybrid_pipeline.py

# 或检查路径配置
python check_paths.py
```

**输出**：
```
================================================================================
路径配置
================================================================================
[输入] FMA数据: E:\Workspace\dataset\fma\metadata
[输入] Last.fm标签: E:\Workspace\dataset\lastfm
[输入] Last.fm训练: E:\Workspace\dataset\lastfm\train
[输出] 清洗数据: E:\Workspace\music_agent\data\processed
[输出] 模型: E:\Workspace\music_agent\data\models
[输出] 向量索引: E:\Workspace\music_agent\index\chroma_bge_m3
================================================================================
```

### 场景2：修改路径位置

如果数据在其他位置，只需修改脚本顶部的常量：

```python
# 在 data_processor_bge.py 顶部
RAW_FMA_PATH = Path("/custom/path/to/fma")
OUTPUT_PROCESSED_PATH = Path("/custom/output/dir")
```

### 场景3：分步骤运行

```bash
# 步骤1：数据清洗
python data_processor_bge.py

# 步骤2：向量化
python vectorizer_bge.py

# 步骤3：模型训练
python train_cf.py
```

---

## 路径映射表

| 模块 | 输入路径 | 输出路径 |
|------|--------|--------|
| `data_processor_bge.py` | `RAW_FMA_PATH` <br> `RAW_LASTFM_PATH` | `OUTPUT_PROCESSED_PATH` |
| `vectorizer_bge.py` | `OUTPUT_PROCESSED_PATH` | `OUTPUT_INDEX_PATH` |
| `train_cf.py` | `RAW_LASTFM_TRAIN_PATH` | `OUTPUT_MODELS_PATH` |
| `run_hybrid_pipeline.py` | 所有上述输入 | 所有上述输出 |

---

## 技术细节

### 相对路径计算

```python
# 脚本位置: e:\Workspace\music_agent\scripts\*.py
script_dir = Path(__file__).parent  # ./scripts

# 输入数据（上级目录）
RAW_FMA_PATH = Path(__file__).parent.parent.parent / "dataset" / "fma" / "metadata"
# 计算: ./scripts/../../../ + dataset/fma/metadata = e:\Workspace\dataset\fma\metadata

# 输出产物（项目内）
OUTPUT_PROCESSED_PATH = Path(__file__).parent.parent / "data" / "processed"
# 计算: ./scripts/.. + data/processed = e:\Workspace\music_agent\data\processed
```

### 自动目录创建

```python
# 所有类都会自动创建输出目录
self.output_dir.mkdir(parents=True, exist_ok=True)
# - parents=True: 创建中间目录
# - exist_ok=True: 目录存在时不报错
```

---

## 验证清单

运行以下命令验证重构成功：

```bash
# 1. 检查路径配置
cd e:\Workspace\music_agent\scripts
python check_paths.py

# 2. 运行数据处理（如果有输入数据）
python data_processor_bge.py

# 3. 检查输出文件
dir ..\data\processed
dir ..\data\models
dir ..\index
```

---

## 注意事项

⚠️ **重要**：
1. **原始数据位置必须正确**：`../dataset/fma/metadata/` 和 `../dataset/lastfm/`
2. **lightfm_py311环境**：确保激活了正确的虚拟环境
3. **相对路径依赖**：脚本必须从 `scripts/` 目录运行，或使用绝对路径修改常量

---

## 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| v2.0 | 2025-12-02 | 路径映射重构 |
| v1.0 | 2025-11-xx | 初始版本 |

---

**最后修改**：2025-12-02  
**负责人**：Qoder AI
