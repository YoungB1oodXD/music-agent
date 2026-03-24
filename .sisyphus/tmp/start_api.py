import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)

import sys
sys.path.insert(0, 'E:/Workspace/music_agent')

import uvicorn

print('=' * 60)
print('Starting Music Agent API Server')
print('=' * 60)

uvicorn.run('src.api.app:app', host='127.0.0.1', port=8000)