# -*- coding: utf-8 -*-
"""
academic_core 配置与跨平台环境管理器
自动适配 Windows, macOS, Linux (Docker/CI) 环境
"""

import os
import sys
import shutil
from dotenv import load_dotenv

# 优先查找当前工作目录，其次查找 academic-core 根目录
pkg_root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(pkg_root_env):
    load_dotenv(pkg_root_env)
load_dotenv()

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MINERU_TOKEN = os.getenv("MINERU_TOKEN", "")


def find_chrome_executable() -> str:
    """
    跨平台自动寻找 Google Chrome / Microsoft Edge / Chromium 可执行文件路径
    优先级：环境变量 CHROME_PATH -> 系统 PATH 查找 -> 操作系统标准预设路径
    """
    custom = os.getenv("CHROME_PATH", "")
    if custom and os.path.exists(custom):
        return custom

    path_candidates = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "chrome",
        "msedge",
        "edge",
    ]
    for cmd in path_candidates:
        p = shutil.which(cmd)
        if p and os.path.exists(p):
            return p

    if sys.platform == "win32":
        win_candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        ]
        for c in win_candidates:
            if os.path.exists(c):
                return c
    elif sys.platform == "darwin":
        mac_candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for c in mac_candidates:
            if os.path.exists(c):
                return c
    else:
        linux_candidates = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
            "/usr/local/bin/chrome",
        ]
        for c in linux_candidates:
            if os.path.exists(c):
                return c

    return ""
