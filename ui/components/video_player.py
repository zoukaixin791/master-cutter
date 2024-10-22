import os
from PyQt5.QtWidgets import *
from PyQt5.QtMultimedia import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtMultimediaWidgets import QVideoWidget
import sys


class VideoPlayerWidget(QWidget):
    """自定义视频播放器部件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()

    def setupUi(self):
        """初始化UI布局"""
        self.gridLayout = QGridLayout(self)

        # 视频显示窗口
        self.wgt_video = myVideoWidget(self)
        self.wgt_video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 自动适应父布局
        self.setupVideoPalette()
        self.gridLayout.addWidget(self.wgt_video, 0, 0, 1, 2)  # 占用两列以留出空隙

        # 进度条和进度显示
        self.sld_video = myVideoSlider(self)
        self.sld_video.setMinimumSize(QSize(300, 0))  # 缩短进度条长度
        self.sld_video.setMaximum(100)
        self.gridLayout.addWidget(self.sld_video, 1, 0, 1, 1)  # 放在第一列

        # 显示当前进度百分比
        self.lab_video = QLabel("0%", self)
        self.lab_video.setMaximumSize(QSize(45, 50))  # 进度显示不占满行
        self.lab_video.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # 设置百分比显示右对齐并垂直居中
        self.gridLayout.addWidget(self.lab_video, 1, 1, 1, 1)  # 放在第二列

        # 控制区
        self.setupControlPanel()

        # 音量标签与默认设置
        self.lab_audio.setText("音量:100%")
        self.sld_audio.setValue(100)

        # 创建播放器
        self.player = QMediaPlayer(self)
        self.player.setVideoOutput(self.wgt_video)

        # 绑定信号与槽函数
        self.connectSignals()

    def setupVideoPalette(self):
        """设置视频窗口的颜色调色板"""
        palette = QPalette()
        brush = QBrush(QColor(0, 0, 0), Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.Window, brush)
        palette.setBrush(QPalette.Inactive, QPalette.Window, brush)
        palette.setBrush(QPalette.Disabled, QPalette.Window, brush)
        self.wgt_video.setPalette(palette)
        self.wgt_video.setAutoFillBackground(True)

    def setupControlPanel(self):
        """设置底部控制面板"""
        self.splitter = QSplitter(self)
        self.splitter.setOrientation(Qt.Horizontal)

        self.btn_open = QPushButton("打开", self.splitter)
        self.btn_play = QPushButton("播放", self.splitter)
        self.btn_stop = QPushButton("暂停", self.splitter)

        # 缩短音量滑块的宽度
        self.sld_audio = QSlider(Qt.Horizontal, self.splitter)
        self.sld_audio.setMinimumSize(QSize(80, 0))  # 将音量滑块宽度缩短到 80
        self.sld_audio.setMaximumSize(QSize(100, 20))
        self.lab_audio = QLabel("音量:100%", self.splitter)

        # 显示截图按钮
        self.btn_cast = QPushButton("截图", self.splitter)
        self.btn_cast.show()  # 显示截图按钮

        self.gridLayout.addWidget(self.splitter, 2, 0, 1, 2)

    def connectSignals(self):
        """绑定控件与相应的功能"""
        self.btn_open.clicked.connect(self.openVideoFile)
        self.btn_play.clicked.connect(self.playVideo)
        self.btn_stop.clicked.connect(self.pauseVideo)
        self.sld_audio.valueChanged.connect(self.volumeChange)
        self.player.positionChanged.connect(self.changeSlide)
        self.sld_video.ClickedValue.connect(self.clickedSlider)
        self.btn_cast.clicked.connect(self.castVideo)  # 绑定截图功能

    def castVideo(self):
        """视频截图功能"""
        screen = QGuiApplication.primaryScreen()
        cast_jpg = './' + QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss") + '.jpg'
        screen.grabWindow(self.wgt_video.winId()).save(cast_jpg)

    def openVideoFile(self):
        """打开视频文件"""
        file_url, _ = QFileDialog.getOpenFileUrl(self, "选择视频文件")
        if file_url:
            self.player.setMedia(QMediaContent(file_url))
            self.player.play()

    def playVideo(self):
        """播放视频"""
        self.player.play()

    def pauseVideo(self):
        """暂停视频"""
        self.player.pause()

    def volumeChange(self, position):
        """音量调节"""
        volume = round(position / self.sld_audio.maximum() * 100)
        self.player.setVolume(volume)
        self.lab_audio.setText(f"音量:{volume}%")

    def clickedSlider(self, position):
        """进度条点击跳转"""
        if self.player.duration() > 0:
            video_position = int((position / 100) * self.player.duration())
            self.player.setPosition(video_position)

    def changeSlide(self, position):
        """进度条随视频进度更新"""
        if not self.sld_video.isSliderDown():
            video_length = self.player.duration() + 0.1
            self.sld_video.setValue(round((position / video_length) * 100))
            self.lab_video.setText(f"{round((position / video_length) * 100, 2)}%")

    def play_video(self, video_path, start_time=None, end_time=None):
        """播放整个视频或指定片段"""
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))

        # 如果有指定的开始时间，跳转到该时间
        if start_time is not None:
            self.player.setPosition(start_time)  # 转换为毫秒
            self.player.play()

            # 如果有结束时间，设置一个定时器在结束时间暂停
            if end_time is not None:
                duration_ms = end_time - start_time  # 计算需要播放的时长
                QTimer.singleShot(duration_ms, self.player.pause)
        else:
            # 否则播放整个视频
            self.player.play()


class myVideoWidget(QVideoWidget):
    """自定义视频显示部件，支持双击全屏"""
    doubleClickedItem = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def mouseDoubleClickEvent(self, QMouseEvent):
        self.doubleClickedItem.emit("double clicked")


class myVideoSlider(QSlider):
    """自定义进度条控件，支持点击跳转"""
    ClickedValue = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        value = event.localPos().x()
        value = round(value / self.width() * self.maximum())
        self.ClickedValue.emit(value)


class VideoPlayerDialog(QDialog):
    """用于弹出的视频播放器对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("视频播放器")
        self.setGeometry(100, 100, 800, 600)  # 设置窗口大小
        self.video_player_widget = VideoPlayerWidget(self)  # 嵌入VideoPlayerWidget
        layout = QVBoxLayout()
        layout.addWidget(self.video_player_widget)
        self.setLayout(layout)
