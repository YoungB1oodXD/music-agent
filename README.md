# 🎵 Mustify - 智能音乐推荐对话助手

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> 基于**混合推荐架构**的智能音乐推荐对话助手，结合语义搜索与内容相似度匹配，通过 LLM Agent 编排实现自然语言交互式推荐。

<!-- 【UI界面展示】 -->
<!-- 详情见 docs/screenshots/ 目录 -->
<!-- ![登录页面](docs/screenshots/login.png) -->
<!-- ![对话推荐](docs/screenshots/chat-recommend.png) -->
<!-- ![用户画像](docs/screenshots/portrait.png) -->
<!-- ![历史会话](docs/screenshots/history.png) -->

---

## ✨ 核心特性

- 🧠 **混合推荐架构**
  - **语义检索**：BGE-M3 向量检索 + ChromaDB 语义匹配
  - **内容匹配**：基于 FMA 元数据的内容相似度（genre/mood/energy/tags）
  - **融合**：加权混合推荐（默认 0.6:0.4），平衡语义相关性与内容多样性
- 🤖 **LLM Agent 编排** - 意图识别 → 槽位填充 → 工具调度 → RAG 上下文 → 响应生成
- 💬 **自然语言交互** - 中文/英文对话式推荐，支持多轮上下文
- 🎧 **在线试听** - 8000+ 首歌曲可直接在线播放
- 📊 **智能分数** - 基于排名和相似度的校准匹配指数（65-98%）
- 🌐 **现代 Web 界面** - React 19 + TailwindCSS v4 暗色主题
- 🔄 **反馈闭环** - Like/Dislike → 流派计数 + 能量加权平均 → 加法融合影响推荐排序
- 🎨 **AI 用户画像** - 基于喜欢歌曲 + 对话历史 + 场景偏好，由 Qwen 生成个性化品味深度解读（缓存至 DB）
- 💾 **会话持久化** - SQLite 存储会话状态，重启后推荐历史不丢失

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Mustify 系统架构                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐          │
│  │   Frontend   │────▶│   FastAPI   │────▶│ Orchestrator │          │
│  │   (React)    │◀────│   Backend   │◀────│   (LLM)     │          │
│  └──────────────┘     └──────────────┘     └──────┬───────┘          │
│                                                      │                 │
│                                    ┌─────────────────┼──────────────┐  │
│                                    │                 │              │  │
│                                    ▼                 ▼              ▼  │
│                           ┌──────────────┐  ┌────────────┐  ┌──────────┐│
│                           │  Semantic    │  │    RAG    │  │  Token   ││
│                           │  Search     │  │  Context  │  │  Store   ││
│                           └──────┬───────┘  └────────────┘  └──────────┘│
│                                  │                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                      混合推荐引擎                                   ││
│  ├────────────────────────────┬────────────────────────────────────────┤│
│  │     🧠 语义检索            │         🧠 内容匹配                    ││
│  │  BGE-M3 + ChromaDB        │  Content-Based (FMA Metadata)          ││
│  │  语义向量检索               │  流派/情绪/能量/标签匹配               ││
│  └────────────────────────────┴────────────────────────────────────────┘│
│                                                                       │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐          │
│  │ ai_portrait  │────▶│ Portrait     │────▶│  AI Deep     │          │
│  │   API        │     │  Service     │     │  Analysis    │          │
│  └──────────────┘     └──────────────┘     └──────────────┘          │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
music_agent/
├── src/                          # Python 后端源码
│   ├── agent/                     # LLM Agent 编排层
│   │   ├── orchestrator.py       # 意图识别、工具调度、响应合成
│   │   └── mock_llm.py           # Mock LLM（开发测试用）
│   ├── api/                      # FastAPI 应用
│   │   ├── app.py               # 主应用、路由、中间件
│   │   ├── auth.py              # 认证
│   │   ├── sessions.py          # 会话管理（含持久化）
│   │   ├── session_store.py    # 内存会话存储
│   │   ├── playlist.py          # 歌单管理
│   │   ├── user.py             # 用户管理
│   │   ├── ai_portrait.py      # AI 用户画像 API
│   │   └── session_persistence.py # 会话持久化模型
│   ├── llm/                     # LLM 客户端
│   │   ├── clients/
│   │   │   └── qwen_openai_compat.py  # Qwen (OpenAI-compatible)
│   │   └── prompts/             # Prompt 模板
│   ├── rag/                     # 检索增强生成
│   │   ├── context_builder.py  # 上下文构建
│   │   ├── retriever.py        # 文档检索
│   │   └── sanitize.py          # 注入防护
│   ├── tools/                   # 工具层
│   │   ├── registry.py         # 工具注册表
│   │   ├── semantic_search_tool.py  # 语义搜索
│   │   └── hybrid_recommend_tool.py # 混合推荐
│   ├── searcher/               # 向量搜索
│   │   └── music_searcher.py   # ChromaDB + BGE-M3
│   ├── recommender/            # 内容推荐
│   │   └── music_recommender.py # 基于 FMA 元数据的相似度匹配
│   ├── manager/                # 状态管理
│   │   └── session_state.py    # 会话状态
│   ├── models/                 # 数据模型
│   │   └── session_persistence.py
│   └── services/
│       └── portrait_service.py  # 用户画像服务（Deep Analysis）
│
├── frontend/                     # React 前端
│   ├── src/
│   │   ├── components/
│   │   │   ├── pages/          # 页面组件
│   │   │   │   ├── ChatPage.tsx      # 对话页面
│   │   │   │   ├── PlaylistPage.tsx # 歌单页面
│   │   │   │   ├── HistoryPage.tsx  # 历史会话页面
│   │   │   │   └── LandingPage.tsx  # 落地页
│   │   │   ├── layout/         # 布局组件
│   │   │   │   ├── Sidebar.tsx          # 侧边栏
│   │   │   │   ├── ChatArea.tsx         # 对话区域
│   │   │   │   ├── RecommendationPanel.tsx  # 推荐面板
│   │   │   │   └── Toast.tsx            # 提示组件
│   │   │   ├── profile/        # 用户画像
│   │   │   │   └── UserProfileModal.tsx # 画像弹窗
│   │   │   └── auth/           # 认证组件
│   │   │       ├── Login.tsx
│   │   │       └── Register.tsx
│   │   ├── services/           # API 服务
│   │   │   ├── api.ts         # API 客户端
│   │   │   ├── chat.ts        # 对话服务
│   │   │   └── feedback.ts    # 反馈服务
│   │   ├── store/              # Zustand 状态
│   │   │   ├── useChatStore.ts     # 对话状态
│   │   │   ├── useAuthStore.ts     # 认证状态
│   │   │   ├── usePlaylistStore.ts # 歌单状态
│   │   │   └── useProfileStore.ts  # 用户画像状态
│   │   └── contexts/           # React Context
│   │       └── AudioPlayerContext.tsx
│   └── vite.config.ts           # Vite 配置
│
├── scripts/                     # 数据处理与工具脚本
│   ├── run_api.py              # 启动 API 服务
│   ├── chat_cli.py            # 命令行对话
│   ├── vectorizer_bge.py       # 构建向量索引
│   ├── data_processor_bge.py  # 数据预处理
│   ├── build_metadata_from_json.py
│   ├── build_audio_mapping.py
│   ├── migrate_add_portrait_deep_analysis.py  # 画像字段迁移
│   └── migrate_add_portrait_columns.py
│
├── tests/                       # 独立测试脚本（非 pytest）
│   ├── agent_orchestrator_smoke.py
│   ├── tool_registry_unit.py
│   └── api_chat_smoke.py
│
└── docs/                        # 文档
    └── screenshots/             # UI 界面截图
        ├── login.png            # 【登录页面】
        ├── chat-recommend.png   # 【对话推荐界面】
        ├── portrait.png         # 【用户画像弹窗】
        ├── history.png          # 【历史会话页面】
        └── playlist.png         # 【歌单管理页面】
