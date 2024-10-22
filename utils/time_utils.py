# 新建一个 util.py 文件夹，创建 util.py/time_utils.py
import re

class TimeUtils:
    @staticmethod
    def format_time(seconds):
        """将时间转换为 HH:MM:SS,mmm 格式"""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        return f"{int(hours):02}:{int(minutes):02}:{seconds:02},{milliseconds:03}"

    @staticmethod
    def parse_time_input(time_str):
        """将时间字符串 HH:MM:SS,mmm 转换为毫秒"""
        try:
            hours, minutes, seconds = time_str.split(':')
            seconds, milliseconds = seconds.split(',')
            return (int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000 + int(milliseconds)
        except ValueError:
            raise ValueError("时间格式不正确，请使用 HH:MM:SS,mmm 格式")

    @staticmethod
    def extract_time_from_input(input_text):
        """从输入框中的文本提取时间，格式为 [HH:MM:SS,mmm]"""
        match = re.search(r'\[(\d{2}:\d{2}:\d{2},\d{3})\]', input_text)
        if match:
            return match.group(1)
        else:
            raise ValueError("无法从文本中提取时间")
