## Qwen Real-Mode Smoke Suite Issues
- Encountered `UnicodeEncodeError` when printing emojis/special characters to the Windows console in the logging handler.
- The `/chat` endpoint can be slow due to multiple LLM calls and tool executions, requiring a longer timeout (e.g., 5 minutes).
