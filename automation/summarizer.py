import json
from analyzer import call_deepseek


def summarize_note(note):
    """
    对一篇互动笔记生成结构化摘要
    返回: dict 包含 ai_summary, tags 等
    """
    title = note.get("title", "")
    content = note.get("content", "")
    action_type = note.get("action_type", "like")

    text_input = f"""请分析以下小红书笔记，生成结构化摘要。

笔记标题: {title}
笔记正文: {content}
用户互动: {"点赞+收藏" if action_type == "bookmark" else "点赞"}

请用 JSON 格式返回，结构如下:
{{
  "core_insight": "笔记核心观点（1-2句话概括）",
  "key_points": ["要点1", "要点2", "要点3"],
  "why_interested": "为什么用户会对这篇笔记感兴趣",
  "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"]
}}
"""

    messages = [{"role": "user", "content": text_input}]
    response = call_deepseek(messages, temperature=0.5, response_format="json_object")
    if not response:
        return {"core_insight": "", "key_points": [], "why_interested": "", "tags": []}

    try:
        result = json.loads(response)
        return result
    except json.JSONDecodeError:
        return {"core_insight": title, "key_points": [], "why_interested": "", "tags": []}


def build_markdown_summary(summary_result):
    """将 JSON 摘要结果拼成 Markdown 格式"""
    lines = []
    if summary_result.get("core_insight"):
        lines.append(f"**核心观点**\n\n{summary_result['core_insight']}\n")
    if summary_result.get("key_points"):
        lines.append("**关键要点**\n")
        for point in summary_result["key_points"]:
            lines.append(f"- {point}")
        lines.append("")
    if summary_result.get("why_interested"):
        lines.append(f"**兴趣匹配**\n\n{summary_result['why_interested']}\n")
    return "\n".join(lines)


def batch_summarize(notes):
    """批量总结多篇笔记"""
    summarized = []
    for i, note in enumerate(notes):
        print(f"  🤖 总结笔记 {i+1}/{len(notes)}: {note.get('title', '')[:30]}...")
        summary = summarize_note(note)
        md = build_markdown_summary(summary)
        summarized.append({
            "title": note.get("title", ""),
            "url": note.get("url", ""),
            "cover_url": note.get("images", [None])[0] if note.get("images") else "",
            "action_type": note.get("action_type", "like"),
            "interest_score": note.get("interest_score", 0),
            "ai_summary": md,
            "original_content": note.get("content", ""),
            "tags": ", ".join(summary.get("tags", [])),
        })
    return summarized