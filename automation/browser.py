import random
import time
import math
from DrissionPage import ChromiumPage, ChromiumOptions
from config import MAX_BROWSING_MINUTES, FEED_COUNT_FOR_PROFILE

XHS_DISCOVER_URL = "https://www.xiaohongshu.com/explore"


def _bezier_path(start_x, start_y, end_x, end_y, steps=30):
    """生成三次贝塞尔曲线路径点"""
    cp1_x = start_x + (end_x - start_x) * random.uniform(0.2, 0.5)
    cp1_y = start_y + (end_y - start_y) * random.uniform(-0.1, 0.3)
    cp2_x = start_x + (end_x - start_x) * random.uniform(0.5, 0.8)
    cp2_y = start_y + (end_y - start_y) * random.uniform(0.7, 1.1)
    points = []
    for i in range(steps + 1):
        t = i / steps
        x = ((1 - t) ** 3) * start_x + 3 * ((1 - t) ** 2) * t * cp1_x + 3 * (1 - t) * (t ** 2) * cp2_x + (t ** 3) * end_x
        y = ((1 - t) ** 3) * start_y + 3 * ((1 - t) ** 2) * t * cp1_y + 3 * (1 - t) * (t ** 2) * cp2_y + (t ** 3) * end_y
        points.append((int(x), int(y)))
    return points


def human_pause(min_sec=1.0, max_sec=3.0):
    """随机时长暂停，模拟阅读停顿"""
    duration = random.uniform(min_sec, max_sec)
    time.sleep(duration)


def human_scroll(page):
    """拟人化滚动：随机距离 + 随机停顿 + 概率回滚"""
    scroll_distance = random.randint(300, 800)
    jitter = random.randint(-50, 50)
    final_distance = scroll_distance + jitter

    page.scroll.down(final_distance)
    human_pause(2.0, 6.0)

    if random.random() < 0.1:
        back_distance = random.randint(80, 200)
        page.scroll.up(back_distance)
        human_pause(0.5, 1.5)


def human_mouse_move(page, target_x, target_y):
    """贝塞尔曲线移动鼠标到目标坐标"""
    current_pos = page.actions.move_to
    try:
        rect = page.run_script("return {x: window.scrollX, y: window.scrollY}")
        start_x = random.randint(100, 500)
        start_y = random.randint(100, 400)
    except Exception:
        start_x = random.randint(100, 500)
        start_y = random.randint(100, 400)

    raw_points = _bezier_path(start_x, start_y, target_x, target_y, steps=random.randint(20, 35))
    total_steps = len(raw_points)
    for i, (px, py) in enumerate(raw_points):
        progress = i / total_steps
        speed_factor = 1.0 + math.sin(progress * math.pi) * 0.5
        page.actions.move_to(px, py)
        delay = (0.008 + random.uniform(0, 0.012)) / speed_factor
        time.sleep(delay)


def human_click(page, selector_or_element):
    """拟人化点击"""
    try:
        if isinstance(selector_or_element, str):
            ele = page.wait.ele_displayed(selector_or_element, timeout=3)
        else:
            ele = selector_or_element
        if ele is None:
            return False
        rect = ele.rect.bounding
        target_x = rect.midpoint[0] + random.randint(-3, 3)
        target_y = rect.midpoint[1] + random.randint(-3, 3)
        human_mouse_move(page, target_x, target_y)
        human_pause(0.3, 0.8)
        ele.click()
        return True
    except Exception:
        return False


def take_break(min_sec=30, max_sec=90):
    """模拟长时间休息"""
    duration = random.randint(min_sec, max_sec)
    print(f"  [休息] 暂停 {duration} 秒...")
    time.sleep(duration)


def batch_rest(post_count, batch_size_low=8, batch_size_high=12):
    """浏览批次之间的休息"""
    if post_count == 0:
        return
    batch_check = random.randint(batch_size_low, batch_size_high)
    if post_count % batch_check == 0:
        take_break(30, 90)


def init_browser():
    """初始化浏览器，配置反检测参数"""
    co = ChromiumOptions()
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-blink-features=AutomationControlled")
    co.set_pref("excludeSwitches", ["enable-automation"])
    co.set_pref("useAutomationExtension", False)
    page = ChromiumPage(co)
    page.get(XHS_DISCOVER_URL)
    return page


