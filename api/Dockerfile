# 基于项目已有的全局Docker镜像
FROM ubuntu:22.04

# 设置非交互式环境变量以避免在安装过程中出现提示
ENV DEBIAN_FRONTEND=noninteractive

# 设置环境变量，强制使用CPU模式
ENV CUDA_VISIBLE_DEVICES=
ENV OMP_NUM_THREADS=1
ENV OMP_WAIT_POLICY=PASSIVE
ENV OMP_PROC_BIND=FALSE
ENV OMP_DYNAMIC=FALSE
ENV OMP_PLACES=CORES
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=DEBUG

# 更新包列表并安装必要的包
RUN apt-get update && \
    apt-get install -y \
        software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
        python3.10 \
        python3.10-venv \
        python3.10-distutils \
        python3-pip \
        wget \
        git \
        libgl1 \
        libglib2.0-0 \
        curl \
        && rm -rf /var/lib/apt/lists/*

# 设置Python 3.10为默认python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# 创建工作目录
WORKDIR /app

# 创建工作目录结构
RUN mkdir -p /app/api /root/.cache

# 复制项目文件
COPY api/start.sh /app/api/
COPY api/requirements.txt /app/api/requirements.txt
COPY api/magic-pdf.cpu.json /app/api/magic-pdf.cpu.json
COPY api/download_cpu_models.py /app/api/download_cpu_models.py
COPY requirements.txt /app/requirements.txt

# 确保脚本可执行
RUN chmod +x /app/api/start.sh
RUN chmod +x /app/api/download_cpu_models.py

# 创建虚拟环境并安装依赖
RUN python3 -m venv /opt/mineru_venv && \
    /bin/bash -c "source /opt/mineru_venv/bin/activate && \
    pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple && \
    # 按照依赖顺序安装，先安装基础库 \
    pip install 'numpy>=1.21.6,<2.0.0' 'PyYAML>=6.0.2,<7' -i https://mirrors.aliyun.com/pypi/simple && \
    # 安装PyMuPDF和相关依赖 \
    pip install 'PyMuPDF>=1.24.9,<1.25.0' 'pdfminer.six==20231228' -i https://mirrors.aliyun.com/pypi/simple && \
    # 安装机器学习基础库（CPU版本） \
    pip install 'torch==2.6.0+cpu' torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install 'scikit-learn>=1.0.2' -i https://mirrors.aliyun.com/pypi/simple && \
    # 安装OpenCV \
    pip install opencv-python==4.8.1.78 -i https://mirrors.aliyun.com/pypi/simple && \
    # 安装NLP相关依赖 \
    pip install 'transformers>=4.49.0,<5.0.0' 'ftfy>=6.3.1,<7' 'accelerate==1.6.0' -i https://mirrors.aliyun.com/pypi/simple && \
    # 安装文档处理专用模型 \
    pip install 'dill>=0.3.9,<1' -i https://mirrors.aliyun.com/pypi/simple && \
    pip install 'ultralytics>=8.3.48' -i https://mirrors.aliyun.com/pypi/simple && \
    pip install 'doclayout-yolo==0.0.2b1' -i https://pypi.org/simple/ && \
    pip install 'rapid_table>=1.0.3,<2.0.0' -i https://mirrors.aliyun.com/pypi/simple && \
    pip install 'shapely>=2.0.7,<3' 'pyclipper>=1.3.0,<2' 'omegaconf>=2.3.0,<3' -i https://mirrors.aliyun.com/pypi/simple && \
    # 最后安装其他依赖 \
    pip install 'matplotlib>=3.10' 'tqdm>=4.67.1' 'loguru>=0.6.0' 'boto3>=1.28.43' 'Brotli>=1.1.0' 'fast-langdetect>=0.2.3,<0.3.0' -i https://mirrors.aliyun.com/pypi/simple && \
    # 最后安装API特定依赖 \
    pip install -r /app/api/requirements.txt -i https://mirrors.aliyun.com/pypi/simple"

# 使用我们的CPU配置文件
RUN cp /app/api/magic-pdf.cpu.json /root/magic-pdf.json

# 复制项目代码
COPY . /app/

# 创建API服务需要的目录
RUN mkdir -p /app/api/output \
    /app/magic_pdf/resources/models/MFD/YOLO \
    /app/magic_pdf/resources/models/TabRec/RapidTable \
    /app/magic_pdf/resources/models/OCR \
    /tmp/models/MFD/YOLO

# 下载模型（使用专用的CPU模型下载脚本）
RUN /bin/bash -c "source /opt/mineru_venv/bin/activate && \
    pip install modelscope -i https://mirrors.aliyun.com/pypi/simple && \
    export PYTHONPATH=/app:$PYTHONPATH && \
    export CUDA_VISIBLE_DEVICES= && \
    python3 /app/api/download_cpu_models.py"

# 修改run_api.py，确保CPU模式
RUN echo 'import os\nimport sys\nimport uvicorn\n\n# 强制使用CPU模式\nos.environ["CUDA_VISIBLE_DEVICES"] = ""\nos.environ["OMP_NUM_THREADS"] = "1"\n\n# 添加项目根目录到Python路径\nsys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))\n\nif __name__ == "__main__":\n    # 启动FastAPI服务\n    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, app_dir="api")' > /app/api/run_api.py

# 创建一个简单的启动脚本
RUN echo '#!/bin/bash\n\n# 设置环境变量\nexport CUDA_VISIBLE_DEVICES=\nexport OMP_NUM_THREADS=1\n\n# 启动API服务\ncd /app\npython3 api/run_api.py' > /app/api/start.sh && \
    chmod +x /app/api/start.sh

# 检查安装的依赖版本
RUN /bin/bash -c "source /opt/mineru_venv/bin/activate && \
    python3 -c 'import numpy; print(\"NumPy version:\", numpy.__version__)' && \
    python3 -c 'import cv2; print(\"OpenCV version:\", cv2.__version__)' && \
    python3 -c 'import torch; print(\"PyTorch version:\", torch.__version__); print(\"CUDA available:\", torch.cuda.is_available())' && \
    python3 -c 'import ftfy; print(\"ftfy imported successfully\")' && \
    python3 -c 'import ultralytics; print(\"Ultralytics version:\", ultralytics.__version__)' && \
    python3 -c 'import doclayout_yolo; print(\"DocLayout YOLO imported successfully\")' && \
    python3 -c 'import rapid_table; print(\"Rapid Table imported successfully\")'"

# 暴露端口
EXPOSE 8000

# 使用启动脚本
CMD ["/bin/bash", "-c", "source /opt/mineru_venv/bin/activate && /app/api/start.sh"] 