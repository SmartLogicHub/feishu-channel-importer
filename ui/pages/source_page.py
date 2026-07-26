from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from ui.widgets import Card, page_heading


class SourcePage(QWidget):
    add_requested = Signal()
    edit_requested = Signal(int)
    delete_requested = Signal(int)
    toggle_requested = Signal(int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(page_heading("来源管理", "随时添加小红书、得物、天猫、京东或其他飞书来源视图。"))
        card = Card("已配置来源", "每个来源独立保存日期筛选、字段映射和查重字段。")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["启用", "来源名称", "类型", "日期字段", "映射", "状态"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(lambda index: self.edit_requested.emit(index.row()))
        self.table.itemChanged.connect(self._on_item_changed)
        card.layout.addWidget(self.table)
        buttons = QHBoxLayout()
        self.add_button = QPushButton("添加飞书来源")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self.add_requested)
        self.edit_button = QPushButton("编辑")
        self.edit_button.clicked.connect(lambda: self.edit_requested.emit(self.table.currentRow()))
        self.delete_button = QPushButton("删除")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(lambda: self.delete_requested.emit(self.table.currentRow()))
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.edit_button)
        buttons.addWidget(self.delete_button)
        buttons.addStretch()
        card.layout.addLayout(buttons)
        layout.addWidget(card)

    def set_sources(self, sources):
        self.table.blockSignals(True)
        self.table.setRowCount(len(sources))
        for row, source in enumerate(sources):
            enabled_item = QTableWidgetItem("")
            enabled_item.setFlags(
                enabled_item.flags() | Qt.ItemFlag.ItemIsUserCheckable
            )
            enabled_item.setCheckState(
                Qt.CheckState.Checked
                if source.enabled
                else Qt.CheckState.Unchecked
            )
            self.table.setItem(row, 0, enabled_item)
            values = [
                source.name,
                "飞书表" if source.source_type == "feishu" else "Excel",
                source.date_field_name or "未设置",
                str(sum(1 for item in source.mappings if item.enabled)),
                "已配置" if source.mappings else "待配置",
            ]
            for column, value in enumerate(values, start=1):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.blockSignals(False)

    def _on_item_changed(self, item):
        if item.column() == 0:
            self.toggle_requested.emit(
                item.row(), item.checkState() == Qt.CheckState.Checked
            )
