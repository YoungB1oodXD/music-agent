#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from pathlib import Path

def main():
    # 确保输出使用 UTF-8，避免 Windows 编码问题
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            getattr(sys.stdout, "reconfigure")(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            getattr(sys.stderr, "reconfigure")(encoding="utf-8")

    project_root = Path(__file__).parent.absolute()
    chat_cli = project_root / "scripts" / "chat_cli.py"
    
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    
    if not api_key:
        print("mock mode", flush=True)
        cmd = [sys.executable, str(chat_cli), "--llm", "mock", "--once", "推荐点适合学习的歌"]
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)
    else:
        print("qwen mode", flush=True)
        cmd = [sys.executable, str(chat_cli), "--llm", "qwen", "--once", "推荐点适合学习的歌"]
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)

if __name__ == "__main__":
    main()
