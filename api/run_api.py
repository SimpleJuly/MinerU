import os
import sys
import ctypes
import ctypes.util

# 在最开始设置ONNX Runtime环境变量禁用线程亲和性
os.environ['ORT_DISABLE_THREADS_AFFINITY'] = '999'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OMP_WAIT_POLICY'] = 'PASSIVE'
os.environ['OMP_PROC_BIND'] = 'FALSE'
os.environ['OMP_DYNAMIC'] = 'FALSE'
os.environ['OMP_PLACES'] = 'CORES'
os.environ['ORT_INTER_OP_NUM_THREADS'] = '1'
os.environ['ORT_INTRA_OP_NUM_THREADS'] = '1'
os.environ['GOMP_CPU_AFFINITY'] = '0'
os.environ['KMP_AFFINITY'] = 'disabled'
os.environ['KMP_WARNINGS'] = '0'
os.environ['ORT_LOG_SEVERITY_LEVEL'] = '4'
os.environ['ORT_PROVIDERS'] = 'CPUExecutionProvider'

# 直接在这里禁用pthread_setaffinity_np函数
try:
    # 加载libc
    libc_name = ctypes.util.find_library('c')
    if libc_name:
        libc = ctypes.CDLL(libc_name)
        print(f"已加载libc: {libc_name}")
        
        # 检查是否存在pthread_setaffinity_np函数
        if hasattr(libc, 'pthread_setaffinity_np'):
            print("找到pthread_setaffinity_np函数，正在替换...")
            
            # 创建一个替代函数，总是返回0（成功）
            @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_ulong, ctypes.c_size_t, ctypes.c_void_p)
            def dummy_setaffinity(*args):
                return 0
            
            # 替换函数
            try:
                libc.pthread_setaffinity_np = dummy_setaffinity
                print("成功替换pthread_setaffinity_np函数")
            except Exception as e:
                print(f"替换pthread_setaffinity_np函数时出错: {e}")
        else:
            print("未找到pthread_setaffinity_np函数，无需替换")
    else:
        print("未找到libc库")
except Exception as e:
    print(f"禁用线程亲和性时出错: {e}")

# 现在导入其他模块
import uvicorn

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if __name__ == "__main__":
    # 启动FastAPI服务
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, app_dir="api") 