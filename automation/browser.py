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


def wait_for_login(page, check_interval=3):
    """等待用户手动登录"""
    print("=" * 50)
    print("请在浏览器中完成小红书登录（扫码/手机号均可）")
    print("登录成功后程序将自动继续...")
    print("=" * 50)

    logged = False
    retries = 0
    while not logged and retries < 120:
        try:
            url = page.url.lower()
            if "explore" in url or "recommend" in url:
                try:
                    login_modal = page.wait.ele_displayed(".login-container", timeout=1)
                    if login_modal is None:
                        logged = True
                except Exception:
                    logged = True
        except Exception:
            pass

        if not logged:
            retries += 1
            time.sleep(check_interval)

    if logged:
        print("✅ 登录检测成功，开始浏览...\n")
    else:
        print("⚠️  超时未检测到登录成功，请确认登录状态后重试")
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
    collected = []
    seen_titles = set()
    last_items_count = 0
    stale_count = 0

    while len(collected) < count:
        human_scroll(page)
        post_count = discover_post_count(page)
        if post_count == last_items_count:
            stale_count += 1
            if stale_count > 8:
                print("  ⚠️  页面内容不再更新，可能已到底")
                break
        else:
            stale_count = 0
        last_items_count = post_count

        try:
            note_items = page.eles(".note-item")
            if not note_items:
                continue
            for item in note_items:
                if len(collected) >= count:
                    break
                try:
                    title_ele = item.wait.ele_displayed(".title", timeout=1)
                    title = title_ele.text if title_ele else ""
                    if not title:
                        title_ele = item.wait.ele_displayed(".footer .title", timeout=1)
                        title = title_ele.text if title_ele else ""
                except Exception:
                    title = ""

                if not title.strip():
                    try:
                        title = item.attr("aria-label") or ""
                    except Exception:
                        title = ""

                if not title.strip():
                    continue
                if title.strip() in seen_titles:
                    continue

                seen_titles.add(title.strip())
                try:
                    cover_ele = item.wait.ele_displayed(".cover img", timeout=1)
                    cover_url = cover_ele.attr("src") if cover_ele else ""
                except Exception:
                    cover_url = ""

                collected.append({"title": title.strip(), "cover_url": cover_url})
                human_pause(1.0, 3.0)

        except Exception as e:
            print(f"  ⚠️  采集过程中出现异常: {e}")

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