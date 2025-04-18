#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入需要测试的模块
from magic_pdf.dict2md.ocr_mkcontent import union_make
from magic_pdf.config.make_content_config import MakeMode, DropMode

# 创建测试数据 - 模拟没有to_dict方法的普通字典
class TestDict(dict):
    pass

# 创建一个样例PDF信息字典，模拟真实情况
test_page_info = TestDict({
    'page_idx': 0,
    'need_drop': False,
    'para_blocks': [
        {
            'type': 'text',
            'blocks': [],
            'lines': [
                {
                    'spans': [
                        {
                            'type': 1,  # ContentType.Text
                            'content': '这是一个测试文本'
                        }
                    ]
                }
            ]
        }
    ]
})

# 创建测试PDF信息列表
pdf_info_list = [test_page_info]

# 测试union_make函数
try:
    print("测试 union_make 函数...")
    result = union_make(pdf_info_list, MakeMode.MM_MD, DropMode.NONE, '')
    print(f"结果类型: {type(result)}")
    print(f"结果内容: {result[:100]}...")  # 仅显示前100个字符
    print("测试成功！")
except Exception as e:
    print(f"测试失败: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n所有测试完成!") 