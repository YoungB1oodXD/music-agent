# Learnings - Vector Retrieval Quality
Append-only log of patterns, conventions, and successful approaches.
  
## Vector Retrieval Audit Script  
To run the vector retrieval audit script, use:  
```bash  
python scripts/vector_retrieval_audit.py --out .sisyphus/tmp/vector_retrieval_baseline.json  
```  
The script will output the path to the generated JSON file, which contains similarity metrics and document examples for the audit queries. 

## Query Expansion (2026-03-12)
Implemented low-risk bilingual query expansion in `src/tools/semantic_search_tool.py` to improve retrieval for Chinese scene/mood queries.
- Mapping:
  - 学习/复习/专注 -> "study learning focus"
  - 轻音乐/纯音乐/器乐 -> "instrumental calm ambient"
  - emo/难过/伤心/安静 -> "calm quiet sad"
  - 夜跑/跑步/运动/健身 -> "run runner running workout"
  - 高能量/动感/燃/节奏 -> "energy energetic upbeat"
  - 夜/深夜 -> "night"
- Constraints:
  - Substring detection (case-insensitive).
  - No duplicate expansions.
  - Capped at 12 extra words.
  - Append-only to original query.

## Non-Regressive Query Expansion (2026-03-12)
Implemented a non-regressive query expansion strategy in `src/tools/semantic_search_tool.py`.
- Strategy:
  - Run both the original query and the expanded query.
  - Merge results by item ID (using `_collect_result_ids`).
  - Keep the higher similarity for duplicate items.
  - Sort merged results by similarity descending.
- Benefits:
  - Preserves baseline retrieval quality while benefiting from bilingual cues.
  - Prevents regression in cases where the original query was more effective than the expanded one.
- Verification:
   - Audit results showed improvement in "night-run" query similarity (0.305 -> 0.318) while maintaining other results.

## Embedding Rich Text Format (2026-03-12)
Updated `scripts/data_processor_bge.py` (`DataMerger.build_rich_text`) to produce a richer bilingual, token-efficient `rich_text` for BGE indexing.
- Format:
  - English block: `Music track. Title: {title}. Artist: {artist}. Title: {title}. Artist: {artist}. Genre: {genre}. Tags: {tag1, tag2, ...}.`
  - Chinese KV block: `{CN_TITLE}: {title} | {CN_ARTIST}: {artist} | {CN_GENRE}: {genre} | {CN_TAGS}: {tag1, tag2, ...}`
- Weighting: repeat title and artist once in the English block.
- Tags:
  - Clean: keep non-empty strings only; normalize whitespace; lowercase; replace '_' with space; dedupe preserving order.
  - Cap: keep up to 10 tags; join comma-separated; omit tag fields entirely when empty.
- Length: clamp final `rich_text` to <= 320 characters.

## Patterns and Conventions  
- Always include '# -*- coding: utf-8 -*-' in Python files as a general repo convention. 
