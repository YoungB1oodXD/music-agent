#!/usr/bin/env python3
import os
import sys
import json
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

project_root = 'E:/Workspace/music_agent'
sys.path.insert(0, project_root)

from src.tools.hybrid_recommend_tool import hybrid_recommend

q = "我想听适合学习的轻音乐"
seed = "Adelitas Way - Dirty Little Thing"

res = hybrid_recommend({
    'query_text': q,
    'seed_song_name': seed,
    'top_k': 10,
    'w_sem': 0.6,
    'w_cf': 0.4
})

items = res.get('data', []) if res.get('ok') else []
output = ['Detailed hybrid results:']
for i, item in enumerate(items):
    if isinstance(item, dict):
        sem = item.get('semantic_similarity')
        cf = item.get('cf_score')
        score = item.get('score')
        sources = item.get('sources', [])
        title = item.get('title', '')
        artist = item.get('artist', '')
        output.append(f'{i}: {artist} - {title}')
        output.append(f'   sem={sem}, cf={cf}, score={score:.4f}, sources={sources}')

result = '\n'.join(output)
print(result)