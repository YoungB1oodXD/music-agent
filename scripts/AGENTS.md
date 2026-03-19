# AGENTS.md — Scripts (Entry Points)

## OVERVIEW

22 standalone scripts for training, evaluation, CLI, and API serving. All have `if __name__ == "__main__"` blocks.

## WHERE TO LOOK

| Script | Purpose |
|--------|---------|
| `train_cf.py` | Train ALS collaborative filtering model |
| `vectorizer_bge.py` | Build ChromaDB index from embeddings |
| `chat_cli.py` | Interactive chat CLI — `--llm {mock,qwen}` |
| `run_api.py` | Launch FastAPI server (uvicorn) |
| `eval_model.py` | Model evaluation metrics |
| `data_processor_bge.py` | Process FMA data for embedding |

## CONVENTIONS

- **sys.path injection**: `sys.path.insert(0, repo_root)` before `from src.*`
- **Argparse**: CLI scripts use argparse for flags
- **Logging**: `logging.basicConfig()` at module level

## CLI EXAMPLES

```bash
python scripts/chat_cli.py --llm mock
python scripts/chat_cli.py --llm qwen --once "推荐适合学习的歌"
python scripts/run_api.py  # Starts on port 8000
```

## KNOWN ISSUES

- `run_hybrid_pipeline.py` — references missing `cleanup.py`, interactive prompt
- `run_demo_qwen.ps1` — Windows-only, port mismatch (5173 vs 3000)