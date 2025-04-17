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
    pip install --upgrade pip && \
    pip install -r /app/api/requirements.txt"

# 复制配置文件模板并设置
RUN wget https://github.com/opendatalab/MinerU/raw/master/magic-pdf.template.json && \
    cp magic-pdf.template.json /root/magic-pdf.json

# 复制项目代码
COPY . /app/

# 创建API服务需要的目录
RUN mkdir -p /app/api/output

# 下载模型
RUN /bin/bash -c "source /opt/mineru_venv/bin/activate && \
    python3 /app/scripts/download_models_hf.py && \
    sed -i 's|cpu|cuda|g' /root/magic-pdf.json"

# 暴露端口
EXPOSE 8000

# 设置启动命令
CMD ["/bin/bash", "-c", "source /opt/mineru_venv/bin/activate && cd /app && python api/run_api.py"] 