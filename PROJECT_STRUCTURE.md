# AI 笔记助手 — 项目结构说明

## 📂 顶层文件

| 文件 | 作用 |
|------|------|
| `.env` | 全局环境变量（DeepSeek API Key、端口号等） |
| `.gitignore` | Git 忽略规则 |
| `README.md` | 项目阶段任务说明 |
| `automation/` | 🐍 Python 自动化模块（被测系统核心） |
| `backend/` | 🟢 Node.js 后端（API 服务） |
| `frontend/` | ⚛️ React 前端（用户界面） |
| `data/` | 💾 数据存储目录（SQLite + ChromaDB） |

---

## 🐍 `automation/` — Python 自动化核心

这是整个项目的**大脑**，负责模拟人类浏览小红书、调用 LLM 分析内容、执行互动操作。

| 文件 | 作用 |
|------|------|
| `config.py` | 📋 **总配置中心**：DeepSeek API Key、SQLite/Chroma 路径、每日点赞/收藏上限（15/5）、最大浏览时间（60分钟）、画像采集篇数（50） |
| `main.py` | 🎯 **主控程序**：`DailyTask` 类编排完整每日任务流程（登录→画像→浏览→互动→总结→入库），提供 `--daily` / `--schedule` / `--profile` 三种运行模式 |
| `browser.py` | 🌐 **浏览器自动化**：基于 DrissionPage 实现拟人化滚动（贝塞尔曲线鼠标移动、随机停顿、分批休息）、笔记提取、点击详情、点赞/收藏操作 |
| `analyzer.py` | 🧠 **LLM 分析引擎**：封装 DeepSeek API，提供 `generate_profile()`（生成用户画像）、`judge_interest()`（判断笔记兴趣）、`judge_action()`（决定是否互动） |
| `summarizer.py` | 📝 **笔记总结**：调用 DeepSeek 对互动笔记生成结构化摘要（核心观点 + 关键要点 + 标签），输出 Markdown 格式 |
| `chroma_store.py` | 🧬 **向量库操作**：ChromaDB 写入（笔记→embedding）、语义检索、RAG 流式问答（`query_and_answer_stream`） |
| `chroma_server.py` | 🌍 **Chroma HTTP 服务**：Flask 监听 `127.0.0.1:5002`，提供 `POST /query` SSE 流式接口，供 Node.js 后端代理 |
| `init_db.py` | 🛠️ **数据库初始化**：一键创建 SQLite `notes` 表和 ChromaDB 集合 |
| `requirements.txt` | Python 依赖清单 |

### 三种运行模式

| 命令 | 用途 | 进程行为 |
|------|------|---------|
| `python main.py --profile` | 一次性生成用户画像 | 运行完退出 |
| `python main.py --daily` | 手动运行一次完整每日任务 | 运行完退出 |
| `python main.py --schedule` | 守护进程：每天 9:00 自动执行 | 持续运行 |

---

## 🟢 `backend/` — Node.js 后端

提供 REST API，是前端的**数据引擎**。

```
backend/
├── src/
│   ├── index.ts              # 🚀 Express 入口（端口 3001），挂载路由，CORS
│   ├── db/
│   │   └── sqlite.ts         # 🗄️  SQLite 数据层：建表、分页查询、按 ID/日期/标签查询
│   └── routes/
│       ├── notes.ts          # 📄 笔记 API
│       └── chat.ts           # 💬 问答代理：POST /api/chat → SSE 代理到 Python :5002
├── package.json              # 依赖：express、better-sqlite3、cors、dotenv
└── tsconfig.json             # TypeScript 配置
```

