"""飞书渠道数据汇总工具 - 入口。"""
import sys
from PySide6.QtWidgets import QApplication
from ui.app_icon import application_icon
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("飞书渠道数据汇总工具")
    app.setOrganizationName("FeishuChannelImporter")
    app.setStyle("Fusion")
    app.setWindowIcon(application_icon())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
