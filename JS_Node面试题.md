# Self-Study-Agent JS / Node.js 面试题

> 基于项目实际代码，聚焦 JavaScript 核心原理与 Node.js 后端实践

---

## 一、JavaScript 核心原理

### Q1：你的 ChatWindow 中流式对话用了 `setMessages(prev => prev.map(...))`，为什么用函数式更新而不是直接 `setMessages(messages.map(...))`？

**回答：**

React 的 `setState` 是异步的。如果在闭包中直接引用 `messages` 变量，拿到的是**创建闭包时的旧值**，而不是最新的 state。

流式对话场景下，`askQuestion` 的 `onChunk` 回调可能在短时间内被调用多次，每次都基于同一个闭包中的 `messages` 做更新，后面的更新会覆盖前面的，导致消息丢失。

**函数式更新** `setMessages(prev => ...)` 保证 `prev` 始终是最新 state，即使多次快速调用也能正确累加：

```typescript
// ❌ 错误：闭包中的 messages 可能是旧值
setMessages(messages.map(msg => ...));

// ✅ 正确：prev 始终是最新 state
setMessages(prev => prev.map(msg => ...));
```

这是 React Hooks 中经典的**闭包陷阱**问题，在定时器、事件监听、异步回调中尤其常见。

---

### Q2：你的 `askQuestion` 中用 `while(true)` 循环读取流式数据，这会阻塞主线程吗？为什么？

**回答：**

不会阻塞。`reader.read()` 返回的是 Promise，`await` 会暂停当前 async 函数的执行，**将控制权交还给事件循环**，不会阻塞主线程。

```typescript
while (true) {
  const { done, value } = await reader.read(); // 遇到 await 挂起，不阻塞
  if (done) break;
  // 处理 chunk
}
```

**执行流程：**
1. 调用 `reader.read()` 发起读取请求
2. `await` 暂停函数执行，将控制权交给事件循环
3. 浏览器继续处理 UI 渲染、用户输入等任务
4. 数据到达后，Promise resolve，async 函数从暂停处恢复执行

这就是 JavaScript **单线程 + 异步非阻塞** 的核心机制：通过事件循环和微任务队列实现并发。

---

### Q3：你的 `askQuestion` 中 `decoder.decode(value, { stream: true })` 的 `stream: true` 参数有什么作用？不用会怎样？

**回答：**

`TextDecoder` 用于将字节流（`Uint8Array`）解码为字符串。`stream: true` 表示**当前数据块不是最终块**，解码器会保留未完成的字符序列。

**不用 `stream: true` 的问题：**

UTF-8 中多字节字符（如中文）可能被分割在两个 chunk 中：

```
chunk1: [..., 0xE4, 0xB8]  // "你" 的前两个字节
chunk2: [0xAD, ...]          // "你" 的最后一个字节
```

如果不加 `stream: true`，第一个 chunk 解码时遇到不完整的字节序列，会输出替换字符 `�`，导致中文乱码。

加了 `stream: true`，解码器会将不完整的字节缓存，等下一个 chunk 到达后拼接成完整字符再输出。

---

### Q4：你的 `askQuestion` 中 `for...of` 遍历 `text.split("\n")` 时，如果 SSE 数据跨 chunk 分割（一个 data 行被拆到两个 chunk），会怎样？怎么解决？

**回答：**

**当前问题：** SSE 协议中一条完整的 `data: {...}\n\n` 可能被分割在两个 chunk 中：

```
chunk1: "data: {\"content\": \"hel"
chunk2: "lo\"}\n\n"
```

当前代码按 `\n` 分割后，`chunk1` 产生 `data: {"content": "hel`，`JSON.parse` 会失败，被 `catch` 静默忽略，导致数据丢失。

**解决方案：** 用 buffer 累积数据，按 `\n\n` 分割完整的 SSE 消息：

