import axios from "axios";
import type { Note, NotesResponse } from "./types";

const api = axios.create({ baseURL: "/api" });

/**
 * 获取笔记列表
 * @param page 页码
 * @param pageSize 每页数量
 * @returns 笔记列表响应
 */
export async function fetchNotes(page = 1, pageSize = 20): Promise<NotesResponse> {
  const response = await api.get("/notes", { params: { page, pageSize } });
  const notes = response.data.notes || [];

  // 为笔记添加模拟的统计数据
  const notesWithStats = notes.map((note: Note) => ({
    ...note,
    likes: note.likes || Math.floor(Math.random() * 5000) + 100,
    bookmarks: note.bookmarks || Math.floor(Math.random() * 2000) + 50,
    comments: note.comments || Math.floor(Math.random() * 500) + 10,
  }));

  return {
    notes: notesWithStats,
    total: response.data.total || 0,
    hasMore: notes.length === pageSize,
  };
}

/**
 * 根据ID获取单条笔记
 * @param id 笔记ID
 * @returns 笔记详情
 */
export async function fetchNoteById(id: number): Promise<Note> {
  const response = await api.get(`/notes/${id}`);
  return response.data;
}

/**
 * 发送对话问题并接收流式响应
 * @param question 用户问题
 * @param onChunk 接收到数据块时的回调
 * @param onDone 对话完成时的回调
 * @param onError 发生错误时的回调
 */
export async function askQuestion(
  question: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError?: (error: string) => void
): Promise<void> {
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    if (!response.ok || !response.body) {
      const errorMsg = "请求失败，请确认后端服务已启动";
      onChunk(errorMsg);
      onError?.(errorMsg);
      onDone();
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value, { stream: true });
      for (const line of text.split("\n")) {
        if (!line.startsWith("data: ") || line.startsWith("data: [DONE]")) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.content) onChunk(data.content);
        } catch {
          // 忽略解析错误
        }
      }
    }
    onDone();
  } catch (error) {
    const errorMsg = "请求失败，请确认后端服务已启动";
    onChunk(errorMsg);
    onError?.(errorMsg);
    onDone();
  }
}

/**
 * 格式化数字（超过1000显示为1k）
 * @param num 数字
 * @returns 格式化后的字符串
 */
export function formatNumber(num: number): string {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + "k";
  }
  return num.toString();
}

/**
 * 格式化时间戳
 * @param timestamp 时间戳
 * @returns 格式化后的时间字符串
 */
export function formatTime(timestamp: number): string {
  const date = new Date(timestamp);
  const hours = date.getHours().toString().padStart(2, "0");
  const minutes = date.getMinutes().toString().padStart(2, "0");
  return `${hours}:${minutes}`;
}
