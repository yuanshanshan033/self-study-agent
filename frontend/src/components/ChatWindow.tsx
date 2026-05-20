import { useState, useRef, useEffect, useCallback } from "react";
import type { ChatMessage } from "../types";
import { askQuestion, formatTime } from "../api";

/**
 * 对话窗口组件
 * 右侧显示区域，磨砂玻璃效果，支持流式对话
 */
export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  /**
   * 自动滚动到底部
   */
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // 消息变化时滚动到底部
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  /**
   * 发送消息
   */
  const handleSend = async () => {
    const question = inputValue.trim();
    if (!question || isLoading) return;

    // 创建用户消息
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: question,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    // 创建AI消息占位
    const aiMessageId = (Date.now() + 1).toString();
    const aiMessage: ChatMessage = {
      id: aiMessageId,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, aiMessage]);

    // 调用API获取流式响应
    await askQuestion(
      question,
      (chunk) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === aiMessageId
              ? { ...msg, content: msg.content + chunk }
              : msg
          )
        );
      },
      () => {
        setIsLoading(false);
      },
      (error) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === aiMessageId ? { ...msg, content: error } : msg
          )
        );
        setIsLoading(false);
      }
    );
  };

  /**
   * 处理键盘事件
   */
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /**
   * 渲染消息内容（支持Markdown简单格式）
   */
  const renderMessageContent = (content: string) => {
    return content.split("\n").map((line, index) => (
      <p key={index} className={line.trim() === "" ? "empty-line" : ""}>
        {line}
      </p>
    ));
  };

  return (
    <div className="chat-window">
      {/* 标题区域 */}
      <div className="chat-header">
        <h2 className="section-title">
          <span className="section-number">2.</span>
          与知识库对话
        </h2>
        <p className="section-subtitle">基于爬取的笔记内容，随时与知识库对话</p>
      </div>

      {/* 消息列表区域 */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
              </svg>
            </div>
            <p>开始与知识库对话吧</p>
            <span>基于爬取的笔记内容，为你解答问题</span>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`message ${message.role === "user" ? "message-user" : "message-assistant"}`}
            >
              {/* 头像 */}
              <div className="message-avatar">
                {message.role === "user" ? (
                  <div className="avatar-user">你</div>
                ) : (
                  <div className="avatar-assistant">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                    </svg>
                  </div>
                )}
              </div>

              {/* 消息内容 */}
              <div className="message-content-wrapper">
                <div className="message-header">
                  <span className="message-author">
                    {message.role === "user" ? "你" : "self-study-agent"}
                  </span>
                  <span className="message-time">{formatTime(message.timestamp)}</span>
                </div>
                <div className="message-content">
                  {message.content ? (
                    renderMessageContent(message.content)
                  ) : (
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="chat-input-area">
        <div className="chat-input-wrapper">
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder="输入你的问题..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isLoading}
          />
          <button
            className="chat-send-btn"
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