def wait_for_login(page, check_interval=3, max_wait_minutes=15):
    """等待用户手动登录，支持自动检测和随时手动确认"""
    print("=" * 50)
    print("请在浏览器中完成小红书登录（扫码/手机号均可）")
    print("登录成功后程序将自动继续...")
    print("提示：按回车后输入 y 可手动确认登录（15分钟内）")
    print("=" * 50)

    logged = False
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    last_prompt_time = 0

    while not logged:
        # 检查是否超时
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            print("\n⚠️  等待超时（15分钟），请重新运行程序")
            break

        # 检查自动检测条件（方法1或方法4满足其一即可）
        try:
            url = page.url.lower()
            if "explore" in url or "recommend" in url:
                # 检测方法1：检查登录弹窗是否消失
                try:
                    login_modal = page.wait.ele_displayed(".login-container", timeout=1)
                    if login_modal is None:
                        logged = True
                        print("✅ 检测方式1：登录弹窗已消失")
                except Exception:
                    pass

                # 检测方法4：检查左侧登录按钮消失 + 用户头像/"我"出现
                if not logged:
                    try:
                        login_btn = page.ele("text=登录", timeout=1)
                        has_login_btn = login_btn is not None
                    except Exception:
                        has_login_btn = False

                    try:
                        user_avatar = page.ele(".avatar", timeout=1) or page.ele("[class*='avatar']", timeout=1)
                        has_user_avatar = user_avatar is not None
                    except Exception:
                        has_user_avatar = False

                    try:
                        me_text = page.ele("text=我", timeout=1)
                        has_me_text = me_text is not None
                    except Exception:
                        has_me_text = False

                    if not has_login_btn and (has_user_avatar or has_me_text):
                        logged = True
                        print(f"✅ 检测方式4：登录按钮消失，检测到用户标识")
        except Exception:
            pass

        if logged:
            break

        # 每10秒提示一次
        if int(elapsed) - last_prompt_time >= 10:
            print(f"⏳ 已等待 {int(elapsed)} 秒，按回车输入 y 确认登录")
            last_prompt_time = int(elapsed)

        # 使用select实现非阻塞输入检查
        try:
            import select
            import sys
            # 检查是否有输入（等待1秒）
            ready, _, _ = select.select([sys.stdin], [], [], 1)
            if ready:
                user_input = sys.stdin.readline().strip().lower()
                if user_input in ['y', 'yes']:
                    logged = True
                    print("✅ 手动确认登录成功")
                    break
                elif user_input in ['n', 'no']:
                    print("❌ 登录确认失败")
                    return False
        except (ImportError, Exception):
            # 如果不支持select，使用普通sleep
            time.sleep(check_interval)

    if logged:
        print("✅ 登录检测成功，开始生成用户画像...")
        print("⏱️  将在15分钟内爬取50篇笔记\n")
    return logged


def discover_post_count(page):
    """统计发现页当前已加载的帖子数量"""
    try:
        items = page.wait.eles_displayed(".note-item", timeout=2)
        if items is None:
            items = page.eles(".note-item")
        return len(items) if items else 0
    except Exception:
        return 0


def collect_feed_items(page, count=FEED_COUNT_FOR_PROFILE):
    """
    在发现页拟人化滚动浏览，采集帖子的标题和封面信息
    返回: [{title, cover_url}, ...]
    """
    print(f"📋 开始采集 {count} 篇帖子的标题和封面信息...")
    print("  [模拟浏览] 提示：请勿手动滚动，程序将自动模拟滚动浏览...")
    collected = []
    seen_titles = set()
    last_items_count = 0
    stale_count = 0
    max_scroll_attempts = 50
    scroll_attempts = 0

    while len(collected) < count and scroll_attempts < max_scroll_attempts:
        human_scroll(page)
        scroll_attempts += 1
        human_pause(1.0, 2.0)

        post_count = discover_post_count(page)
        print(f"  📊 当前页面帖子数: {post_count}, 已采集: {len(collected)}")

        if post_count == last_items_count:
            stale_count += 1
            if stale_count > 5:
                print("  ⚠️  页面内容不再更新，可能已到底")
                break
        else:
            stale_count = 0
        last_items_count = post_count

        try:
            note_items = page.eles(".note-item")
            if not note_items:
                print("  ⚠️  未找到 .note-item 元素，尝试其他选择器...")
                note_items = page.eles('div[data-v-]') or page.eles('a[href*="/explore/"]')

            if not note_items:
                print("  ⚠️  仍未找到笔记元素，继续滚动...")
                continue

            print(f"  📝 找到 {len(note_items)} 个笔记元素")

            for item in note_items:
                if len(collected) >= count:
                    break

                title = ""

                if not title:
                    try:
                        footer = item.ele(".footer", timeout=1)
                        if footer:
                            title = footer.text.strip()
                    except Exception:
                        pass

                if not title:
                    try:
                        title = item.attr("aria-label") or ""
                    except Exception:
                        pass

                if not title:
                    try:
                        spans = item.eles("span")
                        for span in spans:
                            text = span.text.strip()
                            if text and len(text) > 5:
                                title = text
                                break
                    except Exception:
                        pass

                if not title.strip():
                    continue
                if title.strip() in seen_titles:
                    continue

                seen_titles.add(title.strip())

                cover_url = ""
                try:
                    cover_ele = item.ele(".cover img", timeout=1)
                    if cover_ele:
                        cover_url = cover_ele.attr("src") or ""
                except Exception:
                    pass

                collected.append({"title": title.strip(), "cover_url": cover_url})
                print(f"  ✅ 采集第 {len(collected)} 条: {title.strip()[:30]}...")
                human_pause(0.5, 1.5)

        except Exception as e:
            print(f"  ⚠️  采集过程中出现异常: {e}")
            import traceback
            traceback.print_exc()

        if len(collected) < count:
            batch_rest(len(collected))

    print(f"✅ 采集完成，共获取 {len(collected)} 条帖子信息")
    return collected[:count]


