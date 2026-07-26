"""Main application shell, navigation and user-facing orchestration."""
from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from core.config_manager import (
    clear_app_config,
    clear_credentials,
    load_app_config,
    load_credentials,
    save_app_config,
    save_credentials,
)
from core.excel_reader import read_excel_preview
from core.feishu_client import FeishuClient
from core.models import AppConfig, TargetConfig
from core.sync_service import SyncService
from core.url_parser import parse_bitable_url
from ui.app_icon import application_icon
from ui.dialogs.source_editor import SourceEditorDialog
from ui.pages.daily_sync_page import DailySyncPage
from ui.pages.excel_page import ExcelPage
from ui.pages.history_page import HistoryPage
from ui.pages.settings_page import SettingsPage
from ui.pages.source_page import SourcePage
from ui.theme import APP_STYLE


class WorkerSignals(QObject):
    finished = Signal(str, object)
    failed = Signal(str, str)
    progress = Signal(int, int, str)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("飞书渠道数据汇总工具")
        self.setWindowIcon(application_icon())
        self.resize(1180, 780)
        self.setMinimumSize(1020, 680)
        self.app_config: AppConfig = load_app_config()
        self.client: FeishuClient | None = None
        self.sync_service: SyncService | None = None
        self.target_fields: list[dict] = []
        self.daily_preflight = None
        self.excel_preflight = None
        self.worker = WorkerSignals()
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.failed.connect(self._on_worker_failed)
        self.worker.progress.connect(self._on_worker_progress)

        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_sidebar())

        self.page_stack = QStackedWidget()
        self.daily_page = DailySyncPage()
        self.source_page = SourcePage()
        self.excel_page = ExcelPage()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage()
        self._install_pages()
        root_layout.addWidget(self.page_stack, 1)
        self.setStyleSheet(APP_STYLE)
        self._connect_actions()
        self._load_saved_state()

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(206)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 18)
        layout.setSpacing(8)
        brand = QLabel("飞书渠道汇总")
        brand.setObjectName("brandTitle")
        subtitle = QLabel("Excel · 多来源 · 防重复")
        subtitle.setObjectName("brandSubtitle")
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(16)
        self._sidebar_layout = layout
        return sidebar

    def _install_pages(self):
        pages = [
            ("每日同步", self.daily_page),
            ("来源管理", self.source_page),
            ("Excel 导入", self.excel_page),
            ("同步记录", self.history_page),
            ("设置", self.settings_page),
        ]
        self.nav_buttons = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, (label, page) in enumerate(pages):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, i=index: self.page_stack.setCurrentIndex(i)
            )
            group.addButton(button)
            self._sidebar_layout.addWidget(button)
            self.nav_buttons[label] = button
            self.page_stack.addWidget(page)
        self.nav_buttons["每日同步"].setChecked(True)
        self._sidebar_layout.addStretch()
        version = QLabel("v2.0 · 单文件便携版")
        version.setObjectName("brandSubtitle")
        self._sidebar_layout.addWidget(version)

    def _connect_actions(self):
        self.settings_page.save_requested.connect(self._save_settings)
        self.settings_page.test_requested.connect(self._test_settings)
        self.settings_page.clear_requested.connect(self._clear_settings)
        self.source_page.add_requested.connect(lambda: self._edit_source(-1))
        self.source_page.edit_requested.connect(self._edit_source)
        self.source_page.delete_requested.connect(self._delete_source)
        self.source_page.toggle_requested.connect(self._toggle_source)
        self.daily_page.preflight_requested.connect(self._start_daily_preflight)
        self.daily_page.sync_requested.connect(self._start_daily_sync)
        self.excel_page.file_selected.connect(self._load_excel_preview)
        self.excel_page.sheet_selected.connect(self._load_excel_preview)
        self.excel_page.preflight_requested.connect(self._start_excel_preflight)
        self.excel_page.import_requested.connect(self._start_excel_sync)
        self.history_page.delete_requested.connect(self._delete_history_rows)
        self.history_page.clear_requested.connect(self._clear_history)

    def _load_saved_state(self):
        credentials = load_credentials()
        if credentials:
            self.settings_page.app_id_edit.setText(credentials.get("app_id", ""))
            self.settings_page.app_secret_edit.setText(credentials.get("app_secret", ""))
            if credentials.get("app_id") and credentials.get("app_secret"):
                self.client = FeishuClient(
                    credentials["app_id"], credentials["app_secret"]
                )
                self.sync_service = SyncService(self.client)
        if self.app_config.target:
            self.settings_page.target_url_edit.setText(self.app_config.target.url)
        self._refresh_source_views()
        self.history_page.set_history(self.app_config.history)

    def _refresh_source_views(self):
        self.source_page.set_sources(self.app_config.sources)
        self.daily_page.set_sources(self.app_config.sources)
        self.daily_page.invalidate_preflight()

    def _run_worker(self, key, function):
        def run():
            try:
                self.worker.finished.emit(key, function())
            except Exception as exc:
                self.worker.failed.emit(key, str(exc))

        threading.Thread(target=run, daemon=True).start()

    def _current_credentials(self):
        app_id = self.settings_page.app_id_edit.text().strip()
        secret = self.settings_page.app_secret_edit.text().strip()
        if not app_id or not secret:
            raise ValueError("请填写 App ID 和 App Secret")
        return app_id, secret

    def _target_from_form(self):
        url = self.settings_page.target_url_edit.text().strip()
        location = parse_bitable_url(url)
        if not location.table_id:
            raise ValueError("汇总表链接必须包含 table 参数")
        return TargetConfig(
            url=url,
            app_token=location.app_token,
            table_id=location.table_id,
            view_id=location.view_id,
        )

    def _save_settings(self):
        try:
            app_id, secret = self._current_credentials()
            target = self._target_from_form()
        except Exception as exc:
            QMessageBox.warning(self, "设置不完整", str(exc))
            return
        old_target = self.app_config.target
        target_changed = (
            old_target is None
            or old_target.app_token != target.app_token
            or old_target.table_id != target.table_id
        )
        save_credentials(app_id, secret, target.url)
        self.app_config = AppConfig(
            schema_version=self.app_config.schema_version,
            target=target,
            sources=self.app_config.sources,
            history=self.app_config.history,
        )
        save_app_config(self.app_config)
        self.client = FeishuClient(app_id, secret)
        self.sync_service = SyncService(self.client)
        if target_changed:
            self.target_fields = []
            status = "设置已保存，请测试连接读取字段"
        elif self.target_fields:
            status = f"设置已保存，已保留 {len(self.target_fields)} 个目标字段"
        else:
            status = "设置已保存，请测试连接读取字段"
        self.settings_page.status_label.setText(status)
        self.daily_page.invalidate_preflight()

    def _test_settings(self):
        try:
            app_id, secret = self._current_credentials()
            target = self._target_from_form()
        except Exception as exc:
            QMessageBox.warning(self, "无法测试", str(exc))
            return
        self.settings_page.test_button.setEnabled(False)
        self.settings_page.status_label.setText("正在连接并读取目标字段…")

        def operation():
            client = FeishuClient(app_id, secret)
            fields = client.list_fields(target.app_token, target.table_id)
            return client, target, fields

        self._run_worker("settings_test", operation)

    def _clear_settings(self):
        answer = QMessageBox.question(
            self,
            "清除本机配置",
            "确定清除 API 凭证、汇总目标、来源配置和同步记录吗？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        clear_credentials()
        clear_app_config()
        self.app_config = AppConfig()
        self.client = None
        self.sync_service = None
        self.target_fields = []
        self.settings_page.app_id_edit.clear()
        self.settings_page.app_secret_edit.clear()
        self.settings_page.target_url_edit.clear()
        self.settings_page.status_label.setText("本机配置已清除")
        self._refresh_source_views()
        self.history_page.set_history([])

    def _load_source_dialog_fields(self, dialog):
        if not self.client or not self.app_config.target:
            raise ValueError("请先到“设置”页读取汇总表字段")
        location = parse_bitable_url(dialog.source_url_edit.text())
        if not location.table_id:
            raise ValueError("来源链接必须包含 table 参数")
        source_fields = self.client.list_fields(
            location.app_token, location.table_id
        )
        target = self.app_config.target
        target_fields = self.client.list_fields(target.app_token, target.table_id)
        self.target_fields = list(target_fields)
        dialog.set_field_metadata(source_fields, self.target_fields)
        source_name = dialog.source_name_edit.text().strip() or "来源"
        dialog.mapping_hint.setText(
            f"已读取{source_name} {len(source_fields)} 个字段和汇总表 "
            f"{len(self.target_fields)} 个字段。"
        )
        return source_fields, self.target_fields

    def _edit_source(self, row):
        if row < -1 or row >= len(self.app_config.sources):
            return
        if not self.client or not self.app_config.target or not self.target_fields:
            QMessageBox.information(
                self, "请先设置", "请先到“设置”页测试 API，并成功读取汇总表字段。"
            )
            self.nav_buttons["设置"].click()
            return
        source = self.app_config.sources[row] if row >= 0 else None
        dialog = SourceEditorDialog(source, self)

        def load_fields():
            try:
                self._load_source_dialog_fields(dialog)
            except Exception as exc:
                QMessageBox.warning(dialog, "读取字段失败", str(exc))

        dialog.test_button.clicked.connect(load_fields)
        if source:
            load_fields()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            location = parse_bitable_url(dialog.source_url_edit.text())
            new_source = dialog.build_source_config(location)
            if not new_source.name:
                raise ValueError("请填写来源名称")
            if not new_source.table_id or not dialog.source_fields:
                raise ValueError("请先测试来源链接并读取字段")
            if not any(mapping.enabled for mapping in new_source.mappings):
                raise ValueError("请至少勾选一个写入字段")
            if not new_source.dedupe_target_field_ids:
                raise ValueError("请至少勾选一个查重字段")
            if not new_source.date_field_id:
                raise ValueError("请选择创建时间或日期字段")
        except Exception as exc:
            QMessageBox.warning(self, "来源配置不完整", str(exc))
            return
        sources = list(self.app_config.sources)
        if row >= 0:
            sources[row] = new_source
        else:
            sources.append(new_source)
        self._replace_sources(sources)

    def _replace_sources(self, sources):
        self.app_config = AppConfig(
            schema_version=self.app_config.schema_version,
            target=self.app_config.target,
            sources=sources,
            history=self.app_config.history,
        )
        save_app_config(self.app_config)
        self._refresh_source_views()

    def _delete_source(self, row):
        if row < 0 or row >= len(self.app_config.sources):
            return
        source = self.app_config.sources[row]
        if QMessageBox.question(self, "删除来源", f"确定删除“{source.name}”吗？") != QMessageBox.StandardButton.Yes:
            return
        sources = list(self.app_config.sources)
        sources.pop(row)
        self._replace_sources(sources)

    def _toggle_source(self, row, enabled):
        if row < 0 or row >= len(self.app_config.sources):
            return
        sources = list(self.app_config.sources)
        sources[row] = replace(sources[row], enabled=enabled)
        self._replace_sources(sources)

    def _selected_sources(self):
        selected = set(self.daily_page.selected_source_ids())
        return [source for source in self.app_config.sources if source.id in selected]

    def _start_daily_preflight(self):
        sources = self._selected_sources()
        if not self.sync_service or not self.app_config.target:
            QMessageBox.warning(self, "尚未设置", "请先配置并测试飞书 API 和汇总目标。")
            return
        if not sources:
            QMessageBox.warning(self, "未选择来源", "请至少勾选一个来源。")
            return
        start_date, end_date = self.daily_page.selected_dates()
        if end_date < start_date:
            QMessageBox.warning(self, "日期错误", "结束日期不能早于开始日期。")
            return
        self.daily_page.preflight_button.setEnabled(False)
        self.daily_page.sync_button.setEnabled(False)
        self.daily_page.log_edit.setPlainText("正在读取来源和汇总表，仅执行只读预检…")
        self._run_worker(
            "daily_preflight",
            lambda: self.sync_service.preflight(
                self.app_config.target, sources, start_date, end_date
            ),
        )

    def _start_daily_sync(self):
        if not self.daily_preflight or not self.sync_service:
            return
        pending = sum(len(plan.creates) for plan in self.daily_preflight.plans if not plan.errors)
        if QMessageBox.question(
            self, "确认同步", f"本次将新增 {pending} 条记录。确定继续吗？"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.daily_page.sync_button.setEnabled(False)
        self.daily_page.preflight_button.setEnabled(False)
        self._run_worker(
            "daily_sync",
            lambda: self.sync_service.apply(
                self.daily_preflight.token,
                progress_callback=lambda current, total, message: self.worker.progress.emit(
                    current, total, message
                ),
            ),
        )

    def _load_excel_preview(self, path, sheet_name=None):
        if not self.target_fields:
            QMessageBox.information(self, "请先设置", "请先在设置页测试并读取汇总表字段。")
            return
        try:
            preview = read_excel_preview(
                path, preview_rows=8, sheet_name=sheet_name or None
            )
            self.excel_page.set_preview(preview, self.target_fields)
        except Exception as exc:
            QMessageBox.warning(self, "读取 Excel 失败", str(exc))

    def _start_excel_preflight(self):
        if not self.sync_service or not self.app_config.target:
            QMessageBox.warning(self, "尚未设置", "请先配置飞书 API 和汇总目标。")
            return
        source = self.excel_page.build_source()
        if not source.url:
            QMessageBox.warning(self, "未选择文件", "请先选择 Excel 文件。")
            return
        if not any(mapping.enabled for mapping in source.mappings):
            QMessageBox.warning(self, "未配置字段", "请至少勾选一个写入字段。")
            return
        if not source.dedupe_target_field_ids:
            QMessageBox.warning(self, "未配置查重", "请至少勾选一个查重字段。")
            return
        today = datetime.now().date()
        self.excel_page.preflight_button.setEnabled(False)
        self._run_worker(
            "excel_preflight",
            lambda: self.sync_service.preflight(
                self.app_config.target, [source], today, today
            ),
        )

    def _start_excel_sync(self):
        if not self.excel_preflight or not self.sync_service:
            return
        pending = sum(len(plan.creates) for plan in self.excel_preflight.plans)
        if QMessageBox.question(
            self, "确认导入", f"本次将从 Excel 新增 {pending} 条记录。确定继续吗？"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.excel_page.import_button.setEnabled(False)
        self._run_worker(
            "excel_sync", lambda: self.sync_service.apply(self.excel_preflight.token)
        )

    def _on_worker_finished(self, key, payload):
        if key == "settings_test":
            self.settings_page.test_button.setEnabled(True)
            self.client, target, self.target_fields = payload
            self.sync_service = SyncService(self.client)
            app_id, secret = self._current_credentials()
            save_credentials(app_id, secret, target.url)
            self.app_config = AppConfig(
                schema_version=self.app_config.schema_version,
                target=target,
                sources=self.app_config.sources,
                history=self.app_config.history,
            )
            save_app_config(self.app_config)
            self.settings_page.target_url_edit.setText(target.url)
            self.settings_page.status_label.setText(
                f"连接成功，已读取 {len(self.target_fields)} 个目标字段"
            )
        elif key == "daily_preflight":
            self.daily_page.preflight_button.setEnabled(True)
            self.daily_preflight = payload
            self.daily_page.show_preflight(payload)
            pending = sum(len(plan.creates) for plan in payload.plans if not plan.errors)
            errors = sum(len(plan.errors) for plan in payload.plans)
            self.daily_page.log_edit.setPlainText(
                f"预检完成：待新增 {pending} 条，异常 {errors} 条。"
            )
            self.daily_page.sync_button.setEnabled(pending > 0)
        elif key == "daily_sync":
            self.daily_page.preflight_button.setEnabled(True)
            self.daily_page.progress_bar.setValue(100)
            self.daily_page.log_edit.append(
                f"写入完成：新增 {payload.created_count}，跳过 {payload.skipped_count}，写后核对 {'通过' if payload.verified else '失败'}。"
            )
            self._append_history(payload, "每日同步")
            QMessageBox.information(self, "同步完成", f"新增 {payload.created_count} 条，写后核对 {'通过' if payload.verified else '失败'}。")
            self.daily_preflight = None
        elif key == "excel_preflight":
            self.excel_page.preflight_button.setEnabled(True)
            self.excel_preflight = payload
            plan = payload.plans[0]
            if plan.errors:
                QMessageBox.warning(self, "Excel 预检发现异常", "\n".join(error.message for error in plan.errors[:10]))
                self.excel_page.import_button.setEnabled(False)
            else:
                self.excel_page.import_button.setEnabled(bool(plan.creates))
                QMessageBox.information(
                    self,
                    "Excel 预检完成",
                    f"读取 {plan.read_count} 行，跳过 {plan.skipped_count} 行，待新增 {len(plan.creates)} 行。",
                )
        elif key == "excel_sync":
            self.excel_page.preflight_button.setEnabled(True)
            self.excel_page.import_button.setEnabled(False)
            self._append_history(payload, "Excel 导入")
            QMessageBox.information(self, "Excel 导入完成", f"新增 {payload.created_count} 条，写后核对 {'通过' if payload.verified else '失败'}。")
            self.excel_preflight = None

    def _on_worker_failed(self, key, message):
        self.settings_page.test_button.setEnabled(True)
        self.daily_page.preflight_button.setEnabled(True)
        self.excel_page.preflight_button.setEnabled(True)
        self.daily_page.sync_button.setEnabled(False)
        self.excel_page.import_button.setEnabled(False)
        if key.startswith("daily"):
            self.daily_page.log_edit.append(f"失败：{message}")
        QMessageBox.critical(self, "操作失败", message)

    def _on_worker_progress(self, current, total, message):
        if total > 0:
            self.daily_page.progress_bar.setValue(int(current * 100 / total))
        self.daily_page.log_edit.append(message)

    def _append_history(self, result, source_label):
        start_date, end_date = self.daily_page.selected_dates()
        item = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "date_range": f"{start_date} ~ {end_date}",
            "sources": source_label,
            "read": result.created_count + result.skipped_count,
            "created": result.created_count,
            "skipped": result.skipped_count,
            "result": "核对通过" if result.verified else "核对失败",
        }
        history = [item] + list(self.app_config.history)
        history = history[:100]
        self.app_config = AppConfig(
            schema_version=self.app_config.schema_version,
            target=self.app_config.target,
            sources=self.app_config.sources,
            history=history,
        )
        save_app_config(self.app_config)
        self.history_page.set_history(history)

    def _replace_history(self, history):
        self.app_config = replace(self.app_config, history=list(history))
        save_app_config(self.app_config)
        self.history_page.set_history(self.app_config.history)

    def _delete_history_rows(self, rows):
        valid_rows = sorted(
            {
                row
                for row in rows
                if isinstance(row, int) and 0 <= row < len(self.app_config.history)
            }
        )
        if not valid_rows:
            return
        answer = QMessageBox.question(
            self,
            "删除同步记录",
            f"确定删除选中的 {len(valid_rows)} 条同步记录吗？\n\n"
            "此操作只删除本机日志，不会删除或更改飞书汇总表中的任何数据。",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        removed = set(valid_rows)
        history = [
            item
            for row, item in enumerate(self.app_config.history)
            if row not in removed
        ]
        self._replace_history(history)

    def _clear_history(self):
        if not self.app_config.history:
            return
        answer = QMessageBox.question(
            self,
            "清空同步记录",
            "确定清空所有同步记录吗？\n\n"
            "此操作只删除本机日志，不会删除或更改飞书汇总表中的任何数据。",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._replace_history([])
