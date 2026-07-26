from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from ui.widgets import Card, page_heading


class SettingsPage(QWidget):
    save_requested = Signal()
    test_requested = Signal()
    clear_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(page_heading("设置", "配置飞书开放 API 和汇总目标。凭证仅加密保存在当前电脑。"))

        api_card = Card("飞书开放 API", "换到另一台电脑时只需要重新填写一次 API。")
        form = QFormLayout()
        self.app_id_edit = QLineEdit()
        self.app_id_edit.setPlaceholderText("例如 cli_xxxxxxxxx")
        self.app_secret_edit = QLineEdit()
        self.app_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.app_secret_edit.setPlaceholderText("输入 App Secret")
        self.show_secret_check = QCheckBox("显示 App Secret")
        self.show_secret_check.toggled.connect(
            lambda checked: self.app_secret_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        form.addRow("App ID", self.app_id_edit)
        form.addRow("App Secret", self.app_secret_edit)
        form.addRow("", self.show_secret_check)
        api_card.layout.addLayout(form)
        layout.addWidget(api_card)

        target_card = Card("汇总目标", "粘贴带 table 和 view 参数的飞书多维表格视图链接。")
        self.target_url_edit = QLineEdit()
        self.target_url_edit.setPlaceholderText("https://xxx.feishu.cn/base/...?...table=...&view=...")
        target_card.layout.addWidget(self.target_url_edit)
        self.status_label = QLabel("尚未测试连接")
        self.status_label.setObjectName("muted")
        target_card.layout.addWidget(self.status_label)
        layout.addWidget(target_card)

        buttons = QHBoxLayout()
        self.test_button = QPushButton("测试连接并读取字段")
        self.test_button.clicked.connect(self.test_requested)
        self.save_button = QPushButton("保存设置")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.save_requested)
        self.clear_button = QPushButton("清除本机配置")
        self.clear_button.setObjectName("dangerButton")
        self.clear_button.clicked.connect(self.clear_requested)
        buttons.addWidget(self.test_button)
        buttons.addWidget(self.save_button)
        buttons.addStretch()
        buttons.addWidget(self.clear_button)
        layout.addLayout(buttons)
        layout.addStretch()
