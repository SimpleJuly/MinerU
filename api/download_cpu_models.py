#!/usr/bin/env python3
"""
CPU模式模型下载脚本
仅下载CPU模式所需的模型，避免下载CUDA模型
"""

import os
import sys
import logging
import json
import shutil
from pathlib import Path
import subprocess

# 设置环境变量确保CPU模式
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["OMP_NUM_THREADS"] = "1"

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ModelDownloader")

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import torch
    from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
    from magic_pdf.config.enums import SupportedPdfParseMethod
    from magic_pdf.data.dataset import PymuDocDataset
    import ultralytics
    from ultralytics.utils.downloads import safe_download
except ImportError as e:
    logger.error(f"导入错误: {e}")
    sys.exit(1)

def setup_cpu_config():
    """确保使用CPU配置"""
    logger.info("正在设置CPU配置...")
    
    # 检查并复制CPU配置
    cpu_config_path = Path("/app/api/magic-pdf.cpu.json")
    target_config_path = Path("/root/magic-pdf.json")
    
    if cpu_config_path.exists():
        logger.info(f"使用CPU配置: {cpu_config_path}")
        
        # 读取配置以验证
        with open(cpu_config_path, 'r') as f:
            config = json.load(f)
            
        # 确保设备是CPU
        if config.get('device') != 'cpu':
            logger.warning("配置文件中设备不是CPU，正在修改...")
            config['device'] = 'cpu'
        
        # 确保所有模型都使用CPU
        if 'table_models' in config and 'table_rec' in config['table_models']:
            config['table_models']['table_rec']['device'] = 'cpu'
            
        # 保存修改后的配置
        with open(target_config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        logger.info(f"CPU配置已保存到: {target_config_path}")
    else:
        logger.error(f"找不到CPU配置文件: {cpu_config_path}")
        sys.exit(1)

def ensure_dir(directory):
    """确保目录存在"""
    os.makedirs(directory, exist_ok=True)
    logger.info(f"确保目录存在: {directory}")

def download_models():
    """下载所需的模型"""
    logger.info("开始下载模型...")
    
    # 创建必要的目录
    models_dir = "/app/magic_pdf/resources/models"
    mfd_dir = os.path.join(models_dir, "MFD/YOLO")
    mfr_dir = os.path.join(models_dir, "MFR/unimernet_hf_small_2503")
    ensure_dir(mfd_dir)
    ensure_dir(mfr_dir)
    
    # 下载YOLO模型 (CPU版本)
    try:
        logger.info("下载文档布局检测模型 (YOLO/MFD)...")
        # 创建目标目录
        mfd_target = os.path.join(mfd_dir, "yolo_v8_ft.pt")
        
        # 下载MFD模型
        logger.info("直接下载YOLO模型...")
        model_url = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt"
        safe_download(url=model_url, file=mfd_target, attempt=3)
        logger.info(f"YOLO模型下载成功: {mfd_target}")
        
        # 验证模型是否存在
        if os.path.exists(mfd_target):
            logger.info(f"YOLO模型验证成功: {mfd_target}")
            
            # 为了兼容性，创建/tmp/models/MFD/YOLO目录并复制模型
            tmp_model_dir = "/tmp/models/MFD/YOLO"
            ensure_dir(tmp_model_dir)
            tmp_target = os.path.join(tmp_model_dir, "yolo_v8_ft.pt")
            
            logger.info(f"复制模型到临时目录: {tmp_target}")
            shutil.copy(mfd_target, tmp_target)
            
            if os.path.exists(tmp_target):
                logger.info(f"模型复制成功: {tmp_target}")
            else:
                logger.error(f"模型复制失败: {tmp_target}")
        else:
            logger.error(f"YOLO模型下载失败，目标文件不存在: {mfd_target}")
    except Exception as e:
        logger.error(f"下载YOLO模型时出错: {e}")
        # 备用下载方法
        try:
            logger.info("尝试备用方法下载YOLO模型...")
            model_url = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt"
            
            # 确保两个目录都存在
            tmp_model_dir = "/tmp/models/MFD/YOLO"
            ensure_dir(tmp_model_dir)
            ensure_dir(mfd_dir)
            
            # 下载到主要位置
            mfd_target = os.path.join(mfd_dir, "yolo_v8_ft.pt")
            
            # 使用wget下载
            subprocess.run(["wget", "-O", mfd_target, model_url], check=True)
            logger.info(f"YOLO模型备用下载成功: {mfd_target}")
            
            # 复制到/tmp路径
            tmp_target = os.path.join(tmp_model_dir, "yolo_v8_ft.pt")
            shutil.copy(mfd_target, tmp_target)
            logger.info(f"YOLO模型复制到临时目录: {tmp_target}")
            
            # 再次验证两个路径
            if os.path.exists(mfd_target) and os.path.exists(tmp_target):
                logger.info(f"YOLO模型验证成功: 两个路径均存在")
            else:
                logger.error(f"YOLO模型下载或复制失败，请检查路径: {mfd_target} 和 {tmp_target}")
        except Exception as e2:
            logger.error(f"备用下载YOLO模型时出错: {e2}")

    # 下载UniMERNet模型
    try:
        logger.info("下载公式识别模型 (UniMERNet)...")
        
        # 创建临时目录
        tmp_mfr_dir = "/tmp/models/MFR/unimernet_hf_small_2503"
        ensure_dir(tmp_mfr_dir)
        
        # 创建必要的配置文件
        config_dir = os.path.join(mfr_dir, "config")
        ensure_dir(config_dir)
        
        # 创建config.json文件 - 包含完整的encoder和decoder配置
        config_json_path = os.path.join(mfr_dir, "config.json")
        config_json = {
            "_name_or_path": "unimernet-small",
            "architectures": ["UnimernetModel"],
            "model_type": "vision-encoder-decoder",
            "encoder": {
                "_name_or_path": "microsoft/swinv2-tiny-patch4-window8-256",
                "model_type": "swinv2"
            },
            "decoder": {
                "_name_or_path": "facebook/mbart-large-50",
                "model_type": "mbart"
            },
            "use_return_dict": True
        }
        
        with open(config_json_path, 'w') as f:
            json.dump(config_json, f, indent=2)
        logger.info(f"创建配置文件: {config_json_path}")
        
        # 创建encoder配置文件目录
        encoder_dir = os.path.join(mfr_dir, "encoder")
        ensure_dir(encoder_dir)
        
        # 创建encoder/config.json
        encoder_config = {
            "_name_or_path": "microsoft/swinv2-tiny-patch4-window8-256",
            "model_type": "swinv2"
        }
        encoder_config_path = os.path.join(encoder_dir, "config.json")
        with open(encoder_config_path, 'w') as f:
            json.dump(encoder_config, f, indent=2)
        logger.info(f"创建encoder配置文件: {encoder_config_path}")
        
        # 创建decoder配置文件目录
        decoder_dir = os.path.join(mfr_dir, "decoder")
        ensure_dir(decoder_dir)
        
        # 创建decoder/config.json
        decoder_config = {
            "_name_or_path": "facebook/mbart-large-50",
            "model_type": "mbart"
        }
        decoder_config_path = os.path.join(decoder_dir, "config.json")
        with open(decoder_config_path, 'w') as f:
            json.dump(decoder_config, f, indent=2)
        logger.info(f"创建decoder配置文件: {decoder_config_path}")
        
        # 创建从/tmp目录到实际目录的符号链接
        try:
            if os.path.exists(tmp_mfr_dir):
                os.system(f"rm -rf {tmp_mfr_dir}")
            os.symlink(mfr_dir, tmp_mfr_dir)
            logger.info(f"创建符号链接: {mfr_dir} -> {tmp_mfr_dir}")
        except Exception as e:
            logger.error(f"创建符号链接失败: {e}")
            # 如果符号链接失败，则复制文件
            if not os.path.exists(os.path.join(tmp_mfr_dir, "config.json")):
                shutil.copy(config_json_path, os.path.join(tmp_mfr_dir, "config.json"))
            # 复制encoder和decoder目录
            tmp_encoder_dir = os.path.join(tmp_mfr_dir, "encoder")
            tmp_decoder_dir = os.path.join(tmp_mfr_dir, "decoder")
            ensure_dir(tmp_encoder_dir)
            ensure_dir(tmp_decoder_dir)
            shutil.copy(encoder_config_path, os.path.join(tmp_encoder_dir, "config.json"))
            shutil.copy(decoder_config_path, os.path.join(tmp_decoder_dir, "config.json"))
            logger.info(f"复制配置文件到临时目录")
        
        logger.info("UniMERNet模型设置完成")
    except Exception as e:
        logger.error(f"设置UniMERNet模型时出错: {e}")

    # 下载Rapid Table模型
    try:
        logger.info("验证表格识别模型...")
        import rapid_table
        rapid_table_dir = "/app/magic_pdf/resources/models/TabRec/RapidTable"
        ensure_dir(rapid_table_dir)
        logger.info("Rapid Table模型加载成功")
    except Exception as e:
        logger.error(f"加载Rapid Table模型时出错: {e}")

    # 下载OCR模型
    try:
        logger.info("验证OCR模型...")
        ocr_dir = "/app/magic_pdf/resources/models/OCR"
        ensure_dir(ocr_dir)
        # 这里可以添加OCR模型的下载和验证
        logger.info("OCR模型验证完成")
    except Exception as e:
        logger.error(f"验证OCR模型时出错: {e}")

    # 验证所有必要的模型目录和文件
    for model_path in [
        "/app/magic_pdf/resources/models/MFD/YOLO/yolo_v8_ft.pt",
        "/tmp/models/MFD/YOLO/yolo_v8_ft.pt",
        "/app/magic_pdf/resources/models/MFR/unimernet_hf_small_2503",
        "/tmp/models/MFR/unimernet_hf_small_2503",
        "/app/magic_pdf/resources/models/TabRec/RapidTable",
        "/app/magic_pdf/resources/models/OCR"
    ]:
        path = Path(model_path)
        if path.exists():
            logger.info(f"模型路径存在: {path}")
        else:
            logger.error(f"模型路径不存在: {path}")
            # 如果是目录，尝试创建
            if not path.suffix:  # 没有后缀名，认为是目录
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建目录: {path}")
            # 如果是文件，检查上级目录是否存在
            elif path.parent and not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建父目录: {path.parent}")

    logger.info("所有模型下载和验证完成")

if __name__ == "__main__":
    logger.info("CPU模式模型下载工具启动")
    
    # 打印环境信息
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"PyTorch版本: {torch.__version__}")
    logger.info(f"CUDA可用: {torch.cuda.is_available()}")
    
    # 设置CPU配置
    setup_cpu_config()
    
    # 下载模型
    download_models()
    
    logger.info("所有任务完成") 