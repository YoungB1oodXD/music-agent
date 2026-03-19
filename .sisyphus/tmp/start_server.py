import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import sys
sys.path.insert(0, 'E:/Workspace/music_agent')

from src.api.app import app
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Music Recommender API Server")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000)