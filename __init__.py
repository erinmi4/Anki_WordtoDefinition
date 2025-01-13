import os
import sys

# 将当前目录添加到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 导入 WordProcessor 类
from word_processor import WordProcessor

# 定义可以被其他模块导入的名称
__all__ = ['WordProcessor']

# 版本信息
__version__ = '1.0.0'