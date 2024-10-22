import os
import datetime
import shutil
import re
import whisper
from PyQt5.QtWidgets import QWidget, QGridLayout, QLineEdit, QLabel, QPushButton, QFileDialog, \
    QListWidget, QMessageBox, QHBoxLayout, QCheckBox, QVBoxLayout, QListWidgetItem, QDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal,QObject
import opencc

from ui.components.console import ConsoleBox  # 假设这是自定义的ConsoleBox类
import subprocess
import platform
from ui.components.video_player import VideoPlayerWidget  # 导入封装好的视频播放器
from utils.util import *
from utils.paths_internal import *


if platform.system() == "Windows":
    ffmpeg_path = os.path.join(plugins_dir, "ffmpeg/ffmpeg.exe")
    ffplay_path = os.path.join(plugins_dir, "ffmpeg/ffplay.exe")
    ffprobe_path = os.path.join(plugins_dir, "ffmpeg/ffprobe.exe")
else :  # macOS
    # 对于 macOS 或 Linux，优先使用系统安装的 ffmpeg 工具
    ffmpeg_path = shutil.which("ffmpeg")  # 从环境变量中寻找 ffmpeg 可执行文件
    ffplay_path = shutil.which("ffplay")  # 从环境变量中寻找 ffplay 可执行文件
    ffprobe_path = shutil.which("ffprobe")  # 从环境变量中寻找 ffprobe 可执行文件

    # 如果未找到系统中的 ffmpeg、ffplay、ffprobe，则使用插件目录中的版本
    if not ffmpeg_path:
        ffmpeg_path = "ffmpeg"
    if not ffplay_path:
        ffplay_path = "ffplay"
    if not ffprobe_path:
        ffprobe_path = "ffprobe"

# 输出检测的路径
print(f"ffmpeg path: {ffmpeg_path}")
print(f"ffplay path: {ffplay_path}")
print(f"ffprobe path: {ffprobe_path}")

class VideoMerger:
    def __init__(self,console):
        super().__init__()
        self.console = console

    def merge_videos(self, file_list, output_folder, reencode=False, resolution=None):
        """合并视频文件"""
        file_list_path = self.generate_file_list(file_list)

        # 设置输出文件名
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_file = os.path.join(output_folder, f"merged_{len(file_list)}_videos_{timestamp}.mp4")

        # 根据是否重新编码生成不同的合并命令
        if reencode:
            command = self.generate_reencode_command(file_list_path, output_file, resolution)
        else:
            command = self.generate_concat_command(file_list_path, output_file)

        # 执行合并命令
        self.console.log(f"执行合并命令: {' '.join(command)}")
        subprocess.run(command, check=True)

    def generate_file_list(self, file_list):
        """生成一个临时的 file_list.txt 文件"""
        file_list_folder = os.path.join(cache_dir, "cache_video_files")

        # 检查并创建缓存文件夹和文件列表文件夹
        os.makedirs(file_list_folder, exist_ok=True)

        # 在缓存文件夹中生成 file_list.txt
        file_list_path = os.path.join(file_list_folder, "file_list.txt")
        with open(file_list_path, 'w', encoding='utf-8') as f:
            for video in file_list:
                f.write(f"file '{video}'\n")
        return file_list_path

    def generate_concat_command(self, file_list_path, output_file):
        """生成无损合并命令"""
        return [
            ffmpeg_path, "-f", "concat", "-safe", "0", "-i", file_list_path,
            "-c", "copy", output_file
        ]

    def generate_reencode_command(self, file_list_path, output_file, resolution):
        """生成重新编码的合并命令"""
        command = [
            ffmpeg_path, "-f", "concat", "-safe", "0", "-i", file_list_path,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",  # 使用 libx264 进行编码
            "-vf", f"scale={resolution}" if resolution else "scale=1920x1080",  # 分辨率
            "-c:a", "aac", "-b:a", "192k",  # 音频编码
            output_file
        ]
        return command



class SubtitleWorker(QThread):
    progress = pyqtSignal(int)
    log_signal = pyqtSignal(str)

    def __init__(self, video_files, material_folder, model_name, output_format):
        super().__init__()
        self.video_files = video_files
        self.material_folder = material_folder
        self.model_name = model_name
        self.output_format = output_format
        self.model = None

    def run(self):
        self.log_signal.emit("正在加载模型...")
        try:
            self.model = whisper.load_model(self.model_name)  # 延迟加载模型
            self.log_signal.emit(f"模型加载完成")

            total_files = len(self.video_files)
            for index, video in enumerate(self.video_files):
                video_path = os.path.join(self.material_folder, video)
                subtitle_path = re.sub(r'\.mp4$', f'.{self.output_format}', video_path, flags=re.IGNORECASE)
                # 生成字幕并保存
                self.generate_subtitles(video_path, subtitle_path)
                self.progress.emit(index + 1)
                self.log_signal.emit(f"已完成 {index + 1}/{total_files}: {subtitle_path}")
            self.log_signal.emit(f"创建索引已完成")
        except Exception as e:
            self.log_signal.emit(f"处理时发生错误: {str(e)}")

    def generate_subtitles(self, video_path, output_path):
        """从视频生成字幕并保存为指定格式"""
        subtitles = self.model.transcribe(video_path, language="zh")  # 当模型认为视频中无语音时，不生成字幕。默认0.5灵敏度适中
        # result = self.adjust_subtitle_time(subtitles, offset_seconds=1.02)
        # 向前偏移 300 毫秒，向后偏移 500 毫秒
        result = self.adjust_subtitle_time(subtitles, offset_ms=960)

        # 创建转换器
        converter = opencc.OpenCC('t2s')  # 't2s' 表示繁体转简体，'s2t' 表示简体转繁体

        # 假设 result['text'] 是 Whisper 生成的字幕

        subtitles = []
        for i, segment in enumerate(result['segments']):
            start = self.format_time(segment['start'])
            end = self.format_time(segment['end'])
            # text = segment['text']
            text = converter.convert(segment['text'])
            if self.output_format == 'srt':
                subtitles.append(f"{i + 1}\n{start} --> {end}\n{text}\n\n")
            elif self.output_format == 'vtt':
                subtitles.append(f"{i + 1}\n{start} --> {end}\n{text}\n\n")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(subtitles)

    def adjust_subtitle_time(self, subtitles, offset_ms):
        """
        调整字幕的时间戳，可以向前或向后偏移。

        :param subtitles: Whisper 模型生成的字幕结果
        :param offset_ms: 偏移时间，单位为毫秒。正数表示向后（延迟），负数表示向前（提前）。
                          建议范围：-1000 到 1000 毫秒（即最多提前或延迟 1 秒）。
        :return: 调整后的字幕
        """
        # 确保偏移值在合理范围内（避免过大偏移）
        if offset_ms < -1000 or offset_ms > 1000:
            raise ValueError("偏移时间应在 -1000 到 1000 毫秒之间")

        for segment in subtitles['segments']:
            start_ms = segment['start'] * 1000  # 秒转毫秒
            end_ms = segment['end'] * 1000  # 秒转毫秒

            # 调整时间，根据 offset_ms 的正负来向前或向后偏移
            start_ms += offset_ms
            end_ms += offset_ms

            # 确保时间戳不低于 0
            if start_ms < 0:
                start_ms = 0
            if end_ms < 0:
                end_ms = 0

            # 毫秒转回秒并更新
            segment['start'] = start_ms / 1000
            segment['end'] = end_ms / 1000

        return subtitles

    @staticmethod
    def format_time(seconds):
        """格式化时间为字幕格式"""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        return f"{int(hours):02}:{int(minutes):02}:{seconds:02},{milliseconds:03}"


