# Issues

Append-only. Track blockers, errors, and workarounds.

- 2026-03-04: `lsp_diagnostics` initially failed because `basedpyright-langserver` was missing; workaround was installing `basedpyright` via `python -m pip install basedpyright` before running diagnostics.
  
## Qwen Integration Issues (2026-03-06)  
- \`tests/qwen_live_smoke.py\` had a \`NameError\` due to missing \`json\` import when handling error responses.  
- \`scripts/chat_cli.py\` was blocking users who only had the Bailian key set, as it only checked for the Coding key. 