```typescript
let sseBuffer = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  sseBuffer += decoder.decode(value, { stream: true });
  
  // 按双换行分割完整的 SSE 消息
  const messages = sseBuffer.split("\n\n");
  sseBuffer = messages.pop() || ""; // 最后一段可能不完整，保留

  for (const msg of messages) {
    for (const line of msg.split("\n")) {
      if (!line.startsWith("data: ") || line.startsWith("data: [DONE]")) continue;
      try {
        const data = JSON.parse(line.slice(6));
        if (data.content) onChunk(data.content);
      } catch {}
    }
  }
}
```

---

### Q5：你的 `fetchNotes` 中用 `Math.random()` 生成模拟统计数据，每次渲染数据都不同，这有什么问题？怎么解决？

**回答：**

**问题：**

1. **数据不稳定**：每次调用 `fetchNotes` 返回的 `likes`、`bookmarks` 都不同，导致组件重渲染时 UI 闪烁
2. **React 渲染异常**：React 18 的 StrictMode 下 `useEffect` 会执行两次，两次调用 `fetchNotes` 得到不同数据，可能导致无限重渲染
3. **不可调试**：随机数据无法复现问题

**解决方案：**

1. **后端返回真实数据**（根本解决）
2. **基于 ID 生成伪随机数**：相同 ID 始终生成相同数值
   ```typescript
   function seededRandom(seed: number): number {
     const x = Math.sin(seed) * 10000;
     return x - Math.floor(x);
   }
   
   const likes = Math.floor(seededRandom(note.id) * 5000) + 100;
   ```
3. **前端缓存**：用 `Map` 缓存已生成的随机数
   ```typescript
   const statsCache = new Map<number, { likes: number; bookmarks: number }>();
   ```

---

## 二、Node.js 后端实践

### Q6：你的后端用 `better-sqlite3` 而不是 `sqlite3`，两者有什么区别？为什么选 better-sqlite3？

**回答：**

| 维度 | `sqlite3`（异步） | `better-sqlite3`（同步） |
|---|---|---|
| API 风格 | 回调/Promise | 同步（直接返回结果） |
| 性能 | 较慢（每次操作有 Promise 开销） | 快 2-3 倍（无异步调度开销） |
| 事务 | 需手动 `BEGIN/COMMIT` | `db.transaction()` 一键包装 |
| 线程模型 | Worker Thread | 主线程阻塞 |
| 适用场景 | 高并发 I/O | 中小规模、简单查询 |

**选择 better-sqlite3 的原因：**

1. **本项目并发量低**：个人工具，不会有大量并发请求，同步阻塞不是问题
2. **API 更简洁**：不需要 `await` 或回调，代码可读性好
   ```typescript
   // better-sqlite3：同步，一行搞定
   const notes = db.prepare("SELECT * FROM notes LIMIT ? OFFSET ?").all(pageSize, offset);
   
   // sqlite3：异步，需要回调或 Promise 包装
   db.all("SELECT * FROM notes LIMIT ? OFFSET ?", [pageSize, offset], (err, rows) => { ... });
   ```
3. **事务支持好**：`db.transaction()` 自动处理 BEGIN/COMMIT/ROLLBACK
4. **性能更优**：SQLite 本身就是文件数据库，异步包装反而增加开销

**不适用场景：** 如果是高并发 Web 服务（如每秒数千请求），同步查询会阻塞事件循环，应该用异步的 `sqlite3` 或迁移到 PostgreSQL。

---

### Q7：你的 `chat.ts` 中用 Node.js 的 `http.request` 做代理转发，为什么不用 `axios` 或 `fetch`？SSE 流式转发有什么特殊要求？

**回答：**

**不能用 axios 的原因：**

`axios` 会**等待整个响应体接收完毕**后才触发回调，无法实现流式转发。对于 SSE 场景，后端需要逐 chunk 将数据转发给前端，而不是等全部生成完再一次性返回。

**SSE 流式转发的关键：**

1. **设置 SSE 响应头：**
   ```typescript
   res.setHeader("Content-Type", "text/event-stream");
   res.setHeader("Cache-Control", "no-cache");
   res.setHeader("Connection", "keep-alive");
   ```

2. **逐 chunk 转发：**
   ```typescript
   proxyRes.on("data", (chunk) => {
     res.write(chunk); // 收到一块就转发一块
   });
   ```

