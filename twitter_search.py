#!/usr/bin/env python3
"""
Twitter 搜索功能模块
- 搜索关键字
- 搜索用户推文
- 搜索用户资料
"""

import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from chrome_utils import CDP_URL, ensure_chrome_cdp


# PaddleOCR 脚本路径
PADDLE_OCR_DIR = Path.home() / "paddle-ocr"

# 常用用户 (Albert 时间线上常见的人)
KNOWN_USERS = {
    # 格式: "昵称/备注": "username"
    # 可以随时添加
}

# 默认 viewport
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 4000


def run_paddle_ocr(image_path: str) -> str | None:
    """调用 PaddleOCR 识别图片"""
    try:
        result = subprocess.run(
            ["uv", "run", "python", "ocr.py", image_path],
            cwd=PADDLE_OCR_DIR,
            capture_output=True,
            text=True,
            timeout=60,
            env={
                **dict(__import__("os").environ),
                "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK": "True"
            }
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"❌ OCR 失败: {result.stderr}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"❌ OCR 错误: {e}", file=sys.stderr)
        return None


def search_keyword(
    query: str,
    filter_type: str = "top",
    scroll_times: int = 1,
    output_image: str | None = None,
    height: int = DEFAULT_HEIGHT,
) -> str | None:
    """
    搜索关键字
    
    Args:
        query: 搜索关键字
        filter_type: 过滤类型 (top/latest/people/photos/videos)
        scroll_times: 滚动次数
        output_image: 保存截图路径
        height: viewport 高度
    
    Returns:
        OCR 提取的文字
    """
    if not ensure_chrome_cdp():
        return None

    # 构建搜索 URL
    filter_map = {
        "top": "",
        "latest": "&f=live",
        "people": "&f=user",
        "photos": "&f=image",
        "videos": "&f=video",
    }
    filter_param = filter_map.get(filter_type, "")
    url = f"https://x.com/search?q={query}{filter_param}"

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"❌ 无法连接 CDP ({CDP_URL}): {e}", file=sys.stderr)
            return None

        context = browser.contexts[0]
        page = context.new_page()
        page.set_viewport_size({"width": DEFAULT_WIDTH, "height": height})

        try:
            print(f"🔍 搜索: {query} (类型: {filter_type})...", file=sys.stderr)
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 等待搜索结果
            try:
                page.wait_for_selector('[data-testid="tweet"], [data-testid="UserCell"]', timeout=30000)
            except PlaywrightTimeout:
                page.wait_for_selector('[data-testid="primaryColumn"]', timeout=10000)
            
            time.sleep(2)
            
            # 滚动加载更多
            for i in range(scroll_times):
                print(f"📜 滚动加载 ({i + 1}/{scroll_times})...", file=sys.stderr)
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(1.5)
            
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(0.5)
            
            # 截图
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                screenshot_path = f.name
            
            print("📸 截图中...", file=sys.stderr)
            page.screenshot(path=screenshot_path, full_page=False)
            
            if output_image:
                import shutil
                shutil.copy(screenshot_path, output_image)
                print(f"💾 截图已保存: {output_image}", file=sys.stderr)
            
            # OCR
            print("🔍 OCR 识别中...", file=sys.stderr)
            result = run_paddle_ocr(screenshot_path)
            Path(screenshot_path).unlink(missing_ok=True)
            
            if result:
                print("✅ 搜索完成", file=sys.stderr)
            return result

        except PlaywrightTimeout as e:
            print(f"❌ 超时: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"❌ 错误: {e}", file=sys.stderr)
            return None
        finally:
            page.close()


def search_user_tweets(
    username: str,
    filter_type: str = "tweets",
    scroll_times: int = 1,
    output_image: str | None = None,
    height: int = DEFAULT_HEIGHT,
) -> str | None:
    """
    查看某用户的推文
    
    Args:
        username: 用户名 (不带@)
        filter_type: tweets/replies/highlights/media/likes
        scroll_times: 滚动次数
        output_image: 保存截图路径
        height: viewport 高度
    
    Returns:
        OCR 提取的文字
    """
    if not ensure_chrome_cdp():
        return None

    # 检查是否是已知用户昵称
    if username in KNOWN_USERS:
        username = KNOWN_USERS[username]
    
    # 去掉可能的 @ 符号
    username = username.lstrip("@")

    # 构建 URL
    url_map = {
        "tweets": f"https://x.com/{username}",
        "replies": f"https://x.com/{username}/with_replies",
        "highlights": f"https://x.com/{username}/highlights",
        "media": f"https://x.com/{username}/media",
        "likes": f"https://x.com/{username}/likes",
    }
    url = url_map.get(filter_type, url_map["tweets"])

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"❌ 无法连接 CDP ({CDP_URL}): {e}", file=sys.stderr)
            return None

        context = browser.contexts[0]
        page = context.new_page()
        page.set_viewport_size({"width": DEFAULT_WIDTH, "height": height})

        try:
            print(f"👤 查看用户 @{username} 的 {filter_type}...", file=sys.stderr)
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 等待内容加载
            try:
                page.wait_for_selector('[data-testid="tweet"], [data-testid="primaryColumn"]', timeout=30000)
            except PlaywrightTimeout:
                pass
            
            time.sleep(2)
            
            # 滚动
            for i in range(scroll_times):
                print(f"📜 滚动加载 ({i + 1}/{scroll_times})...", file=sys.stderr)
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(1.5)
            
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(0.5)
            
            # 截图
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                screenshot_path = f.name
            
            print("📸 截图中...", file=sys.stderr)
            page.screenshot(path=screenshot_path, full_page=False)
            
            if output_image:
                import shutil
                shutil.copy(screenshot_path, output_image)
                print(f"💾 截图已保存: {output_image}", file=sys.stderr)
            
            # OCR
            print("🔍 OCR 识别中...", file=sys.stderr)
            result = run_paddle_ocr(screenshot_path)
            Path(screenshot_path).unlink(missing_ok=True)
            
            if result:
                print("✅ 完成", file=sys.stderr)
            return result

        except PlaywrightTimeout as e:
            print(f"❌ 超时: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"❌ 错误: {e}", file=sys.stderr)
            return None
        finally:
            page.close()


def get_user_profile(username: str) -> dict | None:
    """
    获取用户资料
    
    Returns:
        包含用户信息的字典，或 None
    """
    if not ensure_chrome_cdp():
        return None

    username = username.lstrip("@")
    if username in KNOWN_USERS:
        username = KNOWN_USERS[username]

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"❌ 无法连接 CDP ({CDP_URL}): {e}", file=sys.stderr)
            return None

        context = browser.contexts[0]
        page = context.new_page()

        try:
            print(f"👤 获取用户 @{username} 资料...", file=sys.stderr)
            page.goto(f"https://x.com/{username}", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector('[data-testid="primaryColumn"]', timeout=30000)
            time.sleep(2)

            profile = {"username": username}
            
            # 获取显示名
            try:
                name_elem = page.locator('[data-testid="UserName"] span').first
                profile["name"] = name_elem.text_content()
            except:
                pass
            
            # 获取简介
            try:
                bio_elem = page.locator('[data-testid="UserDescription"]')
                if bio_elem.count() > 0:
                    profile["bio"] = bio_elem.text_content()
            except:
                pass
            
            # 截图保存
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                screenshot_path = f.name
            page.screenshot(path=screenshot_path, full_page=False)
            
            # OCR 获取更多信息
            ocr_text = run_paddle_ocr(screenshot_path)
            Path(screenshot_path).unlink(missing_ok=True)
            
            if ocr_text:
                profile["ocr_text"] = ocr_text
            
            print("✅ 获取完成", file=sys.stderr)
            return profile

        except PlaywrightTimeout as e:
            print(f"❌ 超时: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"❌ 错误: {e}", file=sys.stderr)
            return None
        finally:
            page.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Twitter 搜索工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  twsearch "Claude AI"                   # 搜索关键字
  twsearch "Claude AI" -f latest         # 搜索最新
  twsearch -u elonmusk                   # 查看某用户推文
  twsearch -u elonmusk -t media          # 查看某用户媒体
  twsearch -p elonmusk                   # 获取用户资料

搜索过滤 (-f/--filter):
  top      热门 (默认)
  latest   最新
  people   用户
  photos   图片
  videos   视频

用户推文类型 (-t/--type):
  tweets     推文 (默认)
  replies    回复
  highlights 精选
  media      媒体
  likes      点赞
        """,
    )
    
    parser.add_argument("query", nargs="?", help="搜索关键字")
    parser.add_argument("-u", "--user", metavar="USERNAME", help="查看某用户推文")
    parser.add_argument("-p", "--profile", metavar="USERNAME", help="获取用户资料")
    parser.add_argument("-f", "--filter", choices=["top", "latest", "people", "photos", "videos"], default="top", help="搜索过滤类型")
    parser.add_argument("-t", "--type", choices=["tweets", "replies", "highlights", "media", "likes"], default="tweets", help="用户推文类型")
    parser.add_argument("-s", "--scroll", type=int, default=1, help="滚动次数")
    parser.add_argument("-i", "--image", metavar="FILE", help="保存截图")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="viewport 高度")

    args = parser.parse_args()

    # 获取用户资料
    if args.profile:
        profile = get_user_profile(args.profile)
        if profile:
            print(f"用户名: @{profile.get('username', 'N/A')}")
            print(f"显示名: {profile.get('name', 'N/A')}")
            print(f"简介: {profile.get('bio', 'N/A')}")
            if "ocr_text" in profile:
                print(f"\n--- 页面内容 ---\n{profile['ocr_text']}")
            sys.exit(0)
        else:
            sys.exit(1)

    # 查看用户推文
    if args.user:
        text = search_user_tweets(
            username=args.user,
            filter_type=args.type,
            scroll_times=args.scroll,
            output_image=args.image,
            height=args.height,
        )
        if text:
            print(text)
            sys.exit(0)
        else:
            sys.exit(1)

    # 搜索关键字
    if args.query:
        text = search_keyword(
            query=args.query,
            filter_type=args.filter,
            scroll_times=args.scroll,
            output_image=args.image,
            height=args.height,
        )
        if text:
            print(text)
            sys.exit(0)
        else:
            sys.exit(1)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
