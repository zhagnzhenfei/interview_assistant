import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# 创建日志记录器
logger = logging.getLogger('interview_assistant')
logger.setLevel(logging.INFO)

# 确保日志目录存在
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 创建控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)

# 创建文件处理器
file_handler = RotatingFileHandler(
    os.path.join(log_dir, 'app.log'),
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)

# 清除现有的处理器
logger.handlers = []

# 添加处理器到日志记录器
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# 防止日志重复
logger.propagate = False 