3. **结束信号：**
   ```typescript
   proxyRes.on("end", () => {
     res.write("data: [DONE]\n\n"); // SSE 结束标记
     res.end();
   });
   ```

**Node.js 原生 `http` 模块的优势：** 可以直接操作底层流（Stream），实现真正的逐字节转发，延迟最低。

**替代方案：** Node 18+ 可以用原生 `fetch` + `ReadableStream`，但需要手动处理背压（backpressure），不如 `http.request` 直接。

---

### Q8：你的 `sqlite.ts` 中做了数据库迁移（`ALTER TABLE ADD COLUMN`），这种迁移方式有什么问题？生产环境怎么做？

**回答：**

**当前方式的问题：**

1. **不可逆**：SQLite 不支持 `DROP COLUMN`（3.35.0 之前），加了的字段无法回退
2. **无版本管理**：每次启动都检查字段是否存在，无法知道当前数据库是哪个版本
3. **无回滚机制**：迁移失败后数据库可能处于不一致状态
4. **并发风险**：多个实例同时启动可能同时执行迁移

**生产环境推荐方案：**

1. **迁移工具**：使用 `knex`、`sequelize-cli` 或 `prisma migrate` 管理迁移
2. **版本化迁移文件：**
   ```
   migrations/
     001_create_notes.ts
     002_add_text_column.ts
     003_add_ai_tags_column.ts
   ```
3. **迁移表记录版本：**
   ```sql
   CREATE TABLE IF NOT EXISTS migrations (
     id INTEGER PRIMARY KEY,
     name TEXT NOT NULL,
     applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```
4. **每个迁移支持 up 和 down：**
   ```typescript
   export function up(db: Database) {
     db.exec("ALTER TABLE notes ADD COLUMN text TEXT");
   }
   export function down(db: Database) {
     // SQLite 不支持 DROP COLUMN，需要重建表
   }
   ```

---

### Q9：你的后端 `index.ts` 中 `app.use(cors())` 直接允许所有来源，这有什么安全风险？生产环境怎么配置？

**回答：**

**风险：**

1. **CSRF 攻击**：恶意网站可以代替用户向后端发送请求
2. **数据泄露**：任何网站都可以读取 API 返回的数据
3. **XSS 放大**：如果存在 XSS 漏洞，攻击者可以无限制调用 API

**生产环境配置：**

```typescript
import cors from "cors";

app.use(cors({
  origin: [
    "https://your-domain.com",
    "http://localhost:5173"  // 开发环境
  ],
  methods: ["GET", "POST"],
  allowedHeaders: ["Content-Type"],
  credentials: true,  // 允许携带 Cookie
  maxAge: 86400       // 预检请求缓存 24 小时
}));
```

**额外防护：**
- 添加 CSP（Content-Security-Policy）头
- 使用 `helmet` 中间件设置安全头
- API 接口添加认证（JWT / Session）

---

### Q10：你的后端用 Express 4.x，如果请求量增大，有什么性能瓶颈？怎么优化？

**回答：**

**瓶颈分析：**

1. **单线程阻塞**：`better-sqlite3` 的同步查询会阻塞事件循环，一个慢查询影响所有请求
2. **无连接池**：SQLite 单写者模型，并发写入需要排队
3. **无缓存**：每次请求都查数据库，重复查询浪费资源
4. **无压缩**：响应未启用 gzip，传输体积大

**优化方案：**

| 优化方向 | 方案 |
|---|---|
| 数据库 | 慢查询移到 Worker Thread，或换 PostgreSQL |
| 缓存 | 添加内存缓存（`node-cache`），热点数据不查库 |
| 压缩 | `app.use(compression())` 启用 gzip |
| 限流 | `express-rate-limit` 防止恶意请求 |
| 集群 | `cluster` 模块利用多核 CPU |
| 连接管理 | 启用 `keep-alive`，减少 TCP 握手 |

**示例：**

