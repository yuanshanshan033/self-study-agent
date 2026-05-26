import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import path from "path";

dotenv.config({ path: path.resolve(__dirname, "..", "..", ".env") });

import { notesRouter } from "./routes/notes";
import { chatRouter } from "./routes/chat";

const app = express();
const PORT = process.env.NODE_PORT || 3001;

app.use(cors());
app.use(express.json());

// 提供截图文件的静态访问
const screenshotsDir = process.env.SCREENSHOTS_DIR || path.resolve(__dirname, "..", "..", "data", "screenshots");
app.use("/screenshots", express.static(screenshotsDir));

app.use("/api/notes", notesRouter);
app.use("/api/chat", chatRouter);

app.get("/api/health", (_req, res) => {
  res.json({ status: "ok" });
});

app.listen(PORT, () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
});