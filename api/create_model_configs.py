#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
import argparse
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('model_config_creator')

def ensure_dir(directory):
    """确保目录存在，如果不存在则创建"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def create_model_configs(model_dir=None):
    """创建UnimerNet模型所需的配置文件"""
    # 从环境变量或参数中获取模型目录
    mfr_dir = model_dir
    if not mfr_dir:
        # 如果没有提供模型目录，则使用环境变量或默认相对路径
        mfr_dir = os.environ.get('MFR_DIR', './models/unimernet')
    
    logger.info(f"正在为模型目录 {mfr_dir} 创建配置文件")
    
    # 确保所需目录存在
    ensure_dir(mfr_dir)
    ensure_dir(os.path.join(mfr_dir, 'encoder'))
    ensure_dir(os.path.join(mfr_dir, 'decoder'))
    
    # 主配置文件
    main_config = {
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
    
    # Encoder配置
    encoder_config = {
        "_name_or_path": "microsoft/swinv2-tiny-patch4-window8-256",
        "model_type": "swinv2"
    }
    
    # Decoder配置
    decoder_config = {
        "_name_or_path": "facebook/mbart-large-50",
        "model_type": "mbart"
    }
    
    # 写入配置文件
    try:
        # 主配置
        main_config_path = os.path.join(mfr_dir, 'config.json')
        if not os.path.exists(main_config_path):
            with open(main_config_path, 'w', encoding='utf-8') as f:
                json.dump(main_config, f, indent=2)
            logger.info(f"已创建主配置文件: {main_config_path}")
        else:
            logger.info(f"主配置文件已存在: {main_config_path}")
        
        # Encoder配置
        encoder_config_path = os.path.join(mfr_dir, 'encoder', 'config.json')
        if not os.path.exists(encoder_config_path):
            with open(encoder_config_path, 'w', encoding='utf-8') as f:
                json.dump(encoder_config, f, indent=2)
            logger.info(f"已创建encoder配置文件: {encoder_config_path}")
        else:
            logger.info(f"Encoder配置文件已存在: {encoder_config_path}")
        
        # Decoder配置
        decoder_config_path = os.path.join(mfr_dir, 'decoder', 'config.json')
        if not os.path.exists(decoder_config_path):
            with open(decoder_config_path, 'w', encoding='utf-8') as f:
                json.dump(decoder_config, f, indent=2)
            logger.info(f"已创建decoder配置文件: {decoder_config_path}")
        else:
            logger.info(f"Decoder配置文件已存在: {decoder_config_path}")
            
        logger.info("所有配置文件创建完成")
        
    except Exception as e:
        logger.error(f"创建配置文件时出错: {str(e)}")
        raise

if __name__ == "__main__":
    # 添加命令行参数
    parser = argparse.ArgumentParser(description='创建UnimerNet模型配置文件')
    parser.add_argument('--model-dir', type=str, help='模型目录路径 (默认: ./models/unimernet)')
    args = parser.parse_args()
    
    create_model_configs(args.model_dir) 