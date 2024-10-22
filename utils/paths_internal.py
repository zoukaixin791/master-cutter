"""
This module defines internal paths used by the program and is safe to import before dependencies are installed in launch.py.
"""
# 导入必要的模块
import os  # 提供与操作系统交互的功能，如路径操作、获取环境变量等
from pathlib import Path  # 提供跨平台的路径处理工具
import sys
# 定义用于标准化文件路径的 lambda 函数，将相对路径转换为绝对路径
normalized_filepath = lambda filepath: str(Path(filepath).absolute())

# 获取当前工作目录 (Current Working Directory)
cwd = os.getcwd()



if getattr(sys, 'frozen', False):
    # 如果被 PyInstaller 打包
    script_path = sys._MEIPASS  # PyInstaller 在打包时解压的临时路径
else:
    # 获取当前模块的路径并规范化为绝对路径，获取当前脚本所在目录
    script_path = os.path.dirname(os.path.realpath(__file__))
# 获取脚本的父目录，通常是项目的根目录
project_path = os.path.dirname(script_path)

# 定义扩展缓存路径，默认存放在 data_path/cache 下
cache_dir = os.path.join(project_path, "cache")
plugins_dir = os.path.join(project_path, "plugins")
resources_dir = os.path.join(project_path, "resources")

# 定义输出文件存放路径，默认在 data_path/outputs 目录下
default_output_dir = os.path.join(project_path, "outputs")


# 确保目录存在，不存在则创建
def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)  # 递归创建目录

# 确保这些目录存在
ensure_directory_exists(cache_dir)
