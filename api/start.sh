#!/bin/bash

# 设置ONNX Runtime环境变量以禁用线程亲和性 (强制禁用)
export ORT_DISABLE_THREADS_AFFINITY=999
export OMP_NUM_THREADS=1
export OMP_WAIT_POLICY=PASSIVE
export OMP_PROC_BIND=FALSE
export OMP_DYNAMIC=FALSE
export OMP_PLACES=CORES
export ORT_INTER_OP_NUM_THREADS=1
export ORT_INTRA_OP_NUM_THREADS=1
export GOMP_CPU_AFFINITY="0"
export KMP_AFFINITY=disabled
export KMP_WARNINGS=0
export ORT_LOG_SEVERITY_LEVEL=4
export ORT_PROVIDERS=CPUExecutionProvider

# 打印ONNX Runtime环境变量
echo "ONNX Runtime 环境变量设置:"
echo "ORT_DISABLE_THREADS_AFFINITY=$ORT_DISABLE_THREADS_AFFINITY"
echo "OMP_NUM_THREADS=$OMP_NUM_THREADS"
echo "OMP_WAIT_POLICY=$OMP_WAIT_POLICY"
echo "OMP_PROC_BIND=$OMP_PROC_BIND"
echo "OMP_DYNAMIC=$OMP_DYNAMIC"
echo "OMP_PLACES=$OMP_PLACES"
echo "ORT_INTER_OP_NUM_THREADS=$ORT_INTER_OP_NUM_THREADS"
echo "ORT_INTRA_OP_NUM_THREADS=$ORT_INTRA_OP_NUM_THREADS"
echo "GOMP_CPU_AFFINITY=$GOMP_CPU_AFFINITY"
echo "KMP_AFFINITY=$KMP_AFFINITY"
echo "ORT_LOG_SEVERITY_LEVEL=$ORT_LOG_SEVERITY_LEVEL"
echo "ORT_PROVIDERS=$ORT_PROVIDERS"

# 确认ONNX配置文件存在
if [ -f /root/.onnxruntime_config.json ]; then
    echo "ONNX配置文件已找到: /root/.onnxruntime_config.json"
    echo "配置内容:"
    cat /root/.onnxruntime_config.json
else
    echo "警告: ONNX配置文件不存在，创建默认配置"
    # 创建默认配置文件
    cat > /root/.onnxruntime_config.json << EOF
{
  "session_options": {
    "execution_mode": 0,
    "graph_optimization_level": 99,
    "inter_op_num_threads": 1,
    "intra_op_num_threads": 1,
    "execution_mode_string": "ORT_SEQUENTIAL",
    "enable_profiling": false,
    "disable_cpu_mem_arena": false,
    "enable_cpu_mem_arena": true,
    "enable_mem_pattern": true,
    "enable_mem_reuse": true,
    "thread_pool_allow_spinning": false,
    "enable_sequential_execution": true,
    "disable_all_telemetry": true,
    "log_severity_level": 4
  },
  "provider_options": {
    "CPUExecutionProvider": {
      "use_arena": true,
      "enable_thread_spinlock": false,
      "arena_extend_strategy": 0,
      "allow_cpu_ctx_across_thread": true,
      "disable_thread_pool": true
    }
  },
  "disable_thread_affinity": true
}
EOF
    echo "已创建默认配置"
fi

# 创建简化的直接启动脚本
cat > /app/api/run_with_simple_patch.py << EOF
"""
修复版：简化的带补丁启动API服务
"""
import os
import sys

# 先设置Python路径
sys.path.insert(0, '/app')

# 直接设置环境变量 - 不使用复杂的机制
def set_env_vars():
    """简单地设置必要的环境变量"""
    important_vars = {
        'ORT_DISABLE_THREADS_AFFINITY': '999',
        'OMP_NUM_THREADS': '1',
        'OMP_WAIT_POLICY': 'PASSIVE', 
        'OMP_PROC_BIND': 'FALSE',
        'OMP_DYNAMIC': 'FALSE',
        'OMP_PLACES': 'CORES',
        'ORT_INTER_OP_NUM_THREADS': '1',
        'ORT_INTRA_OP_NUM_THREADS': '1',
        'GOMP_CPU_AFFINITY': '0',
        'KMP_AFFINITY': 'disabled',
        'ORT_LOG_SEVERITY_LEVEL': '4',
        'ORT_PROVIDERS': 'CPUExecutionProvider'
    }
    
    for key, value in important_vars.items():
        os.environ[key] = value
        print(f"设置环境变量: {key}={value}")

