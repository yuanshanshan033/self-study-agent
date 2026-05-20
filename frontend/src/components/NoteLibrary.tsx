import { useState, useEffect, useRef, useCallback } from "react";
import type { Note } from "../types";
import { fetchNotes } from "../api";
import { NoteCard } from "./NoteCard";

/**
 * 笔记库组件
 * 左侧显示区域，双列布局展示笔记卡片，支持滚动加载
 */
export function NoteLibrary() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const pageSize = 20;

  /**
   * 加载笔记数据
   */
  const loadNotes = useCallback(async (pageNum: number) => {
    if (loading) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetchNotes(pageNum, pageSize);
      
      if (pageNum === 1) {
        setNotes(response.notes);
      } else {
        setNotes(prev => [...prev, ...response.notes]);
      }
      
      setHasMore(response.hasMore);
    } catch (err) {
      setError("加载笔记失败，请稍后重试");
      console.error("Failed to load notes:", err);
    } finally {
      setLoading(false);
    }
  }, [loading]);

  // 初始加载
  useEffect(() => {
    loadNotes(1);
  }, []);

  /**
   * 处理滚动事件，实现无限滚动加载
   */
  const handleScroll = useCallback(() => {
    if (!containerRef.current || loading || !hasMore) return;
    
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const scrollBottom = scrollHeight - scrollTop - clientHeight;
    
    // 距离底部100px时触发加载
    if (scrollBottom < 100) {
      const nextPage = page + 1;
      setPage(nextPage);
      loadNotes(nextPage);
    }
  }, [page, loading, hasMore, loadNotes]);

  // 绑定滚动事件
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener("scroll", handleScroll);
    return () => container.removeEventListener("scroll", handleScroll);
  }, [handleScroll]);

  /**
   * 手动加载更多
   */
  const handleLoadMore = () => {
    if (loading || !hasMore) return;
    const nextPage = page + 1;
    setPage(nextPage);
    loadNotes(nextPage);
  };

  return (
    <div className="note-library">
      {/* 标题区域 */}
      <div className="note-library-header">
        <h2 className="section-title">
          <span className="section-number">1.</span>
          笔记库
        </h2>
        <p className="section-subtitle">爬取自小红书的优质笔记内容</p>
      </div>

      {/* 笔记列表容器 */}
      <div className="note-library-content" ref={containerRef}>
        {/* 双列网格布局 */}
        <div className="notes-grid">
          {notes.map((note, index) => (
            <NoteCard key={`${note.id}-${index}`} note={note} />
          ))}
        </div>

        {/* 加载状态 */}
        {loading && (
          <div className="loading-indicator">
            <div className="loading-spinner"></div>
            <span>加载中...</span>
          </div>
        )}

        {/* 错误提示 */}
        {error && (
          <div className="error-message">
            <span>{error}</span>
            <button onClick={() => loadNotes(page)}>重试</button>
          </div>
        )}

        {/* 加载更多按钮 */}
        {!loading && hasMore && (
          <div className="load-more-container">
            <button className="load-more-btn" onClick={handleLoadMore}>
              查看更多笔记
              <svg className="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        )}

        {/* 没有更多数据 */}
        {!hasMore && notes.length > 0 && (
          <div className="no-more-data">
            <span>已加载全部笔记</span>
          </div>
        )}
      </div>
    </div>
  );
}
