# 小红书 AI 自动化代理 — 项目阶段性规划

## 项目概述

本项目是一个面向**小红书网页端**的 AI 自动化代理原型。核心流程如下：

1. **Python 自动化模块**：使用 DrissionPage 模拟浏览器行为，每日自动刷小红书"发现页"，利用 DeepSeek LLM 分析笔记内容，判断是否与用户兴趣匹配，并自动执行互动（点赞、收藏）。
2. **数据持久化**：每日将点赞/收藏的笔记内容经过 AI 总结后，写入 SQLite 数据库，同时同步写入 Chroma 向量数据库。
3. **Node.js API 服务**：读取 SQLite 数据库，向前端提供笔记展示 API；代理转发用户对话请求到 Python 侧的 Chroma + DeepSeek RAG 服务。
4. **React 前端**：单页面展示收藏笔记列表，并提供对话问答面板，支持流式输出。

---

## 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 浏览器自动化 | Python + DrissionPage | 强大的反检测自动化库，支持拟人化行为 |
| LLM | DeepSeek API | 调用 OpenAI 兼容 SDK |
| 自动化调度 | Python `schedule` 库 | 代码内定时器，每天早上 9:00 触发 |
| 后端 API | Node.js + TypeScript + Express | 提供 REST API 服务 |
| 关系数据库 | SQLite | 存储笔记摘要数据 |
| 向量数据库 | Chroma (Python 原生库) | 存储笔记向量，支持 RAG 问答 |
| 前端 | React + TypeScript + Vite | 单页面展示 + 对话面板 |
| 进程通信 | Python 自动化 → 直写 SQLite / Chroma；Node.js → 子进程调用 Python 问答服务 | 共享数据 + 代理转发 |

---

## 项目目录结构

```
self-study-agent/
│
├── automation/                  # Python 自动化模块（浏览器操作 + 分析 + 调度）
│   ├── main.py                  # 入口文件：定时器调度 + 完整流程编排
│   ├── config.py                # 配置管理：API Key、路径、参数等
│   ├── browser.py               # DrissionPage 浏览器封装：拟人化行为、登录检测、页面采集、互动操作
│   ├── analyzer.py              # DeepSeek 分析封装：画像生成、兴趣判断、行为决策
│   ├── summarizer.py            # 笔记总结：生成结构化摘要
│   ├── chroma_store.py          # Chroma 向量库：写入笔记内容 + RAG 问答检索
│   ├── chroma_server.py         # Flask/FastAPI HTTP 服务：暴露 /query 接口供 Node.js 调用
│   └── requirements.txt         # Python 依赖清单
│
├── backend/                     # Node.js/TypeScript 后端 API 模块
│   ├── src/
│   │   ├── index.ts             # Express 服务入口
│   │   ├── routes/
│   │   │   ├── notes.ts         # 笔记数据 API（GET /api/notes, GET /api/notes/:id）
│   │   │   └── chat.ts          # 对话问答 API（POST /api/chat，SSE 流式输出）
│   │   ├── db/
│   │   │   └── sqlite.ts        # SQLite 数据库查询封装
│   │   └── chroma-proxy.ts      # 转发用户问题到 Python chroma_server 并流式返回
│   ├── package.json
│   └── tsconfig.json
│
├── frontend/                    # React 前端模块
│   ├── src/
│   │   ├── App.tsx              # 主布局：左右分栏
│   │   ├── App.css
│   │   ├── components/
│   │   │   ├── NoteList.tsx     # 左侧：收藏笔记列表（Markdown 渲染）
│   │   │   └── ChatPanel.tsx    # 右侧：对话问答面板
│   │   └── ...
│   └── package.json
│
├── data/                        # 共享数据目录（供 Python 和 Node.js 共同读写）
│   ├── xiaohongshu.db           # SQLite 数据库文件
│   └── chroma/                  # Chroma 向量库持久化目录
│
├── .env                         # 环境变量（DeepSeek API Key 等）
├── .gitignore
└── README.md                    # 本规划文档
```

---

## 数据流架构

