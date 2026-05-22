import json
import random
import sys
import os

# 添加 vendor 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import schedule
import sqlite3
import time
from datetime import datetime
import browser
import analyzer
import summarizer
import chroma_store
from config import MAX_DAILY_LIKES, MAX_DAILY_BOOKMARKS, MAX_BROWSING_MINUTES, SQLITE_PATH, FEED_COUNT_FOR_PROFILE


class DailyTask:
    """
    每日任务编排：画像加载 → 发现页浏览 → 兴趣判断 → 互动操作
    包含概率化行为、每日上限控制、时间限制
    """

    def __init__(self):
        self.profile = None
        self.page = None
        self.like_count = 0
        self.bookmark_count = 0
        self.interacted_notes = []
        self.start_time = None
        self.like_probability = 0.8
        self.bookmark_probability = 0.6
        self.interact_cooldown = 0
        self.posts_since_last_interact = 0

    def _ensure_profile(self):
        """确保用户画像存在"""
        self.profile = analyzer.load_profile()
        if self.profile:
            return True

        print(f"\n📋 未找到用户画像，先采集前{FEED_COUNT_FOR_PROFILE}篇帖子生成画像...")
        feed_items = browser.collect_feed_items(self.page, count=FEED_COUNT_FOR_PROFILE)
        if len(feed_items) < 10:
            print(f"❌ 采集到的帖子太少({len(feed_items)}篇)")
            return False
        self.profile = analyzer.generate_profile(feed_items)
        if not self.profile:
            print("❌ 画像生成失败")
        return bool(self.profile)

    def _is_time_up(self):
        """检查是否超时"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return elapsed > MAX_BROWSING_MINUTES * 60

    def _is_limit_reached(self):
        """检查是否达到每日上限"""
        return self.like_count >= MAX_DAILY_LIKES

    def _should_like(self):
        """概率决定是否点赞（模拟'感兴趣但忘记点赞'）"""
        return random.random() < self.like_probability

    def _should_bookmark(self):
        """概率决定是否同时收藏"""
        return random.random() < self.bookmark_probability

    def _can_interact(self):
        """cooling 期必须浏览 2 篇其他帖子后才能下一次互动"""
        return self.posts_since_last_interact >= 2

    def _get_feed_titles(self):
        """从当前发现页提取所有可见帖子的标题和元素"""
        items = []
        try:
            note_items = self.page.eles(".note-item")
            if not note_items:
                return items
            for item in note_items:
                try:
                    title_ele = item.wait.ele_displayed(".title", timeout=1)
                    title = title_ele.text if title_ele else ""
                    if not title.strip():
                        title_ele = item.wait.ele_displayed(".footer .title", timeout=1)
                        title = title_ele.text if title_ele else ""
                except Exception:
                    title = ""
                items.append({"element": item, "title": title.strip()})
        except Exception:
            pass
        return items

    def _handle_note(self, item):
        """处理单篇帖子：初判 → （不感兴趣就跳过） → 进详情 → 二次判断 → 互动"""
        title = item["title"]
        element = item["element"]

        if not title:
            return

        print(f"\n📌 帖子标题: {title[:50]}...")

        interest = analyzer.judge_interest(self.profile, title)
        if not interest.get("is_interested"):
            print(f"  ⌛ 不感兴趣 (评分:{interest.get('interest_score', 0)})，跳过")
            return

        print(f"  ✅ 感兴趣 (评分:{interest.get('interest_score')})，进入详情页...")
        browser.human_pause(2.0, 5.0)

        if not browser.click_note(self.page, element):
            print("  ⚠️  点击详情失败")
            return

        detail = browser.get_page_content(self.page)
        print(f"  详情文字: {detail['content'][:80]}..." if detail["content"] else "  无文字内容")
        print(f"  图片数量: {len(detail['images'])}")

        browser.human_pause(5.0, 12.0)

        action_result = analyzer.judge_action(self.profile, detail)
        action = action_result.get("action", "none")
        print(f"  🧠 AI判断: {action}，原因: {action_result.get('reason', '')}")

        if action not in ("like", "bookmark"):
            print("  ⌛ 最终决定不互动")
            browser.close_detail(self.page)
            browser.human_pause(2.0, 5.0)
            self.posts_since_last_interact += 1
            return

        if not self._can_interact():
            print("  ⌛ 互动冷却期，跳过互动")
            browser.close_detail(self.page)
            browser.human_pause(2.0, 5.0)
            self.posts_since_last_interact += 1
            return

        if not self._should_like():
            print("  ⌛ AI建议点赞，但概率决定不执行（模拟忘记点赞）")
            browser.close_detail(self.page)
            browser.human_pause(2.0, 5.0)
            self.posts_since_last_interact += 1
            return

        print("  ❤️  执行点赞...")
        if browser.do_like(self.page):
            self.like_count += 1
            self.posts_since_last_interact = 0
            print(f"  点赞成功！今日已点赞: {self.like_count}/{MAX_DAILY_LIKES}")

        bookmark_executed = False
        if action == "bookmark" and self._should_bookmark():
            browser.human_pause(2.0, 4.0)
            print("  ⭐ 兴趣极高，执行收藏...")
            if browser.do_bookmark(self.page):
                self.bookmark_count += 1
                bookmark_executed = True
                print(f"  收藏成功！今日已收藏: {self.bookmark_count}/{MAX_DAILY_BOOKMARKS}")

        action_type = "bookmark" if bookmark_executed else "like"
        self.interacted_notes.append({
            "title": detail["title"],
            "content": detail["content"],
            "images": detail["images"],
            "url": detail["url"],
            "action_type": action_type,
            "interest_score": interest.get("interest_score", 0),
            "ai_reason": action_result.get("reason", ""),
            "post_title": title,
        })

        browser.human_pause(3.0, 8.0)
        browser.close_detail(self.page)
        browser.human_pause(2.0, 5.0)

    def _save_to_sqlite(self, summarized_notes):
        """将总结后的笔记写入 SQLite"""
        conn = sqlite3.connect(SQLITE_PATH)
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        saved = 0
        for note in summarized_notes:
            try:
                cursor.execute("""
                    INSERT INTO notes (title, url, cover_url, action_type, interest_score,
                                       ai_summary, original_content, tags, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    note.get("title", ""),
                    note.get("url", ""),
                    note.get("cover_url", ""),
                    note.get("action_type", "like"),
                    note.get("interest_score", 0),
                    note.get("ai_summary", ""),
                    note.get("original_content", ""),
                    note.get("tags", ""),
                    today,
                ))
                saved += 1
            except Exception as e:
                print(f"  ⚠️  SQLite 写入失败: {e}")
        conn.commit()
        conn.close()
        print(f"✅ 已将 {saved} 条笔记写入 SQLite")
        return saved

    def _print_summary(self):
        """打印每日任务摘要"""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        print(f"\n{'=' * 60}")
        print(f"  每日任务完成！")
        print(f"{'=' * 60}")
        print(f"  用时: {elapsed:.1f} 分钟")
        print(f"  浏览帖子: {self.posts_since_last_interact + self.like_count}篇+")
        print(f"  点赞: {self.like_count} 篇")
        print(f"  收藏: {self.bookmark_count} 篇")
        print(f"  累计互动笔记: {len(self.interacted_notes)} 条")
        print(f"{'=' * 60}\n")

    def run(self):
        """执行一次完整的每日任务"""
        self.start_time = datetime.now()
        print(f"\n{'=' * 60}")
        print(f"  每日任务启动")
        print(f"  开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  点赞上限: {MAX_DAILY_LIKES} | 收藏上限: {MAX_DAILY_BOOKMARKS}")
        print(f"  时间上限: {MAX_BROWSING_MINUTES} 分钟")
        print(f"{'=' * 60}\n")

        self.page = browser.init_browser()
        if not browser.wait_for_login(self.page):
            print("❌ 登录失败，退出")
            return self.interacted_notes

        if not self._ensure_profile():
            print("❌ 无法建立用户画像，退出")
            return self.interacted_notes

        print(f"\n📊 当前用户画像: {', '.join(self.profile.get('preferred_categories', [])[:5])}")
        print("🔄 进入持续浏览 + 互动模式...\n")

        last_items_count = 0
        stale_rounds = 0

        while not self._is_limit_reached() and not self._is_time_up():
            browser.human_scroll(self.page)
            browser.batch_rest(self.like_count)

            items = self._get_feed_titles()
            all_titles = [item["title"] for item in items if item["title"]]

            if len(all_titles) == last_items_count:
                stale_rounds += 1
                if stale_rounds > 10:
                    print("⚠️  页面长时间无新内容，结束浏览")
                    break
            else:
                stale_rounds = 0
            last_items_count = len(all_titles)

            for item in items:
                if self._is_limit_reached() or self._is_time_up():
                    break
                self._handle_note(item)
                browser.human_pause(3.0, 8.0)

            items_remaining = MAX_DAILY_LIKES - self.like_count
            print(f"\n📊 进度: 点赞 {self.like_count}/{MAX_DAILY_LIKES} | "
                  f"收藏 {self.bookmark_count}/{MAX_DAILY_BOOKMARKS} | "
                  f"还需{items_remaining}个点赞或到时结束")

            if stale_rounds > 5:
                browser.take_break(60, 180)

        self._print_summary()

        if not self.interacted_notes:
            print("⚠️  本次没有互动数据，跳过总结和入库")
            return self.interacted_notes

        print("\n📝 开始 AI 总结互动笔记...")
        summarized = summarizer.batch_summarize(self.interacted_notes)

        print("\n💾 写入 SQLite 数据库...")
        self._save_to_sqlite(summarized)

        print("\n🧬 写入 Chroma 向量库...")
        chroma_store.add_notes_to_chroma(summarized)

        return self.interacted_notes


