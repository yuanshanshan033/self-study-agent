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
        # 新增：类别计数器（每个画像类别单独计数）
        self.category_counters = {}
        # 新增：总笔记计数器（用于收藏判断）
        self.total_notes_checked = 0

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

    def _get_first_note_title(self):
        """从当前发现页提取第一个可见笔记的标题"""
        try:
            # 小红书发现页笔记选择器
            note_items = self.page.eles(".note-item")
            if not note_items:
                # 尝试其他可能的选择器
                note_items = self.page.eles("[class*='note']")
            
            if not note_items:
                return None
                
            # 只取第一个笔记
            first_item = note_items[0]
            
            # 获取标题 - 尝试多种选择器
            title = ""
            try:
                title_ele = first_item.ele(".title", timeout=1)
                title = title_ele.text if title_ele else ""
            except:
                pass
            
            if not title.strip():
                try:
                    title_ele = first_item.ele(".footer .title", timeout=1)
                    title = title_ele.text if title_ele else ""
                except:
                    pass
            
            if not title.strip():
                try:
                    footer = first_item.ele(".footer", timeout=1)
                    if footer:
                        title = footer.text[:50]
                except:
                    pass

            if title.strip():
                return title.strip()
            
        except Exception as e:
            print(f"  ⚠️  获取笔记标题失败: {e}")
        return None

    def _find_note_by_title(self, title):
        """根据标题在当前页面重新查找笔记元素"""
        try:
            all_items = self.page.eles(".note-item")
            for item in all_items:
                try:
                    title_ele = item.ele(".title", timeout=1)
                    if title_ele and title in title_ele.text:
                        return item
                except:
                    pass
                # 尝试从footer找
                try:
                    footer = item.ele(".footer", timeout=1)
                    if footer and title in footer.text:
                        return item
                except:
                    pass
        except:
            pass
        return None

    def _handle_note_by_title(self, title):
        """处理单篇帖子：初判 → （不感兴趣就跳过） → 进详情 → 按规则互动"""
        if not title:
            return

        print(f"\n📌 帖子标题: {title[:50]}...")

        interest = analyzer.judge_interest(self.profile, title)
        if not interest.get("is_interested"):
            print(f"  ⌛ 不感兴趣 (评分:{interest.get('interest_score', 0)})，跳过")
            return

        # 获取匹配的画像类别
        matched_category = interest.get("matched_category", "其他")
        print(f"  ✅ 感兴趣 (类别:{matched_category})，进入详情页...")
        browser.human_pause(2.0, 5.0)

        # 每次点击前都重新查找元素（避免元素失效）
        click_target = self._find_note_by_title(title)
        if not click_target:
            print(f"  ⚠️  无法找到该笔记元素，可能已滚动出视图")
            return

        if not browser.click_note(self.page, click_target):
            print("  ⚠️  点击详情失败")
            return

        detail = browser.get_page_content(self.page)
        print(f"  详情文字: {detail['content'][:80]}..." if detail["content"] else "  无文字内容")
        print(f"  图片数量: {len(detail['images'])}")

        browser.human_pause(5.0, 12.0)

        # 更新计数器
        self.total_notes_checked += 1

        # 类别计数器：每个类别单独计数
        if matched_category not in self.category_counters:
            self.category_counters[matched_category] = 0
        self.category_counters[matched_category] += 1
        category_count = self.category_counters[matched_category]

        # 判断是否应该点赞（每3个同类笔记点赞一次）
        should_like = (category_count % 3 == 0)

        # 判断是否应该收藏（每5个笔记收藏一次）
        should_bookmark = (self.total_notes_checked % 5 == 0)

        print(f"  📊 类别计数:{category_count} | 总计数:{self.total_notes_checked}")
        print(f"  🎯 点赞规则:每3个同类笔记点赞一次 {'✅' if should_like else '⏳'}")
        print(f"  🎯 收藏规则:每5个笔记收藏一次 {'✅' if should_bookmark else '⏳'}")

        if not should_like:
            print("  ⌛ 未达到点赞条件，跳过")
            browser.close_detail(self.page)
            browser.human_pause(2.0, 5.0)
            return

        # 执行点赞
        print("  ❤️  执行点赞...")
        if browser.do_like(self.page):
            self.like_count += 1
            print(f"  点赞成功！今日已点赞: {self.like_count}/{MAX_DAILY_LIKES}")

        # 执行收藏（如果满足条件）
        bookmark_executed = False
        if should_bookmark:
            browser.human_pause(2.0, 4.0)
            print("  ⭐ 满足收藏条件，执行收藏...")
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
            "ai_reason": interest.get("reason", ""),
            "post_title": title,
            "matched_category": matched_category,
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

        processed_titles = set()  # 记录已处理的笔记标题，避免重复
        current_title = None  # 当前正在处理的笔记标题
        skip_count = 0  # 连续跳过同一笔记的次数

        while not self._is_limit_reached() and not self._is_time_up():
            # 只获取第一个可见笔记的标题
            title = self._get_first_note_title()

            if not title:
                # 没有获取到标题，滚动页面
                skip_count += 1
                if skip_count > 10:
                    print("⚠️  页面长时间无新内容，结束浏览")
                    break
                print("  📜 滚动页面寻找新笔记...")
                browser.human_scroll(self.page)
                browser.human_pause(2.0, 4.0)
                continue

            # 如果获取到的标题和当前标题一样，说明还在同一个笔记上
            # 需要滚动到下一个
            if title == current_title:
                skip_count += 1
                if skip_count > 5:
                    print(f"  ⏭️  该笔记已处理，滚动到下一个: {title[:30]}...")
                    browser.scroll_to_next_note(self.page)
                    skip_count = 0
                continue

            # 重置 skip_count
            skip_count = 0

            # 记录当前标题
            current_title = title

            # 检查是否已处理过（从详情页返回后，可能还是同一个笔记）
            if title in processed_titles:
                print(f"  ⏭️  该笔记已处理过，滚动到下一个: {title[:30]}...")
                browser.scroll_to_next_note(self.page)
                continue

            # 记录已处理
            processed_titles.add(title)

            # 处理这一篇笔记（进入详情页 → 分析 → 点赞/跳过 → 返回发现页）
            self._handle_note_by_title(title)

            # 显示进度
            items_remaining = MAX_DAILY_LIKES - self.like_count
            print(f"\n📊 进度: 点赞 {self.like_count}/{MAX_DAILY_LIKES} | "
                  f"收藏 {self.bookmark_count}/{MAX_DAILY_BOOKMARKS} | "
                  f"还需{items_remaining}个点赞或到时结束")

            # 返回发现页后，短暂休息继续处理下一个
            browser.human_pause(2.0, 4.0)

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