```
┌──────────────────────────────────────────────────────────┐
│  Python 自动化模块 (每日 9:00 自动运行)                     │
│                                                            │
│  打开浏览器 → 等待登录 → 刷50篇生成画像                       │
│         ↓                                                  │
│  继续刷发现页 → AI判断兴趣 → 点详情 → AI决定互动               │
│         ↓                                                  │
│  AI总结笔记 → 写入 SQLite → 写入 Chroma                      │
└──────────────┬───────────────────────┬───────────────────┘
               │ 直写                   │ 直写
               ▼                        ▼
┌──────────────────────┐    ┌──────────────────────┐
│     SQLite 数据库     │    │    Chroma 向量数据库    │
│   (笔记摘要存储)       │    │   (笔记向量 + 文档原文)  │
└──────────┬───────────┘    └──────────┬───────────┘
           │ 读取                       │ 检索
           ▼                            ▼
┌──────────────────────────────────────────────────────────┐
│  Node.js/TypeScript API 服务                              │
│                                                            │
│  GET /api/notes     → 从 SQLite 查询笔记列表                 │
│  GET /api/notes/:id → 从 SQLite 查询单篇笔记详情              │
│  POST /api/chat     → 代理转发到 Python chroma_server       │
│                     → SSE 流式返回给前端                     │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTP
                       ▼
┌──────────────────────────────────────────────────────────┐
│  React 前端                                               │
│                                                            │
│  左侧面板：笔记列表（Markdown渲染）                          │
│  右侧面板：对话问答（流式输出）                              │
└──────────────────────────────────────────────────────────┘
```

---

## 拟人化行为设计方案

> 此设计为自动化浏览的核心安全策略，贯穿阶段二和阶段三的实现。目的是让浏览行为尽可能接近真实人类，降低被平台反爬/风控系统检测的风险。

### 一、滚动行为

- **非匀速滚动**：每次滚动的像素距离在一定范围内随机（如 300px ~ 800px），避免机械化的等距滚动。
- **随机间隔**：两次滚动之间的等待间隔随机在 2 ~ 6 秒，模拟真实用户的阅读节奏。
- **微抖动**：滚动目标距离加入 ±50px 的随机偏移，使滚动终点不完全一致。
- **偶尔回滚**：有 10% 的概率在向下滚动后向上回滚一小段（模拟"刚才没看清再回头看"的行为）。
- **滚动后短暂停顿**：每次滚动后停留 1 ~ 2 秒再开始提取内容，模拟眼睛扫视的延迟。

### 二、鼠标行为

- **贝塞尔曲线轨迹**：鼠标移动沿三次贝塞尔曲线执行，而非直线移动，模拟真实手腕轨迹。
- **随机移速**：鼠标移动速度在一定范围内随机，同一段轨迹中也会出现自然的加速/减速变化。
- **非关键区域悬停**：有概率在非点击元素上停留片刻（模拟无意识的鼠标游移），然后继续移动。
- **点击前微调**：在执行点击前，鼠标先在目标附近做微小调整（±3px），模拟真实点击的精度误差。

### 三、帖子停留时间

- **前50篇画像采集阶段**：每篇帖子停留 3 ~ 8 秒（随机），不进行任何互动，仅提取标题和封面信息。
- **兴趣判断阶段**：扫描帖子标题/封面时停留 4 ~ 10 秒；如果判断为感兴趣并点进详情，停留 12 ~ 25 秒（模拟阅读正文的时间）。
- **停留时间的自然波动**：即便是同一类型的操作，停留时间也遵循正态分布随机，避免出现固定的模式。

### 四、间歇休息策略

- **浏览批次**：每连续浏览 8 ~ 12 篇帖子后，进入休息期。
- **休息时长**：休息 30 ~ 90 秒（随机），期间浏览器不做任何操作。
- **长时间休息**：如果任务途中累计浏览超过 50 篇帖子，插入一次 3 ~ 5 分钟的较长休息，模拟去干别的事情。

### 五、互动行为概率化

