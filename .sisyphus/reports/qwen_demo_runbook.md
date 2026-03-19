# 真实模式答辩演示运行手册 (Real Mode Defense Demo Runbook)

本手册用于指导在“真实模式”（Qwen LLM + Chroma 向量库 + ALS 协同过滤）下进行答辩演示。

> **⚠️ 重要提示：请务必提前 10 分钟开始准备。**
> 首次启动涉及模型加载（BGE-M3）和向量库索引打开，冷启动耗时可能在 2-5 分钟。预热后的响应时间通常在 30s-100s 之间。

## 1. 演示前置检查 (Preflight Checklist)

在开始演示前，请确保以下条件已满足：

### 1.1 环境变量与 API Key
必须配置 DashScope API Key，否则后端将无法调用 Qwen 模型。
- **检查命令**：
  ```powershell
  $env:DASHSCOPE_API_KEY_BAILIAN -ne $null -or $env:DASHSCOPE_API_KEY -ne $null
  ```
- **设置命令**（如果缺失）：
  ```powershell
  $env:DASHSCOPE_API_KEY="您的Key"
  ```

### 1.2 核心产物 (Artifacts)
确保以下文件/目录存在。
- **检查命令**：
  ```powershell
  Test-Path "index/chroma_bge_m3/", "data/models/implicit_model.pkl", "data/models/cf_mappings.pkl", "dataset/processed/metadata.json"
  ```
- **清单**：
  - `index/chroma_bge_m3/` (向量数据库索引)
  - `data/models/implicit_model.pkl` (协同过滤模型)
  - `data/models/cf_mappings.pkl` (ID 映射)
  - `dataset/processed/metadata.json` (元数据映射)

### 1.3 端口占用
确保以下端口未被占用。
- **检查命令**：
  ```powershell
  Get-NetTCPConnection -LocalPort 8000, 5173 -ErrorAction SilentlyContinue
  ```
- **端口说明**：
  - `8000`: 后端 API 端口
  - `5173`: 前端 Vite 端口

---

## 2. 启动流程 (Startup Flow)

### 2.1 启动后端 (Qwen 模式)

**路径 A：一键脚本（推荐）**
```powershell
.\scripts\run_demo_qwen.ps1
```
*该脚本会自动检查环境、启动后端与前端、并执行预热。*

**路径 B：手动启动**
1. 打开一个新的 PowerShell 窗口，执行：
   ```powershell
   $env:MUSIC_AGENT_LLM_MODE="qwen"
   python scripts/run_api.py
   ```
2. 启动前端：
   ```powershell
   cd frontend
   npm run dev -- --host 127.0.0.1 --port 5173
   ```

### 2.2 系统预热 (Warmup)
为了避免演示时出现长时间等待，请执行以下预热步骤：
1. **确认状态**：访问 `http://127.0.0.1:8000/health`，确认返回 `{"status":"ok","llm_mode":"qwen"}`。
2. **预热消息 1（短消息）**：发送“你好”，观察后端日志是否出现 `[LLM SUCCESS]`。
3. **预热消息 2（真实场景）**：发送“推荐一些适合工作的轻音乐”，触发向量库检索。
   - **观察日志**：确认出现 `MusicSearcher 初始化完成` 和 `向量库文档数: 106573`。

---

## 3. 演示脚本 (Demo Script)

### 场景 1：语义搜索 (Left Brain)
- **输入**：`我想听适合学习的轻音乐`
- **观察点**：
    - 后端日志显示 `[LLM SUCCESS]`。
    - 推荐结果包含真实的歌曲名（如 `Learning Music - Short Tempered`）。
    - 展开详情可见 `citations` 中包含 `semantic_search.similarity`。

### 场景 2：情感与场景感知
- **输入**：`我现在有点emo，想听安静一点的歌`
- **观察点**：
    - 系统识别出 `mood: emo`（可在前端状态栏或 API 返回的 `state` 中确认）。
    - 推荐结果转向低能量、安静的曲风。

### 场景 3：高能量场景切换
- **输入**：`来点适合夜跑的高能量音乐`
- **观察点**：
    - 系统识别出 `scene: 夜跑`，`preferred_energy: high`。
    - 推荐结果应包含节奏感强的音乐。

### 场景 4：反馈循环 (Feedback Loop)
- **UI 操作**：
    1. 点击某首歌旁边的“不喜欢”按钮（或输入 `不喜欢 id: <ID>`）。
    2. 点击“换一批”按钮（或输入 `换一批`）。
- **观察点**：
    - 系统将该 ID 加入排除列表。
    - “换一批”后的结果不包含该 ID。
- **API 验证**：`POST /chat` 返回的 `state.excluded_ids` 应包含该 ID。

---

## 4. 真实性确认 (Verification)

- **确认非 Mock 模式**：访问 `/health` 确认 `llm_mode` 为 `qwen`。
- **确认真实元数据**：推荐结果的 ID 应为数字（FMA ID）或长字符串（Last.fm ID），而非 `mock_` 开头。
- **确认引用**：推荐理由中应包含具体的相似度数值，如 `citations: ["tool_results.semantic_search.similarity=0.30..."]`。

---

## 5. 故障排除与备选方案 (Fallback Plan)

### 5.1 Qwen 响应慢或超时
- **现象**：前端显示加载中超过 2 分钟。
- **对策**：
    1. **重试一次**：可能是网络波动，再次发送请求。
    2. **重启后端**：如果持续超时，关闭后端窗口并重新运行 `.\scripts\run_demo_qwen.ps1`。
    3. **答辩话术**：解释系统正在进行深度语义分析和多路召回（BGE-M3 向量检索 + ALS 协同过滤），且当前运行在 CPU 环境下，真实生产环境会使用 GPU 加速。

### 5.2 API 彻底失效（紧急备选）
如果网络或 API 彻底失效，请立即切换回 Mock 模式：
1. 停止当前后端。
2. 执行：
   ```powershell
   $env:MUSIC_AGENT_LLM_MODE="mock"
   python scripts/run_api.py
   ```
3. **答辩说明**：诚实说明由于网络环境限制，切换至本地离线模拟模式演示交互逻辑。

---

