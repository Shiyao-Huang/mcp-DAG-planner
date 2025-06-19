#!/usr/bin/env python3
"""
系统工具模块

此模块提供系统信息和环境检测功能，包括：
- get_system_info: 获取系统环境信息

版本: 1.0.0
"""

import json
import sys
import os
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

# 导入调试功能和环境检测函数
from ..debug import server_debug_log as debug_log


def is_wsl_environment() -> bool:
    """检测是否在WSL环境中运行"""
    try:
        if os.path.exists("/proc/version"):
            with open("/proc/version") as f:
                version_info = f.read().lower()
                if "microsoft" in version_info or "wsl" in version_info:
                    return True

        wsl_env_vars = ["WSL_DISTRO_NAME", "WSL_INTEROP", "WSLENV"]
        for env_var in wsl_env_vars:
            if os.getenv(env_var):
                return True

        wsl_paths = ["/mnt/c", "/mnt/d", "/proc/sys/fs/binfmt_misc/WSLInterop"]
        for path in wsl_paths:
            if os.path.exists(path):
                return True

    except Exception:
        pass

    return False


def is_remote_environment() -> bool:
    """检测是否在远程环境中运行"""
    # WSL不应被视为远程环境
    if is_wsl_environment():
        return False

    # 检查SSH连接指标
    ssh_env_vars = ["SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY"]
    for env_var in ssh_env_vars:
        if os.getenv(env_var):
            return True

    # 检查远程开发环境
    remote_env_vars = ["REMOTE_CONTAINERS", "CODESPACES"]
    for env_var in remote_env_vars:
        if os.getenv(env_var):
            return True

    # 检查Docker容器
    if os.path.exists("/.dockerenv"):
        return True

    # Windows远程桌面检查
    if sys.platform == "win32":
        session_name = os.getenv("SESSIONNAME", "")
        if session_name and "RDP" in session_name:
            return True

    # Linux无显示环境检查（但排除WSL）
    if (
        sys.platform.startswith("linux")
        and not os.getenv("DISPLAY")
        and not is_wsl_environment()
    ):
        return True

    return False


async def get_system_info(mcp: FastMCP) -> str:
    """
    获取系统环境资讯

    Returns:
        str: JSON 格式的系统资讯
    """
    is_remote = is_remote_environment()
    is_wsl = is_wsl_environment()

    system_info = {
        "平台": sys.platform,
        "Python 版本": sys.version.split()[0],
        "WSL 環境": is_wsl,
        "遠端環境": is_remote,
        "介面類型": "Web UI",
        "環境變數": {
            "SSH_CONNECTION": os.getenv("SSH_CONNECTION"),
            "SSH_CLIENT": os.getenv("SSH_CLIENT"),
            "DISPLAY": os.getenv("DISPLAY"),
            "VSCODE_INJECTION": os.getenv("VSCODE_INJECTION"),
            "SESSIONNAME": os.getenv("SESSIONNAME"),
            "WSL_DISTRO_NAME": os.getenv("WSL_DISTRO_NAME"),
            "WSL_INTEROP": os.getenv("WSL_INTEROP"),
            "WSLENV": os.getenv("WSLENV"),
        },
        "Python執行器": sys.executable,
        "當前工作目錄": os.getcwd(),
        "用戶主目錄": os.path.expanduser("~"),
        "系統架構": os.uname() if hasattr(os, 'uname') else "Unknown"
    }

    debug_log(f"系統資訊查詢完成 - 平台: {sys.platform}, WSL: {is_wsl}, 遠端: {is_remote}")
    return json.dumps(system_info, ensure_ascii=False, indent=2) 