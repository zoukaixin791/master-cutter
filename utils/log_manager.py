# util.py/log_manager.py
import logging
from logging.handlers import RotatingFileHandler

# 设置日志管理器
log_manager = logging.getLogger('MyAppLogger')
log_manager.setLevel(logging.INFO)

# 日志格式
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# 控制台日志处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)


# 文件日志处理器 (自动轮转日志)
file_handler = RotatingFileHandler('app.log', maxBytes=1000000, backupCount=5)
file_handler.setFormatter(formatter)

# 添加处理器到日志管理器
log_manager.addHandler(console_handler)
log_manager.addHandler(file_handler)
