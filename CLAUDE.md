# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

小红书 AI 自动化代理：Python 自动化浏览小红书发现页 → DeepSeek LLM 分析兴趣 → 自动点赞/收藏 → 笔记摘要存入 SQLite + ChromaDB → Node.js 提供 API → React 前端展示笔记与 RAG 问答。

## 启动命令（需 3~4 个终端）

```bash
# 终端 1：Python Chroma HTTP 服务
cd automation && source venv/bin/activate && python chroma_server.py
# → http://127.0.0.1:5002

# 终端 2：Node.js 后端
cd backend && npm run dev
# → http://localhost:3001

# 终端 3：React 前端
cd frontend && npm run dev
# → http://localhost:5173

# 终端 4（可选）：定时任务守护进程
cd automation && source venv/bin/activate && python main.py --schedule
```

## 构建命令

```bash
cd backend && npm run build      # TypeScript 编译
cd frontend && npm run build     # Vite 生产构建
```

## Python 自动化 CLI

```bash
cd automation && source venv/bin/activate
python main.py --profile         # 一次性生成用户画像（采集 50 篇帖子）
python main.py --daily           # 手动运行一次完整每日任务
python main.py --schedule        # 守护进程，每天 09:00 自动执行
```

## 架构概览

三层架构，数据流为单向：**Python 生产数据 → Node.js 读取并提供 API → React 展示**。

### Layer 1 — Python 自动化 (`automation/`)

- `main.py`：`DailyTask` 类编排完整流程（登录→画像→浏览→互动→总结→入库）
- `browser.py`：DrissionPage 浏览器自动化，含反检测拟人行为（贝塞尔曲线鼠标移动、随机滚动、分批休息、概率化互动）
- `analyzer.py`：DeepSeek API 调用（画像生成、兴趣判断、互动决策）
- `summarizer.py`：笔记结构化摘要生成
- `chroma_store.py`：ChromaDB 写入 + RAG 流式问答
- `chroma_server.py`：Flask HTTP 服务（端口 5002），暴露 `POST /query` SSE 接口供 Node.js 代理
- `config.py`：集中配置（API Key、路径、限额）

### Layer 2 — Node.js 后端 (`backend/`)

- Express 端口 3001，直接读 SQLite
- `GET /api/notes`、`GET /api/notes/:id`：笔记列表/详情
- `POST /api/chat`：SSE 代理转发到 Python Flask `:5002`

### Layer 3 — React 前端 (`frontend/`)

- Vite dev server 代理 `/api` → `localhost:3001`
- 左侧 `NoteLibrary`：无限滚动笔记网格 + 详情弹窗
- 右侧 `ChatWindow`：SSE 流式对话，Markdown 渲染

### 进程间通信

- Python 直写 `data/xiaohongshu.db`（SQLite）和 `data/chroma/`（ChromaDB）
- Node.js 直读 SQLite，通过 HTTP 调用 Python Flask 做 RAG 查询
- 所有服务配置在项目根目录 `.env` 文件中

## 关键配置值（`automation/config.py`）

- 每日点赞上限：15，收藏上限：5
- 浏览时间限制：10 分钟
- 画像采集帖子数：50
- LLM：DeepSeek (deepseek-v4-flash) via DashScope API
- Chroma 服务端口：5002，Node.js 端口：3001

## 注意事项

- Python 虚拟环境在 `automation/venv/`，安装依赖：`cd automation && source venv/bin/activate && pip install -r requirements.txt`
- Node.js 依赖：`cd backend && npm install`
- 前端依赖：`cd frontend && npm install`
- 自动化模块中的 `vendor/` 目录存放本地化的 Python 包
- 截图存储在 `data/screenshots/`，用户画像缓存在 `data/user_profile.json`
