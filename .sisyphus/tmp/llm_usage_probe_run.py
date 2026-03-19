#!/usr/bin/env python3


from __future__ import annotations

import importlib
import json
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
    if "tool_results" in last or "FINAL_RESPONSE_SCHEMA" in last or "rag_context" in last:
        return "final_response"
    if "INTENT_AND_SLOTS_SCHEMA" in last or ("recent_dialogues" in last and "state_summary" in last):
        return "intent_slots"
    return "unknown"


def main() -> None:
    os.environ["MUSIC_AGENT_LLM_MODE"] = "qwen"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    app_module = importlib.import_module("src.api.app")
    testclient_module = importlib.import_module("fastapi.testclient")
    TestClient = testclient_module.TestClient

    llm = app_module.ORCHESTRATOR.llm
    original_create = llm._create_completion

    records: list[dict[str, object]] = []
    current_chat_idx: int | None = None

    def wrapped_create_completion(*, messages, tools, temperature, max_tokens, stream):
        nonlocal records
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

        records.append(
            {
                "chat_idx": current_chat_idx,
                "phase": _label(messages),
                "latency_ms_wrapper": dt_ms,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "system_chars": system_chars,
                "history_chars": history_chars,
                "user_prompt_chars": user_prompt_chars,
            }
        )
        return completion

    llm._create_completion = wrapped_create_completion

    api = TestClient(app_module.app)
    turns = [
        "我想听适合学习的轻音乐",
        "我现在有点emo，想听安静一点的歌",
        "来点适合夜跑的高能量音乐",
    ]

    sid: str | None = None
    chat_summaries: list[dict[str, object]] = []

    for idx, msg in enumerate(turns, start=1):
        current_chat_idx = idx
        payload: dict[str, object] = {"message": msg}
        if sid:
            payload["session_id"] = sid

        t0 = time.perf_counter()
        resp = api.post("/chat", json=payload)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        data = resp.json()
        sid = data.get("session_id")
        recs = data.get("recommendations") or []

        chat_summaries.append(
            {
                "chat_idx": idx,
                "message": msg,
                "elapsed_ms": elapsed_ms,
                "status_code": resp.status_code,
                "recommendations_len": len(recs),
            }
        )

    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for rec in records:
        chat_idx = rec.get("chat_idx")
        if isinstance(chat_idx, int):
            grouped[chat_idx].append(rec)

    per_chat_summary: list[dict[str, object]] = []
    for chat_idx in sorted(grouped.keys()):
        items = grouped[chat_idx]
        phases: dict[str, int] = defaultdict(int)
        for item in items:
            phases[str(item.get("phase") or "unknown")] += 1
        per_chat_summary.append(
            {
                "chat_idx": chat_idx,
                "llm_completions": len(items),
                "phase_counts": dict(phases),
                "prompt_tokens_total": sum(int(x.get("prompt_tokens") or 0) for x in items),
                "completion_tokens_total": sum(int(x.get("completion_tokens") or 0) for x in items),
                "total_tokens_total": sum(int(x.get("total_tokens") or 0) for x in items),
            }
        )

    out = {
        "session_id": sid,
        "chat_summaries": chat_summaries,
        "llm_calls": records,
        "per_chat_summary": per_chat_summary,
    }

    output_path = Path(".sisyphus/tmp/llm_usage_probe.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output_path))


if __name__ == "__main__":
    main()
