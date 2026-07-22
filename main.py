import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from window import MainWindow


def main():
    # HighDpi 속성은 QApplication 생성 전에 설정해야 적용됨
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
