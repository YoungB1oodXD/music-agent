#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import importlib
import json
import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

def _label(messages: list[dict[str, object]]) -> str:
    for msg in messages:
        if str(msg.get("content") or "").strip() == "repair JSON only":
            return "json_repair"

    last = str(messages[-1].get("content") or "") if messages else ""
    if "FINAL_RESPONSE_SCHEMA" in last or "rag_context" in last:
        return "final_response"
    if "INTENT_AND_SLOTS_SCHEMA" in last:
        return "intent_slots"
    return "unknown"

def parse_citations(citations: list[str]) -> dict[str, float]:
    scores = {}
    for c in citations:
        if "=" in c:
            parts = c.split("=", 1)
            if len(parts) == 2:
                key, val = parts
                try:
                    val_clean = val.strip().split(",")[0]
                    scores[key.strip()] = float(val_clean)
                except ValueError:
                    pass
    return scores

def get_stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "min": 0, "p50": 0, "p95": 0, "max": 0}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    return {
        "count": n,
        "min": round(sorted_vals[0], 4),
        "p50": round(sorted_vals[int(n * 0.5)], 4),
        "p95": round(sorted_vals[int(n * 0.95)], 4) if n > 0 else 0,
        "max": round(sorted_vals[-1], 4),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default=".sisyphus/tmp/llm_opt_benchmark.json")
    args = parser.parse_args()

    os.environ["MUSIC_AGENT_LLM_MODE"] = "qwen"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    logging.getLogger().setLevel(logging.ERROR)
    for name in ["httpx", "openai", "src.llm.clients.qwen_openai_compat", "src.searcher.music_searcher", "src.agent.orchestrator"]:
        logging.getLogger(name).setLevel(logging.ERROR)

    try:
        app_module = importlib.import_module("src.api.app")
        from fastapi.testclient import TestClient
    except ImportError:
        sys.exit(1)
    
    logging.getLogger().setLevel(logging.ERROR)

    llm = app_module.ORCHESTRATOR.llm
    llm.timeout = 180.0
    original_create = llm._create_completion

    llm_records = []
    current_chat_idx = None

    def wrapped_create_completion(*, messages, tools, temperature, max_tokens, stream):
        t0 = time.perf_counter()
        completion = original_create(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )
        dt_ms = int((time.perf_counter() - t0) * 1000)
        usage = completion.get("usage") or {}
        
        def _len(val: object) -> int:
            return len(str(val or ""))

        system_chars = _len(messages[0].get("content")) if messages else 0
        history_chars = sum(_len(x.get("content")) for x in messages[1:-1]) if len(messages) > 2 else 0
        user_prompt_chars = _len(messages[-1].get("content")) if messages else 0

        llm_records.append({
            "chat_idx": current_chat_idx,
            "phase": _label(messages),
            "latency_ms": dt_ms,
            "prompt_tokens": usage.get("prompt_tokens") or 0,
            "completion_tokens": usage.get("completion_tokens") or 0,
            "total_tokens": usage.get("total_tokens") or 0,
            "system_chars": system_chars,
            "history_chars": history_chars,
            "user_prompt_chars": user_prompt_chars,
        })
        return completion

    llm._create_completion = wrapped_create_completion

    client = TestClient(app_module.app)
    queries = [
        "我想听适合学习的轻音乐",
        "我现在有点emo，想听安静一点的歌",
        "来点适合夜跑的高能量音乐",
    ]

    session_id = None
    chats = []
    all_scores = defaultdict(list)

    for idx, query in enumerate(queries, start=1):
        current_chat_idx = idx
        payload = {"message": query}
        if session_id:
            payload["session_id"] = session_id

        t0 = time.perf_counter()
        resp = client.post("/chat", json=payload)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        if resp.status_code != 200:
            chats.append({
                "chat_idx": idx,
                "query": query,
                "status_code": resp.status_code,
                "error": resp.text,
                "elapsed_ms": elapsed_ms,
            })
            continue

        data = resp.json()
        session_id = data.get("session_id")
        recs = data.get("recommendations") or []
        
        for r in recs:
            citations = r.get("citations") or []
            parsed = parse_citations(citations)
            for k, v in parsed.items():
                all_scores[k].append(v)

        chats.append({
            "chat_idx": idx,
            "query": query,
            "status_code": resp.status_code,
            "elapsed_ms": elapsed_ms,
            "assistant_text_prefix": data.get("assistant_text", "")[:100],
            "top_5_recs": [
                {"id": r.get("id"), "name": r.get("name")}
                for r in recs[:5]
            ]
        })

    per_chat_summary = []
    for idx in range(1, len(queries) + 1):
        calls = [c for c in llm_records if c["chat_idx"] == idx]
        phase_counts = defaultdict(int)
        for c in calls:
            phase_counts[c["phase"]] += 1
        
        per_chat_summary.append({
            "chat_idx": idx,
            "llm_completions": len(calls),
            "phase_counts": dict(phase_counts),
            "prompt_tokens_total": sum(c["prompt_tokens"] for c in calls),
            "completion_tokens_total": sum(c["completion_tokens"] for c in calls),
            "total_tokens_total": sum(c["total_tokens"] for c in calls),
            "system_chars_total": sum(c["system_chars"] for c in calls),
            "history_chars_total": sum(c["history_chars"] for c in calls),
            "user_prompt_chars_total": sum(c["user_prompt_chars"] for c in calls),
        })

    citation_stats = {k: get_stats(v) for k, v in all_scores.items()}

    final_output = {
        "metadata": {
            "llm_mode": "qwen",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "chats": chats,
        "llm_calls": llm_records,
        "per_chat_summary": per_chat_summary,
        "citation_stats": citation_stats,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(final_output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))

if __name__ == "__main__":
    main()
