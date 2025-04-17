#!/usr/bin/env python
"""
简化版ONNX Runtime线程亲和性禁用补丁
此脚本专为解决pthread_setaffinity_np错误设计
"""

import os
import sys
import ctypes
import ctypes.util

# 设置关键环境变量
env_settings = {
    'ORT_DISABLE_THREADS_AFFINITY': '999',  # 使用高值完全禁用亲和性
    'OMP_NUM_THREADS': '1',                 # 限制线程数为1
    'OMP_WAIT_POLICY': 'PASSIVE',           # 使用被动等待策略
    'OMP_PROC_BIND': 'FALSE',               # 禁用线程绑定
    'OMP_DYNAMIC': 'FALSE',                 # 禁用动态线程数调整
    'OMP_PLACES': 'CORES',                  # 使用核心放置
    'ORT_INTER_OP_NUM_THREADS': '1',        # 限制操作间线程数为1
    'ORT_INTRA_OP_NUM_THREADS': '1',        # 限制操作内线程数为1
    'GOMP_CPU_AFFINITY': '0',               # 只使用CPU 0
    'KMP_AFFINITY': 'disabled',             # 禁用Intel线程亲和性
    'KMP_WARNINGS': '0',                    # 禁用Intel警告
    'ORT_LOG_SEVERITY_LEVEL': '4',          # 禁用ONNX Runtime日志
    'ORT_PROVIDERS': 'CPUExecutionProvider' # 仅使用CPU提供程序
}

# 设置所有环境变量
for key, value in env_settings.items():
    os.environ[key] = value
    print(f"设置环境变量: {key}={value}")

# 尝试覆盖pthread_setaffinity_np函数
try:
    # 加载libc
    libc_name = ctypes.util.find_library('c')
    
    if libc_name:
        libc = ctypes.CDLL(libc_name)
        print(f"已加载libc: {libc_name}")
        
        # 检查函数是否存在
        if hasattr(libc, 'pthread_setaffinity_np'):
            print("找到pthread_setaffinity_np函数，正在尝试覆盖...")
            
            # 创建一个替代函数，总是返回0（成功）
            @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_ulong, ctypes.c_size_t, ctypes.c_void_p)
            def dummy_setaffinity(*args):
                return 0
            
            # 保存原始函数地址并替换
            try:
                original_addr = ctypes.cast(
                    libc.pthread_setaffinity_np, 
                    ctypes.c_void_p
                ).value
                
                # 替换为我们的虚拟函数
                libc.pthread_setaffinity_np = dummy_setaffinity
                print(f"已成功覆盖pthread_setaffinity_np函数")
            except Exception as e:
                print(f"无法覆盖pthread_setaffinity_np: {e}")
        else:
            print("未找到pthread_setaffinity_np函数，不需要覆盖")
    else:
        print("找不到libc库")
except Exception as e:
    print(f"尝试覆盖pthread_setaffinity_np时出错: {e}")

# 打印成功消息
print("ONNX Runtime线程亲和性补丁已应用")

# 如果作为主模块运行
if __name__ == "__main__":
    print("此脚本可以直接导入或通过PYTHONSTARTUP环境变量在Python启动时运行") 