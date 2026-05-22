import json
import time
from openai import OpenAI
from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    USER_PROFILE_PATH,
)

client = OpenAI(
    api_key="sk-749f61249dda4aacb21c3446da08db66",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)


def call_deepseek(messages, temperature=0.7, response_format=None, max_retries=3):
    """
    通用 DeepSeek API 调用
    支持重试和错误处理
    """
    retry_count = 0
    while retry_count < max_retries:
        try:
            params = {
                "model": "deepseek-v4-flash",
                "messages": messages,
                "temperature": temperature,
                "stream": False,
            }
            if response_format == "json_object":
                params["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**params)
            content = response.choices[0].message.content
            return content
        except Exception as e:
            retry_count += 1
            wait_seconds = 2 ** retry_count
            print(f"  ⚠️  DeepSeek API 调用失败: {e}，{retry_count}s 后重试 ({retry_count}/{max_retries})")
            time.sleep(wait_seconds)
    return None


def generate_profile(feed_items):
    """
    根据采集的帖子生成用户画像
    输入: [{"title", "cover_url"}, ...]
    输出: JSON格式的画像
    """
    titles = [item["title"] for item in feed_items]
    input_text = "\n".join([f"- {t}" for t in titles])

    prompt = f"""我正在构建一个AI代理帮我刷小红书发现页。
这是我刷的前 {len(titles)} 篇帖子标题，帮我分析我的兴趣偏好，输出JSON格式结果。

帖子列表:
{input_text}

请输出JSON格式，结构必须如下：
{{
  "preferred_categories": ["类别1", "类别2", "类别3", ...],
  "keywords": ["关键词1", "关键词2", ...],
  "style_preference": "用一句话描述风格偏好",
  "confidence": 一个0-1之间的浮点数，表示基于当前样本得出结论的置信度
}}
"""

    messages = [{"role": "user", "content": prompt}]
    response_text = call_deepseek(messages, temperature=0.3, response_format="json_object")
    if not response_text:
        return None

    try:
        profile = json.loads(response_text)
        with open(USER_PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        print(f"✅ 用户画像生成完成，已保存到: {USER_PROFILE_PATH}")
        return profile
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON 解析失败: {e}")
        print(f"  API返回内容: {response_text[:200]}...")
        return None


def load_profile():
    """加载已保存的用户画像"""
    import os
    if not os.path.exists(USER_PROFILE_PATH):
        return None
    try:
        with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
            profile = json.load(f)
        print(f"✅ 加载已有用户画像: {USER_PROFILE_PATH}")
        return profile
    except Exception as e:
        print(f"  ⚠️  加载用户画像失败: {e}")
        return None


def judge_interest(profile, title):
    """
    基于用户画像判断帖子是否感兴趣（初判，仅标题）
    使用大模型API分析笔记类别，判断是否与用户画像相符
    输出: {is_interested: bool, interest_score: 1-10, reason: string, matched_category: string}
    """
    if not title or not profile:
        return {"is_interested": False, "interest_score": 0, "reason": "标题或画像为空", "matched_category": "其他"}

    # 提取用户画像的偏好类别
    preferred_categories = profile.get("preferred_categories", [])
    categories_str = "、".join(preferred_categories) if preferred_categories else "未指定"

    prompt = f"""请分析这篇小红书笔记的类别，并判断是否与用户的兴趣偏好相符。

用户画像偏好类别：
{categories_str}

笔记标题：
{title}

请按以下步骤分析：
1. 分析笔记标题，判断笔记属于什么类别（如：游戏、美食、科技、娱乐明星、生活方式、情感等）
2. 判断该类别是否与用户的偏好类别相符
3. 如果相符，返回匹配到的用户画像类别名称
4. 给出兴趣评分（1-10分）

请输出 JSON 格式结果，结构必须如下：
{{
  "note_category": "笔记类别名称",
  "is_interested": true 或 false,
  "matched_category": "匹配到的用户画像类别（如不相符则返回'其他'）",
  "interest_score": 1到10的整数，越高表示越感兴趣,
  "reason": "判断原因，说明笔记类别与用户画像的匹配关系"
}}
"""

    messages = [{"role": "user", "content": prompt}]
    response_text = call_deepseek(messages, temperature=0.5, response_format="json_object")
    if not response_text:
        return {"is_interested": False, "interest_score": 0, "reason": "API调用失败", "matched_category": "其他"}

    try:
        result = json.loads(response_text)
        return {
            "is_interested": result.get("is_interested", False),
            "interest_score": result.get("interest_score", 0),
            "reason": result.get("reason", "未知原因"),
            "matched_category": result.get("matched_category", "其他")
        }
    except Exception as e:
        print(f"  ⚠️  JSON 解析失败: {e}")
        return {"is_interested": False, "interest_score": 0, "reason": "解析失败", "matched_category": "其他"}


def judge_action(profile, note_detail):
    """
    详情二次判断，决定执行什么互动
    简化逻辑：既然已经进入详情页，默认点赞，内容特别好才收藏
    输出: {"action": "none" / "like" / "bookmark", "reason": string}
    """
    # 提取用户画像的偏好类别
    preferred_categories = profile.get("preferred_categories", [])
    categories_str = "、".join(preferred_categories) if preferred_categories else "未指定"

    prompt = f"""这篇笔记已经通过标题筛选，用户已进入详情页浏览。
请判断内容质量，决定是否点赞或收藏。

用户画像偏好类别：
{categories_str}

笔记详情:
标题: {note_detail['title']}
内容: {note_detail['content'][:500]}

请输出 JSON 格式结果，结构必须如下:
{{
  "action": "like" 或 "bookmark",
  "reason": "判断原因"
}}

说明:
- "like": 内容不错，值得点赞（默认选择）
- "bookmark": 内容非常好，值得点赞+收藏（只有内容特别优质时才选）

注意：既然用户已经点进来看了，默认应该点赞，不要返回"none"。
"""

    messages = [{"role": "user", "content": prompt}]
    response_text = call_deepseek(messages, temperature=0.5, response_format="json_object")
    if not response_text:
        # API失败时默认点赞
        return {"action": "like", "reason": "API调用失败，默认点赞"}

    try:
        result = json.loads(response_text)
        action = result.get("action", "like")
        # 确保不返回none
        if action not in ("like", "bookmark"):
            action = "like"
        return {"action": action, "reason": result.get("reason", "内容符合兴趣")}
    except Exception as e:
        print(f"  ⚠️  JSON 解析失败: {e}")
        return {"action": "like", "reason": "解析失败，默认点赞"}