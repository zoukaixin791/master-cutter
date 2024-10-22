from utils.log_manager import log_manager
import qdarkstyle

class ThemeManager:
    def __init__(self, default_theme='light'):
        self.current_theme = default_theme
        self.theme_paths = {
            'light': 'light_cyan.xml',  # 对应 qt-material 的主题
            'dark': 'dark_cyan.xml'     # 对应 qt-material 的主题
        }

    def load_stylesheet(self, app):
        """根据当前主题加载样式表"""
        theme_name = self.theme_paths.get(self.current_theme, None)
        if theme_name:
            try:
                app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
            except Exception as e:
                log_manager.error(f"无法应用 qt-material 主题：{str(e)}")
        else:
            log_manager.error(f"无效的主题：{self.current_theme}")

    def set_theme(self, theme_name):
        """设置当前主题"""
        if theme_name in self.theme_paths:
            self.current_theme = theme_name
            log_manager.info(f"主题切换至 {theme_name}")
        else:
            log_manager.error(f"无效的主题：{theme_name}")
