#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['KERAS_BACKEND'] = 'none'
os.environ['TF_USE_LEGACY_KERAS'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

import sys
from pathlib import Path
import uvicorn

def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]

def _add_project_root_to_syspath(project_root: Path) -> None:
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

def main():
    project_root = _project_root()
    _add_project_root_to_syspath(project_root)
    
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()