# 补丁pthread函数
def patch_pthread():
    """尝试禁用线程亲和性"""
    import ctypes
    import ctypes.util
    
    try:
        # 尝试加载libc
        libc_name = ctypes.util.find_library('c')
        if libc_name:
            libc = ctypes.CDLL(libc_name)
            print(f"已加载libc: {libc_name}")
            
            # 检查是否存在pthread_setaffinity_np函数
            if hasattr(libc, 'pthread_setaffinity_np'):
                print("找到pthread_setaffinity_np函数，尝试覆盖")
                
                # 定义一个替代函数，总是返回成功(0)
                @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_ulong, ctypes.c_size_t, ctypes.c_void_p)
                def dummy_func(*args):
                    return 0
                
                try:
                    # 使用ctypes提供的函数
                    original_addr = ctypes.cast(libc.pthread_setaffinity_np, ctypes.c_void_p).value
                    libc.pthread_setaffinity_np = dummy_func
                    print(f"成功覆盖pthread_setaffinity_np函数")
                except Exception as e:
                    print(f"无法覆盖函数: {e}")
            else:
                print("未找到pthread_setaffinity_np函数，无需覆盖")
    except Exception as e:
        print(f"修补libc时出错: {e}")

# 应用环境变量和补丁
set_env_vars()
patch_pthread()

print("启动API服务...")
# 导入并运行API
try:
    # 直接执行run_api.py脚本 - 简单可靠
    with open('/app/api/run_api.py') as f:
        exec(f.read(), {'__file__': '/app/api/run_api.py', '__name__': '__main__'})
except Exception as e:
    print(f"启动API服务时出错: {e}")
    import traceback
    traceback.print_exc()
EOF

# 确保环境变量对Python进程可见
export PYTHONPATH=/app:$PYTHONPATH

# 检查模型文件
MFD_MODEL_PATH="/tmp/models/MFD/YOLO/yolo_v8_ft.pt"
APP_MODEL_PATH="/app/magic_pdf/resources/models/MFD/YOLO/yolo_v8_ft.pt"
MFR_DIR="/app/magic_pdf/resources/models/MFR/unimernet_hf_small_2503"
TMP_MFR_DIR="/tmp/models/MFR/unimernet_hf_small_2503"

# 确保目录存在
mkdir -p "/tmp/models/MFD/YOLO"
mkdir -p "/app/magic_pdf/resources/models/MFD/YOLO"
mkdir -p "$MFR_DIR"
mkdir -p "$TMP_MFR_DIR"

# 如果模型不存在，尝试下载一个基础模型
if [ ! -f "$MFD_MODEL_PATH" ]; then
    echo "MFD模型文件不存在，尝试下载..."
    wget -O "$APP_MODEL_PATH" "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt"
    
    # 复制到tmp目录
    if [ -f "$APP_MODEL_PATH" ]; then
        cp "$APP_MODEL_PATH" "$MFD_MODEL_PATH"
        echo "模型文件已下载并复制到: $MFD_MODEL_PATH"
    else
        echo "警告: 无法下载模型文件"
    fi
else
    echo "MFD模型文件存在: $MFD_MODEL_PATH"
fi

# 检查和创建MFR配置文件
if [ ! -f "$MFR_DIR/config.json" ] || [ ! -f "$MFR_DIR/encoder/config.json" ] || [ ! -f "$MFR_DIR/decoder/config.json" ]; then
    echo "使用辅助脚本创建MFR模型配置..."
    # 先尝试安装transformers库
    pip install transformers --no-cache-dir -i https://pypi.org/simple || true
    
    # 执行配置创建脚本
    python3 /app/api/create_model_configs.py
    
    echo "MFR模型配置创建完成"
fi

# 如果临时目录不是符号链接，则创建符号链接或复制文件
if [ -L "$TMP_MFR_DIR" ]; then
    echo "MFR模型符号链接已存在"
else
    echo "创建MFR模型目录结构..."
    # 删除可能存在的临时目录
    rm -rf "$TMP_MFR_DIR"
    # 尝试创建符号链接
    if ln -s "$MFR_DIR" "$TMP_MFR_DIR" 2>/dev/null; then
        echo "创建符号链接成功: $MFR_DIR -> $TMP_MFR_DIR"
    else
        # 如果符号链接失败，则复制文件
        echo "符号链接创建失败，使用文件复制..."
        mkdir -p "$TMP_MFR_DIR"
        # 复制配置文件
        cp "$MFR_DIR/config.json" "$TMP_MFR_DIR/config.json"
        
        # 复制encoder配置
        mkdir -p "$TMP_MFR_DIR/encoder"
        cp "$MFR_DIR/encoder/config.json" "$TMP_MFR_DIR/encoder/config.json"
        
        # 复制decoder配置
        mkdir -p "$TMP_MFR_DIR/decoder" 
        cp "$MFR_DIR/decoder/config.json" "$TMP_MFR_DIR/decoder/config.json"
        
        echo "配置文件已复制到临时目录"
    fi
fi

# 启动API服务
cd /app
echo "启动API服务..."
exec python /app/api/run_with_simple_patch.py 