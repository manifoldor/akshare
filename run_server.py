#!/usr/bin/env python3
"""Launcher script for AKShare MCP Server with virtualenv auto-detection."""

import os
import sys
from pathlib import Path

# 获取当前项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 检查本地是否有 .venv 虚拟环境并优先使用
venv_python = BASE_DIR / ".venv" / "bin" / "python3"
if venv_python.exists() and sys.executable != str(venv_python):
    # 重定向至虚拟环境解释器执行
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

# 将项目目录加入 sys.path
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    from akshare_mcp.server import main
    main()
