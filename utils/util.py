import os
import os
import gradio as gr  # Gradio 库，用于展示信息和警告
import platform  # 用于检测操作系统
import sys  # 用于系统相关的操作，例如输出错误信息
import subprocess  # 用于执行系统命令
import re

def natural_sort_key(s, regex=re.compile('([0-9]+)')):
    # 使用正则表达式将字符串 s 中的数字和非数字部分分开
    return [
        int(text) if text.isdigit() else text.lower()  # 如果分割的部分是数字，将其转换为整数，否则将其转换为小写字符串
        for text in regex.split(s)  # 使用正则表达式按数字进行分割
    ]

def listfiles(dirname):
    # 获取给定目录中所有不以 '.' 开头的文件或文件夹，并按自然排序法排序
    filenames = [
        os.path.join(dirname, x)  # 获取文件的完整路径
        for x in sorted(os.listdir(dirname), key=natural_sort_key)  # 对文件名进行自然排序
        if not x.startswith(".")  # 排除以 '.' 开头的隐藏文件
    ]

    # 只返回其中是文件的项，排除文件夹
    return [file for file in filenames if os.path.isfile(file)]





def open_folder(path):
    """Open a folder in the file manager of the respective OS."""

    # 检查路径是否存在
    if not os.path.exists(path):
        # 如果路径不存在，打印并通过 Gradio 提示用户
        msg = f'Folder "{path}" does not exist. After you save an image, the folder will be created.'
        print(msg)  # 打印消息到控制台
        gr.Info(msg)  # Gradio 信息弹出
        return

    # 检查路径是否是一个目录
    elif not os.path.isdir(path):
        # 如果路径不是一个目录，打印警告并发出安全警告
        msg = f"""
WARNING
An open_folder request was made with a path that is not a folder.
This could be an error or a malicious attempt to run code on your computer.
Requested path was: {path}
"""
        print(msg, file=sys.stderr)  # 打印警告到标准错误输出
        gr.Warning(msg)  # Gradio 警告弹出
        return

    # 规范化路径，避免路径中出现奇怪的符号或格式问题
    path = os.path.normpath(path)

    # 根据操作系统的不同，执行相应的命令
    if platform.system() == "Windows":
        # Windows 系统使用 os.startfile 打开文件管理器
        os.startfile(path)
    elif platform.system() == "Darwin":
        # macOS 使用 `open` 命令
        subprocess.Popen(["open", path])
    elif "microsoft-standard-WSL2" in platform.uname().release:
        # 如果在 WSL2 环境下（Linux子系统），使用 explorer.exe 打开
        subprocess.Popen(["explorer.exe", subprocess.check_output(["wslpath", "-w", path])])
    else:
        # 其他 Linux 系统使用 `xdg-open`
        subprocess.Popen(["xdg-open", path])
