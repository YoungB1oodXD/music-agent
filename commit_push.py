#!/usr/bin/env python3
import subprocess
import sys

def run_cmd(args, check=True):
    result = subprocess.run(args, capture_output=True, text=True)
    print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, file=sys.stderr, end='')
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result

# Add files
print("Staging files...")
run_cmd(['git', 'add', 
    '.sisyphus/evidence/llm_acceptance_2026-03-07.md',
    '.sisyphus/plans/llm-integration-dev-plan.md',
    'scripts/chat_cli.py',
    'src/llm/clients/qwen_openai_compat.py'
])

# Check status
print("\nStatus:")
run_cmd(['git', 'status', '--short'])

# Commit
print("\nCommitting...")
commit_msg = """feat: add LLM observability logs and Plan Reconcile

- Add [LLM INIT]/[LLM SUCCESS]/[LLM ERROR] tags with latency measurement
- Add [SESSION SUMMARY] with llm_status and recommendation_count
- Update .sisyphus/plans/llm-integration-dev-plan.md (mark tasks 3-8, F1-F4 done)
- Add acceptance evidence .sisyphus/evidence/llm_acceptance_2026-03-07.md

Ultraworked with Sisyphus
Co-authored-by: Sisyphus <clio-agent@sisyphuslabs.ai>"""

run_cmd(['git', 'commit', '-m', commit_msg])

# Push
print("\nPushing to origin/main...")
run_cmd(['git', 'push', 'origin', 'main'])

print("\nDone!")