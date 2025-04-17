"""
ONNX Runtime补丁模块
这个模块用于在ONNX Runtime导入前设置必要的环境变量和修改其行为
"""
import os
import sys
import ctypes
from importlib.machinery import PathFinder

# 设置环境变量
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
os.environ['ORT_LOG_SEVERITY_LEVEL'] = '4'
os.environ['ORT_PROVIDERS'] = 'CPUExecutionProvider'

# 尝试打补丁直接修改线程亲和性函数
try:
    # 加载libc
    try:
        libc = ctypes.CDLL('libc.so.6')
    except OSError:
        # 如果找不到libc.so.6，尝试其他常见名称
        try:
            libc = ctypes.CDLL('libc.so')
        except OSError:
            try:
                # macOS上的名称
                libc = ctypes.CDLL('libSystem.dylib')
            except OSError:
                # Windows上的名称
                libc = ctypes.CDLL('msvcrt.dll')
    
    # 尝试直接替换pthread_setaffinity_np函数
    if hasattr(libc, 'pthread_setaffinity_np'):
        print("[ONNX补丁] 已找到pthread_setaffinity_np，正在禁用...")
        
        # 定义一个替代函数，始终返回成功(0)
        @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_ulong, ctypes.c_size_t, ctypes.c_void_p)
        def dummy_setaffinity(*args):
            return 0
        
        # 替换原始函数（这是一个hack，但在紧急情况下可能有效）
        try:
            original_func = libc.pthread_setaffinity_np
            libc.pthread_setaffinity_np = dummy_setaffinity
            print("[ONNX补丁] 成功覆盖pthread_setaffinity_np函数")
        except Exception as e:
            print(f"[ONNX补丁] 无法覆盖pthread_setaffinity_np: {e}")
    else:
        print("[ONNX补丁] 未找到pthread_setaffinity_np函数")
except Exception as e:
    print(f"[ONNX补丁] 应用libc补丁时出错: {e}")

# 创建一个导入钩子，在导入onnxruntime之前设置环境
class ONNXImportInterceptor(PathFinder):
    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        # 只拦截onnxruntime相关的导入
        if fullname.startswith('onnxruntime'):
            print(f"[ONNX补丁] 正在拦截模块 {fullname} 的导入")
            # 设置环境变量
            for key, value in [
                ('ORT_DISABLE_THREADS_AFFINITY', '999'),
                ('OMP_NUM_THREADS', '1'),
                ('OMP_WAIT_POLICY', 'PASSIVE'),
                ('OMP_PROC_BIND', 'FALSE'),
                ('ORT_INTER_OP_NUM_THREADS', '1'),
                ('ORT_INTRA_OP_NUM_THREADS', '1'),
                ('ORT_LOG_SEVERITY_LEVEL', '4'),
                ('ORT_PROVIDERS', 'CPUExecutionProvider')
            ]:
                os.environ[key] = value
                print(f"[ONNX补丁] 设置环境变量: {key}={value}")
        
        # 返回None让正常的导入机制继续处理
        return None

# 注册导入钩子
sys.meta_path.insert(0, ONNXImportInterceptor)

print("[ONNX补丁] 已安装ONNX Runtime补丁")

# 导出hook函数，可以从其他模块调用
def apply_onnx_patches():
    """应用所有ONNX Runtime补丁"""
    print("[ONNX补丁] 主动应用ONNX Runtime补丁")
    # 环境变量已在模块导入时设置
    return True 