```

---

## 🚀 快速开始

### 前置依赖

- Python 3.11+
- Node.js 18+
- [FMA Small Dataset](https://github.com/mdeff/fma)（需手动下载）
- [Qwen API Key](https://dashscope.console.aliyun.com/)（可选，mock 模式无需）

### 1. 克隆与安装

```bash
git clone https://github.com/YoungB1oodXD/music-agent.git
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

# 启动后端（端口 8000）
python scripts/run_api.py

# 新终端：启动前端（端口 3000）
cd frontend && npm run dev
```

### 4. 访问

打开 http://localhost:3000

---

## 📸 界面展示

### 登录 & 注册

<div align="center">
  <img src="docs/screenshots/login.png" width="45%" />
  <img src="docs/screenshots/register.png" width="45%" />
</div>

> 登录页面支持邮箱密码认证，注册页面包含用户名、邮箱、密码及确认密码

### 落地页

<div align="center">
  <img src="docs/screenshots/landing.png" width="70%" />
</div>

> Mustify 品牌展示页，突出"智能对话、精准推荐、个性化体验"三大核心价值，一键开始对话

### 对话推荐

<div align="center">
  <img src="docs/screenshots/chat-recommend.png" width="90%" />
</div>

> **主交互界面**：左侧对话区域展示多轮上下文，推荐卡片包含歌曲标题、艺术家、流派标签、匹配度（92%、90%）、可试听徽章、AI 推荐理由；侧边栏展示当前偏好标签与歌单列表

### 用户画像

<div align="center">
  <img src="docs/screenshots/ai_portrait.png" width="70%" />
</div>

> 点击侧边栏「我的画像」触发弹窗，展示流派偏好柱状图（Rock ×5、Pop ×4、Jazz ×1、Experimental ×1）、能量偏好分析、AI 个性化深度解读

### 历史会话

<div align="center">
  <img src="docs/screenshots/history.png" width="90%" />
</div>

> 历史会话列表页，会话卡片展示标题、创建时间（相对时间）、轮次数量、当前偏好标签（心情/场景/风格/能量），支持加载与删除

### 歌单管理

<div align="center">
  <img src="docs/screenshots/playlist.png" width="90%" />
</div>

> 歌单管理页，展示"我喜欢的音乐"等系统歌单及用户自建歌单，显示歌曲数量与创建时间

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

### 偏好反馈

```
你：来点高能量的跑步音乐
助手：已更新你的偏好（能量：高），为你推荐：

