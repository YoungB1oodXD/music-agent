# 🎵 Music Agent - 智能音乐推荐对话助手

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> 基于**双脑架构**的智能音乐推荐对话助手，结合语义搜索与内容相似度匹配，通过 LLM Agent 编排实现自然语言交互式推荐。

![Demo](docs/demo.gif)

---

## ✨ 核心特性

- 🧠 **双脑推荐架构**
  - **左脑**：BGE-M3 向量检索 + ChromaDB 语义匹配
  - **右脑**：基于 FMA 元数据的内容相似度（genre/mood/energy/tags）
  - **融合**：加权混合推荐，平衡语义相关性与内容多样性
- 🤖 **LLM Agent 编排** - 意图识别 → 槽位填充 → 工具调度 → RAG 上下文 → 响应生成
- 💬 **自然语言交互** - 中文/英文对话式推荐，支持多轮上下文
- 🎧 **在线试听** - 8000+ 首歌曲可直接在线播放
- 📊 **智能分数** - 基于排名和相似度的校准匹配指数（65-98%）
- 🌐 **现代 Web 界面** - React 19 + TailwindCSS v4 暗色主题

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Music Agent 系统架构                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │   Frontend   │────▶│  FastAPI    │────▶│ Orchestrator │        │
│  │   (React)    │◀────│  Backend    │◀────│   (LLM)     │        │
│  └──────────────┘     └──────────────┘     └──────┬───────┘        │
│                                                      │               │
│                                    ┌─────────────────┼───────────┐   │
│                                    │                 │           │   │
│                                    ▼                 ▼           ▼   │
│                           ┌──────────────┐  ┌────────────┐ ┌─────┐ │
│                           │   Semantic   │  │   RAG     │ │Token│ │
│                           │   Search    │  │  Context  │ │Store│ │
│                           └──────┬───────┘  └────────────┘ └─────┘ │
│                                  │                                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     双脑推荐引擎                               │ │
│  ├────────────────────────────┬─────────────────────────────────┤ │
│  │      🧠 Left Brain        │        🧠 Right Brain            │ │
│  │   BGE-M3 + ChromaDB       │   Content-Based (FMA Metadata)   │ │
│  │   语义向量检索             │   流派/情绪/能量/标签匹配          │ │
│  └────────────────────────────┴─────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
music_agent/
├── src/                         # Python 后端源码
│   ├── agent/                   # LLM Agent 编排层
│   │   ├── orchestrator.py      # 意图识别、工具调度、响应合成
│   │   └── mock_llm.py          # Mock LLM（开发测试用）
│   ├── api/                     # FastAPI 应用
│   │   ├── app.py               # 主应用、路由、中间件
│   │   ├── auth.py              # 认证
│   │   ├── session_store.py    # 会话存储
│   │   └── playlist.py          # 歌单管理
│   ├── llm/                     # LLM 客户端
│   │   ├── clients/
│   │   │   └── qwen_openai_compat.py  # Qwen (OpenAI-compatible)
│   │   └── prompts/             # Prompt 模板
│   ├── rag/                     # 检索增强生成
│   │   ├── context_builder.py   # 上下文构建
│   │   ├── retriever.py         # 文档检索
│   │   └── sanitize.py          # 注入防护
│   ├── tools/                  # 工具层
│   │   ├── registry.py          # 工具注册表
│   │   ├── semantic_search_tool.py  # 语义搜索
│   │   └── hybrid_recommend_tool.py # 混合推荐
│   ├── searcher/                # 向量搜索
│   │   └── music_searcher.py    # ChromaDB + BGE-M3
│   ├── manager/                # 状态管理
│   │   └── session_state.py     # 会话状态
│   └── models/                 # 数据模型
│
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── components/         # React 组件
│   │   │   ├── pages/          # 页面组件
│   │   │   │   ├── ChatPage.tsx
│   │   │   │   └── PlaylistPage.tsx
│   │   │   └── layout/         # 布局组件
│   │   ├── services/           # API 服务
│   │   │   ├── api.ts         # API 客户端
│   │   │   ├── chat.ts        # 对话服务
│   │   │   └── feedback.ts    # 反馈服务
│   │   ├── store/             # Zustand 状态
│   │   │   ├── useChatStore.ts
│   │   │   └── useAuthStore.ts
│   │   └── contexts/          # React Context
│   │       └── AudioPlayerContext.tsx
│   └── vite.config.ts          # Vite 配置
│
├── scripts/                     # 数据处理脚本
│   ├── run_api.py              # 启动 API 服务
│   ├── chat_cli.py            # 命令行对话
│   ├── vectorizer_bge.py      # 构建向量索引
│   └── data_processor_bge.py  # 数据预处理
│
├── tests/                      # 测试脚本
│   ├── agent_orchestrator_smoke.py
│   └── tool_registry_unit.py
│
└── docs/                       # 文档
```

---

## 🚀 快速开始

### 前置依赖

- Python 3.11+
- Node.js 18+
- [FMA Small Dataset](https://github.com/mdeff/fma) (需手动下载)
- [Qwen API Key](https://dashscope.console.aliyun.com/) (可选，mock 模式无需)

### 1. 克隆与安装

```bash
git clone https://github.com/YOUR_USERNAME/music_agent.git
cd music_agent

# 创建 Python 环境
conda create -n music_agent python=3.11 -y
conda activate music_agent

# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend && npm install && cd ..
```

### 2. 数据准备

```bash
# 下载 FMA Small 数据集到 dataset/raw/fma_small/

# 数据预处理
python scripts/data_processor_bge.py

# 构建向量索引
python scripts/vectorizer_bge.py

# 构建元数据映射
python scripts/build_metadata_from_json.py

# 构建音频映射
python scripts/build_audio_mapping.py
```

### 3. 配置与启动

```bash
# 配置环境变量
# Windows
set MUSIC_AGENT_LLM_MODE=mock
set MUSIC_AGENT_LLM_MODE=qwen   # 需要真实 API Key

# Linux/Mac
export MUSIC_AGENT_LLM_MODE=mock

# 启动后端 (端口 8000)
python scripts/run_api.py

# 新终端：启动前端 (端口 3000)
cd frontend && npm run dev
```

### 4. 访问

打开 http://localhost:3000

---

## 💡 使用示例

### 对话式推荐

```
你：推荐一些适合晚上一个人听的音乐
助手：为你找到以下适合夜间独处的歌曲：

🎵 Quiet Pages - Paper Lanterns
   流派：Lo-fi / 匹配度：91%
   理由：旋律轻柔、节奏缓慢，符合夜间放松的氛围

🎵 Soft Rain Notes - Window Seat  
   流派：Ambient / 匹配度：88%
   理由：环境音乐风格，适合安静的夜晚

你：换成更欢快的
助手：好的，为你推荐更欢快的歌曲：
...
```

### 偏好调整

```
你：来点高能量的跑步音乐
助手：已更新你的偏好（能量：高），为你推荐：

🎵 Caffeine Loop - Night Library
   流派：Electronic / 匹配度：93%
   理由：节奏明快、能量充沛，适合运动场景
```

---

## 🔧 API 参考

### 核心端点

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/chat` | 对话式推荐 | 可选 |
| POST | `/feedback` | 反馈（喜欢/不喜欢） | 必需 |
| GET | `/sessions` | 会话列表 | 必需 |
| GET | `/sessions/{id}` | 会话详情 | 必需 |
| POST | `/sessions/{id}/reset` | 重置会话 | 必需 |
| GET | `/playlists` | 歌单列表 | 必需 |
| GET | `/health` | 健康检查 | 否 |

### `/chat` 请求示例

```json
{
  "session_id": "abc123",
  "message": "推荐适合学习的轻音乐"
}
```

### `/chat` 响应示例

```json
{
  "session_id": "abc123",
  "assistant_text": "为你找到以下适合学习的歌曲：",
  "recommendations": [
    {
      "id": "fma_000123",
      "name": "Quiet Pages - Paper Lanterns",
      "reason": "旋律轻柔、节奏缓慢，适合学习场景",
      "is_playable": true,
      "audio_url": "/audio/fma_small/000/000123.mp3",
      "display_score": 91,
      "genre": "Lo-fi"
    }
  ],
  "state": {
    "current_scene": "学习",
    "current_mood": "平静"
  }
}
```

---

## 📊 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| Python 3.11 | 运行环境 |
| FastAPI | Web 框架 |
| ChromaDB | 向量数据库 |
| BGE-M3 | 多语言向量模型 |
| Qwen (DashScope) | 大语言模型 |
| SQLAlchemy + SQLite | 数据持久化 |

### 前端

| 技术 | 用途 |
|------|------|
| React 19 | UI 框架 |
| TypeScript | 类型安全 |
| Vite | 构建工具 |
| TailwindCSS v4 | 样式 |
| Zustand | 状态管理 |

### 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 向量维度 | 1024 | BGE-M3 输出维度 |
| 音乐规模 | 106,573 首 | FMA 元数据 |
| 可试听 | 8,000+ 首 | FMA Small |
| 推荐 Top-K | 5-20 | 可配置 |
| 匹配分数 | 65-98% | 校准后显示 |

---

## 🧪 测试

```bash
# 后端测试
python -m compileall src scripts tests

# Agent 编排测试
python tests/agent_orchestrator_smoke.py

# 工具注册测试
python tests/tool_registry_unit.py

# 工具排除测试
python tests/tool_exclude_ids_smoke.py

# 前端类型检查
cd frontend && npm run lint
```

---

## 🛠️ 开发

### 项目规范

- **Python**: 4 空格缩进，类型提示，snake_case
- **TypeScript**: 2 空格缩进，PascalCase 组件
- **提交**: 使用 `git commit` (非必须)
- **测试**: 独立 smoke 脚本，非 pytest

### 相关文档

- [AGENTS.md](AGENTS.md) - 开发规范
- [CLAUDE.md](CLAUDE.md) - AI 助手指南
- `src/tools/AGENTS.md` - 工具层规范
- `src/agent/AGENTS.md` - 编排层规范

---

## ⚠️ 已知限制

- **会话存储**：内存存储，重启后会话丢失（生产环境建议用 Redis）
- **LLM 模式**：mock 模式使用确定性回复，qwen 模式需要 API Key
- **数据规模**：FMA Small 子集，非完整数据集

---

## 📜 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [FMA Dataset](https://github.com/mdeff/fma) - Free Music Archive 数据集
- [BGE-M3](https://github.com/BAAI-bge/bge-m3) - BAAI 多语言向量模型
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [Qwen](https://tongyi.aliyun.com/) - 阿里通义千问大模型
- [React](https://react.dev/) - UI 框架