- **点赞概率**：即使 AI 判断为"感兴趣"，也只有 80% 的概率会实际执行点赞。20% 的情况模拟"感兴趣但忘记点赞"的真实场景。
- **收藏概率**：兴趣评分达到 8/10 以上的高兴趣笔记，只有 60% 的概率同时执行收藏（兴趣评分够了才收藏，但也不是每次都收藏）。
- **互动间隔**：两次点赞/收藏操作之间的时间间隔在 3 ~ 15 秒之间随机，不会连续快速点赞。
- **详情页行为**：进入详情页后，先滚动浏览完整内容，再决定是否点赞。不会在打开详情页后立即点击点赞按钮。

### 六、每日安全上限

- **每日点赞上限**：最多 15 篇。
- **每日收藏上限**：最多 5 篇（收藏必须少于或等于点赞数）。
- **每日浏览总时长**：控制在 30 ~ 60 分钟。
- **点击/收藏后行为**：互动完成后至少再浏览 2 篇其他帖子，才会进行下一次互动。

### 七、时序模式

- **启动时间**：每天早上 9:00 自动触发。
- **渐进浏览**：启动后先慢速浏览 5 ~ 10 分钟（滚动间隔较长），然后逐渐提高浏览节奏，模拟从"刚睡醒刷手机"到"进入状态"的过渡。
- **任务收尾**：最后几分钟浏览节奏放慢，模拟开始分心。

---

## 阶段一：项目初始化与环境搭建

### 目标

搭建完整的项目骨架，配置好三个技术栈（Python、Node.js、React）的开发环境，创建共享数据库。

### 任务详情

**1.1 创建项目目录结构**

按照上述"项目目录结构"创建所有文件夹。确保 `data/` 目录位于项目根目录，Python 和 Node.js 都能访问到。

**1.2 初始化 Python 环境**

- 在 `automation/` 目录下创建 Python 虚拟环境（venv）。
- 安装核心依赖：
  - `DrissionPage`：浏览器自动化。
  - `openai`：DeepSeek API 的 SDK（兼容 OpenAI SDK 调用方式）。
  - `chromadb`：Chroma 向量数据库。
  - `schedule`：Python 定时任务调度。
  - `flask` 或 `fastapi`：为 chroma_server.py 提供 HTTP 接口。
- 生成 `requirements.txt` 锁定依赖版本。

**1.3 初始化 Node.js 后端**

- 在 `backend/` 目录下执行 `npm init` 初始化项目。
- 安装依赖：
  - `express`：HTTP 服务框架。
  - `better-sqlite3`：SQLite 操作库（比 sqlite3 更高效）。
  - `cors`：处理跨域请求。
  - `typescript`、`ts-node`、`@types/express`、`@types/better-sqlite3`：TypeScript 支持。
- 配置 `tsconfig.json`，设置输出目录和模块解析规则。

**1.4 初始化 React 前端**

- 使用 Vite 创建 React + TypeScript 项目：
  ```
  npm create vite@latest frontend -- --template react-ts
  ```
- 安装额外依赖：
  - `axios`：HTTP 请求。
  - `react-markdown`：Markdown 渲染组件。
  - `remark-gfm`：GitHub Flavored Markdown 支持（表格、任务列表等）。

**1.5 配置环境变量**

- 在项目根目录创建 `.env` 文件，内容包括：
  - `DEEPSEEK_API_KEY=你的DeepSeek API Key`
  - `DEEPSEEK_BASE_URL=https://api.deepseek.com`
  - `SQLITE_PATH=./data/xiaohongshu.db`
  - `CHROMA_PATH=./data/chroma`
  - `NODE_PORT=3001`
  - `PYTHON_CHROMA_PORT=5001`

**1.6 创建 SQLite 数据库表结构**

在 Python 的 `automation/` 模块中创建建表脚本（也可作为初始化脚本单独放在 `data/` 下），表结构如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY | 自增主键 |
| title | TEXT | 笔记标题 |
| url | TEXT | 笔记链接 |
| cover_url | TEXT | 封面图 URL |
| action_type | TEXT | 互动类型：like / bookmark |
| interest_score | INTEGER | 兴趣评分 1-10 |
| ai_summary | TEXT | AI 生成的笔记摘要（Markdown 格式） |
| original_content | TEXT | 笔记原始文字内容 |
| tags | TEXT | AI 提取的标签（逗号分隔） |
| created_at | TEXT | 爬取日期（YYYY-MM-DD） |

