from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.widgets import Card, page_heading


class HistoryPage(QWidget):
    delete_requested = Signal(list)
    clear_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(page_heading("同步记录", "查看本机最近的同步摘要；这里不会保存 API 密钥或访问令牌。"))
        card = Card("最近记录")
        actions = QHBoxLayout()
        actions.addStretch()
        self.delete_button = QPushButton("删除选中")
        self.delete_button.setEnabled(False)
        self.clear_button = QPushButton("清空全部")
        self.clear_button.setObjectName("dangerButton")
        self.clear_button.setEnabled(False)
        actions.addWidget(self.delete_button)
        actions.addWidget(self.clear_button)
        card.layout.addLayout(actions)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["时间", "日期范围", "来源", "读取", "新增", "跳过", "结果"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.table.itemSelectionChanged.connect(self._update_actions)
        self.delete_button.clicked.connect(self._request_delete)
        self.clear_button.clicked.connect(self.clear_requested.emit)
        card.layout.addWidget(self.table)
        layout.addWidget(card)

    def set_history(self, history):
        self.table.setRowCount(len(history))
        for row, item in enumerate(history):
            values = [
                item.get("time", ""),
                item.get("date_range", ""),
                item.get("sources", ""),
                item.get("read", 0),
                item.get("created", 0),
                item.get("skipped", 0),
                item.get("result", ""),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        self._update_actions()

    def _selected_rows(self):
        return sorted(
            {index.row() for index in self.table.selectionModel().selectedRows()}
        )

    def _update_actions(self):
        self.delete_button.setEnabled(bool(self._selected_rows()))
        self.clear_button.setEnabled(self.table.rowCount() > 0)

    def _request_delete(self):
        rows = self._selected_rows()
        if rows:
            self.delete_requested.emit(rows)
