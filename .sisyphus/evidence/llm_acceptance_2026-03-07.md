# LLM Integration Acceptance Report (Qwen / Bailian)

Date: 2026-03-07
Workspace: `E:\Workspace\music_agent`

This report captures evidence for the following acceptance commands (run in order):

1) `python -m compileall src scripts tests -q`
2) `python tests/dashscope_key_smoke.py`
3) `python tests/qwen_live_smoke.py`
4) `python scripts/chat_cli.py --llm qwen --once "推荐点适合学习的歌"`
5) `python scripts/replay_transcript.py --latest`

Evidence focus:
- `[LLM INIT]`
- `[LLM SUCCESS]`
- `[SESSION SUMMARY]`
- `llm_status=live`
- real Qwen response content
- proof of non-fallback

---

## 1) compileall

Command:

```bash
python -m compileall src scripts tests -q
```

Result: PASS

Evidence:
- Command completed without compilation errors.

Conclusion:
- Codebase is syntactically valid for `src/`, `scripts/`, and `tests/`.

---

## 2) DashScope key wiring smoke

Command:

```bash
python tests/dashscope_key_smoke.py
```

Result: PASS

Key evidence (excerpt):

```text
[LLM INIT]
provider=qwen
base_url=https://dashscope.aliyuncs.com/compatible-mode/v1
model=qwen3.5-plus
api_key_present=true
api_key_prefix=coding

OK: QwenClient reads DASHSCOPE_API_KEY as fallback
OK: DASHSCOPE_API_KEY_BAILIAN overrides DASHSCOPE_API_KEY
OK: Explicit api_key overrides both env vars
OK: Missing keys raise EnvironmentError naming both env vars
```

Conclusion:
- API key precedence works: explicit > `DASHSCOPE_API_KEY_BAILIAN` > `DASHSCOPE_API_KEY`.
- `[LLM INIT]` block is emitted and does not leak full API key.

---

## 3) Qwen live connectivity smoke

Command:

```bash
python tests/qwen_live_smoke.py
```

Result: PASS

Key evidence (excerpt):

```text
[LLM INIT]
provider=qwen
base_url=https://dashscope.aliyuncs.com/compatible-mode/v1
model=qwen3.5-plus
api_key_present=true
api_key_prefix=sk-77e63e

HTTP Request: POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions "HTTP/1.1 200 OK"

[LLM SUCCESS]
model=qwen3.5-plus
latency_ms=10992

Assistant response: ok
Result: SUCCESS
```

Conclusion:
- Confirms a real online call to Bailian OpenAI-compatible endpoint returns HTTP 200.
- `[LLM SUCCESS]` confirms non-fallback and records latency.

---

## 4) Chat CLI one-shot (qwen)

Command:

```bash
python scripts/chat_cli.py --llm qwen --once "推荐点适合学习的歌"
```

Result: PASS

Key evidence (excerpt):

```text
model=qwen session_id=f81cf620300a4793b07ce5c403c41a30

[LLM INIT]
provider=qwen
base_url=https://dashscope.aliyuncs.com/compatible-mode/v1
model=qwen3.5-plus
api_key_present=true
api_key_prefix=sk-77e63e

[LLM SUCCESS]
model=qwen3.5-plus
latency_ms=15653

[SESSION SUMMARY]
llm_status=live
recommendation_count=5
```

Proof of non-fallback:
- No `[WARN] LLM request failed, fallback to local recommendation pipeline.` line printed.
- Session summary shows `llm_status=live`.

Transcript evidence:
- File created: `data\sessions\f81cf620300a4793b07ce5c403c41a30.jsonl`
- Record includes `"llm_status": "live"`.

Conclusion:
- CLI runs end-to-end in Qwen mode.
- Transcript logging is working and records `llm_status`.

---

## 5) Replay latest transcript

Command:

```bash
python scripts/replay_transcript.py --latest
```

Result: PASS

Evidence:

```text
replay ok
```

Conclusion:
- Transcript format is parseable and replayable.

---

## Overall Acceptance Conclusion

Passed commands: 5/5

This evidence set proves:
- Real Qwen (Bailian) LLM calls succeed (HTTP 200 + `[LLM SUCCESS]`).
- System distinguishes live vs fallback (`llm_status=live`, fallback warning absent).
- CLI + transcript persistence + transcript replay are operational.

## Remaining / Next Suggested Work

- Recommended next step: Plan Reconcile against `E:\Workspace\music_agent\.sisyphus\plans\llm-integration-dev-plan.md` tasks 3-8 and Final Verification Wave (F1-F4).
