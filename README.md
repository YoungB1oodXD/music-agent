# 🎵 Music Agent - 智能音乐推荐系统

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-blue.svg)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> 基于「双脑架构」的智能音乐推荐系统：结合**语义搜索**与**协同过滤**，通过 LLM Agent 编排实现自然语言交互式推荐。

---

## ✨ 核心特性

- 🧠 **双脑架构** - 语义搜索（BGE-M3）+ 协同过滤（Implicit ALS）
- 🤖 **LLM Agent 编排** - 意图识别 → 槽位填充 → 工具调度 → 响应生成
- 💬 **自然语言交互** - 支持中英文对话式推荐
- 🎧 **试听功能** - 8000+ 歌曲可在线试听
- 📊 **展示分数校准** - 用户友好的匹配指数显示
- 🌐 **Web 界面** - React 前端 + FastAPI 后端

---

## 🧠 双脑架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      Music Agent 双脑架构                        │
├─────────────────────────────┬───────────────────────────────────┤
│       🧠 Left Brain         │         🧠 Right Brain            │
│      (语义理解)              │        (行为学习)                  │
├─────────────────────────────┼───────────────────────────────────┤
│  ✦ BGE-M3 向量模型           │  ✦ Implicit ALS 协同过滤           │
│  ✦ ChromaDB 向量数据库       │  ✦ Last.fm 用户行为数据            │
│  ✦ FMA 音乐元数据 (106K)     │  ✦ 839K+ 歌曲交互数据              │
├─────────────────────────────┼───────────────────────────────────┤
│  📝 "relaxing jazz music"   │  🎧 "喜欢这首歌的人还喜欢..."       │
│  📝 "适合学习的轻音乐"        │  🎧 基于历史听歌行为推荐            │
└─────────────────────────────┴───────────────────────────────────┘
```

---

## 📁 项目结构

```
music_agent/
├── 📁 src/                         # 核心模块
│   ├── 📁 agent/                   # LLM Agent 编排层
│   │   └── orchestrator.py         # 意图识别、工具调度、响应生成
│   ├── 📁 api/                     # FastAPI 应用
│   │   └── app.py                  # /chat, /recommend, /search 端点
│   ├── 📁 llm/                     # LLM 客户端
│   │   └── clients/                # Qwen (OpenAI-compatible), Mock
│   ├── 📁 rag/                     # 检索增强生成
│   │   ├── context_builder.py      # 上下文构建
│   │   └── retriever.py            # 相关文档检索
│   ├── 📁 tools/                   # 工具注册
│   │   ├── semantic_search_tool.py # 语义搜索工具
│   │   ├── cf_recommend_tool.py    # 协同过滤工具
│   │   └── hybrid_recommend_tool.py# 混合推荐工具
│   ├── 📁 manager/                 # 会话状态管理
│   ├── 📁 recommender/             # 协同过滤 (Right Brain)
│   └── 📁 searcher/                # 语义搜索 (Left Brain)
│
├── 📁 frontend/                    # React 前端
│   ├── 📁 src/
│   │   ├── 📁 components/          # UI 组件
│   │   ├── 📁 contexts/            # React Context
│   │   ├── 📁 mappers/             # 数据映射
│   │   └── 📁 services/            # API 服务
│   └── vite.config.ts              # Vite 配置
│
├── 📁 scripts/                     # 入口脚本
│   ├── run_api.py                  # 启动 API 服务
│   ├── chat_cli.py                 # 命令行聊天
│   ├── train_cf.py                 # 训练协同过滤模型
│   ├── vectorizer_bge.py           # 构建向量索引
│   └── data_processor_bge.py       # 数据预处理
│
├── 📁 data/                        # 模型产物
│   ├── models/                     # 训练好的模型
│   └── processed/                  # 处理后的数据
│
├── 📁 dataset/                     # 原始数据
│   └── raw/fma_small/              # FMA 音频文件 (8000+ MP3)
│
├── 📁 index/                       # 向量索引
│   └── chroma_bge_m3/              # ChromaDB 持久化
│
├── 📁 docs/                        # 文档
│   ├── 阶段性总结报告_v2.md
│   ├── 试听功能修复报告_20260324.md
│   └── score_calibration_analysis.md
│
├── 📁 tests/                       # 测试脚本
└── 📄 AGENTS.md                    # Agent 开发指南
```

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 创建 Conda 环境
conda create -n music_agent python=3.11 -y
conda activate music_agent

# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend && npm install
```

### 2. 配置环境变量