```typescript
import compression from "compression";
import rateLimit from "express-rate-limit";
import NodeCache from "node-cache";

// 压缩
app.use(compression());

// 限流
app.use(rateLimit({ windowMs: 60000, max: 100 }));

// 缓存
const cache = new NodeCache({ stdTTL: 60 });
notesRouter.get("/", (req, res) => {
  const cacheKey = `notes_${req.query.page}_${req.query.pageSize}`;
  const cached = cache.get(cacheKey);
  if (cached) return res.json(cached);
  
  const result = getNotes(page, pageSize);
  cache.set(cacheKey, result);
  res.json(result);
});
```

---

## 三、异步编程深度

### Q11：你的后端 `chat.ts` 中 `proxyReq.on("error", ...)` 和 `proxyRes.on("data", ...)` 是什么模式？和 Promise/async-await 有什么区别？

**回答：**

这是 **EventEmitter 事件驱动模式**，Node.js 的核心设计模式。

**三种异步模式对比：**

| 模式 | 适用场景 | 特点 |
|---|---|---|
| 回调函数 | 简单异步操作 | 容易回调地狱 |
| Promise/async-await | 一次性异步操作 | 代码线性，易读 |
| EventEmitter | 持续性事件流 | 多次触发，适合流式数据 |

**SSE 流式场景为什么用 EventEmitter：**

- 数据是**持续不断**到达的，不是一次性返回
- `data` 事件可能触发几十次甚至上百次
- `end` 事件表示流结束
- `error` 事件表示异常

**如果用 async-await 改写：**

```typescript
// 用 Node 18+ 的 stream/consumers
import { toArrayBuffer } from "node:stream/consumers";

// 但这样会等待全部数据，失去流式特性
const fullData = await toArrayBuffer(proxyRes);
```

所以流式场景**必须用事件驱动模式**，Promise 只能处理"一次性"的异步操作。

---

### Q12：你的前端 `askQuestion` 中 `reader.read()` 返回 `{ done, value }`，这是什么的 API？和 Node.js Stream 有什么区别？

**回答：**

这是 **Web Streams API**（`ReadableStream`），浏览器原生的流式读取接口。

**Web Streams vs Node.js Streams：**

| 维度 | Web Streams | Node.js Streams |
|---|---|---|
| 环境 | 浏览器 | Node.js |
| 读取方式 | `reader.read()` 返回 Promise | `stream.on("data", chunk)` 事件 |
| 背压控制 | 自动（`read()` 是 pull 模式） | 需手动 `pause()/resume()` |
| 取消 | `reader.cancel()` | `stream.destroy()` |
| 数据类型 | `Uint8Array` | `Buffer` |

**Web Streams 的优势：**

- **Pull 模式**：消费者主动拉取数据，天然支持背压，不会因为生产者太快导致内存溢出
- **Promise 接口**：和 async/await 配合良好
- **标准化**：W3C 标准，Node.js 16+ 也开始支持

**项目中的应用：**
- 前端用 Web Streams（`fetch` + `ReadableStream`）读取 SSE
- 后端用 Node.js Streams（`http.request` + `EventEmitter`）转发 SSE
- 两者通过 HTTP 协议连接，各自用最合适的流式 API

---

## 四、TypeScript 与工程化

### Q13：你的后端用了 TypeScript，但 `req.query.page as string` 这种类型断言有什么风险？怎么改进？

**回答：**

**风险：**

`req.query` 的类型是 `qs.ParsedQs`，值可能是 `string | string[] | undefined`。直接 `as string` 断言：
1. 如果值是数组（`?page=1&page=2`），断言后类型是 `string`，实际是数组，`parseInt` 结果为 `NaN`
2. 如果值是 `undefined`，断言不会报错，但 `parseInt(undefined)` 返回 `NaN`

**改进方案：**

```typescript
import { z } from "zod";

const querySchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  pageSize: z.coerce.number().int().positive().max(100).default(20),
});

notesRouter.get("/", (req, res) => {
  const result = querySchema.safeParse(req.query);
  if (!result.success) {
    return res.status(400).json({ error: result.error.flatten() });
  }
  const { page, pageSize } = result.data;
  const notes = getNotes(page, pageSize);
  res.json(notes);
});
```

**好处：**
1. 类型安全：自动推导出 `page: number`
2. 运行时校验：非法参数直接返回 400
3. 默认值：`default(1)` 处理 undefined
4. 边界限制：`max(100)` 防止一次请求过多数据

