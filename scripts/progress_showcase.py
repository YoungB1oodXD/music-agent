#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目进度展示脚本
- 模块 1：数据治理成果（基于统一后的 Parquet 与统计文件）
- 模块 2：知识库与语义检索（基于 BGE-M3 + ChromaDB 的 MusicSearcher）
- 模块 3：核心逻辑 SessionState（多轮对话状态管理）

使用方式：在项目根目录下运行
    python scripts/progress_showcase.py
"""

import sys
import os
import json

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# 将项目根目录加入路径，确保能导入 src 和 scripts
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# 尝试导入真实模块
try:
    # 1. 导入搜索器 (对应知识库构建)
    from src.searcher.music_searcher import MusicSearcher
    # 2. 导入会话状态 (对应核心逻辑)
    from src.manager.session_state import SessionState
except ImportError as e:
    print(f"环境路径配置有误，请确保在项目根目录下运行。错误: {e}")
    sys.exit(1)

console = Console()


def show_data_governance() -> None:
    """模块一：展示数据治理成果"""
    console.print(Panel("[bold green]1. 数据治理成果 (Data Governance)[/]", expand=False))

    parquet_path = os.path.join(PROJECT_ROOT, "data", "processed", "unified_songs_bge.parquet")
    summary_path = os.path.join(PROJECT_ROOT, "data", "processed", "data_summary.json")

    if os.path.exists(parquet_path):
        df = pd.read_parquet(parquet_path)

        table = Table(title="Unified Metadata Statistics (FMA + Last.fm)")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Total Tracks", f"{len(df):,}")
        table.add_row("Features", ", ".join(df.columns[:4]) + "...")
        table.add_row("Data Source", "FMA (Audio) + Last.fm (Behavior)")
        console.print(table)

        # 如果有 summary 文件，可以展示更多统计
        if os.path.exists(summary_path):
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary = json.load(f)
                console.print("\n[bold cyan][INFO] Data Summary from data_summary.json:[/]")
                for k, v in summary.items():
                    console.print(f"  - {k}: {v}")
            except Exception:
                pass

        console.print("\n[bold cyan][INFO] Previewing Aligned Data (Top 3):[/]")
        cols_to_show = [c for c in ["track_id", "title", "artist", "genre"] if c in df.columns]
        console.print(df[cols_to_show].head(3))

    else:
        console.print(f"[red]未找到数据文件: {parquet_path}[/]")


def show_knowledge_base() -> None:
    """模块二：展示知识库语义检索"""
    console.print(Panel("[bold blue]2. 知识库与语义检索 (Knowledge Base & Retrieval)[/]", expand=False))

    try:
        console.print("[dim]Loading BGE-M3 Index from 'index/chroma_bge_m3/'...[/]")

        # 初始化真实的搜索器（内部默认指向 index/chroma_bge_m3）
        searcher = MusicSearcher()

        query = "适合深夜写代码的安静后摇"
        console.print(f"[bold yellow]User Query:[/] '{query}'")

        results = searcher.search(query, top_k=3)

        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Rank")
        table.add_column("Similarity")
        table.add_column("Title")
        table.add_column("Artist")

        for idx, res in enumerate(results):
            if isinstance(res, dict):
                score = res.get("similarity") or (1.0 - res.get("distance", 0.0))
                title = str(res.get("title", "Unknown"))
                artist = str(res.get("artist", "Unknown"))
            else:
                # 兜底：直接转字符串
                score = getattr(res, "similarity", 0.0)
                title = str(res)
                artist = "-"

            table.add_row(str(idx + 1), f"{score:.4f}", title[:40], artist[:30])

        console.print(table)

    except Exception as e:
        console.print(f"[red]搜索演示失败 (可能是模型路径或环境问题): {e}[/]")
        console.print("[dim](Displaying mock results due to loading error)[/]")


def show_core_logic() -> None:
    """模块三：展示 Session Manager 核心逻辑"""
    console.print(Panel("[bold magenta]3. 核心逻辑: Session State (DST)[/]", expand=False))

    session = SessionState(session_id="DEMO_001", user_id="User_Lee")

    console.print(f"[bold]Initial State:[/] Mood={session.current_mood}, Scene={session.current_scene}")

    console.print("[dim]>> Simulating User Input: '我有点emo，想听点治愈的歌'[/dim]")

    session.update_mood("EMO")
    session.update_scene("Healing")

    table = Table(title="State Trace Log")
    table.add_column("Slot Name", style="green")
    table.add_column("Current Value", style="bold white")
    table.add_row("Session ID", session.session_id)
    table.add_row("Current Mood", str(session.current_mood))
    table.add_row("Current Scene", str(session.current_scene))
    table.add_row("History Len", str(len(session.dialogue_history)))

    console.print(table)
    console.print("[bold green]✔ Context Updated Successfully![/]")


if __name__ == "__main__":
    console.rule("[bold]Music Agent - Progress Showcase[/]")
    show_data_governance()
    show_knowledge_base()
    show_core_logic()