```bash
# Windows BLAS 线程固定（推荐）
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1

# DashScope API Key（Qwen 模式必需）
set DASHSCOPE_API_KEY_BAILIAN=your_api_key
# 或
set DASHSCOPE_API_KEY=your_api_key

# LLM 模式选择
set MUSIC_AGENT_LLM_MODE=qwen  # 使用 Qwen
# set MUSIC_AGENT_LLM_MODE=mock  # 使用 Mock（无需 API Key）
```

### 3. 启动服务

```bash
# 启动后端 API (端口 8000)
python scripts/run_api.py

# 新终端：启动前端 (端口 3000)
cd frontend && npm run dev
```

### 4. 访问应用

打开浏览器访问 http://localhost:3000

---

## 💡 功能演示

### 🤖 智能对话推荐

通过自然语言与系统交互：

```
用户：推荐一些适合学习的歌
Agent：我为你找到 5 首适合学习的歌曲：
       1. Quiet Pages - Paper Lanterns (匹配度: 92%)
       2. Soft Rain Notes - Window Seat (匹配度: 89%)
       ...

用户：我想要更欢快一点的
Agent：好的，我为你推荐更欢快的歌曲：
       1. Caffeine Loop - Night Library (匹配度: 91%)
       ...
```

### 🎧 试听功能

- 推荐卡片显示「可试听」标签
- 点击播放按钮即可在线试听
- 支持单实例播放（自动暂停前一首）

### 📊 匹配指数

- 每首推荐歌曲显示匹配百分比
- 分数范围 65%~98%
- 基于排名和原始分数校准

---

## 🔧 API 接口

### POST /chat

智能对话接口

```json
{
  "session_id": "optional-session-id",
  "message": "推荐适合学习的歌"
}
```

响应：
```json
{
  "session_id": "xxx",
  "assistant_text": "我为你找到了...",
  "recommendations": [
    {
      "id": "fma_123",
      "name": "Song Name",
      "reason": "适合学习的轻松音乐",
      "is_playable": true,
      "audio_url": "/audio/fma_small/000/000123.mp3",
      "display_score": 92
    }
  ],
  "state": { "mood": "calm", "scene": "study" }
}
```

### GET /audio/{path}

静态音频文件服务

---

## 📊 技术参数

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
| 索引数据 | 106K | FMA 音乐元数据 |

### 试听功能

| 参数 | 值 |
|------|-----|
| 可试听歌曲数 | 8000+ |
| 音频格式 | MP3 |
| 数据来源 | FMA Small |

---

## 🛠️ 开发指南

### 运行测试

```bash
# 测试模块
python src/recommender/music_recommender.py
python src/searcher/music_searcher.py

# 测试 Agent
python tests/agent_orchestrator_smoke.py
python tests/tool_registry_unit.py
```

### 构建系统

```bash
# 1. 数据预处理
python scripts/data_processor_bge.py

# 2. 构建元数据映射
python scripts/build_metadata_from_json.py

# 3. 训练协同过滤模型
python scripts/train_cf.py

# 4. 构建向量索引
python scripts/vectorizer_bge.py

# 5. 构建音频映射
python scripts/build_audio_mapping.py
```

### 命令行聊天

```bash
# Mock 模式（无需 API Key）
python scripts/chat_cli.py --llm mock

# Qwen 模式
python scripts/chat_cli.py --llm qwen

# 单次执行
python scripts/chat_cli.py --llm qwen --once "推荐适合学习的歌"
```

---

## 🆕 Recent Updates

### v1.1.0 (2026-03-24)

#### Audio Playback Fixes
- Fixed audio 404 errors (path prefix mismatch in `audio_mapping.json`)
- Fixed no sound issue (Vite proxy missing `/audio` route)
- Fixed multiple simultaneous playback (global `AudioPlayerContext` singleton)
- Added file existence verification before marking songs as playable

#### Match Score Fixes
- Fixed match score always showing 0%
- Added `score` field extraction from `evidence` to top-level
- Added `display_score` calibration (65-98% range)
- Fixed bottom match bar not syncing with score

#### UI Improvements
- Added toast notifications for playback errors
- Added development logging for score mapping

### Roadmap

- [ ] Offline evaluation metrics (Precision@K, NDCG)
- [ ] Multi-turn dialogue test suite
- [ ] Recommendation robustness optimization
- [ ] User preference persistence across sessions

---

## 📝 注意事项

1. **Windows 用户**：建议设置 `OPENBLAS_NUM_THREADS=1` 避免 implicit 库问题
2. **GPU 加速**：向量化过程支持 CUDA，建议使用 GPU
3. **内存要求**：加载完整模型约需 2-4 GB 内存
4. **API Key**：Qwen 模式需要 DashScope API Key

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
- [Qwen](https://tongyi.aliyun.com/) - 通义千问大模型