---

### Q14：你的 `sqlite.ts` 中数据库连接是模块级单例，这有什么问题？怎么实现连接管理？

**回答：**

**当前方式：**

```typescript
const db: DatabaseType = new Database(DB_PATH); // 模块加载时立即创建
```

**问题：**

1. **无法延迟连接**：即使不需要数据库也会创建连接
2. **无法关闭连接**：进程退出时连接未显式关闭，可能丢失未刷盘的数据
3. **测试困难**：单例无法 mock，测试用真实数据库
4. **多实例风险**：如果多个模块 import，SQLite 不支持多进程并发写入

**改进方案：**

```typescript
let db: DatabaseType | null = null;

export function getDb(): DatabaseType {
  if (!db) {
    db = new Database(DB_PATH);
    db.pragma("journal_mode = WAL");       // WAL 模式提升并发读
    db.pragma("synchronous = NORMAL");      // 平衡性能和安全
  }
  return db;
}

export function closeDb(): void {
  if (db) {
    db.close();
    db = null;
  }
}

// 进程退出时关闭连接
process.on("SIGINT", () => {
  closeDb();
  process.exit(0);
});
```

---

## 五、网络与 HTTP

### Q15：你的 SSE 流式对话中，如果用户快速连续发送多条消息，会发生什么？怎么处理并发请求？

**回答：**

**当前问题：**

1. **多个流同时写入**：前一个请求的流还没结束，新请求又开始了，`setMessages` 可能交错更新
2. **AI 回复混乱**：两个流式响应的 chunk 交替到达，消息内容可能串接
3. **后端无状态**：`chat.ts` 不维护会话上下文，每次请求独立

**解决方案：**

1. **前端加锁**（当前已部分实现）：
   ```typescript
   const handleSend = async () => {
     if (!question || isLoading) return; // loading 时禁止发送
   };
   ```

2. **取消前一个请求**：
   ```typescript
   const abortRef = useRef<AbortController | null>(null);
   
   const handleSend = async () => {
     // 取消上一个未完成的请求
     abortRef.current?.abort();
     abortRef.current = new AbortController();
     
     await fetch("/api/chat", { signal: abortRef.current.signal });
   };
   ```

3. **后端请求队列**：
   ```typescript
   const queue: express.Request[] = [];
   let processing = false;
   
   chatRouter.post("/", (req, res) => {
     queue.push(req);
     processQueue();
   });
   ```

---

### Q16：你的前端 `axios.create({ baseURL: "/api" })` 和 `fetch("/api/chat")` 混用了两种请求方式，Vite 开发环境下 `/api` 是怎么代理到后端的？

**回答：**

Vite 通过 `server.proxy` 配置将前端请求代理到后端：

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:3001",
        changeOrigin: true,
      },
      "/screenshots": {
        target: "http://localhost:3001",
        changeOrigin: true,
      },
    },
  },
});
```

**工作原理：**

1. 前端请求 `/api/notes` → Vite Dev Server 拦截
2. Vite 将请求转发到 `http://localhost:3001/api/notes`
3. 后端响应 → Vite 转发回前端

**生产环境：** 不需要 Vite 代理，需要 Nginx 反向代理或后端直接服务前端静态文件：

```nginx
location /api/ {
  proxy_pass http://localhost:3001;
}
location /screenshots/ {
  proxy_pass http://localhost:3001;
}
```

---

## 六、数据库与 SQL

### Q17：你的 `getNotes` 用 `LIMIT ? OFFSET ?` 分页，深分页时性能如何？怎么优化？

**回答：**

**深分页问题：**

`LIMIT 20 OFFSET 100000` 需要 MySQL/SQLite 先扫描前 100020 行，再丢弃前 100000 行，时间复杂度 O(offset + limit)。

**优化方案：**

1. **游标分页（Cursor-based）：**
   ```sql
   -- 第一页
   SELECT * FROM notes ORDER BY id DESC LIMIT 20;
   
   -- 下一页（用上一页最后一条的 id 作为游标）
   SELECT * FROM notes WHERE id < ? ORDER BY id DESC LIMIT 20;
   ```
   利用主键索引，深分页也只需扫描 20 行，时间复杂度 O(limit)。

