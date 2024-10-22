# main.py
import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainUi


def main():
    app = QApplication(sys.argv)
    gui = MainUi()
    gui.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
