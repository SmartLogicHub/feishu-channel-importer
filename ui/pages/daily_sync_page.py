from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from ui.widgets import Card, page_heading


class DailySyncPage(QWidget):
    preflight_requested = Signal()
    sync_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(page_heading("每日同步", "选择日期和来源，先预检，再把缺少的数据写入汇总表。"))

        controls = Card("同步范围")
        row = QHBoxLayout()
        row.addWidget(QLabel("快捷选择"))
        self.date_mode_combo = QComboBox()
        self.date_mode_combo.addItems(["今天", "昨天", "自定义范围"])
        row.addWidget(self.date_mode_combo)
        row.addWidget(QLabel("开始日期"))
        self.start_date_edit = QDateEdit(QDate.currentDate())
        self.start_date_edit.setCalendarPopup(True)
        row.addWidget(self.start_date_edit)
        row.addWidget(QLabel("结束日期"))
        self.end_date_edit = QDateEdit(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        row.addWidget(self.end_date_edit)
        row.addStretch()
        controls.layout.addLayout(row)
        layout.addWidget(controls)

        results = Card("来源与预检结果", "勾选一个或多个来源。日期或配置改变后需要重新预检。")
        self.source_table = QTableWidget(0, 7)
        self.source_table.setHorizontalHeaderLabels(["同步", "来源", "读取", "范围内", "已存在", "待新增", "异常"])
        self.source_table.setAlternatingRowColors(True)
        self.source_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.source_table.horizontalHeader().setStretchLastSection(True)
        results.layout.addWidget(self.source_table)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        results.layout.addWidget(self.progress_bar)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(86)
        self.log_edit.setPlaceholderText("预检与同步状态会显示在这里")
        results.layout.addWidget(self.log_edit)
        buttons = QHBoxLayout()
        self.preflight_button = QPushButton("预检选中来源")
        self.preflight_button.clicked.connect(self.preflight_requested)
        self.sync_button = QPushButton("确认同步")
        self.sync_button.setObjectName("primaryButton")
        self.sync_button.setEnabled(False)
        self.sync_button.clicked.connect(self.sync_requested)
        buttons.addWidget(self.preflight_button)
        buttons.addWidget(self.sync_button)
        buttons.addStretch()
        results.layout.addLayout(buttons)
        layout.addWidget(results)

        self.date_mode_combo.currentIndexChanged.connect(self._apply_date_mode)
        self.start_date_edit.dateChanged.connect(self.invalidate_preflight)
        self.end_date_edit.dateChanged.connect(self.invalidate_preflight)

    def _apply_date_mode(self, index):
        today = QDate.currentDate()
        if index == 0:
            self.start_date_edit.setDate(today)
            self.end_date_edit.setDate(today)
        elif index == 1:
            yesterday = today.addDays(-1)
            self.start_date_edit.setDate(yesterday)
            self.end_date_edit.setDate(yesterday)
        self.invalidate_preflight()

    def invalidate_preflight(self):
        self.sync_button.setEnabled(False)

    def set_sources(self, sources):
        self.source_table.setRowCount(len(sources))
        for row, source in enumerate(sources):
            check = QTableWidgetItem("")
            check.setFlags(check.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            check.setCheckState(
                Qt.CheckState.Checked if source.enabled else Qt.CheckState.Unchecked
            )
            check.setData(Qt.ItemDataRole.UserRole, source.id)
            self.source_table.setItem(row, 0, check)
            self.source_table.setItem(row, 1, QTableWidgetItem(source.name))
            for column in range(2, 7):
                self.source_table.setItem(row, column, QTableWidgetItem("—"))
        self.source_table.itemChanged.connect(lambda *_: self.invalidate_preflight())

    def selected_source_ids(self):
        result = []
        for row in range(self.source_table.rowCount()):
            item = self.source_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                result.append(item.data(Qt.ItemDataRole.UserRole))
        return result

    def show_preflight(self, preflight):
        plans = {plan.source_id: plan for plan in preflight.plans}
        for row in range(self.source_table.rowCount()):
            source_id = self.source_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            plan = plans.get(source_id)
            if not plan:
                continue
            values = [
                plan.read_count,
                plan.in_range_count,
                plan.skipped_count,
                len(plan.creates),
                len(plan.errors),
            ]
            for column, value in enumerate(values, start=2):
                self.source_table.setItem(row, column, QTableWidgetItem(str(value)))

    def selected_dates(self):
        return self.start_date_edit.date().toPython(), self.end_date_edit.date().toPython()