---

## 阶段二：Python 自动化核心 — 浏览器操作与用户画像生成

### 目标

实现 DrissionPage 控制浏览器完成前 50 篇帖子的拟人化浏览，并调用 DeepSeek 生成用户画像。此阶段不涉及点赞收藏等互动操作。

### 任务详情

**2.1 实现拟人化浏览器封装（`browser.py`）**

将所有拟人化行为封装为可复用的方法：

- `human_scroll(page)`：执行一次拟人化滚动（随机距离 + 随机延迟 + 概率回滚）。
- `human_mouse_move(page, target_x, target_y)`：贝塞尔曲线移动鼠标到目标坐标。
- `human_click(page, selector)`：拟人化点击（先移动 + 微调 + 点击）。
- `human_pause(min_sec, max_sec)`：随机时长暂停。
- `take_break(min_sec, max_sec)`：长时间休息。
- `batch_rest()`：浏览批次间的休息（每 8~12 篇后触发）。

**2.2 实现登录检测与等待（`browser.py`）**

- `wait_for_login(page)`：打开小红书发现页 URL，检测页面是否出现登录弹窗或跳转到了登录页。
  - 如果检测到未登录，在控制台打印提示："请在浏览器中完成登录..."
  - 循环检测（每 3 秒检查一次），直到确认登录成功（页面正常显示发现页内容）。
  - 登录成功后打印确认信息，流程继续。

**2.3 实现发现页帖子列表采集（`browser.py`）**

- `collect_feed_items(page, count=50)`：在发现页滚动浏览，采集帖子的标题文本和封面图片 URL。
  - 每滚动一次，提取当前视口内新出现的帖子卡片信息。
  - 使用拟人化滚动方法，不做机械化匀速滚动。
  - 处理懒加载：帖子的封面图可能是在可见时才加载。
  - 采集够 50 篇后停止，返回列表 `[{title, cover_url}, ...]`。

**2.4 实现 DeepSeek API 调用封装（`analyzer.py`）**

- `call_deepseek(messages, response_format=None)`：封装通用调用方法。
  - 读取 `.env` 中的 `DEEPSEEK_API_KEY` 和 `DEEPSEEK_BASE_URL`。
  - 使用 OpenAI 兼容 SDK 调用。
  - 支持 `response_format={"type": "json_object"}` 获取结构化 JSON 返回。
  - 加入重试机制（失败重试最多 3 次，间隔递增）。

**2.5 实现用户画像生成（`analyzer.py`）**

- `generate_profile(feed_items)`：接收前 50 篇帖子列表（标题 + 封面 URL），发给 DeepSeek 生成用户画像。
  - Prompt 设计要点：
    - 让模型根据 50 篇帖子的标题判断用户的兴趣偏好类型（如穿搭、美食、科技数码、旅行、美妆等）。
    - 输出结构化 JSON，包含：
      - `preferred_categories`：兴趣类型列表，按偏好程度排序。
      - `keywords`：高频关键词列表。
      - `style_preference`：风格偏好描述（如"简约风"、"实用型"等）。
      - `confidence`：基于 50 篇样本的信心度。
  - 将画像保存为 JSON 文件到 `data/user_profile.json`，供后续阶段复用。

**2.6 测试阶段二**

- 编写测试入口，完整运行：打开浏览器 → 等待登录 → 采集 50 篇帖子 → 生成画像。
- 验证画像 JSON 输出是否合理（类别是否准确、关键词是否有代表性）。
- 确认拟人化行为肉眼看起来是否自然。

---

## 阶段三：Python 自动化核心 — 兴趣判断与互动操作

### 目标

在已有用户画像的基础上，继续刷发现页，通过 LLM 对每篇帖子进行兴趣判断，并对匹配的帖子执行点赞/收藏操作。

### 任务详情

**3.1 实现帖子兴趣初判（`analyzer.py`）**

