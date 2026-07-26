"""One editable source-to-target mapping card."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
)

from core.models import FieldMapping
from ui.dialogs.field_catalog import field_type_name


def _field_label(field: dict) -> str:
    return field["name"]


class MappingRowWidget(QFrame):
    """Controls and serializes one optional field mapping."""

    delete_requested = Signal(object)
    target_changed = Signal()

    def __init__(self, source_fields, target_fields, source_name="", parent=None):
        super().__init__(parent)
        self.setObjectName("mappingCard")
        self.source_fields = list(source_fields)
        self.target_fields = list(target_fields)
        self.source_name = str(source_name or "").strip()
        self.source_by_id = {field["id"]: field for field in self.source_fields}
        self.target_by_id = {field["id"]: field for field in self.target_fields}
        self.missing_target_id = None

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(9)

        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(9)
        self.target_combo = QComboBox()
        self.target_combo.setPlaceholderText("选择汇总表目标字段")
        self.target_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.arrow_label = QLabel("→")
        self.arrow_label.setObjectName("mappingArrow")
        self.arrow_label.setFixedWidth(24)
        self.arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.source_combo = QComboBox()
        self.source_combo.setPlaceholderText("选择来源字段")
        self.source_combo.addItem("", None)
        for field in self.source_fields:
            self.source_combo.addItem(_field_label(field), field["id"])
        self.fixed_edit = QLineEdit()
        self.fixed_edit.setPlaceholderText("输入固定值")
        self.value_stack = QStackedWidget()
        self.value_stack.addWidget(self.source_combo)
        self.value_stack.addWidget(self.fixed_edit)
        self.value_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        self.delete_button = QPushButton("删除")
        self.delete_button.setObjectName("mappingDeleteButton")
        self.delete_button.setFixedWidth(72)
        self.top_layout.addWidget(self.value_stack, 5)
        self.top_layout.addWidget(self.arrow_label)
        self.top_layout.addWidget(self.target_combo, 5)
        self.top_layout.addWidget(self.delete_button)
        root.addLayout(self.top_layout)

        bottom = QHBoxLayout()
        bottom.setSpacing(14)
        self.enabled_checkbox = QCheckBox("写入此字段")
        self.enabled_checkbox.setChecked(True)
        self.dedupe_checkbox = QCheckBox("用于查重")
        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("mappingModeCombo")
        self.mode_combo.addItem("", "source")
        self.mode_combo.addItem("取值方式：固定值", "constant")
        self.error_label = QLabel("")
        self.error_label.setObjectName("rowError")
        self.error_label.setWordWrap(True)
        bottom.addWidget(self.enabled_checkbox)
        bottom.addWidget(self.dedupe_checkbox)
        bottom.addWidget(self.mode_combo)
        bottom.addWidget(self.error_label, 1)
        root.addLayout(bottom)

        self.set_target_occupancy()
        self.mode_combo.currentIndexChanged.connect(self._update_value_mode)
        self.target_combo.currentIndexChanged.connect(
            self._on_target_changed
        )
        self.delete_button.clicked.connect(
            lambda: self.delete_requested.emit(self)
        )
        self.set_source_name(self.source_name)
        self._update_value_mode()

    def set_source_name(self, source_name):
        self.source_name = str(source_name or "").strip()
        source_label = f"{self.source_name}字段" if self.source_name else "来源字段"
        self.source_combo.setItemText(0, f"请选择{source_label}")
        self.mode_combo.setItemText(0, f"取值方式：{source_label}")

    def _on_target_changed(self, _index):
        if self.selected_target_id():
            self.missing_target_id = None
        self.target_changed.emit()

    def _update_value_mode(self):
        constant_mode = self.mode_combo.currentData() == "constant"
        self.value_stack.setCurrentWidget(
            self.fixed_edit if constant_mode else self.source_combo
        )

    def set_target_occupancy(self, occupied_target_ids=()):
        current_id = self.selected_target_id()
        missing_target_id = self.missing_target_id
        occupied_target_ids = set(occupied_target_ids)
        writable_fields = [
            field for field in self.target_fields if field.get("writable", True)
        ]
        read_only_fields = [
            field for field in self.target_fields if not field.get("writable", True)
        ]
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItem("请选择汇总表字段", None)
        self._add_target_heading("—— 可写字段 ——")
        for field in writable_fields:
            occupied = field["id"] in occupied_target_ids and field["id"] != current_id
            label = _field_label(field)
            if occupied:
                label = f"{label}（已用于其他映射）"
            self._add_target_item(label, field["id"], enabled=not occupied)
        if read_only_fields:
            self._add_target_heading("—— 自动生成/不可写字段 ——")
            for field in read_only_fields:
                label = (
                    f"{_field_label(field)}（{field_type_name(field)}，"
                    "自动生成/不可写）"
                )
                self._add_target_item(label, field["id"], enabled=False)
        self.target_combo.blockSignals(False)
        self.select_target(current_id, emit=False)
        if current_id is None and missing_target_id:
            self.missing_target_id = missing_target_id

    def _add_target_heading(self, label):
        self.target_combo.addItem(label, None)
        item = self.target_combo.model().item(self.target_combo.count() - 1)
        item.setEnabled(False)

    def _add_target_item(self, label, field_id, *, enabled):
        self.target_combo.addItem(label, field_id)
        item = self.target_combo.model().item(self.target_combo.count() - 1)
        item.setEnabled(enabled)

    def available_target_ids(self):
        return [
            self.target_combo.itemData(index)
            for index in range(self.target_combo.count())
            if self.target_combo.itemData(index)
            and self.target_combo.model().item(index).isEnabled()
        ]

    def selected_target_id(self):
        return self.target_combo.currentData()

    def selected_source_id(self):
        return self.source_combo.currentData()

    def selected_target(self):
        return self.target_by_id.get(self.selected_target_id())

    def selected_source(self):
        return self.source_by_id.get(self.selected_source_id())

    def select_target(self, field_id, *, emit=True, remember_missing=False):
        index = self.target_combo.findData(field_id)
        if index < 0:
            index = self.target_combo.findData(None)
            if remember_missing and field_id:
                self.missing_target_id = field_id
        else:
            self.missing_target_id = None
        if not emit:
            self.target_combo.blockSignals(True)
        self.target_combo.setCurrentIndex(index)
        if not emit:
            self.target_combo.blockSignals(False)

    def select_source(self, field_id):
        index = self.source_combo.findData(field_id)
        self.source_combo.setCurrentIndex(index if index >= 0 else 0)

    def restore(self, mapping: FieldMapping, dedupe_ids=()):
        self.select_target(mapping.target_field_id, remember_missing=True)
        mode_index = self.mode_combo.findData(mapping.value_mode)
        if mode_index >= 0:
            self.mode_combo.setCurrentIndex(mode_index)
        self.select_source(mapping.source_field_id)
        self.fixed_edit.setText(str(mapping.constant_value or ""))
        self.enabled_checkbox.setChecked(mapping.enabled)
        self.dedupe_checkbox.setChecked(mapping.target_field_id in dedupe_ids)
        self._update_value_mode()

    def to_mapping(self):
        target = self.selected_target()
        if not target:
            return None
        source = (
            self.selected_source()
            if self.mode_combo.currentData() == "source"
            else None
        )
        return FieldMapping(
            enabled=self.enabled_checkbox.isChecked(),
            value_mode=self.mode_combo.currentData(),
            source_field_id=source["id"] if source else None,
            source_field_name=source["name"] if source else None,
            target_field_id=target["id"],
            target_field_name=target["name"],
            target_field_type=int(target["type"]),
            constant_value=self.fixed_edit.text().strip(),
        )

    def validation_error(self):
        if self.missing_target_id:
            return "原目标字段已不存在，请重新选择"
        if not self.selected_target():
            return "请选择目标字段"
        if not self.selected_target().get("writable", True):
            return "该目标字段由飞书自动生成，不能写入"
        if not self.enabled_checkbox.isChecked():
            if self.dedupe_checkbox.isChecked():
                return "参与查重的映射必须启用写入"
            return ""
        if self.mode_combo.currentData() == "source" and not self.selected_source():
            return "请选择来源字段"
        if (
            self.mode_combo.currentData() == "constant"
            and not self.fixed_edit.text().strip()
        ):
            return "请填写固定值"
        return ""

    def show_error(self, message):
        self.error_label.setText(message or "")
