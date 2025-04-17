import os
import sys
import uvicorn

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if __name__ == "__main__":
    # 启动FastAPI服务
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, app_dir="api") 