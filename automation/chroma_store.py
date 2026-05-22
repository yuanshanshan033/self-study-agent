import os
import sys

# 添加 vendor 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import chromadb
from chromadb.config import Settings
from config import CHROMA_PATH
from analyzer import call_deepseek

COLLECTION_NAME = "xiaohongshu_notes"

_client = None
_collection = None


def _get_client():
    global _client
    if _client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def _get_collection():
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def add_notes_to_chroma(notes):
    """
    将总结后的笔记写入 Chroma 向量库
    notes: [{title, ai_summary, tags, url, ...}, ...]
    """
    collection = _get_collection()
    added = 0
    for note in notes:
        doc_id = f"note_{note.get('title', '').replace(' ', '_')[:40]}_{added}"
        doc_content = f"标题: {note.get('title', '')}\n摘要: {note.get('ai_summary', '')}"

        try:
            collection.add(
                ids=[doc_id],
                documents=[doc_content],
                metadatas=[{
                    "title": note.get("title", ""),
                    "url": note.get("url", ""),
                    "tags": note.get("tags", ""),
                    "action_type": note.get("action_type", "like"),
                }],
            )
            added += 1
        except Exception as e:
            print(f"  ⚠️  Chroma 写入失败 [{note.get('title', '')[:20]}]: {e}")

    print(f"✅ 已将 {added} 条笔记写入 Chroma 向量库")
    return added


def query_notes(query_text, top_k=5):
    """从 Chroma 检索与问题最相关的笔记片段"""
    collection = _get_collection()
    try:
        results = collection.query(query_texts=[query_text], n_results=top_k)
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        return documents, metadatas
    except Exception as e:
        print(f"  ⚠️  Chroma 检索失败: {e}")
        return [], []


def query_and_answer(user_question, top_k=5):
    """
    RAG 问答：检索 + DeepSeek 生成回答（非流式）
    返回完整的回答文本
    """
    docs, metas = query_notes(user_question, top_k=top_k)

    if not docs:
        return "抱歉，目前数据库中没有找到相关笔记。请稍后再试。"

    context_parts = []
    for i, (doc, meta) in enumerate(zip(docs, metas)):
        title = meta.get("title", "未知")
        context_parts.append(f"[来源{i+1}] 标题: {title}\n内容: {doc[:500]}")

    context = "\n\n".join(context_parts)

    prompt = f"""你是一个根据用户收藏的小红书笔记来回答问题的助手。

以下是数据库中与用户问题相关的笔记内容:
{context}

用户问题: {user_question}

请基于以上笔记内容回答问题。如果笔记内容不足以完整回答，可以基于你自己的知识补充，但要明确指出哪些是你的推测。回答尽量简洁有用。
"""

    messages = [{"role": "user", "content": prompt}]
    answer = call_deepseek(messages, temperature=0.5)
    return answer if answer else "抱歉，生成回答时出现错误。"


def query_and_answer_stream(user_question, top_k=5):
    """
    RAG 问答：检索 + DeepSeek 流式生成
    返回一个遍历器，逐 token 输出
    """
    from openai import OpenAI
    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

    docs, metas = query_notes(user_question, top_k=top_k)

    if not docs:
        yield "抱歉，目前数据库中没有找到相关笔记。"
        return

    context_parts = []
    for i, (doc, meta) in enumerate(zip(docs, metas)):
        title = meta.get("title", "未知")
        context_parts.append(f"[来源{i+1}] 标题: {title}\n内容: {doc[:500]}")

    context = "\n\n".join(context_parts)

    system_prompt = """你是一个根据用户收藏的小红书笔记来回答问题的助手。
回答时，请基于提供的笔记内容。如果不够，可以补充你自己的知识，但要说明。回答简洁有用。"""

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"数据库笔记内容:\n{context}\n\n用户问题: {user_question}"},
    ]

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.5,
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
    except Exception as e:
        yield f"\n\n[生成出错: {e}]"