def get_page_content(page):
    """提取当前详情页的完整内容"""
    title = ""
    content = ""
    images = []
    url = page.url

    try:
        title_ele = page.wait.ele_displayed("#detail-title", timeout=2)
        title = title_ele.text if title_ele else ""
    except Exception:
        pass

    if not title:
        try:
            title_ele = page.wait.ele_displayed(".info .title", timeout=2)
            title = title_ele.text if title_ele else ""
        except Exception:
            pass

    try:
        content_ele = page.wait.ele_displayed("#detail-desc", timeout=2)
        content = content_ele.text if content_ele else ""
    except Exception:
        pass

    if not content:
        try:
            content_ele = page.wait.ele_displayed(".desc", timeout=2)
            content = content_ele.text if content_ele else ""
        except Exception:
            content = ""

    try:
        img_eles = page.eles(".swiper-slide img")
        if not img_eles:
            img_eles = page.eles(".note-image img")
        if img_eles:
            for img in img_eles[:6]:
                src = img.attr("src") or img.attr("data-src") or ""
                if src:
                    images.append(src)
    except Exception:
        pass

    if not images:
        try:
            all_imgs = page.eles("img")
            for img in all_imgs:
                src = img.attr("src") or ""
                if src and ("xhslink" in src or "pic" in src.lower() or "image" in src.lower()):
                    images.append(src)
                    if len(images) >= 6:
                        break
        except Exception:
            pass

    return {
        "title": title,
        "content": content,
        "images": images,
        "url": url,
    }


def click_note(page, note_element):
    """点击帖子进入详情页"""
    try:
        human_click(page, note_element)
        human_pause(2.0, 4.0)
        page.wait.load_complete(timeout=5)
        return True
    except Exception as e:
        print(f"  ⚠️  点击笔记失败: {e}")
        return False


def close_detail(page):
    """关闭详情页返回发现页"""
    try:
        close_btn = page.wait.ele_displayed(".close-button", timeout=2)
        if not close_btn:
            close_btn = page.wait.ele_displayed(".close .close-icon", timeout=2)
        if close_btn:
            human_click(page, close_btn)
            human_pause(1.0, 2.0)
            return True
    except Exception:
        pass

    try:
        overlay = page.wait.ele_displayed(".note-scroller .close", timeout=1)
        if overlay:
            human_click(page, overlay)
            human_pause(1.0, 2.0)
            return True
    except Exception:
        pass

    page.back()
    human_pause(1.5, 3.0)
    return True


def do_like(page):
    """拟人化点击点赞按钮"""
    selectors = [
        ".interaction .like-btn",
        ".interaction .like-wrapper",
        ".like-lottie",
        ".like-wrapper",
    ]
    for sel in selectors:
        try:
            btn = page.wait.ele_displayed(sel, timeout=2)
            if btn:
                human_click(page, btn)
                human_pause(1.0, 3.0)
                return True
        except Exception:
            continue
    print("  ⚠️  未找到点赞按钮")
    return False


def do_bookmark(page):
    """拟人化点击收藏按钮"""
    selectors = [
        ".interact .collect",
        ".interaction .collect-btn",
        ".collect-wrapper",
    ]
    for sel in selectors:
        try:
            btn = page.wait.ele_displayed(sel, timeout=2)
            if btn:
                human_click(page, btn)
                human_pause(1.0, 3.0)
                return True
        except Exception:
            continue
    print("  ⚠️  未找到收藏按钮")
    return False