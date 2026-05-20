/**
 * 笔记数据类型定义
 */

export interface Note {
  id: number;
  title: string;
  url: string | null;
  cover_url: string | null;
  action_type: "like" | "bookmark";
  interest_score: number | null;
  ai_summary: string | null;
  original_content: string | null;
  tags: string | null;
  created_at: string;
  // 统计数据（模拟数据，实际应从后端获取）
  likes?: number;
  bookmarks?: number;
  comments?: number;
}

export interface NotesResponse {
  notes: Note[];
  total: number;
  hasMore: boolean;
}

/**
 * 对话消息类型
 */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

/**
 * 导航项类型
 */
export interface NavItem {
  id: string;
  label: string;
  icon: string;
  active?: boolean;
}
