from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.models import FieldMapping, SourceConfig

from ui.widgets import Card, page_heading


class ExcelPage(QWidget):
    file_selected = Signal(str)
    sheet_selected = Signal(str, str)
    preflight_requested = Signal()
    import_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(page_heading("Excel 导入", "选择 Excel 工作表，自行决定哪些列写入汇总表。"))
        file_card = Card("选择文件")
        row = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("选择 .xlsx 或 .xls 文件")
        self.browse_button = QPushButton("浏览")
        self.browse_button.clicked.connect(self._browse)
        row.addWidget(self.file_path_edit)
        row.addWidget(self.browse_button)
        file_card.layout.addLayout(row)
        sheet_row = QHBoxLayout()
        sheet_row.addWidget(QLabel("工作表"))
        self.sheet_combo = QComboBox()
        self._updating_sheet = False
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        sheet_row.addWidget(self.sheet_combo)
        sheet_row.addStretch()
        file_card.layout.addLayout(sheet_row)
        layout.addWidget(file_card)
        mapping_card = Card("预览与字段映射", "只有勾选的映射会写入；字段名称不需要一致。")
        self.preview_table = QTableWidget(0, 0)
        self.mapping_table = QTableWidget(0, 5)
        self.mapping_table.setHorizontalHeaderLabels(["写入", "Excel 列", "目标字段", "固定值", "查重"])
        mapping_card.layout.addWidget(QLabel("数据预览"))
        mapping_card.layout.addWidget(self.preview_table)
        mapping_card.layout.addWidget(QLabel("字段映射"))
        mapping_card.layout.addWidget(self.mapping_table)
        buttons = QHBoxLayout()
        self.preflight_button = QPushButton("预检 Excel")
        self.import_button = QPushButton("确认导入")
        self.import_button.setObjectName("primaryButton")
        self.import_button.setEnabled(False)
        self.preflight_button.clicked.connect(self.preflight_requested)
        self.import_button.clicked.connect(self.import_requested)
        buttons.addWidget(self.preflight_button)
        buttons.addWidget(self.import_button)
        buttons.addStretch()
        mapping_card.layout.addLayout(buttons)
        layout.addWidget(mapping_card)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 Excel", "", "Excel (*.xlsx *.xls)")
        if path:
            self.file_path_edit.setText(path)
            self.file_selected.emit(path)

    def set_preview(self, preview, target_fields):
        headers = preview.get("headers", [])
        rows = preview.get("rows", [])
        self._updating_sheet = True
        self.sheet_combo.clear()
        self.sheet_combo.addItems(preview.get("sheet_names", []))
        selected_sheet = preview.get("selected_sheet")
        if selected_sheet:
            self.sheet_combo.setCurrentText(selected_sheet)
        self._updating_sheet = False
        self.preview_table.setColumnCount(len(headers))
        self.preview_table.setHorizontalHeaderLabels([str(item) for item in headers])
        self.preview_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, value in enumerate(row):
                self.preview_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        writable = [field for field in target_fields if field.get("writable", True)]
        self.mapping_table.setRowCount(len(writable))
        for row, target in enumerate(writable):
            enabled = QTableWidgetItem("")
            enabled.setFlags(enabled.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            enabled.setCheckState(Qt.CheckState.Unchecked)
            enabled.setData(Qt.ItemDataRole.UserRole, target)
            self.mapping_table.setItem(row, 0, enabled)
            source_combo = QComboBox()
            source_combo.addItem("固定值", None)
            for header in headers:
                source_combo.addItem(str(header), str(header))
            target_item = QTableWidgetItem(target["name"])
            target_item.setData(Qt.ItemDataRole.UserRole, target)
            self.mapping_table.setCellWidget(row, 1, source_combo)
            self.mapping_table.setItem(row, 2, target_item)
            self.mapping_table.setCellWidget(row, 3, QLineEdit())
            self.mapping_table.setCellWidget(row, 4, QCheckBox())

    def _on_sheet_changed(self, sheet_name):
        if self._updating_sheet or not sheet_name:
            return
        file_path = self.file_path_edit.text().strip()
        if file_path:
            self.sheet_selected.emit(file_path, sheet_name)

    def build_source(self):
        mappings = []
        dedupe = []
        for row in range(self.mapping_table.rowCount()):
            enabled = self.mapping_table.item(row, 0).checkState() == Qt.CheckState.Checked
            target = self.mapping_table.item(row, 2).data(Qt.ItemDataRole.UserRole)
            source_combo = self.mapping_table.cellWidget(row, 1)
            excel_column = source_combo.currentData()
            mapping = FieldMapping(
                enabled=enabled,
                value_mode="source" if excel_column else "constant",
                excel_column=excel_column,
                source_field_name=excel_column,
                target_field_id=target["id"],
                target_field_name=target["name"],
                target_field_type=int(target["type"]),
                constant_value=self.mapping_table.cellWidget(row, 3).text().strip(),
            )
            mappings.append(mapping)
            if enabled and self.mapping_table.cellWidget(row, 4).isChecked():
                dedupe.append(target["id"])
        return SourceConfig(
            id="excel-ad-hoc",
            name="Excel 临时导入",
            source_type="excel",
            url=self.file_path_edit.text().strip(),
            excel_sheet_name=self.sheet_combo.currentText() or None,
            mappings=mappings,
            dedupe_target_field_ids=dedupe,
        )
