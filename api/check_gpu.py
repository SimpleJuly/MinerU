#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GPU/CUDA 检查和调试工具
此脚本可以:
1. 检查系统信息和NVIDIA驱动状态
2. 检查Docker环境中的NVIDIA支持
3. 验证PyTorch CUDA设置
4. 检查模型依赖包的安装状态
5. 提供常见问题的解决方案
"""

import platform
import sys
import subprocess
import os

def print_system_info():
    """打印系统信息"""
    print("="*50)
    print("系统信息:")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"Python版本: {platform.python_version()}")
    print("="*50)

def check_nvidia_driver():
    """检查NVIDIA驱动"""
    print("="*50)
    print("NVIDIA驱动检查:")
    try:
        output = subprocess.check_output(["nvidia-smi"], stderr=subprocess.STDOUT, universal_newlines=True)
        print("NVIDIA驱动正常工作:")
        print(output)
    except subprocess.CalledProcessError as e:
        print("无法执行nvidia-smi命令. 错误信息:")
        print(e.output)
        print("\n可能的原因:")
        print("- NVIDIA驱动未安装")
        print("- NVIDIA驱动版本与CUDA不兼容")
        print("- 系统没有NVIDIA GPU")
    except FileNotFoundError:
        print("未找到nvidia-smi命令. NVIDIA驱动可能未安装.")
    print("="*50)

def check_docker_nvidia():
    """检查Docker的NVIDIA支持"""
    print("="*50)
    print("Docker NVIDIA支持检查:")
    
    # 检查nvidia-docker版本
    try:
        output = subprocess.check_output(["nvidia-docker", "version"], stderr=subprocess.STDOUT, universal_newlines=True)
        print("nvidia-docker已安装:")
        print(output)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("nvidia-docker未找到或无法正常工作")
        
        # 检查nvidia-container-toolkit
        try:
            output = subprocess.check_output(["nvidia-container-cli", "-V"], stderr=subprocess.STDOUT, universal_newlines=True)
            print("nvidia-container-toolkit已安装:")
            print(output)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("nvidia-container-toolkit未找到或无法正常工作")
            print("您可能需要安装nvidia-docker2或nvidia-container-toolkit")
    
    print("="*50)

def check_pytorch_gpu():
    """检查PyTorch GPU/CUDA支持"""
    print("="*50)
    print("PyTorch CUDA支持检查:")
    
    try:
        import torch
        print(f"PyTorch版本: {torch.__version__}")
        
        if torch.cuda.is_available():
            print("CUDA可用性: 是")
            print(f"CUDA版本: {torch.version.cuda}")
            print(f"可用GPU数量: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
            print(f"当前GPU: {torch.cuda.current_device()}")
        else:
            print("CUDA可用性: 否")
            print("PyTorch无法使用CUDA。可能的原因:")
            print("- PyTorch安装的是CPU版本")
            print("- CUDA版本与PyTorch不兼容")
            print("- NVIDIA驱动未正确安装")
            print("- 系统没有NVIDIA GPU")
            
    except ImportError:
        print("无法导入PyTorch。请确认PyTorch已正确安装。")
        
    print("="*50)

def check_dependencies():
    """检查关键依赖包"""
    print("="*50)
    print("检查关键依赖包:")
    
    # 检查doclayout-yolo
    try:
        import doclayout_yolo
        version = getattr(doclayout_yolo, '__version__', '未知')
        print(f"doclayout-yolo: 已安装 (版本: {version})")
    except ImportError:
        print("doclayout-yolo: 未安装或无法导入")
        
    # 检查rapid_table
    try:
        import rapid_table
        version = getattr(rapid_table, '__version__', '未知')
        print(f"rapid_table: 已安装 (版本: {version})")
    except ImportError:
        print("rapid_table: 未安装或无法导入")
        
    # 检查ftfy (用于unimernet_hf)
    try:
        import ftfy
        version = getattr(ftfy, '__version__', '未知')
        print(f"ftfy: 已安装 (版本: {version})")
    except ImportError:
        print("ftfy: 未安装或无法导入")
    
    print("="*50)

def suggest_solutions():
    """提供一些常见问题的解决方案"""
    print("="*50)
    print("可能的解决方案:")
    
    print("\n1. 如果NVIDIA驱动未安装或不兼容:")
    print("   - 访问 https://www.nvidia.com/Download/index.aspx 下载适合您GPU的最新驱动")
    print("   - 或使用系统包管理器安装: sudo apt install nvidia-driver-XXX (Ubuntu)")
    
    print("\n2. 如果Docker不支持NVIDIA:")
    print("   - 安装nvidia-docker2: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html")
    print("   - 或将docker-compose.yml配置为使用CPU模式，在环境变量中添加: CUDA_VISIBLE_DEVICES=")
    
    print("\n3. 如果PyTorch无法使用CUDA:")
    print("   - 重新安装与您CUDA版本兼容的PyTorch: https://pytorch.org/get-started/locally/")
    
    print("\n4. 对于MinerU API服务:")
    print("   - 修改Dockerfile中doclayout-yolo的安装源为官方PyPI:")
    print("     pip install 'doclayout-yolo==0.0.2b1' -i https://pypi.org/simple/")
    print("   - 或仅使用CPU模式运行服务，修改docker-compose.yml中的环境变量:")
    print("     CUDA_VISIBLE_DEVICES=")
    
    print("="*50)

def main():
    """主函数"""
    print("\n==== MinerU API GPU 诊断工具 ====\n")
    
    print_system_info()
    check_nvidia_driver()
    check_docker_nvidia()
    check_pytorch_gpu()
    check_dependencies()
    suggest_solutions()
    
    print("\n诊断完成。如需更多帮助，请访问项目文档或提交GitHub issue。")

if __name__ == "__main__":
    main() 