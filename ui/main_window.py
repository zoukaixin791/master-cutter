# ui/main_window.py
from ui.pages.subtitle_editing import subtitle_editing
from ui.pages.sponsor_page import sponsor_page
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from ui.themes import ThemeManager
import platform
from utils.settings import APP_NAME, WINDOW_SIZE
platfm = platform.system()
import os
from utils.paths_internal import *

class MainUi(QMainWindow):
    def __init__(self):
        super().__init__()
        self.menu_actions = {}  # 更改为 menu_actions，避免与内建函数冲突
        self.theme_manager = ThemeManager()  # 使用封装的主题管理器
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(APP_NAME)
        # self.setFixedSize(*WINDOW_SIZE)
        image_path = os.path.join(resources_dir, "images/icon.ico")
        self.setWindowIcon(QIcon(image_path))
        self.center()

        # 创建菜单栏用于切换主题
        # self.create_menu_bar()

        # 创建TabWidget并添加标签页
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.add_tabs() # 添加标签页

        # 加载默认主题
        self.theme_manager.load_stylesheet(self)  # 使用主题管理器加载样式表

    def create_menu_bar(self):
        """创建菜单栏，并封装菜单项的添加逻辑"""
        menubar = QMenuBar(self)

        # 创建“设置”菜单
        settings_menu = menubar.addMenu("设置")

        # 创建“主题切换”子菜单
        theme_menu = settings_menu.addMenu("主题切换")

        # 创建一个互斥组
        action_group = QActionGroup(self)
        action_group.setExclusive(True)  # 设置为互斥

        self.create_menu_item(theme_menu, "白色主题", self.set_light_theme, is_checkable=True, is_checked=True,
                              action_group=action_group)
        self.create_menu_item(theme_menu, "暗黑主题", self.set_dark_theme, is_checkable=True, action_group=action_group)

        # 未来可以继续在此处添加更多的菜单和功能
        # 示例：添加帮助菜单
        help_menu = menubar.addMenu("帮助")
        self.create_menu_item(help_menu, "关于", self.show_about)

        self.setMenuBar(menubar)

    def create_menu_item(self, parent_menu, title, callback, is_checkable=False, is_checked=False, action_group=None):
        """
           封装菜单项的创建和处理，方便后续扩展
           :param parent_menu: 父菜单（即子菜单将添加到哪个父菜单中）
           :param title: 菜单项的标题
           :param callback: 菜单项的点击回调
           :param is_checkable: 是否可以选中
           :param is_checked: 是否默认选中
           :param action_group: QActionGroup，用于互斥菜单项
           """
        action = QAction(title, self)
        action.triggered.connect(callback)

        if is_checkable:
            action.setCheckable(True)
            action.setChecked(is_checked)

            if action_group:
                action.setActionGroup(action_group)

            # 将可选项保存到 menu_actions 字典中，以便后续操作
            self.menu_actions[title] = action

        parent_menu.addAction(action)

    def add_tabs(self):
        """根据配置动态添加标签页"""
        self.tabs.addTab(subtitle_editing(), '视频剪辑')
        # self.tabs.addTab(Page1(), '视频剪辑')
        self.tabs.addTab(sponsor_page(), "打赏作者")
        # self.tabs.addTab(Page2(), '关于')
        # self.tabs.addTab(ConsoleBox(), '控制台')

    def set_light_theme(self):
        """切换到白色主题"""
        self.theme_manager.set_theme('light')
        self.theme_manager.load_stylesheet(self)

    def set_dark_theme(self):
        """切换到暗黑主题"""
        self.theme_manager.set_theme('dark')
        self.theme_manager.load_stylesheet(self)

    def center(self):
        """窗口居中"""
        screen = self.frameGeometry()
        center_point = self.screen().availableGeometry().center()
        screen.moveCenter(center_point)
        self.move(screen.topLeft())

    def show_about(self):
        """显示关于对话框的功能示例"""
        SponsorDialog()

class SponsorDialog(QDialog):
    def __init__(self, parent=None):
        super(SponsorDialog, self).__init__(parent)
        self.resize(865, 475)
        if platfm == 'Darwin':
            self.setWindowIcon(QIcon('resources/icon.icns'))
        else:
            self.setWindowIcon(QIcon('resources/icon.ico'))
        self.setWindowTitle(self.tr('打赏作者'))
        self.exec()

    def paintEvent(self, event):
        painter = QPainter(self)
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        wechat_image_path = os.path.abspath(os.path.join(BASE_DIR, '..', 'resources', 'images', 'brander.png'))
        pixmap = QPixmap(wechat_image_path)
        painter.drawPixmap(self.rect(), pixmap)