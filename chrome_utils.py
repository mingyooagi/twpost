#!/usr/bin/env python3
"""Chrome CDP utilities for browser automation."""

import os
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path


CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
XVFB_DISPLAY = ":99"


def find_chrome() -> str | None:
    """Find Chrome executable path across platforms."""
    if platform.system() == "Darwin":
        mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if Path(mac_path).exists():
            return mac_path
    # Linux / fallback
    for name in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
        if shutil.which(name):
            return name
    return None


def wake_screen() -> bool:
    """Wake up the screen if it's in power saving mode.
    
    This helps with performance - screens in DPMS off mode can cause
    browser operations to be slow.
    """
    try:
        # Check if screen is on
        result = subprocess.run(
            ["xset", "q"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if "Monitor is Off" in result.stdout:
            print("🖥️ 屏幕未亮，正在唤醒...")
            # Wake the screen with mouse movement and key press
            subprocess.run(["xdotool", "mousemove_relative", "1", "1"], capture_output=True, timeout=2)
            subprocess.run(["xdotool", "mousemove_relative", "--", "-1", "-1"], capture_output=True, timeout=2)
            subprocess.run(["xdotool", "key", "shift"], capture_output=True, timeout=2)
            time.sleep(0.5)
            print("✅ 屏幕已唤醒")
            return True
        return True
    except Exception as e:
        # Don't fail if we can't check - might be headless
        print(f"⚠️ 无法检查屏幕状态: {e}")
        return True


def is_port_open(port: int) -> bool:
    """Check if a port is open."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def has_real_display() -> bool:
    """Check if a real (non-virtual) display is available."""
    display = os.environ.get("DISPLAY", "")
    # Skip if it's our Xvfb display
    if display == XVFB_DISPLAY:
        return False
    if not display:
        return False
    # Try to verify the display is actually working
    result = subprocess.run(
        ["xdpyinfo"],
        capture_output=True,
        env={**os.environ, "DISPLAY": display},
        timeout=2
    )
    return result.returncode == 0


def ensure_xvfb() -> bool:
    """Ensure Xvfb is running for headless display."""
    # Check if Xvfb is already running on our display
    result = subprocess.run(["pgrep", "-f", f"Xvfb {XVFB_DISPLAY}"], capture_output=True)
    if result.returncode == 0:
        os.environ["DISPLAY"] = XVFB_DISPLAY
        return True

    print(f"启动 Xvfb 虚拟显示器 {XVFB_DISPLAY}...")
    subprocess.Popen(
        ["Xvfb", XVFB_DISPLAY, "-screen", "0", "1920x1080x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)
    os.environ["DISPLAY"] = XVFB_DISPLAY
    return True


def ensure_chrome_cdp() -> bool:
    """Ensure Chrome is running with CDP enabled."""
    if is_port_open(CDP_PORT):
        return True

    chrome_bin = find_chrome()
    if not chrome_bin:
        print("❌ 未找到 Chrome，请先安装 Google Chrome")
        return False

    is_mac = platform.system() == "Darwin"

    if is_mac:
        # macOS: no display management needed
        display = None
    else:
        # Linux: wake screen, manage display
        wake_screen()
        if has_real_display():
            display = os.environ.get("DISPLAY")
            print(f"检测到真实显示器 {display}，使用物理屏幕")
        else:
            if not ensure_xvfb():
                print("无法启动虚拟显示器")
                return False
            display = XVFB_DISPLAY
            print(f"未检测到真实显示器，使用虚拟显示器 {display}")

    print(f"CDP 端口 {CDP_PORT} 未开启，正在启动 Chrome...")

    # Kill existing Chrome processes
    if is_mac:
        subprocess.run(["pkill", "-9", "-f", "Google Chrome"], capture_output=True)
    else:
        subprocess.run(["pkill", "-9", "-f", "google-chrome"], capture_output=True)
    time.sleep(2)

    # Start Chrome with CDP using dedicated profile
    chrome_data_dir = Path.home() / ".chrome_bot"
    # Clean up stale lock file left after force kill
    singleton_lock = chrome_data_dir / "SingletonLock"
    singleton_lock.unlink(missing_ok=True)
    headless_mode = os.environ.get("CHROME_HEADLESS", "").lower() in ("1", "true", "yes")
    chrome_args = [
        chrome_bin,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={chrome_data_dir}",
    ]
    if headless_mode or (display == XVFB_DISPLAY):
        chrome_args.append("--headless=new")
        print("🔇 使用 Chrome headless 模式")

    env = {**os.environ}
    if display:
        env["DISPLAY"] = display

    subprocess.Popen(
        chrome_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )

    # Wait for CDP to be ready
    for _ in range(5):
        time.sleep(1)
        if is_port_open(CDP_PORT):
            print("Chrome CDP 已就绪")
            time.sleep(2)  # Extra wait for full initialization
            return True

    print("Chrome 启动超时")
    return False


if __name__ == "__main__":
    import sys
    success = ensure_chrome_cdp()
    sys.exit(0 if success else 1)
