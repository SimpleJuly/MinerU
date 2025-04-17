"""
MinerU API 模块 - 纯CPU模式
"""
import os

# 强制使用CPU模式
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["OMP_NUM_THREADS"] = "1"

# 从api.py导入FastAPI应用
from .api import app 