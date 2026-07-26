"""Read-only target field catalog shown from the source editor."""
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


FIELD_TYPE_NAMES = {
    1: "文本",
    2: "数字",
    3: "单选",
    4: "多选",
    5: "日期",
    7: "复选框",
    11: "人员",
    13: "电话号码",
    15: "网址",
    17: "附件",
    18: "关联记录",
    19: "查找引用",
    20: "公式",
    21: "双向关联",
    1001: "创建时间",
    1002: "最后更新时间",
    1003: "创建人",
    1004: "最后修改人",
}


def field_type_name(field):
    field_type = int(field.get("type", 0) or 0)
    return FIELD_TYPE_NAMES.get(field_type, f"类型 {field_type}")


class FieldCatalogDialog(QDialog):
    def __init__(self, target_fields, parent=None):
        super().__init__(parent)
        self.setWindowTitle("汇总表全部字段")
        self.resize(720, 500)
        layout = QVBoxLayout(self)
        hint = QLabel(
            "可写字段可以添加到映射；公式、查找引用和汇总字段由飞书自动生成。"
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.table = QTableWidget(len(target_fields), 3)
        self.table.setHorizontalHeaderLabels(["字段名称", "类型", "状态"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        for row, field in enumerate(target_fields):
            status = "可写" if field.get("writable", True) else "飞书自动生成/只读"
            values = [
                field.get("name", ""),
                field_type_name(field),
                status,
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        layout.addWidget(self.table)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