class SubtitleSearchWorker(QThread):
    search_finished = pyqtSignal(list)
    log_signal = pyqtSignal(str)

    def __init__(self, keyword, material_folder):
        super().__init__()
        self.keyword = keyword.lower()
        self.material_folder = material_folder

    def run(self):
        """执行字幕搜索操作"""
        self.log_signal.emit(f"开始搜索关键字: {self.keyword}")

        subtitle_files = [f for f in os.listdir(self.material_folder) if f.endswith('.srt')]
        matches = []

        if not subtitle_files:
            self.log_signal.emit("没有找到任何索引文件，请先创建索引。")
            return

        for subtitle_file in subtitle_files:
            srt_path = os.path.join(self.material_folder, subtitle_file)
            video_file = os.path.splitext(subtitle_file)[0] + '.mp4'
            video_path = os.path.join(self.material_folder, video_file)

            with open(srt_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i in range(0, len(lines), 4):  # 假设每个字幕块由4行组成
                    timestamp = lines[i + 1].strip()  # 第二行是时间戳
                    text = lines[i + 2].strip()  # 第三行是字幕内容

                    if self.keyword in text.lower():
                        # 解析时间戳，获取开始和结束时间
                        start_time, end_time = self.parse_srt_timestamp(timestamp)
                        matches.append((video_path, srt_path, text, start_time, end_time))

        self.search_finished.emit(matches)
        self.log_signal.emit(f"搜索完成，共找到 {len(matches)} 个匹配结果。")

    @staticmethod
    def time_to_milliseconds(time_str):
        """将时间字符串转换为毫秒数"""
        hours, minutes, seconds = time_str.split(':')
        seconds, milliseconds = seconds.split(',')
        total_ms = (int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000 + int(milliseconds)
        return total_ms

    def parse_srt_timestamp(self, timestamp):
        """解析 SRT 文件中的时间戳"""
        start, end = timestamp.split(' --> ')
        start_ms = self.time_to_milliseconds(start)
        end_ms = self.time_to_milliseconds(end)
        return start_ms, end_ms


class subtitle_editing(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.subtitle_items = []  # 存储字幕信息的列表
        self.last_focused_input = None  # 记录最后一次获得焦点的输入框
        self.search_results = []  # 保存搜索匹配项的索引
        self.current_search_index = -1  # 当前搜索结果的索引

    def init_ui(self):
        """初始化UI，使用网格布局"""

        # 创建主网格布局 QGridLayout，并设置列的伸缩比例
        self.main_layout = QGridLayout()  # 创建主布局 main_layout
        self.main_layout.setColumnStretch(0, 1)  # 第一列的宽度比例为 1
        self.main_layout.setColumnStretch(1, 2)  # 第二列的宽度比例为 2
        self.main_layout.setColumnStretch(2, 2)  # 第三列的宽度比例为 2
        self.main_layout.setColumnStretch(3, 2)  # 第四列的宽度比例为 2

        # 初始化4个子布局，分别管理4个区域
        self.first_layout = QGridLayout()  # 第一列布局，主要放文件夹选择及素材列表
        self.second_layout = QGridLayout()  # 第二列布局，主要放搜索字幕及结果展示
        self.thirdly_layout = QGridLayout()  # 第三列上部布局，主要用于字幕搜索和编辑
        self.fourthly_layout = QGridLayout()  # 第四列上部布局，主要用于视频播放

        # 素材文件夹选择部分
        material_browse_button_layout = QHBoxLayout()  # 水平布局，放置两个按钮
        material_folder_label = QLabel('素材文件夹:')  # 标签，用于提示素材文件夹输入
        self.material_folder = QLineEdit()  # 输入框，用于输入素材文件夹路径
        material_browse_button = QPushButton('浏览')  # 浏览按钮，点击后可以选择文件夹
        material_browse_button.clicked.connect(self.browse_material_folder)  # 绑定浏览按钮点击事件
        open_material_folder_button = QPushButton("打开")  # 打开按钮，点击后打开选中的文件夹
        open_material_folder_button.clicked.connect(self.open_material_folder)  # 绑定打开按钮点击事件
        material_browse_button_layout.addWidget(material_browse_button)
        material_browse_button_layout.addWidget(open_material_folder_button)

        # 将素材文件夹选择的控件放入 first_layout 中，指定其占用的行列
        self.first_layout.addWidget(material_folder_label, 0, 0, 1, 3)  # 标签，占据第0行，跨3列
        self.first_layout.addWidget(self.material_folder, 1, 0, 1, 3)  # 输入框，占据第1行，跨3列
        self.first_layout.addLayout(material_browse_button_layout, 2, 0, 1, 3)  # 浏览按钮，占据第2行第0列

        # 输出文件夹选择部分
        output_browse_button_layout = QHBoxLayout()  # 水平布局，放置两个按钮
        output_folder_layout = QLabel('输出文件夹:')  # 标签，用于提示输出文件夹输入
        self.output_folder = QLineEdit()  # 输入框，用于输入输出文件夹路径
        output_browse_button = QPushButton('浏览')  # 浏览按钮，点击后可以选择文件夹
        output_browse_button.clicked.connect(self.browse_output_folder)  # 绑定浏览按钮点击事件
        open_output_folder_button = QPushButton("打开")  # 打开按钮，点击后打开选中的文件夹
        open_output_folder_button.clicked.connect(self.open_output_folder)  # 绑定打开按钮点击事件
        output_browse_button_layout.addWidget(output_browse_button)
        output_browse_button_layout.addWidget(open_output_folder_button)

        # 将输出文件夹选择部分的控件放入 first_layout 中
        self.first_layout.addWidget(output_folder_layout, 3, 0, 1, 3)  # 标签，占据第3行，跨3列
        self.first_layout.addWidget(self.output_folder, 4, 0, 1, 3)  # 输入框，占据第4行，跨3列
        self.first_layout.addLayout(output_browse_button_layout, 5, 0, 1, 3)  # 浏览按钮，占据第5行第0列

        # 第二列部分：清除索引和创建索引按钮放在同一行
        button_layout = QHBoxLayout()  # 水平布局，放置两个按钮

        # 清除索引按钮
        clear_index_button = QPushButton("清除索引")  # 清除按钮
        clear_index_button.clicked.connect(self.clear_index)  # 绑定点击事件
        button_layout.addWidget(clear_index_button)  # 将按钮添加到水平布局中

        # 创建索引按钮
        start_button = QPushButton("创建索引")  # 创建按钮
        start_button.clicked.connect(self.start_processing)  # 绑定点击事件
        button_layout.addWidget(start_button)  # 将按钮添加到水平布局中

        # 将按钮布局添加到 second_layout 中，放在第0行，占据2列
        self.first_layout.addLayout(button_layout, 6, 0, 1, 3)
        # 素材列表部分
        material_list_label = QLabel("素材列表")  # 标签，提示用户素材列表
        self.material_list = QListWidget()  # 列表控件，显示素材文件列表
        self.material_list.itemClicked.connect(self.on_material_item_clicked)  # 绑定素材列表点击事件

        # 将素材列表控件添加到 first_layout 中
        self.first_layout.addWidget(material_list_label, 7, 0, 1, 3)  # 标签，占据第6行，跨3列
        self.first_layout.addWidget(self.material_list, 8, 0, 1, 3)  # 列表，占据第7行，跨3列

        # 刷新按钮
        refresh_button = QPushButton("刷新")  # 刷新按钮
        self.first_layout.addWidget(refresh_button, 9, 1, 1, 1)  # 刷新按钮，占据第8行第1列

        # 搜索字幕区域
        self.search_input = QLineEdit()  # 搜索输入框
        self.second_layout.addWidget(self.search_input, 0, 0, 1, 2)  # 搜索输入框，占据第1行第0列
        search_button = QPushButton('搜索字幕')  # 搜索按钮
        search_button.clicked.connect(self.search_subtitle)  # 绑定搜索按钮点击事件
        self.second_layout.addWidget(search_button, 0, 2, 1, 1)  # 搜索按钮，占据第1行第1列

        self.clip_start_time_input = QLineEdit()
        self.clip_start_time_input.setPlaceholderText("开始时间")
        self.clip_end_time_input = QLineEdit()
        self.clip_end_time_input.setPlaceholderText("结束时间")
        display_clip_button = QPushButton("剪辑")
        display_clip_button.clicked.connect(self.clip_selected_video)  # 剪辑按钮点击事件
        self.second_layout.addWidget(self.clip_start_time_input, 1, 0, 1, 1)  # 列表控件，占据第2行，跨2列
        self.second_layout.addWidget(self.clip_end_time_input, 1, 1, 1, 1)  # 列表控件，占据第2行，跨2列
        self.second_layout.addWidget(display_clip_button, 1, 2, 1, 1)  # 列表控件，占据第2行，跨2列

        # 搜索结果展示区域
        self.display_area = QListWidget()  # 搜索结果展示列表
        # self.display_area = ListWidgetWithButtons()  # 使用封装的带按钮和右键菜单的列表
        self.second_layout.addWidget(self.display_area, 2, 0, 1, 3)  # 列表控件，占据第2行，跨2列
        self.display_area.itemClicked.connect(self.on_video_selected)  # 绑定点击事件

        # 日志显示区域
        # ------ Console 上方添加 Label ------
        console_label = QLabel("日志信息")
        self.second_layout.addWidget(console_label, 3, 0, 1, 3)  # 将 Label 放到日志显示区域上方
        self.console = ConsoleBox(self)  # 日志显示控件
        self.second_layout.addWidget(self.console, 5, 0, 2, 3)  # 日志控件占据第5行和第6行，跨2列

        # 字幕搜索区域（第三列上部）
        search_layout = QHBoxLayout()  # 水平布局，放置字幕搜索相关控件
        self.subtitle_search_input = QLineEdit()  # 字幕搜索输入框
        search_button = QPushButton('搜索')  # 字幕搜索按钮
        self.subtitle_search_input.setPlaceholderText("搜索字幕内容")  # 设置占位符
        search_button.clicked.connect(self.search_in_subtitles)  # 绑定搜索按钮点击事件

        # 上一个、下一个按钮
        prev_button = QPushButton("上一个")  # 上一个按钮
        next_button = QPushButton("下一个")  # 下一个按钮
        prev_button.clicked.connect(self.select_previous_result)  # 绑定上一个按钮点击事件
        next_button.clicked.connect(self.select_next_result)  # 绑定下一个按钮点击事件

        # 将所有控件添加到字幕搜索布局中
        search_layout.addWidget(self.subtitle_search_input)
        search_layout.addWidget(search_button)
        search_layout.addWidget(prev_button)
        search_layout.addWidget(next_button)

        # 将字幕搜索布局添加到 thirdly_layout 中，占据第0行，跨4列
        self.thirdly_layout.addLayout(search_layout, 0, 0, 1, 4)

        # 开始字幕时间输入框
        start_time_layout = QHBoxLayout()  # 水平布局，用于开始时间输入框
        self.start_time_input = QLineEdit()  # 输入框，输入字幕开始时间
        start_time_layout.addWidget(QLabel('开始字幕:'))  # 标签，提示用户输入开始时间
        start_time_layout.addWidget(self.start_time_input)  # 输入框，用户输入开始时间
        self.start_time_input.installEventFilter(self)  # 监听焦点事件
        self.thirdly_layout.addLayout(start_time_layout, 1, 0, 1, 3)  # 放在第1行，占据4列

        # 结束字幕时间输入框
        end_time_layout = QHBoxLayout()  # 水平布局，用于结束时间输入框
        self.end_time_input = QLineEdit()  # 输入框，用于输入字幕结束时间
        end_time_layout.addWidget(QLabel('结束字幕:'))  # 标签，提示用户输入结束时间
        end_time_layout.addWidget(self.end_time_input)  # 输入框，用户输入结束时间
        self.end_time_input.installEventFilter(self)  # 监听焦点事件，便于时间输入处理
        self.thirdly_layout.addLayout(end_time_layout, 2, 0, 1, 3)  # 将结束时间布局放在第2行，占据4列

        clip_section_btn = QPushButton("剪辑")  # 向上按钮，用于操作字幕列表
        clip_section_btn.clicked.connect(self.clip_selected_segment)  # 绑定单击事件
        self.thirdly_layout.addWidget(clip_section_btn, 1, 3, 2, 1)  # 将结束时间布局放在第2行，占据4列

        # 字幕展示区域（用于显示字幕列表）
        self.subtitle_list = QListWidget()  # 列表控件，用于显示字幕列表
        self.thirdly_layout.addWidget(self.subtitle_list, 3, 0, 1, 4)  # 列表控件放在第3行，占据4列
        # 用户点击字幕列表中的某个字幕时播放对应的视频片段
        self.subtitle_list.itemClicked.connect(self.on_subtitle_selected)  # 绑定单击事件
        self.subtitle_list.itemDoubleClicked.connect(self.on_subtitle_double_clicked)  # 绑定双击事件

        # 视频播放器部分（第四列上部）
        self.video_player = VideoPlayerWidget(self)  # 视频播放器控件
        self.fourthly_layout.addWidget(self.video_player, 0, 0, 1, 4)  # 视频播放器占据第0行，占4列

        # 操作按钮组部分
        operate_button_group = QHBoxLayout()  # 水平布局，用于放置操作按钮
        delete_button = QPushButton("删除")  # 创建删除按钮
        clear_cache_button = QPushButton("清除缓存")
        refresh_button = QPushButton("刷新")
        up_btn = QPushButton("向上")  # 向上按钮，用于操作字幕列表
        down_btn = QPushButton("向下")  # 向下按钮，用于操作字幕列表
        top_btn = QPushButton("置顶")  # 置顶按钮，用于操作字幕列表
        bottom_button = QPushButton("置底")  # 置底按钮，用于操作字幕列表
        marge_button = QPushButton("合并")  # 合并按钮，用于操作字幕合并
        operate_button_group.addWidget(delete_button)  # 将"向上"按钮加入布局
        operate_button_group.addWidget(clear_cache_button)  # 将按钮添加到按钮组布局中
        operate_button_group.addWidget(refresh_button)  # 将按钮添加到按钮组布局中
        operate_button_group.addWidget(up_btn)  # 将"向上"按钮加入布局
        operate_button_group.addWidget(down_btn)  # 将"向下"按钮加入布局
        operate_button_group.addWidget(top_btn)  # 将"置顶"按钮加入布局
        operate_button_group.addWidget(bottom_button)  # 将"置底"按钮加入布局
        operate_button_group.addWidget(marge_button)  # 将"合并"按钮加入布局

        delete_button.clicked.connect(self.delete_item)  # 绑定“删除”按钮事件
        clear_cache_button.clicked.connect(self.clear_cache)  # 绑定按钮点击事件
        refresh_button.clicked.connect(self.refresh_cache)  # 绑定按钮点击事件
        up_btn.clicked.connect(self.move_up)  # 绑定“向上”按钮事件
        down_btn.clicked.connect(self.move_down)  # 绑定“向下”按钮事件
        top_btn.clicked.connect(self.move_to_top)  # 绑定“置顶”按钮事件
        bottom_button.clicked.connect(self.move_to_bottom)  # 绑定“置底”按钮事件
        marge_button.clicked.connect(self.merge_videos)  # 绑定“合并”按钮事件

        # 结果显示区域，用于显示操作结果（第三列和第四列的下半部分）
        self.result_display = QListWidget()  # 列表控件，用于显示操作结果
        self.result_display.itemClicked.connect(self.on_result_item_clicked)
        # 调整行高，扩大显示区域，跨越第三列和第四列的下半部分
        self.main_layout.addWidget(self.result_display, 6, 2, 2, 2)  # 放在第3行，跨两列，跨2行
        self.main_layout.addLayout(operate_button_group, 8, 2, 1, 2)  # 将操作按钮组放在第4行，跨两列

        # 将四部分添加到主布局中
        self.main_layout.addLayout(self.first_layout, 0, 0, 9, 1)  # 第一列，跨5行1列
        self.main_layout.addLayout(self.second_layout, 0, 1, 9, 1)  # 第二列，跨5行1列
        self.main_layout.addLayout(self.thirdly_layout, 0, 2, 6, 1)  # 第三列上半部分，占3行1列
        self.main_layout.addLayout(self.fourthly_layout, 0, 3, 6, 1)  # 第四列上半部分，占3行1列

        # 设置主布局
        self.setLayout(self.main_layout)  # 设置窗口的主布局为主网格布局

    def merge_videos(self):
        """合并 result_display 中的所有视频条目，确认合并并选择导出目录"""
        output_folder = self.output_folder.text()
        if not output_folder or not os.path.exists(output_folder):
            QMessageBox.warning(self, "错误", "请选择有效的输出文件夹")
            return

        if self.result_display.count() == 0:
            self.console.log("没有视频可供合并")
            QMessageBox.warning(self, "错误", "没有视频可供合并")
            return

        # 弹出确认对话框
        dialog = QMessageBox(self)
        dialog.setWindowTitle("确认合并")
        dialog.setText("是否确认合并选中的视频文件？")
        dialog.setIcon(QMessageBox.Question)

        # 添加复选框，用户选择是否自定义导出路径
        custom_export_checkbox = QCheckBox("自定义导出目录", dialog)
        dialog.setCheckBox(custom_export_checkbox)

        # 添加确认和取消按钮
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        reply = dialog.exec()

        if reply == QMessageBox.Yes:
            # 如果选择了自定义导出目录，弹出目录选择对话框
            if custom_export_checkbox.isChecked():
                custom_folder = QFileDialog.getExistingDirectory(self, '选择导出目录')
                if not custom_folder:
                    self.console.log("用户取消了目录选择，取消合并")
                    return
                output_folder = custom_folder  # 使用用户选择的导出目录

            # 收集 result_display 中的视频文件路径
            file_list = []
            for i in range(self.result_display.count()):
                video_path = self.result_display.item(i).text()
                file_list.append(video_path)

            # 询问是否重新编码
            reencode = self.ask_user_for_reencode()

            # 获取原始分辨率，如果需要重新编码
            if reencode:
                resolution = self.get_original_resolution(file_list[0])  # 获取第一个视频的分辨率
            else:
                resolution = None

            # 调用 VideoMerger 类中的方法来合并视频
            video_merger = VideoMerger(self.console)  # 假设 console 是日志控件
            try:
                video_merger.merge_videos(file_list, output_folder, reencode=reencode, resolution=resolution)
                self.console.log(f"视频已成功合并并保存到: {output_folder}")
                QMessageBox.information(self, "成功", f"视频已成功合并并保存到: {output_folder}")
            except subprocess.CalledProcessError as e:
                self.console.log(f"合并视频时发生错误: {str(e)}")
                QMessageBox.warning(self, "合并错误", "视频合并失败，请检查ffmpeg配置")

    def ask_user_for_reencode(self):
        """询问用户是否需要重新编码"""
        reply = QMessageBox.question(self, '重新编码', '是否需要重新编码视频？', QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        return reply == QMessageBox.Yes

    def get_original_resolution(self, video_path):
        """获取视频的原始分辨率"""
        try:
            command = [
                ffprobe_path, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                "-of", "csv=s=x:p=0", video_path
            ]
            output = subprocess.check_output(command).decode('utf-8').strip()
            return output  # 返回类似 "1920x1080" 的分辨率
        except subprocess.CalledProcessError as e:
            self.console.log(f"获取分辨率时出错: {str(e)}")
            return "1920x1080"  # 默认分辨率

    def clear_cache(self):
        """清除缓存目录中的所有文件和文件夹"""

        if not os.path.exists(cache_dir):
            self.console.log("缓存目录不存在，无需清理")
            return

        # 弹出确认对话框
        reply = QMessageBox.question(self, '确认清除缓存',
                                     '是否确认清除缓存目录中的所有文件？此操作不可撤销。',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                # 清除缓存目录中的所有内容（不删除缓存目录本身）
                for root, dirs, files in os.walk(cache_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        os.remove(file_path)
                    for dir in dirs:
                        dir_path = os.path.join(root, dir)
                        shutil.rmtree(dir_path)

                self.console.log("缓存目录已成功清空")
                self.result_display.clear()
            except Exception as e:
                self.console.log(f"清空缓存目录时发生错误: {str(e)}")
                QMessageBox.warning(self, "清除错误", f"无法清除缓存: {str(e)}")
        else:
            self.console.log("取消清除缓存操作")

    def refresh_cache(self):
        """刷新 result_display，加载缓存目录下的视频片段"""
        # 获取项目根目录下的缓存目录
        video_clips_folder = os.path.join(cache_dir, "cache_video_fragment")

        # 如果缓存目录或视频片段目录不存在，提示用户
        if not os.path.exists(video_clips_folder):
            self.console.log("缓存已刷新")
            return

        # 清空 result_display
        self.result_display.clear()

        # 定义正则表达式来匹配视频文件扩展名，并忽略大小写
        pattern = re.compile(r'\.(mp4|avi|mkv|mov)$', re.IGNORECASE)

        # 使用正则表达式来检查文件的扩展名是否匹配
        video_files = [f for f in os.listdir(video_clips_folder) if pattern.search(f)]

        if video_files:
            for video in video_files:
                # 构造每个视频的完整路径
                video_path = os.path.join(video_clips_folder, video)
                self.result_display.addItem(video_path)  # 将视频路径添加到 result_display
            self.console.log(f"找到 {len(video_files)} 个视频片段并加载到列表中")
        else:
            self.console.log("缓存目录中没有找到任何视频文件")

    def on_result_item_clicked(self, item):
        """当用户点击 result_display 中的某个视频时播放该视频"""
        video_path = item.text()  # 获取条目中文件的路径
        if os.path.exists(video_path):
            self.play_video(video_path)
        else:
            self.console.log(f"视频文件不存在: {video_path}")

    def move_up(self):
        """将选中的视频条目向上移动"""
        current_row = self.result_display.currentRow()
        if current_row > 0:
            current_item = self.result_display.takeItem(current_row)
            self.result_display.insertItem(current_row - 1, current_item)
            self.result_display.setCurrentRow(current_row - 1)

    def move_down(self):
        """将选中的视频条目向下移动"""
        current_row = self.result_display.currentRow()
        if current_row < self.result_display.count() - 1:
            current_item = self.result_display.takeItem(current_row)
            self.result_display.insertItem(current_row + 1, current_item)
            self.result_display.setCurrentRow(current_row + 1)

    def move_to_top(self):
        """将选中的视频条目置顶"""
        current_row = self.result_display.currentRow()
        if current_row > 0:
            current_item = self.result_display.takeItem(current_row)
            self.result_display.insertItem(0, current_item)
            self.result_display.setCurrentRow(0)

    def move_to_bottom(self):
        """将选中的视频条目置底"""
        current_row = self.result_display.currentRow()
        if current_row < self.result_display.count() - 1:
            current_item = self.result_display.takeItem(current_row)
            self.result_display.addItem(current_item)
            self.result_display.setCurrentRow(self.result_display.count() - 1)

    def delete_item(self):
        """删除选中的视频条目，弹出确认对话框，用户选择是否删除本地文件"""
        current_row = self.result_display.currentRow()
        if current_row >= 0:
            # 获取选中的条目
            item = self.result_display.item(current_row)
            video_path = item.text()  # 获取文件路径

            # 弹出确认对话框
            dialog = QMessageBox(self)
            dialog.setWindowTitle("确认删除")
            dialog.setText(f"是否确认删除选中的文件？\n{video_path}")
            dialog.setIcon(QMessageBox.Warning)

            # 添加复选框，用户选择是否删除本地文件
            delete_local_file_checkbox = QCheckBox("同时删除本地目录中的文件", dialog)
            dialog.setCheckBox(delete_local_file_checkbox)

            # 添加确认和取消按钮
            dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            reply = dialog.exec()

            if reply == QMessageBox.Yes:
                # 如果用户选择了同时删除本地文件，执行删除本地文件的操作
                if delete_local_file_checkbox.isChecked():
                    if os.path.exists(video_path):
                        try:
                            os.remove(video_path)
                            self.console.log(f"本地文件已删除: {video_path}")
                        except OSError as e:
                            self.console.log(f"删除本地文件时发生错误: {e}")
                            QMessageBox.warning(self, "删除错误", f"无法删除文件：{video_path}")
                    else:
                        self.console.log(f"文件不存在或已删除: {video_path}")
                else:
                    self.console.log(f"仅从列表中删除：{video_path}")

                # 从 result_display 列表中删除条目
                self.result_display.takeItem(current_row)

    def on_material_item_clicked(self, item):
        """当用户点击素材列表中的某个视频时，弹出视频播放对话框"""
        video_file = item.text()
        material_folder = self.material_folder.text()
        video_path = os.path.join(material_folder, video_file)

        if os.path.exists(video_path):
            self.show_subtitles(video_path)
            # 弹出视频播放对话框并播放选中的视频文件
            self.play_video(video_path)
        else:
            QMessageBox.warning(self, "错误", "视频文件不存在")

    def play_video(self, video_path, start_time=None, end_time=None):
        """播放整个视频或指定片段"""
        self.video_player.play_video(video_path, start_time, end_time)
        # # 加载视频文件
        # dialog.player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        #
        # # 如果有指定的开始时间，跳转到该时间
        # if start_time is not None:
        #     dialog.player.setPosition(start_time)  # 转换为毫秒
        #     dialog.player.play()
        #
        #     # 如果有结束时间，设置一个定时器在结束时间暂停
        #     if end_time is not None:
        #         duration_ms = (end_time - start_time)  # 计算需要播放的时长
        #         QTimer.singleShot(duration_ms, dialog.player.pause)
        # else:
        #     # 否则播放整个视频
        #     dialog.player.play()

    @staticmethod
    def format_time(ms):
        """格式化时间为 HH:MM:SS"""
        seconds = ms // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def browse_material_folder(self):
        """浏览素材文件夹"""
        folder = QFileDialog.getExistingDirectory(self, '选择素材文件夹')
        if folder:
            self.material_folder.setText(folder)
            self.update_material_list(folder)  # 更新素材列表

    def update_material_list(self, folder):
        """根据选择的素材文件夹更新素材列表"""
        self.material_list.clear()  # 清空现有的列表内容
        pattern = re.compile(r'\.(mp4|avi|mkv|mov)$', re.IGNORECASE)
        video_files = [f for f in os.listdir(folder) if pattern.search(f)]

        if video_files:
            for video in video_files:
                self.material_list.addItem(video)
            self.console.log(f"找到 {len(video_files)} 个视频文件")
        else:
            self.console.log("未找到任何视频文件")

    def browse_output_folder(self):
        """浏览输出文件夹"""
        folder = QFileDialog.getExistingDirectory(self, '选择输出文件夹')
        if folder:
            self.output_folder.setText(folder)

    def open_material_folder(self):
        """打开素材文件夹"""
        folder = self.material_folder.text()
        if os.path.exists(folder):
            open_folder(folder)
        else:
            QMessageBox.warning(self, "错误", "素材文件夹不存在")

    def open_output_folder(self):
        """打开输出文件夹"""
        folder = self.output_folder.text()
        if os.path.exists(folder):
            open_folder(folder)
        else:
            QMessageBox.warning(self, "错误", "输出文件夹不存在")

    # def open_folder(self, folder):
    #     """根据操作系统打开文件夹"""
    #     system_platform = platform.system()
    #     if system_platform == "Windows":
    #         os.startfile(folder)  # Windows
    #     elif system_platform == "Darwin":  # macOS
    #         subprocess.run(["open", folder])
    #     elif system_platform == "Linux":  # Linux
    #         subprocess.run(["xdg-open", folder])

    def on_video_selected(self, item):
        """当用户点击搜索结果中的某个字幕片段时，打开子窗口播放视频"""
        video_file, _, start_time, end_time = item.data(Qt.UserRole)
        # # 将开始时间和结束时间从毫秒转化为秒
        # start_time_seconds = start_time / 1000
        # end_time_seconds = end_time / 1000

        # 将开始和结束时间填入输入框中
        self.clip_start_time_input.setText(self.format_time2(start_time))
        self.clip_end_time_input.setText(self.format_time2(end_time))

        self.show_subtitles(video_file)
        # 创建一个新的视频播放器对话框
        self.play_video(video_file, start_time, end_time)

    def show_subtitles(self,video_file):
        # 清空字幕展示区域
        self.subtitle_list.clear()
        self.subtitle_items = []  # 清空字幕列表

        # 假设有个方法 load_subtitles_for_video 从视频加载字幕
        subtitles = self.load_subtitles_for_video(video_file)
        for subtitle in subtitles:
            subtitle_item = QListWidgetItem(subtitle['text'])
            subtitle_item.setData(Qt.UserRole, (video_file, subtitle['start_time'], subtitle['end_time']))
            self.subtitle_list.addItem(subtitle_item)
            self.subtitle_items.append(subtitle)  # 保存字幕信息

    def load_subtitles_for_video(self, video_file):
        """从视频文件加载字幕（假设有对应的 .srt 文件）"""
        # 假设字幕文件是 .srt 格式，并与视频文件同名
        srt_file = os.path.splitext(video_file)[0] + '.srt'
        subtitles = []
        if os.path.exists(srt_file):
            with open(srt_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i in range(0, len(lines), 4):  # 假设每4行是一个字幕块
                    timestamp = lines[i + 1].strip()
                    text = lines[i + 2].strip()
                    start_time, end_time = self.parse_srt_timestamp(timestamp)
                    subtitles.append({'start_time': start_time, 'end_time': end_time, 'text': text})
        return subtitles

    def update_subtitle_selection(self):
        """根据当前视频的播放时间更新右侧字幕选中状态"""
        current_position = self.player.position()  # 获取当前播放时间 (毫秒)
        for i, subtitle in enumerate(self.subtitle_items):
            start_time = subtitle['start_time']
            end_time = subtitle['end_time']
            if start_time <= current_position <= end_time:
                self.subtitle_list.setCurrentRow(i)  # 自动选中当前播放的字幕
                self.subtitle_list.scrollToItem(self.subtitle_list.currentItem(), QListWidget.PositionAtCenter)
                break

    @staticmethod
    def parse_srt_timestamp(timestamp):
        """解析 SRT 文件中的时间戳"""
        start, end = timestamp.split(' --> ')
        start_ms = SubtitleSearchWorker.time_to_milliseconds(start)
        end_ms = SubtitleSearchWorker.time_to_milliseconds(end)
        return start_ms, end_ms

    def eventFilter(self, obj, event):
        """捕获焦点事件"""
        if event.type() == event.FocusIn:
            if obj == self.start_time_input:
                self.last_focused_input = self.start_time_input
            elif obj == self.end_time_input:
                self.last_focused_input = self.end_time_input
        return super().eventFilter(obj, event)

    def search_in_subtitles(self):
        """在字幕列表中搜索用户输入的关键字"""
        """在字幕列表中搜索用户输入的关键字"""
        search_text = self.subtitle_search_input.text().lower()  # 获取用户输入并转换为小写
        if not search_text:
            QMessageBox.warning(self, "搜索错误", "请输入要搜索的字幕内容")
            return

        # 重置搜索结果
        self.search_results = []
        self.current_search_index = -1

        # 遍历字幕列表，找到所有匹配的项
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            subtitle_text = item.text().lower()  # 将字幕内容转换为小写进行匹配

            if search_text in subtitle_text:
                # 保存匹配的项的索引
                self.search_results.append(i)

        if self.search_results:
            self.console.log(f"找到 {len(self.search_results)} 个匹配结果")
            # 默认选中第一个匹配项
            self.current_search_index = 0
            self.select_search_result(self.current_search_index)
        else:
            self.console.log("未找到匹配的字幕内容")

    def select_search_result(self, index):
        """根据给定的索引选中并滚动到对应的字幕项"""
        if index >= 0 and index < len(self.search_results):
            result_index = self.search_results[index]
            item = self.subtitle_list.item(result_index)
            self.subtitle_list.setCurrentRow(result_index)
            self.subtitle_list.scrollToItem(item, QListWidget.PositionAtCenter)
            self.console.log(f"当前选择: {item.text()}")

    def select_next_result(self):
        """选择下一个匹配的搜索结果"""
        if self.current_search_index == -1 or not self.search_results:
            self.console.log("没有更多匹配的结果")
            return

        if self.current_search_index < len(self.search_results) - 1:
            self.current_search_index += 1
            self.select_search_result(self.current_search_index)
        else:
            self.console.log("已到最后一个匹配结果")

    def select_previous_result(self):
        """选择上一个匹配的搜索结果"""
        if self.current_search_index == -1 or not self.search_results:
            self.console.log("没有更多匹配的结果")
            return

        if self.current_search_index > 0:
            self.current_search_index -= 1
            self.select_search_result(self.current_search_index)
        else:
            self.console.log("已到第一个匹配结果")

    def on_subtitle_double_clicked(self, item):
        """当用户双击字幕时，将时间显示到最后一个获得焦点的输入框"""
        video_file, start_time, end_time = item.data(Qt.UserRole)
        text = item.text()  # 获取字幕文本内容

        # 判断最后一次获得焦点的输入框
        if self.last_focused_input == self.start_time_input:
            # 将字幕文本和开始时间一起显示在开始字幕输入框中
            self.start_time_input.setText(f"{text} [{self.format_time2(start_time)}]")
            self.console.log(f"开始时间和文本已设置为: {text} [{self.format_time2(start_time)}]")
        elif self.last_focused_input == self.end_time_input:
            # 将字幕文本和结束时间一起显示在结束字幕输入框中
            self.end_time_input.setText(f"{text} [{self.format_time2(end_time)}]")
            self.console.log(f"结束时间和文本已设置为: {text} [{self.format_time2(end_time)}]")
        else:
            self.console.log("请先点击'开始字幕'或'结束字幕'输入框，然后双击字幕时间。")

    def format_time2(self, ms):
        """将毫秒转换为 HH:MM:SS,mmm 格式"""
        seconds = ms // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        milliseconds = ms % 1000
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

    def on_subtitle_selected(self, item):
        """当用户点击字幕列表中的某个字幕时，播放对应的视频片段"""
        """当用户点击字幕列表中的某个字幕时，播放对应的视频片段"""
        video_file, start_time, end_time = item.data(Qt.UserRole)
        self.play_video(video_file, start_time, end_time)

    def start_processing(self):
        """启动生成字幕的线程"""
        material_folder = self.material_folder.text()
        if not material_folder or not os.path.exists(material_folder):
            QMessageBox.warning(self, "错误", "请选择有效的素材文件夹")
            return
        pattern = re.compile(r'\.(mp4|avi|mkv|mov)$', re.IGNORECASE)
        video_files = [f for f in os.listdir(material_folder) if pattern.search(f)]
        if not video_files:
            self.console.log("素材文件夹中没有找到任何视频文件。")
            return

        self.console.log(f"开始处理 {len(video_files)} 个视频文件...")

        # 启动后台线程生成字幕
        self.worker = SubtitleWorker(
            video_files=video_files,
            material_folder=material_folder,
            # model_name=self.model_combo.currentText(),
            # output_format=self.format_combo.currentText()
            model_name='base',
            output_format='srt'
        )
        self.worker.log_signal.connect(self.console.log)
        self.worker.start()

    def search_subtitle(self):
        """启动字幕搜索的线程"""
        keyword = self.search_input.text()
        material_folder = self.material_folder.text()
        if not keyword or not material_folder:
            QMessageBox.warning(self, "错误", "请输入搜索关键字和素材文件夹")
            return

        self.display_area.clear()

        self.search_worker = SubtitleSearchWorker(keyword, material_folder)
        self.search_worker.search_finished.connect(self.display_search_results)
        self.search_worker.log_signal.connect(self.console.log)
        self.search_worker.start()

    def display_search_results(self, matches):
        """显示搜索结果"""
        for video_path, srt_path, subtitle_text, start_time, end_time in matches:
            # 展示视频文件名 + 字幕匹配文本
            display_text = f"{video_path} - {subtitle_text} ({start_time // 1000}s - {end_time // 1000}s)"
            item = QListWidgetItem(display_text)
            # 为每个 QListWidgetItem 存储实际的视频路径、开始和结束时间，便于播放时使用
            item.setData(Qt.UserRole, (video_path, srt_path, start_time, end_time))
            self.display_area.addItem(item)

    def clip_selected_video(self):
        """根据 display_area 中选中的视频，结合输入框中的开始和结束时间进行剪辑"""
        # 获取开始时间和结束时间输入框的内容
        start_time_str = self.clip_start_time_input.text().strip()
        end_time_str = self.clip_end_time_input.text().strip()

        if not start_time_str or not end_time_str:
            QMessageBox.warning(self, "错误", "请填写完整的开始时间和结束时间")
            return

        # 转换时间为毫秒
        start_time = self.parse_time_input(start_time_str)
        end_time = self.parse_time_input(end_time_str)

        # 检查时间的有效性
        if start_time is None or end_time is None or start_time >= end_time:
            QMessageBox.warning(self, "错误", "开始时间不能晚于或等于结束时间")
            return

        # 获取选中的视频文件
        selected_item = self.display_area.currentItem()
        if selected_item is not None:
            video_path, _, _, _ = selected_item.data(Qt.UserRole)
            self.clip_video_segment(video_path, start_time, end_time)
        else:
            QMessageBox.warning(self, "错误", "请先选择一个视频片段")

    def clip_selected_segment(self):
        """根据开始和结束时间剪辑视频片段"""
        # 获取输入框中的文本
        start_time_str = self.extract_time_from_input(self.start_time_input.text())
        end_time_str = self.extract_time_from_input(self.end_time_input.text())

        # 检查输入是否为空
        if not start_time_str or not end_time_str:
            QMessageBox.warning(self, "错误", "请填写完整的开始时间和结束时间")
            return

        # 转换时间为毫秒
        start_time = self.parse_time_input(start_time_str)
        end_time = self.parse_time_input(end_time_str)

        # 检查时间的有效性
        if start_time is None or end_time is None or start_time >= end_time:
            QMessageBox.warning(self, "错误", "开始时间不能晚于或等于结束时间")
            return

        # 获取选中的视频文件
        selected_item = self.display_area.currentItem()
        selected_item2 = self.material_list.currentItem()
        if selected_item:
            video_path, _, _, _ = selected_item.data(Qt.UserRole)
            self.clip_video_segment(video_path, start_time, end_time)
        elif selected_item2:
            material_folder = self.material_folder.text()
            video_path = os.path.join(material_folder, selected_item2.text())
            self.clip_video_segment(video_path, start_time, end_time)
        else:
            QMessageBox.warning(self, "错误", "请先选择一个视频片段")

    def extract_time_from_input(self, input_text):
        """从输入框中的文本提取时间，格式为 [HH:MM:SS,mmm]"""
        # 使用正则表达式匹配时间格式 [HH:MM:SS,mmm]
        match = re.search(r'\[(\d{2}:\d{2}:\d{2},\d{3})\]', input_text)
        if match:
            return match.group(1)  # 返回匹配的时间部分，例如 00:01:23,456
        else:
            QMessageBox.warning(self, "错误", f"无法从文本中提取时间: {input_text}")
            return None

    def parse_time_input(self, time_str):
        """将 HH:MM:SS,mmm 格式转换为毫秒"""
        try:
            # 按照时间格式解析，获取小时、分钟、秒和毫秒
            hours, minutes, seconds = time_str.split(':')
            seconds, milliseconds = seconds.split(',')
            return (int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000 + int(milliseconds)
        except ValueError:
            QMessageBox.warning(self, "错误", "时间格式不正确，请使用 HH:MM:SS,mmm 格式")
            return None

    def on_clipping(self):
        selected_item = self.display_area.currentItem()
        if selected_item:
            video_path, srt_path, start_time, end_time = selected_item.data(Qt.UserRole)
            self.console.log(
                f"开始剪辑视频片段: {video_path} 从 {self.format_time2(start_time)} 到 {self.format_time2(end_time)}")
            self.clip_video_segment(video_path, start_time, end_time)
        else:
            QMessageBox.warning(self, "错误", "请先选择要剪辑的字幕片段")

    def get_video_duration(self, video_path):
        command = [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video_path]
        try:
            duration = float(subprocess.check_output(command).decode().strip())
            return duration
        except subprocess.CalledProcessError:
            self.console.log(f"获取视频时长失败: {video_path}")
            return None

    def clip_video_segment(self, video_path, start_time, end_time):
        """使用 ffmpeg 剪辑视频片段并将其保存到项目根目录下的缓存文件夹中"""

        # 先获取视频的时长，确保开始时间和结束时间在视频时长范围内
        video_duration = self.get_video_duration(video_path)
        if video_duration is None:
            QMessageBox.warning(self, "错误", "无法获取视频时长，无法剪辑")
            return

        if start_time >= end_time:
            QMessageBox.warning(self, "错误", "开始时间不能晚于或等于结束时间")
            return

        # 创建缓存文件夹路径
        video_clips_folder = os.path.join(cache_dir, "cache_video_fragment")

        # 检查并创建缓存文件夹和视频片段文件夹
        os.makedirs(video_clips_folder, exist_ok=True)

        # 获取原视频文件名（不带扩展名）
        base_name = os.path.splitext(os.path.basename(video_path))[0]

        # 生成时间戳作为文件名的一部分
        start_time_str = self.format_time2(start_time).replace(",", "_").replace(":", "-")
        end_time_str = self.format_time2(end_time).replace(",", "_").replace(":", "-")

        # 构造初始文件名并放入缓存文件夹的“视频片段”子文件夹中
        output_file_name = f"single_{base_name}_{start_time_str}_to_{end_time_str}.mp4"
        output_file = os.path.join(video_clips_folder, output_file_name)

        # 检查文件是否存在，如果存在，则添加 (1), (2), (3)... 以避免覆盖
        counter = 1
        while os.path.exists(output_file):
            output_file_name = f"single_{base_name}_{start_time_str}_to_{end_time_str}({counter}).mp4"
            output_file = os.path.join(video_clips_folder, output_file_name)
            counter += 1

        # 将毫秒转换为秒（ffmpeg 使用秒为单位）
        start_time_seconds = start_time / 1000
        duration_seconds = (end_time - start_time) / 1000

        # 使用 ffmpeg 剪辑视频片段
        command = [
            ffmpeg_path, "-y",  # -y 表示覆盖输出文件
            "-ss", str(start_time_seconds),  # 开始时间，提前指定位置
            "-i", video_path,  # 输入视频路径
            "-t", str(duration_seconds),  # 持续时间
            "-c:v", "libx264",  # 使用 libx264 进行视频编码
            "-preset", "fast",  # 编码速度，fast 为较快速度与质量平衡
            "-crf", "23",  # CRF 值越低质量越好，23 是默认值
            "-c:a", "aac",  # 使用 AAC 进行音频编码
            "-b:a", "192k",  # 音频比特率为 192 kbps
            output_file  # 输出文件路径
        ]

        try:
            self.console.log(f"执行命令: {' '.join(command)}")
            subprocess.run(command, check=True)
            self.console.log(f"视频片段已剪辑并保存到: {output_file}")
            self.result_display.addItem(output_file)  # 在 result_display 区域显示剪辑后的文件路径
            QMessageBox.information(self, "成功", f"视频片段已剪辑并保存到: {output_file}")
        except subprocess.CalledProcessError as e:
            self.console.log(f"剪辑视频时发生错误: {str(e)}")
            QMessageBox.warning(self, "剪辑错误", "视频剪辑失败，请检查ffmpeg配置")

    def clear_index(self):
        """清除所有生成的 SRT 文件"""
        material_folder = self.material_folder.text()
        if not material_folder:
            QMessageBox.warning(self, "错误", "请选择素材文件夹")
            return

        # 获取素材文件夹中的所有 .srt 文件
        srt_files = [f for f in os.listdir(material_folder) if f.endswith('.srt')]

        if not srt_files:
            self.console.log("没有找到任何索引文件。")
            return

        reply = QMessageBox.question(self, '确认删除', '确定要删除所有SRT文件吗？', QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 删除所有 .srt 文件
            for srt_file in srt_files:
                os.remove(os.path.join(material_folder, srt_file))
                self.console.log(f"索引文件已删除: {srt_file}")

        self.console.log("清除索引操作完成。")
        self.display_area.clear()  # 清空展示区域的内容
        QMessageBox.information(self, "成功", "所有字幕文件已成功清除")
