# 基于项目已有的全局Docker镜像
FROM ubuntu:22.04

# 设置非交互式环境变量以避免在安装过程中出现提示
ENV DEBIAN_FRONTEND=noninteractive

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

# 首先复制依赖文件
COPY api/requirements.txt /app/api/requirements.txt
COPY requirements.txt /app/requirements.txt

# 创建虚拟环境并安装依赖
RUN python3 -m venv /opt/mineru_venv && \
    /bin/bash -c "source /opt/mineru_venv/bin/activate && \
    pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple && \
    # 按照依赖顺序安装，先安装基础库 \
    pip install 'numpy>=1.21.6,<2.0.0' 'PyYAML>=6.0.2,<7' -i https://mirrors.aliyun.com/pypi/simple && \
    # 安装PyMuPDF和相关依赖 \
    pip install 'PyMuPDF>=1.24.9,<1.25.0' 'pdfminer.six==20231228' -i https://mirrors.aliyun.com/pypi/simple && \
    # 安装机器学习基础库 \
    pip install 'torch==2.6.0' torchvision 'scikit-learn>=1.0.2' -i https://mirrors.aliyun.com/pypi/simple && \
    # 安装OpenCV \
    pip install opencv-python==4.8.1.78 -i https://mirrors.aliyun.com/pypi/simple && \
    # 安装NLP相关依赖 \
    pip install 'transformers>=4.49.0,<5.0.0' 'ftfy>=6.3.1,<7' 'accelerate==1.6.0' -i https://mirrors.aliyun.com/pypi/simple && \
    # 安装文档处理专用模型 \
    pip install 'dill>=0.3.9,<1' -i https://mirrors.aliyun.com/pypi/simple && \
    pip install 'ultralytics>=8.3.48' -i https://mirrors.aliyun.com/pypi/simple && \
    pip install 'doclayout-yolo==0.0.2b1' -i https://mirrors.aliyun.com/pypi/simple && \
    pip install 'rapid_table>=1.0.3,<2.0.0' -i https://mirrors.aliyun.com/pypi/simple && \
    pip install 'shapely>=2.0.7,<3' 'pyclipper>=1.3.0,<2' 'omegaconf>=2.3.0,<3' -i https://mirrors.aliyun.com/pypi/simple && \
    # 最后安装其他依赖 \
    pip install 'matplotlib>=3.10' 'tqdm>=4.67.1' 'loguru>=0.6.0' 'boto3>=1.28.43' 'Brotli>=1.1.0' 'fast-langdetect>=0.2.3,<0.3.0' -i https://mirrors.aliyun.com/pypi/simple && \
    # 最后安装API特定依赖 \
    pip install -r /app/api/requirements.txt -i https://mirrors.aliyun.com/pypi/simple"

# 复制配置文件模板并设置
RUN wget https://gcore.jsdelivr.net/gh/opendatalab/MinerU@master/magic-pdf.template.json && \
    cp magic-pdf.template.json /root/magic-pdf.json

# 复制项目代码
COPY . /app/

# 创建API服务需要的目录
RUN mkdir -p /app/api/output

# 下载模型（使用modelscope代替huggingface）
RUN /bin/bash -c "source /opt/mineru_venv/bin/activate && \
    pip install modelscope -i https://mirrors.aliyun.com/pypi/simple && \
    python3 /app/scripts/download_models.py && \
    sed -i 's|cpu|cuda|g' /root/magic-pdf.json"

# 验证依赖版本
RUN /bin/bash -c "source /opt/mineru_venv/bin/activate && \
    python3 -c 'import numpy; print(\"NumPy version:\", numpy.__version__)' && \
    python3 -c 'import cv2; print(\"OpenCV version:\", cv2.__version__)' && \
    python3 -c 'import torch; print(\"PyTorch version:\", torch.__version__)' && \
    python3 -c 'import ftfy; print(\"ftfy imported successfully\")' && \
    python3 -c 'import ultralytics; print(\"Ultralytics version:\", ultralytics.__version__)' && \
    python3 -c 'import doclayout_yolo; print(\"DocLayout YOLO imported successfully\")' && \
    python3 -c 'import rapid_table; print(\"Rapid Table imported successfully\")'"

# 暴露端口
EXPOSE 8000

# 设置启动命令
CMD ["/bin/bash", "-c", "source /opt/mineru_venv/bin/activate && cd /app && python api/run_api.py"] 