# ---- 命令行入口 ---- #

def run_scheduled():
    """守护进程模式：每天早上 9:00 自动执行每日任务"""
    schedule.every().day.at("09:00").do(_scheduled_task)

    print("=" * 60)
    print("  定时任务调度器已启动")
    print("  每日执行时间: 09:00")
    print("  按 Ctrl+C 停止")
    print("=" * 60)

    while True:
        schedule.run_pending()
        time.sleep(60)


def _scheduled_task():
    """包装函数，捕获异常防止崩溃"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'=' * 60}")
    print(f"  ⏰ 定时任务触发: {timestamp}")
    print(f"{'=' * 60}")
    try:
        task = DailyTask()
        notes = task.run()
        print(f"  ✅ 完成，互动笔记: {len(notes)} 条")
    except Exception as e:
        print(f"  ❌ 任务异常: {e}")
        import traceback
        traceback.print_exc()


def run_daily():
    """运行一次完整每日任务"""
    task = DailyTask()
    notes = task.run()
    if notes:
        print(f"\n✅ 每日任务全部完成！共处理 {len(notes)} 条互动笔记")
    else:
        print("\n⚠️  本次没有互动数据")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python main.py --profile   生成用户画像")
        print("  python main.py --daily     运行一次完整每日任务")
        print("  python main.py --schedule  启动定时调度器（每天 9:00 自动运行）")
        return

    cmd = sys.argv[1]
    if cmd == "--profile":
        import signal
        success = False
        try:
            page = browser.init_browser()
            if browser.wait_for_login(page):
                feed_items = browser.collect_feed_items(page, count=FEED_COUNT_FOR_PROFILE)
                if len(feed_items) >= 10:
                    profile = analyzer.generate_profile(feed_items)
                    success = bool(profile)
        except Exception as e:
            print(f"❌ 异常: {e}")
        sys.exit(0 if success else 1)

    elif cmd == "--daily":
        run_daily()

    elif cmd == "--schedule":
        run_scheduled()

    else:
        print(f"未知命令: {cmd}")
        print("可用: --profile | --daily | --schedule")


if __name__ == "__main__":
    main()