- `judge_interest(profile, title, cover_description)`：输入用户画像 + 当前帖子的标题和封面描述，让 DeepSeek 判断是否感兴趣。
  - 封面图本身无法直接发给 LLM。有两种处理方式：
    - 方式一（推荐）：仅用标题文字进行判断，封面图作为辅助参考不参与判断。标题信息在小红书已足够表达内容主题。
    - 方式二（可选）：如果后续需要，可将封面图下载后用多模态模型分析，但会增加复杂度和 token 消耗。
  - 返回结构：`{is_interested: bool, interest_score: 1-10, reason: string}`。

**3.2 实现帖子详情提取（`browser.py`）**

- `extract_note_detail(page)`：在发现页点击进入某篇帖子后，提取详情页内容。
  - 提取帖子全部文字内容（包括正文、标签话题）。
  - 提取所有配图 URL（有的帖子有多张图）。
  - 提取笔记链接 URL。
  - 记录作者名称（可选）。
  - 提取完成后，关闭详情页返回发现页，继续浏览。

**3.3 实现详情二次判断（`analyzer.py`）**

- `judge_action(profile, note_detail)`：将帖子详情内容发给 DeepSeek，做二次确认。
  - 第一次初判（仅标题）可能存在误判，详情二次判断更准确。
  - 输出：`{action: "none" | "like" | "bookmark", reason: string}`。
  - "none"：不互动，跳过。
  - "like"：点赞。
  - "bookmark"：兴趣非常高，点赞 + 收藏。

**3.4 实现点赞/收藏操作（`browser.py`）**

- `do_like(page)`：在详情页中找到点赞按钮并执行拟人化点击。
- `do_bookmark(page)`：在详情页中找到收藏按钮并执行拟人化点击。
  - 操作前加入随机延迟（3~10 秒）。
  - 操作后加入随机冷却期（至少浏览 2 篇其他帖子后再进行下一次互动）。
  - 应用概率化策略：即使 AI 判断为"like"，也仅 80% 概率执行；"bookmark"仅 60% 概率执行。

**3.5 实现每日任务编排（`main.py`）**

- `run_daily_task()`：编排完整流程。
  1. 打开浏览器，等待登录。
  2. 检查 `data/user_profile.json` 是否存在。
     - 如果存在，直接加载已有画像。
     - 如果不存在，执行前 50 篇采集 + 画像生成。
  3. 加载画像后，进入"长期浏览 + 判断 + 互动"循环：
     - 滚动发现页 → 采集新帖子 → 初判兴趣 → 如果感兴趣则进详情 → 二次判断 → 执行互动 → 收集互动笔记数据 → 继续。
     - 达到每日上限（15 赞 / 5 收藏）或浏览时间超限（60 分钟）后退出。
  4. 返回当天所有互动笔记的原始数据列表。

---

## 阶段四：Python — 总结归纳与数据入库

### 目标

将当天互动过的笔记内容发给 DeepSeek 进行总结，然后将总结结果分别写入 SQLite 和 Chroma，并实现 Chroma 的问答检索功能。

### 任务详情

**4.1 实现笔记总结（`summarizer.py`）**

- `summarize_note(note_detail)`：调用 DeepSeek 对单篇笔记生成结构化摘要。
  - 输出 Markdown 格式的摘要，包含：
    - 笔记核心观点（1-2 句）。
    - 关键信息点（列表）。
    - 为什么用户可能感兴趣（结合用户画像）。
  - 同时提取标签（tags），如"穿搭"、"春季"、"通勤"等。

**4.2 实现 SQLite 写入**

- 在完成每日任务后，遍历当天所有互动笔记：
  1. 对每篇笔记调用 `summarize_note()` 生成摘要。
  2. 将笔记数据写入 SQLite 的 `notes` 表。
- 写入数据包括：标题、URL、封面URL、互动类型、兴趣评分、AI 摘要、原始内容、标签、日期。

**4.3 实现 Chroma 向量库写入（`chroma_store.py`）**

- `init_chroma()`：初始化 Chroma 客户端，指定持久化目录为 `data/chroma/`。
- `add_notes_to_chroma(notes)`：将每篇笔记的摘要内容写入 Chroma。
  - 使用 Chroma 内置的 embedding 函数（默认 all-MiniLM-L6-v2）。
  - 将标题作为 `document`，摘要作为 `metadata` 的一部分。
  - 每条记录的 ID 使用 SQLite 中的笔记 ID，便于关联。

