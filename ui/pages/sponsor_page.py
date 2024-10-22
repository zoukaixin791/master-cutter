from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout,QSizePolicy,QHBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import os
from utils.paths_internal import *

class sponsor_page(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("打赏页面")
        # 创建主布局并设置居中对齐
        # 创建主布局并设置居中对齐
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)  # 保持整体垂直居中

        # 创建打赏说明的标签
        self.description_label = QLabel(self)
        self.description_label.setText("如果你觉得这个软件对你有帮助，欢迎通过以下方式打赏支持！")
        self.description_label.setAlignment(Qt.AlignCenter)
        # self.description_label.setWordWrap(True)  # 自动换行

        # 创建水平布局用于图片的居中对齐
        image_layout = QHBoxLayout()
        image_layout.setAlignment(Qt.AlignCenter)

        # 创建显示打赏二维码的标签
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)

        image_path = os.path.join(resources_dir,"images/pay.jpg")
        # 加载打赏二维码图片
        pixmap = QPixmap(image_path)

        # 设置缩小后的图片大小，保持比例
        self.image_label.setPixmap(pixmap.scaled(280, 380, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # 设置图片标签不随窗口大小变化
        self.image_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 将图片添加到水平布局
        image_layout.addWidget(self.image_label)

        # 创建更多打赏信息的标签
        self.info_label = QLabel(self)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setWordWrap(True)  # 允许自动换行
        self.info_label.setText("感谢您的支持！\n\n"
                                "您可以通过微信或支付宝扫码进行打赏。\n\n"
                                "每一份支持都将激励我们不断改进和创新，"
                                "感谢您的慷慨捐赠！")

        # 布局
        main_layout.addWidget(self.description_label)
        main_layout.addLayout(image_layout)  # 使用水平布局确保图片居中
        main_layout.addWidget(self.info_label)

        self.setLayout(main_layout)

    def resizeEvent(self, event):
        # 限制图片最大尺寸，不撑满窗口，保持比例
        image_path = os.path.join(resources_dir, "images/pay.jpg")
        pixmap = QPixmap(image_path)
        self.image_label.setPixmap(pixmap.scaled(280, 380, Qt.KeepAspectRatio, Qt.SmoothTransformation))

