# Demo Dialogue Examples — 演示对话样例

> 以下样例覆盖系统支持的各类意图和交互场景，可用于演示、测试或用户引导。

---

## 场景一：初始推荐 — 学习场景

**用户**: 推荐一些适合学习的歌

**系统预期行为**:
- Intent: `recommend_music` 或 `search_music`
- Slots: `scene=学习`, `energy=low`
- Tool: `semantic_search`
- 返回 5 首安静、适合专注的音乐
- 显示匹配度 65%-98%

**用户**: 我想要更轻一些的，纯音乐最好

**系统预期行为**:
- Intent: `refine_preferences`
- Slots: `energy=low`, `vocals=instrumental`
- 状态更新: `preferred_energy=low`, `preferred_vocals=instrumental`
- 返回更轻柔的纯音乐推荐

---

## 场景二：多轮对话 — 心情驱动

**用户**: 我今天心情不太好，能推荐点治愈的歌吗

**系统预期行为**:
- Intent: `recommend_music`
- Slots: `mood=治愈`, `scene` 为空
- 状态更新: `current_mood=治愈`
- 返回温暖治愈风格的音乐

**用户**: 换一批

**系统预期行为**:
- Intent: `refine_preferences`
- 上一批歌曲 ID 加入 `exclude_ids`
- 使用相同查询条件重新推荐，排除已展示的歌曲

---

## 场景三：运动场景 + 能量调节

**用户**: 推荐适合跑步听的歌，要高能量的

**系统预期行为**:
- Intent: `recommend_music`
- Slots: `scene=运动`, `energy=high`
- 返回节奏感强、高能量的音乐

**用户**: 不要太吵的

**系统预期行为**:
- Intent: `refine_preferences`
- Slots: `energy=low`
- 状态更新: `preferred_energy=low`
- 返回节奏适中、不会太吵的运动音乐

---

## 场景四：睡前放松

**用户**: 来点睡前听的安静的钢琴曲

**系统预期行为**:
- Intent: `recommend_music`
- Slots: `scene=睡前`, `mood=放松`, `energy=low`
- 返回轻柔钢琴曲/ambient 音乐

**用户**: 再来 3 首

**系统预期行为**:
- Intent: `recommend_music`
- Slots: `top_k=3`
- 延续当前 mood/scene/energy 偏好

---

## 场景五：反馈机制

**用户**: 推荐一些 Lo-fi 音乐

**系统**: [返回 5 首 Lo-fi 推荐]

**用户**: 不喜欢第一首

**系统预期行为**:
- Intent: `feedback`
- Slots: `feedback={type: "dislike", target_id: <第一首ID>}`
- 该歌曲 ID 加入 `exclude_ids`
- 确认反馈已记录

---

## 场景六：通勤场景

**用户**: 通勤路上听什么好？

**系统预期行为**:
- Intent: `recommend_music`
- Slots: `scene=通勤`
- 返回适合通勤/开车听的音乐

**用户**: 有没有周杰伦风格的？

**系统预期行为**:
- Intent: `search_music`
- Slots: `scene=通勤`, `artist=周杰伦`
- 返回类似周杰伦风格的音乐

---

## 场景七：纯音乐请求

**用户**: 来点纯音乐

**系统预期行为**:
- Intent: `recommend_music`
- Slots: `vocals=instrumental`
- 状态更新: `preferred_vocals=instrumental`
- 返回器乐/纯音乐

**用户**: 我想要爵士风格的

**系统预期行为**:
- Intent: `refine_preferences`
- Slots: `genre=爵士`, `vocals=instrumental`
- 返回爵士风格的纯音乐

---

## 场景八：数量控制

**用户**: 推荐 10 首适合工作的背景音乐

**系统预期行为**:
- Intent: `recommend_music`
- Slots: `scene=工作`, `top_k=10`
- 返回 10 首适合工作背景播放的音乐

---

## 场景九：解释推荐原因

**用户**: 为什么推荐这首歌？

**系统预期行为**:
- Intent: `explain_why`
- 基于最近一次推荐的 citations 和 evidence 生成自然语言解释
- 说明歌曲风格、节奏、与用户偏好的匹配点

---

## 场景十：完整演示流程（推荐）

以下是一个完整的端到端演示流程，约 5-8 轮对话：

```
1. 用户: 推荐一些适合深夜散步时候独自听的安静的音乐
   → 展示语义搜索能力，返回 ambient/钢琴曲

2. 用户: 我想要更欢快一点的
   → 展示 refine 能力，调整 energy 偏好

3. 用户: 换一批
   → 展示 exclude 机制，不重复推荐

4. 用户: 有纯音乐吗
   → 展示 vocals 偏好追踪

5. 用户: 不喜欢第三首
   → 展示反馈机制，记录 dislike

6. 用户: 推荐 3 首适合旅行的
   → 展示 scene 切换 + top_k 控制
```

---

## Mock 模式下的确定性输出

在 `--llm mock` 模式下，以下查询会产生确定性结果（基于 SHA1 seed）：

| 用户输入 | 生成歌曲种子 | 说明 |
|---------|------------|------|
| "适合深夜独自听的安静的钢琴曲" | SHA1(query)[:10] | 每次相同输入产生相同结果 |
| "适合运动健身的节奏感强的摇滚音乐" | SHA1(query)[:10] | 同上 |
| "浪漫的法语香颂" | SHA1(query)[:10] | 同上 |

Mock 目录包含 7 首循环歌曲:
1. Focus Drift — Studio Waves (Ambient)
2. Quiet Pages — Paper Lanterns (Lo-fi)
3. Caffeine Loop — Night Library (Electronic)
4. Soft Rain Notes — Window Seat (Instrumental)
5. Deep Work — Mono Tone (Minimal)
6. Zero Distraction — No Vocals (Ambient)
7. Warm Lamp — Evening Desk (Lo-fi)

---

## CLI 快速验证命令

```bash
# 单次查询验证
python scripts/chat_cli.py --llm mock --once "推荐适合学习的歌"

# 交互式多轮对话
python scripts/chat_cli.py --llm mock

# 查看会话状态（交互模式下输入 context）
> context
```
