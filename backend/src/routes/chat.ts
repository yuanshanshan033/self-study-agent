import { Router } from "express";
import http from "http";

export const chatRouter = Router();

const CHROMA_HOST = process.env.PYTHON_CHROMA_HOST || "127.0.0.1";
const CHROMA_PORT = process.env.PYTHON_CHROMA_PORT || "5001";

chatRouter.post("/", (req, res) => {
  const { question } = req.body;

  if (!question || typeof question !== "string") {
    res.status(400).json({ error: "question is required" });
    return;
  }

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");

  const postData = JSON.stringify({ question });

  const proxyReq = http.request(
    {
      hostname: CHROMA_HOST,
      port: parseInt(CHROMA_PORT),
      path: "/query",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(postData),
      },
    },
    (proxyRes) => {
      proxyRes.on("data", (chunk: Buffer) => {
        res.write(chunk);
      });

      proxyRes.on("end", () => {
        res.write("data: [DONE]\n\n");
        res.end();
      });
    }
  );

  proxyReq.on("error", (err) => {
    res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
    res.write("data: [DONE]\n\n");
    res.end();
  });

  proxyReq.write(postData);
  proxyReq.end();
});

export default chatRouter;