from PyQt5.QtWidgets import QWidget, QPushButton,QTextEdit, QVBoxLayout,QSizePolicy
from PyQt5.QtGui import QTextCursor
from PyQt5.QtCore import QDateTime
from PyQt5.Qt import Qt

class ConsoleBox(QWidget):
    """
    控制台日志输出组件，集成日志显示、日志级别、时间戳和清除功能。
    使用 QTextEdit 来显示日志信息，支持日志打印、日志清除以及控制最大日志长度。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initGui()

    def initGui(self):
        """
        初始化界面和布局，创建 QTextEdit 作为日志显示框，并提供清空日志的按钮。
        """
        # 设置最大日志长度，超过此长度时会自动清除部分日志
        self.max_log_size = 10000  # 最大字符长度
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)  # 移除内边距

        # 创建 QTextEdit 作为日志显示框，设置为只读
        self.consoleEditBox = QTextEdit(self)
        self.consoleEditBox.setReadOnly(True)  # 设置只读模式，用户不能编辑
        # self.consoleEditBox.setLineWrapMode(QTextEdit.WidgetWidth)  # 自动换行
        self.consoleEditBox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 扩展填充空间


        # 创建清除日志按钮
        self.clearButton = QPushButton("清空日志", self)
        self.clearButton.clicked.connect(self.clear_logs)  # 绑定按钮点击事件到清空日志方法

        # 设置按钮的大小策略
        # self.clearButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 确保按钮不会自动扩展

        # 使用垂直布局来排列日志框和按钮

        self.layout.addWidget(self.consoleEditBox)  # 添加日志框
        self.layout.addWidget(self.clearButton, alignment=Qt.AlignCenter)  # 添加清除日志按钮，靠右对齐
        self.setLayout(self.layout)  # 设置布局



    def log(self, message, level="INFO"):
        """
        输出日志消息，带有时间戳和日志级别。

        参数:
            message (str): 要打印的日志消息。
            level (str): 日志级别（如 INFO, ERROR, DEBUG 等）。默认为 INFO。
        """
        # 获取当前时间作为时间戳
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        # 格式化日志消息
        formatted_message = f"[{timestamp}] [{level}] {message}\n"

        # 获取当前光标并移动到最后
        cursor = self.consoleEditBox.textCursor()
        cursor.movePosition(QTextCursor.End)

        # 插入格式化后的日志消息
        cursor.insertText(formatted_message)
        self.consoleEditBox.setTextCursor(cursor)
        self.consoleEditBox.ensureCursorVisible()  # 确保新消息可见

        # 如果日志内容超过最大限制，清除部分日志
        if len(self.consoleEditBox.toPlainText()) > self.max_log_size:
            self.trim_logs()

    def clear_logs(self):
        """
        清空日志框中的所有内容。
        """
        self.consoleEditBox.clear()

    def set_max_log_size(self, size):
        """
        设置最大日志长度，防止日志内容过长导致内存占用过多。

        参数:
            size (int): 设置允许的最大字符长度。
        """
        self.max_log_size = size

    def trim_logs(self):
        """
        当日志内容超过最大长度时，删除部分旧日志，保持日志框大小在合理范围。
        """
        # 保留最新部分日志，删掉开头的部分
        cursor = self.consoleEditBox.textCursor()
        cursor.select(QTextCursor.Document)
        text = cursor.selectedText()
        if len(text) > self.max_log_size:
            # 保留最新的部分日志，删除头部日志
            trimmed_text = text.splitlines(True)[-self.max_log_size:]
            self.consoleEditBox.setPlainText(''.join(trimmed_text))
        cursor.movePosition(QTextCursor.End)
        self.consoleEditBox.setTextCursor(cursor)