**4.4 实现 Chroma 问答检索（`chroma_store.py`）**

- `query_and_answer(user_question)`：接收用户问题，执行 RAG 流程：
  1. 在 Chroma 中检索与问题最相关的前 5 条笔记片段。
  2. 将检索到的笔记摘要作为上下文，拼接 prompt 发给 DeepSeek。
  3. DeepSeek 基于上下文生成回答并返回。
  4. 支持流式输出（streaming），逐 token 返回。

**4.5 测试阶段四**

- 完整运行一次端到端流程（从打开浏览器到数据入库）。
- 确认 SQLite 中已有数据记录。
- 调用 `query_and_answer()` 提问（如"最近收藏了哪些关于穿搭的笔记？"），验证 RAG 能否正确检索和回答。

---

## 阶段五：Python — 定时任务

### 目标

使自动化流程每天早上 9:00 自动触发，Python 进程持续在后台运行。

### 任务详情

**5.1 实现定时调度（`main.py`）**

- 使用 `schedule` 库设置每天早上 9:00 执行 `run_daily_task()`。
- 添加日志输出：每次任务开始/结束时打印时间戳和任务摘要。
- 任务异常时打印错误日志但不中断调度器（第二天继续正常执行）。

```python
schedule.every().day.at("09:00").do(run_daily_task)

while True:
    schedule.run_pending()
    time.sleep(60)  # 每分钟检查一次
```

**5.2 运行守护进程**

- 确保 Python 进程持续运行，循环等待定时触发。
- 建议使用 `tmux` 或 `screen` 在终端中保持进程运行，或使用 `nohup` 后台启动。
- 日志输出到文件 `data/automation.log`，便于排查问题。

---

## 阶段六：Node.js 后端开发

### 目标

搭建 Node.js/TypeScript Express 服务，提供笔记展示 API 和对话问答代理 API。

### 任务详情

**6.1 实现 SQLite 数据查询（`db/sqlite.ts`）**

- 封装 `better-sqlite3` 连接，指向 `data/xiaohongshu.db`。
- 实现以下查询方法：
  - `getNotes(page, pageSize)`：分页查询笔记列表，按日期倒序。
  - `getNoteById(id)`：查询单篇笔记详情。
  - `getNotesByDate(date)`：按日期筛选笔记。
  - `getNotesByTag(tag)`：按标签筛选笔记。

**6.2 实现笔记 API（`routes/notes.ts`）**

- `GET /api/notes?page=1&pageSize=20`：返回分页笔记列表，每条包含标题、摘要前 100 字、日期、标签。
- `GET /api/notes/:id`：返回单篇笔记完整内容（含 Markdown 摘要全文）。

**6.3 实现 Chroma 问答代理（`routes/chat.ts`）**

- `POST /api/chat`：接收 `{question: string}`。
- Node.js 不直连 Chroma（因为 Chroma 是 Python 原生库），而是通过子进程调用 Python 脚本或 HTTP 请求到 Python 的 chroma_server。
- 方案：在 Python 侧启动一个 Flask/FastAPI 小服务（`chroma_server.py`），监听 `POST /query`，调用 `query_and_answer()` 并流式返回。Node.js 通过 `http.request` 转发请求。
- 将 Python chroma_server 的响应以 SSE 格式流式输出给前端。

**6.4 实现 SSE 流式输出（`routes/chat.ts`）**

- 设置响应头 `Content-Type: text/event-stream`。
- 逐 token 向客户端推送 `data: {token}\n\n`。
- 回答结束时发送 `data: [DONE]\n\n`。

**6.5 实现 Python Chroma HTTP 服务（`chroma_server.py`）**

- 使用 Flask 或 FastAPI 启动 HTTP 服务（端口 5001）。
- 提供 `POST /query` 接口，接收 `{question: string}`。
- 调用 `chroma_store.query_and_answer()` 执行 RAG 检索 + LLM 回答。
- 流式返回回答内容（SSE 或 chunked transfer）。

---

## 阶段七：React 前端开发

### 目标

