"""Card-based editor for one Feishu source and its field mappings."""
from __future__ import annotations

import uuid

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.models import SourceConfig
from ui.dialogs.field_catalog import FieldCatalogDialog
from ui.dialogs.mapping_row import MappingRowWidget
from ui.widgets import Card


class SourceEditorDialog(QDialog):
    def __init__(self, source: SourceConfig | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("配置飞书来源")
        self.resize(1040, 760)
        self.setMinimumSize(900, 650)
        self.source = source
        self.source_fields = []
        self.target_fields = []
        self.writable_target_fields = []
        self.mapping_rows: list[MappingRowWidget] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        source_card = Card(
            "① 来源与筛选",
            "填写来源视图并读取字段；创建时间和日期字段只用于筛选同步范围。",
        )
        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)

        self.source_name_edit = QLineEdit(source.name if source else "")
        self.filter_mode_combo = QComboBox()
        self.filter_mode_combo.addItem("按创建时间", "created_time")
        self.filter_mode_combo.addItem("按日期字段", "field_date")
        form.addWidget(QLabel("来源名称"), 0, 0)
        form.addWidget(self.source_name_edit, 0, 1)
        form.addWidget(QLabel("筛选方式"), 0, 2)
        form.addWidget(self.filter_mode_combo, 0, 3)

        self.source_url_edit = QLineEdit(source.url if source else "")
        self.source_url_edit.setPlaceholderText(
            "粘贴带 table 和 view 参数的来源视图链接"
        )
        self.test_button = QPushButton("读取来源与汇总表字段")
        url_row = QHBoxLayout()
        url_row.setContentsMargins(0, 0, 0, 0)
        url_row.setSpacing(10)
        url_row.addWidget(self.source_url_edit, 1)
        url_row.addWidget(self.test_button)
        url_widget = QWidget()
        url_widget.setLayout(url_row)
        form.addWidget(QLabel("来源视图"), 1, 0)
        form.addWidget(url_widget, 1, 1, 1, 3)

        self.date_field_combo = QComboBox()
        self.date_field_combo.setEnabled(False)
        form.addWidget(QLabel("日期字段"), 2, 0)
        form.addWidget(self.date_field_combo, 2, 1)
        self.mapping_hint = QLabel("请先测试链接并读取来源和汇总表字段。")
        self.mapping_hint.setObjectName("muted")
        self.mapping_hint.setWordWrap(True)
        form.addWidget(self.mapping_hint, 2, 2, 1, 2)
        source_card.layout.addLayout(form)
        root.addWidget(source_card)

        mapping_card = Card()
        toolbar = QHBoxLayout()
        toolbar.setSpacing(9)
        title = QLabel("② 字段映射")
        title.setObjectName("sectionTitle")
        self.mapping_count_label = QLabel("已添加 0 项")
        self.mapping_count_label.setObjectName("statusChip")
        self.field_catalog_button = QPushButton("查看全部目标字段")
        self.field_catalog_button.setEnabled(False)
        self.add_mapping_button = QPushButton("＋ 添加映射")
        self.add_mapping_button.setObjectName("primaryButton")
        self.add_mapping_button.setEnabled(False)
        toolbar.addWidget(title)
        toolbar.addWidget(self.mapping_count_label)
        toolbar.addStretch()
        toolbar.addWidget(self.field_catalog_button)
        toolbar.addWidget(self.add_mapping_button)
        mapping_card.layout.addLayout(toolbar)

        self.field_summary_label = QLabel(
            "读取字段后，只添加需要写入的商品名称、店铺、统计时间等映射。"
        )
        self.field_summary_label.setObjectName("muted")
        self.field_summary_label.setWordWrap(True)
        mapping_card.layout.addWidget(self.field_summary_label)

        mapping_headings = QHBoxLayout()
        mapping_headings.setContentsMargins(16, 0, 14, 0)
        mapping_headings.setSpacing(9)
        self.mapping_source_heading = QLabel("")
        self.mapping_source_heading.setObjectName("mappingColumnHeader")
        mapping_arrow_heading = QLabel("→")
        mapping_arrow_heading.setObjectName("mappingArrow")
        mapping_arrow_heading.setFixedWidth(24)
        mapping_arrow_heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mapping_target_heading = QLabel("汇总表字段")
        self.mapping_target_heading.setObjectName("mappingColumnHeader")
        mapping_headings.addWidget(self.mapping_source_heading, 5)
        mapping_headings.addWidget(mapping_arrow_heading)
        mapping_headings.addWidget(self.mapping_target_heading, 5)
        mapping_headings.addSpacing(72)
        mapping_card.layout.addLayout(mapping_headings)

        self.mapping_scroll = QScrollArea()
        self.mapping_scroll.setWidgetResizable(True)
        self.mapping_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.mapping_scroll.setMinimumHeight(270)
        self.mapping_container = QWidget()
        self.mapping_layout = QVBoxLayout(self.mapping_container)
        self.mapping_layout.setContentsMargins(2, 2, 8, 2)
        self.mapping_layout.setSpacing(10)
        self.empty_state_label = QLabel(
            "尚未添加字段映射\n点击右上角“＋ 添加映射”，再选择目标字段和来源字段。"
        )
        self.empty_state_label.setObjectName("emptyState")
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_label.setWordWrap(True)
        self.mapping_layout.addWidget(self.empty_state_label, 1)
        self.mapping_scroll.setWidget(self.mapping_container)
        mapping_card.layout.addWidget(self.mapping_scroll, 1)

        self.general_error_label = QLabel("")
        self.general_error_label.setObjectName("rowError")
        self.general_error_label.setWordWrap(True)
        mapping_card.layout.addWidget(self.general_error_label)
        root.addWidget(mapping_card, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存来源")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName(
            "primaryButton"
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.add_mapping_button.clicked.connect(self.add_mapping)
        self.field_catalog_button.clicked.connect(self._show_field_catalog)
        self.filter_mode_combo.currentIndexChanged.connect(
            self._update_date_field_state
        )
        self.source_name_edit.textChanged.connect(self._update_source_display_name)
        self._update_source_display_name()
        if source:
            mode_index = self.filter_mode_combo.findData(source.date_filter_mode)
            if mode_index >= 0:
                self.filter_mode_combo.setCurrentIndex(mode_index)

    def set_field_metadata(self, source_fields, target_fields):
        self.source_fields = list(source_fields)
        self.target_fields = list(target_fields)
        self.writable_target_fields = [
            field for field in self.target_fields if field.get("writable", True)
        ]
        self._clear_mapping_rows()
        self._populate_date_fields()

        total = len(self.target_fields)
        writable = len(self.writable_target_fields)
        read_only = total - writable
        self.field_summary_label.setText(
            f"已读取{self._source_display_name()} {len(self.source_fields)} 个字段；"
            f"汇总表共 {total} 个字段，"
            f"其中 {writable} 个可写、{read_only} 个自动生成/只读。"
        )
        self.add_mapping_button.setEnabled(bool(self.writable_target_fields))
        self.field_catalog_button.setEnabled(bool(self.target_fields))
        self.field_catalog_button.setText(f"查看全部 {total} 个汇总表字段")
        if self.source:
            self._restore_source_values()
        self._refresh_mapping_state()

    def _populate_date_fields(self):
        self.date_field_combo.clear()
        for field in self.source_fields:
            if int(field.get("type", 0)) in (5, 1001):
                self.date_field_combo.addItem(field["name"], field["id"])
                index = self.date_field_combo.count() - 1
                self.date_field_combo.setItemData(
                    index, int(field.get("type", 0)), Qt.ItemDataRole.UserRole + 1
                )
        self._update_date_field_state()

    def _update_date_field_state(self):
        created_mode = self.filter_mode_combo.currentData() == "created_time"
        desired_type = 1001 if created_mode else 5
        current_type = self.date_field_combo.itemData(
            self.date_field_combo.currentIndex(), Qt.ItemDataRole.UserRole + 1
        )
        if current_type != desired_type:
            for index in range(self.date_field_combo.count()):
                if (
                    self.date_field_combo.itemData(
                        index, Qt.ItemDataRole.UserRole + 1
                    )
                    == desired_type
                ):
                    self.date_field_combo.setCurrentIndex(index)
                    break
        self.date_field_combo.setEnabled(not created_mode)
        self.date_field_combo.setToolTip(
            "飞书创建时间（自动）" if created_mode else "选择来源表中的日期字段"
        )

    def add_mapping(self, mapping=None, dedupe_ids=()):
        if not self.source_fields or not self.writable_target_fields:
            return None
        row = MappingRowWidget(
            self.source_fields,
            self.target_fields,
            self.source_name_edit.text(),
            self.mapping_container,
        )
        row.delete_requested.connect(self.remove_mapping)
        row.target_changed.connect(self._refresh_target_availability)
        self.mapping_rows.append(row)
        self.mapping_layout.addWidget(row)
        if mapping:
            row.restore(mapping, dedupe_ids)
        self._refresh_target_availability()
        self._refresh_mapping_state()
        return row

    def _update_source_display_name(self):
        source_name = self.source_name_edit.text().strip()
        source_label = f"{source_name}字段" if source_name else "来源字段"
        self.mapping_source_heading.setText(f"{source_label}或固定值")
        self.mapping_source_heading.setToolTip(source_name)
        for row in self.mapping_rows:
            row.set_source_name(source_name)

    def _source_display_name(self):
        return self.source_name_edit.text().strip() or "来源"

    def remove_mapping(self, row):
        if row not in self.mapping_rows:
            return
        self.mapping_rows.remove(row)
        self.mapping_layout.removeWidget(row)
        row.setParent(None)
        row.deleteLater()
        self._refresh_target_availability()
        self._refresh_mapping_state()

    def _clear_mapping_rows(self):
        for row in list(self.mapping_rows):
            self.mapping_layout.removeWidget(row)
            row.setParent(None)
            row.deleteLater()
        self.mapping_rows.clear()

    def mapping_count(self):
        return len(self.mapping_rows)

    def _refresh_target_availability(self):
        selected = {
            row.selected_target_id()
            for row in self.mapping_rows
            if row.selected_target_id()
        }
        for row in self.mapping_rows:
            current = row.selected_target_id()
            occupied = selected - ({current} if current else set())
            row.set_target_occupancy(occupied)

    def _refresh_mapping_state(self):
        count = self.mapping_count()
        self.mapping_count_label.setText(f"已添加 {count} 项")
        self.empty_state_label.setVisible(count == 0)

    def _mapping_is_meaningful(self, mapping):
        dedupe_ids = self.source.dedupe_target_field_ids if self.source else []
        return bool(
            mapping.enabled
            or mapping.source_field_id
            or str(mapping.constant_value or "").strip()
            or mapping.target_field_id in dedupe_ids
        )

    def _restore_source_values(self):
        mode_index = self.filter_mode_combo.findData(self.source.date_filter_mode)
        if mode_index >= 0:
            self.filter_mode_combo.setCurrentIndex(mode_index)
        date_index = self.date_field_combo.findData(self.source.date_field_id)
        if date_index >= 0:
            self.date_field_combo.setCurrentIndex(date_index)
        for mapping in self.source.mappings:
            if self._mapping_is_meaningful(mapping):
                self.add_mapping(mapping, self.source.dedupe_target_field_ids)
        self._update_date_field_state()

    def build_mappings(self):
        mappings = []
        dedupe = []
        for row in self.mapping_rows:
            mapping = row.to_mapping()
            if not mapping:
                continue
            mappings.append(mapping)
            if mapping.enabled and row.dedupe_checkbox.isChecked():
                dedupe.append(mapping.target_field_id)
        return mappings, dedupe

    def validate_mappings(self):
        self.general_error_label.clear()
        valid = True
        targets = []
        for row in self.mapping_rows:
            error = row.validation_error()
            row.show_error(error)
            if error:
                valid = False
            target_id = row.selected_target_id()
            if target_id:
                targets.append(target_id)
        duplicates = {target for target in targets if targets.count(target) > 1}
        if duplicates:
            valid = False
            for row in self.mapping_rows:
                if row.selected_target_id() in duplicates:
                    row.show_error("目标字段不能重复")
        mappings, dedupe = self.build_mappings()
        if not any(mapping.enabled for mapping in mappings):
            self.general_error_label.setText("请至少添加并启用一条字段映射。")
            valid = False
        elif not dedupe:
            self.general_error_label.setText("请至少选择一个参与查重的字段。")
            valid = False
        return valid

    def _validate_and_accept(self):
        if self.validate_mappings():
            self.accept()

    def _show_field_catalog(self):
        if self.target_fields:
            FieldCatalogDialog(self.target_fields, self).exec()

    def build_source_config(self, location) -> SourceConfig:
        mappings, dedupe = self.build_mappings()
        date_index = self.date_field_combo.currentIndex()
        return SourceConfig(
            id=self.source.id if self.source else uuid.uuid4().hex,
            name=self.source_name_edit.text().strip(),
            source_type="feishu",
            enabled=self.source.enabled if self.source else True,
            url=self.source_url_edit.text().strip(),
            app_token=location.app_token,
            table_id=location.table_id or "",
            view_id=location.view_id,
            date_filter_mode=self.filter_mode_combo.currentData(),
            date_field_id=self.date_field_combo.itemData(date_index),
            date_field_name=self.date_field_combo.currentText(),
            mappings=mappings,
            dedupe_target_field_ids=dedupe,
        )
