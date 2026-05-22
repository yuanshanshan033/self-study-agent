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
    api_key="sk-a70a0af7201843f1a2369c51238cffff",
    base_url="https://api.deepseek.com"
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
                "model": DEEPSEEK_MODEL,
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
    输出: {is_interested: bool, interest_score: 1-10, reason: string}
    """
    profile_desc = json.dumps(profile, ensure_ascii=False)

    prompt = f"""根据以下用户画像，判断这篇小红书帖子是否符合用户的兴趣偏好。

用户画像:
{profile_desc}

帖子标题:
{title}

请输出 JSON 格式结果，结构必须如下：
{{
  "is_interested": true or false,
  "interest_score": 1到10的整数，越高表示越感兴趣，
  "reason": "一句话解释原因"
}}
"""

    messages = [{"role": "user", "content": prompt}]
    response_text = call_deepseek(messages, temperature=0.5, response_format="json_object")
    if not response_text:
        return {"is_interested": False, "interest_score": 0, "reason": "API调用失败"}

    try:
        result = json.loads(response_text)
        return result
    except Exception as e:
        print(f"  ⚠️  JSON 解析失败: {e}")
        return {"is_interested": False, "interest_score": 0, "reason": "解析失败"}


def judge_action(profile, note_detail):
    """
    详情二次判断，决定执行什么互动
    输出: {"action": "none" / "like" / "bookmark", "reason": string}
    """
    profile_desc = json.dumps(profile, ensure_ascii=False)

    prompt = f"""根据以下用户画像，判断这篇小红书笔记是否值得用户互动。
用户更愿意给感兴趣的笔记点赞，如果兴趣非常高才点赞+收藏。

用户画像:
{profile_desc}

笔记详情:
标题: {note_detail['title']}
内容: {note_detail['content']}

请输出 JSON 格式结果，结构必须如下：
{{
  "action": "none" 或 "like" 或 "bookmark",
  "reason": "一句话解释为什么这么判断"
}}

说明:
- "none": 不互动，直接跳过
- "like": 只点赞
- "bookmark": 点赞 + 收藏（说明用户非常感兴趣）
"""

    messages = [{"role": "user", "content": prompt}]
    response_text = call_deepseek(messages, temperature=0.5, response_format="json_object")
    if not response_text:
        return {"action": "none", "reason": "API调用失败"}

    try:
        result = json.loads(response_text)
        return result
    except Exception as e:
        print(f"  ⚠️  JSON 解析失败: {e}")
        return {"action": "none", "reason": "解析失败"}