构建单页面 React 应用，展示收藏笔记列表并提供对话问答功能。

### 任务详情

**7.1 实现收藏笔记列表展示（`NoteList.tsx`）**

- 调用 `GET /api/notes` 获取笔记列表。
- 以卡片形式渲染每条笔记，显示：标题、摘要前 100 字、日期、标签、互动类型图标（❤️点赞 / ⭐收藏）。
- 点击卡片可展开查看完整 Markdown 摘要内容（使用 `react-markdown` 渲染）。
- 支持按日期筛选和分页加载。

**7.2 实现对话问答面板（`ChatPanel.tsx`）**

- 聊天界面布局：顶部标题栏、中间消息列表区域、底部输入框 + 发送按钮。
- 用户发送问题后，调用 `POST /api/chat`，通过 EventSource 或 fetch + ReadableStream 接收 SSE 流式数据。
- 流式渲染 AI 回答内容，逐字显示，模拟打字效果。
- 支持 Markdown 格式渲染 AI 回答（回答中可能包含格式化的内容）。
- 消息列表支持滚动到最新消息。

**7.3 页面布局整合（`App.tsx`）**

- 整体布局为左右分栏：
  - 左侧（60% 宽度）：笔记列表，可滚动浏览。
  - 右侧（40% 宽度）：对话面板。
- 响应式设计：小屏幕时上下堆叠（笔记列表在上，对话面板在下）。
- 顶部导航栏：项目名称 + 简洁导航。

**7.4 样式设计**

- 参考小红书配色风格：主色调红色/粉色系，简洁白色背景。
- 卡片设计：圆角、阴影、留白恰当。
- 对话气泡：用户消息靠右（蓝色），AI 消息靠左（灰色）。
- 整体风格现代、清爽。

---

## 阶段八：联调测试

### 目标

整合所有模块，端到端测试全流程，修复问题。

### 任务详情

**8.1 端到端集成测试**

启动顺序：
1. 启动 Python 自动化进程（后台运行，等待定时触发）。
2. 启动 Python chroma_server（端口 5001）。
3. 启动 Node.js 后端（端口 3001）。
4. 启动 React 前端（端口 5173）。

测试流程：
- 访问前端页面，确认笔记列表正常加载。
- 在对话面板提问，确认流式回答正常返回。
- 手动触发一次 Python 自动化任务，确认数据能正确入库并更新前端显示。

**8.2 拟人化行为验证**

- 人工观察一次完整的自动化浏览过程。
- 检查以下几点：
  - 滚动是否自然（非匀速、有停顿）。
  - 鼠标轨迹是否平滑。
  - 浏览和休息节奏是否合理。
  - 点赞/收藏的时机和间隔是否正常。
- 根据观察结果微调参数。

**8.3 Bug 修复与优化**

- 记录测试中发现的问题。
- 逐一修复，确保以下关键路径正常：
  - 首次运行（无画像）→ 生成画像 → 正常浏览互动。
  - 非首次运行（已有画像）→ 跳过画像生成 → 直接进入互动。
  - 网络异常 → API 调用重试 → 不中断流程。
  - 当天无感兴趣帖子 → 空数据入库 → 前端正常显示空状态。

---

## 附录：各模块关键依赖清单

### Python (`automation/requirements.txt`)

```
DrissionPage>=4.0
openai>=1.0
chromadb>=0.4
schedule>=1.2
flask>=3.0
python-dotenv>=1.0
```

### Node.js (`backend/package.json`)

```json
{
  "dependencies": {
    "express": "^4.18",
    "better-sqlite3": "^11.0",
    "cors": "^2.8",
    "dotenv": "^16.3"
  },
  "devDependencies": {
    "typescript": "^5.3",
    "ts-node": "^10.9",
    "@types/express": "^4.17",
    "@types/better-sqlite3": "^7.6",
    "@types/cors": "^2.8"
  }
}
```

### React (`frontend/package.json` 额外依赖)

```json
{
  "dependencies": {
    "axios": "^1.6",
    "react-markdown": "^9.0",
    "remark-gfm": "^4.0"
  }
}
```

---

> **文档版本**：v1.0
> **最后更新**：2026-05-17