2. **前端配合：**
   ```typescript
   // 不再传 page，传 lastId
   notesRouter.get("/", (req, res) => {
     const lastId = parseInt(req.query.lastId as string) || Infinity;
     const notes = db.prepare(
       "SELECT * FROM notes WHERE id < ? ORDER BY id DESC LIMIT ?"
     ).all(lastId, pageSize);
     res.json({ notes, lastId: notes[notes.length - 1]?.id });
   });
   ```

**游标分页的局限：** 不支持跳页（不能直接跳到第 50 页），适合无限滚动场景（正好是本项目的用法）。

---

### Q18：你的 `getNotesByTag` 用 `LIKE '%tag%'` 查询，这有什么性能问题？怎么优化？

**回答：**

**问题：** `LIKE '%tag%'` 前缀通配符导致**无法使用索引**，必须全表扫描，数据量大时性能极差。

**优化方案：**

1. **SQLite FTS5 全文搜索：**
   ```sql
   CREATE VIRTUAL TABLE notes_fts USING fts5(title, text, tags);
   
   SELECT * FROM notes_fts WHERE tags MATCH '编程' ORDER BY rank;
   ```
   支持分词、排序、模糊匹配，查询速度从 O(n) 降到 O(log n)。

2. **标签表拆分（规范化）：**
   ```sql
   CREATE TABLE tags (
     id INTEGER PRIMARY KEY,
     name TEXT NOT NULL UNIQUE
   );
   CREATE TABLE note_tags (
     note_id INTEGER,
     tag_id INTEGER,
     PRIMARY KEY (note_id, tag_id)
   );
   
   -- 查询带某标签的笔记（走索引）
   SELECT n.* FROM notes n
   JOIN note_tags nt ON n.id = nt.note_id
   JOIN tags t ON nt.tag_id = t.id
   WHERE t.name = '编程';
   ```

3. **JSON 查询（SQLite 3.38+）：**
   ```sql
   -- 如果 tags 存为 JSON 数组
   SELECT * FROM notes WHERE tags JSON_EXTRACT(tags, '$') LIKE '%"编程%"';
   ```

---

## 重点准备建议

| 优先级 | 题目 | 考察点 |
|---|---|---|
| ⭐⭐⭐ | Q1 函数式更新 | React 闭包陷阱、setState 原理 |
| ⭐⭐⭐ | Q2 async 不阻塞 | 事件循环、微任务队列 |
| ⭐⭐⭐ | Q7 SSE 流式转发 | Node.js Stream、HTTP 代理 |
| ⭐⭐⭐ | Q11 事件驱动 vs Promise | 异步编程模式、Node.js 核心设计 |
| ⭐⭐⭐ | Q17 深分页优化 | SQL 性能优化、索引原理 |
| ⭐⭐ | Q3 TextDecoder stream | 编码原理、流式数据处理 |
| ⭐⭐ | Q4 SSE 跨 chunk | 协议解析、边界处理 |
| ⭐⭐ | Q6 better-sqlite3 vs sqlite3 | Node.js 数据库选型 |
| ⭐⭐ | Q10 Express 性能优化 | Node.js 性能调优 |
| ⭐⭐ | Q13 类型断言风险 | TypeScript 类型安全、Zod |
| ⭐⭐ | Q15 并发请求处理 | 异步并发控制、AbortController |
| ⭐⭐ | Q18 LIKE 性能 | SQL 索引、全文搜索 |
| ⭐ | Q5 随机数据不稳定 | 前端数据一致性 |
| ⭐ | Q8 数据库迁移 | 工程化、版本管理 |
| ⭐ | Q9 CORS 安全 | HTTP 安全、跨域策略 |
| ⭐ | Q12 Web Streams vs Node Streams | 流式 API 对比 |
| ⭐ | Q14 数据库单例 | 连接管理、资源释放 |
| ⭐ | Q16 Vite 代理 | 开发/生产环境配置 |