🎵 Caffeine Loop - Night Library
   流派：Electronic / 匹配度：93%
   理由：节奏明快、能量充沛，适合运动场景

（点击 ❤️ 喜欢）
系统：记录流派偏好（Electronic +1），更新能量偏好，下次推荐时自动加权融合
```

### 用户画像

```
点击「我的画像」→ 系统分析：
- 喜欢歌曲：Hip-Hop ×3, Jazz ×2, Electronic ×1
- 能量偏好：高（历史评分均值 3.5/5）
- AI 解读：「你偏好律动感强、情绪浓烈的音乐类型...」
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
| DELETE | `/sessions/{id}` | 删除会话 | 必需 |
| POST | `/sessions/{id}/reset` | 重置会话 | 必需 |
| GET | `/playlists` | 歌单列表 | 必需 |
| GET | `/api/ai/portrait` | 获取用户画像 | 必需 |
| DELETE | `/api/ai/portrait` | 清除用户画像 | 必需 |
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
      "title": "Quiet Pages",
      "artist": "Paper Lanterns",
      "reason": "旋律轻柔、节奏缓慢，适合学习场景",
      "is_playable": true,
      "audio_url": "/audio/fma_small/000/000123.mp3",
      "match_score": 91,
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
| 混合权重 | 0.6:0.4 | 语义:内容 默认比例 |
| Like 加分 | +0.03/次 | 上限 +0.15 |
| Dislike 降权 | -0.05/次（≥3次触发） | 下限 -0.20 |

---

## 🧪 测试

```bash
# 后端语法检查
python -m compileall src scripts tests

# Agent 编排测试
python tests/agent_orchestrator_smoke.py

# 工具注册测试
python tests/tool_registry_unit.py

# API 测试
python tests/api_chat_smoke.py

# 前端类型检查
cd frontend && npm run lint
```

---

## 🛠️ 开发规范

### 项目规范

- **Python**: 4 空格缩进，类型提示，snake_case
- **TypeScript**: 2 空格缩进，PascalCase 组件
- **提交**: 使用 `git commit`
- **测试**: 独立 smoke 脚本，非 pytest

### 相关文档

- [AGENTS.md](AGENTS.md) - 开发规范
- [论文写作指南_20260416.md](论文写作指南_20260416.md) - 论文各章节写作参考

---

## ⚠️ 已知限制

- **多 Worker 部署**：当前 SessionStore 为进程内内存 + SQLite 持久化，多 Worker 部署时需引入 Redis 共享状态
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