### API 一览

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /api/health` | 健康检查 | `{"status": "ok"}` |
| `GET /api/notes?page=1&pageSize=20` | 分页获取笔记列表 |
| `GET /api/notes/:id` | 获取单篇笔记详情 |
| `POST /api/chat` | 流式问答（SSE） | `{"question": "..."}` |

---

## ⚛️ `frontend/` — React 前端

用户看到的**界面**。

```
frontend/
├── src/
│   ├── main.tsx              # ReactDOM 挂载入口
│   ├── App.tsx               # 🏠 主布局：顶部标题 + Tab 切换（笔记列表 / AI 问答）
│   ├── App.css               # 🎨 所有样式（~350行）
│   ├── types.ts              # 📐 TypeScript 类型定义（Note, NotesResponse）
│   ├── api.ts                # 📡 API 封装：axios 调用笔记列表 + fetch SSE 流式问答
│   └── components/
│       ├── NoteList.tsx      # 📋 笔记列表：响应式网格卡片、分页、点击弹窗看 AI 摘要
│       └── ChatPanel.tsx     # 💬 对话界面：消息气泡、Markdown 渲染、SSE 流式打字效果
├── vite.config.ts            # Vite 配置 + /api 代理到 localhost:3001
└── dist/                     # 构建产物（npm run build 输出）
```

### 页面功能

- **笔记列表**：响应式网格、分页、点击弹窗展示 AI 摘要（Markdown 渲染）
- **AI 问答**：SSE 流式输出，用户/助手气泡样式，支持 Markdown
- **标签识别**：❤️点赞（橙色）/ ⭐收藏（金色）徽章

---

## 💾 `data/` — 数据文件

运行时自动生成的数据：

| 文件/目录 | 说明 |
|-----------|------|
| `data/xiaohongshu.db` | SQLite 数据库文件（`notes` 表存储所有互动笔记） |
| `data/chroma/` | ChromaDB 向量库持久化目录（自动创建） |
| `data/user_profile.json` | 用户画像缓存（由 `analyzer.generate_profile()` 生成） |

**notes 表结构**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增主键 |
| `title` | TEXT | 笔记标题 |
| `url` | TEXT | 笔记链接 |
| `cover_url` | TEXT | 封面图 URL |
| `action_type` | TEXT | 互动类型：`like` 或 `bookmark` |
| `interest_score` | INTEGER | AI 兴趣评分 |
| `ai_summary` | TEXT | AI 生成的 Markdown 摘要 |
| `original_content` | TEXT | 笔记原始内容 |
| `tags` | TEXT | 逗号分隔的标签 |
| `created_at` | TEXT | 采集日期（格式 `YYYY-MM-DD`） |

---

## 🔗 模块间数据流向

```
┌──────────────────────────────────────────────────────────┐
│ Python automation/                                       │
│                                                          │
│  main.py ──▶ browser.py ──▶ 小红书网页                    │
│     │              │                                     │
│     ▼              ▼                                     │
│  analyzer.py   提取内容 ──▶ summarizer.py                │
│  (DeepSeek)          ──▶  SQLite (data/xiaohongshu.db)  │
│                           Chroma (data/chroma/)          │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ Node.js backend/     直接读 SQLite                       │
│ index.ts ──▶ notes.ts ──▶ GET /api/notes                │
│         ──▶ chat.ts ──▶ 代理 ──▶ Python :5002 ──▶ RAG   │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ React frontend/                                          │
│ App.tsx ──▶ NoteList.tsx ──▶ 卡片展示 + AI 摘要弹窗       │
│         ──▶ ChatPanel.tsx ──▶ SSE 流式对话               │
└──────────────────────────────────────────────────────────┘
```

**简单说：Python 写入数据 → Node.js 读取并提供 API → React 展示。**

---

## 🚀 启动方式

需启动 **3 个服务**（3 个终端）：

### 终端 ❶：Python Chroma HTTP 服务

```bash
cd automation
source venv/bin/activate
python chroma_server.py
# → http://127.0.0.1:5002
```

### 终端 ❷：Node.js 后端

```bash
cd backend
npm run dev
# → http://localhost:3001
```

### 终端 ❸：React 前端

```bash
cd frontend
npm run dev
# → http://localhost:5173
```

### 可选 终端 ❹：定时任务守护进程

```bash
cd automation
source venv/bin/activate
python main.py --schedule
# 每天早上 9:00 自动运行
```

### 服务关系

```
浏览器打开 http://localhost:5173
        │
        ▼ (Vite proxy /api → 3001)
 Node.js :3001 ──直接读取──▶ SQLite (data/xiaohongshu.db)
        │
        ▼ (POST /api/chat SSE 代理)
 Python Flask :5002 ──调用──▶ ChromaDB (data/chroma/) + DeepSeek
```