"""Application-wide Feishu-inspired visual theme."""


APP_STYLE = """
QMainWindow, QWidget#appRoot, QStackedWidget { background: #F4F7FC; color: #18233A; }
QWidget { font-family: "Microsoft YaHei UI"; font-size: 13px; color: #18233A; }
QDialog, QMessageBox { background: #F4F7FC; }

QFrame#sidebar { background: #13213B; border: none; }
QFrame#sidebar QLabel#brandTitle { font-size: 19px; font-weight: 700; color: #EAF2FF; }
QFrame#sidebar QLabel#brandSubtitle { color: #9FB1CD; font-size: 12px; }
QPushButton#navButton { text-align: left; padding: 11px 15px; border: none; border-radius: 10px; background: transparent; color: #9FB1CD; }
QPushButton#navButton:hover { background: rgba(255, 255, 255, 0.08); color: #EAF2FF; }
QPushButton#navButton:checked { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3370FF, stop:1 #4F8CFF); color: #FFFFFF; font-weight: 700; }
QPushButton#navButton:pressed { background: #2860E1; }

QFrame#card { background: #FFFFFF; border: 1px solid #E8EDF5; border-radius: 14px; }
QLabel#pageTitle { font-size: 26px; font-weight: 700; color: #18233A; }
QLabel#sectionTitle { font-size: 15px; font-weight: 650; color: #18233A; }
QLabel#muted { color: #5F6F88; font-size: 12px; }
QFrame#mappingCard { background: #FBFDFF; border: 1px solid #DFE7F3; border-radius: 11px; }
QFrame#mappingCard:hover { background: #FFFFFF; border-color: #B8CAF0; }
QLabel#statusChip { background: #EDF3FF; color: #3370FF; border-radius: 10px; padding: 4px 9px; font-size: 11px; font-weight: 650; }
QLabel#emptyState { color: #7B899F; background: #F8FAFE; border: 1px dashed #CDD8E8; border-radius: 10px; padding: 22px; line-height: 1.5; }
QLabel#rowError { color: #C94A52; font-size: 11px; }
QLabel#mappingArrow { color: #3370FF; font-size: 18px; font-weight: 700; }
QLabel#mappingColumnHeader { color: #536784; font-size: 12px; font-weight: 650; padding: 2px 4px; }

QLineEdit, QComboBox, QDateEdit, QSpinBox {
    background: #F9FBFF; border: 1px solid #DFE6F1; border-radius: 8px;
    padding: 7px 10px; min-height: 20px; selection-background-color: #3370FF;
}
QLineEdit:hover, QComboBox:hover, QDateEdit:hover, QSpinBox:hover { border-color: #B9C8DF; background: #FFFFFF; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus { border: 1.5px solid #3370FF; background: #FFFFFF; }
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled { background: #F0F3F8; color: #9AA6B8; }
QComboBox::drop-down, QDateEdit::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: #FFFFFF; border: 1px solid #DCE4F0; selection-background-color: #E7F0FF; selection-color: #245BDB; outline: 0; }

QPushButton { border: 1px solid #DCE3EE; border-radius: 8px; padding: 8px 15px; background: #FFFFFF; color: #263552; }
QPushButton:hover { background: #F3F7FD; border-color: #BFCDE2; }
QPushButton:pressed { background: #E8EEF7; }
QPushButton:disabled { background: #F1F4F8; color: #A6B0BF; border-color: #E5EAF1; }
QPushButton#primaryButton { background: #3370FF; color: #FFFFFF; border: none; font-weight: 650; }
QPushButton#primaryButton:hover { background: #2860E1; }
QPushButton#primaryButton:pressed { background: #1E50C9; }
QPushButton#primaryButton:disabled { background: #B7C8F5; color: #F7F9FF; }
QPushButton#dangerButton { color: #C94A52; border-color: #F0C9CC; background: #FFF9F9; }
QPushButton#dangerButton:hover { color: #B7333D; background: #FFF0F1; border-color: #EBAEB3; }
QPushButton#mappingDeleteButton { color: #C94A52; border-color: #F0C9CC; background: #FFF9F9; padding: 7px 10px; }
QPushButton#mappingDeleteButton:hover { color: #B7333D; background: #FFF0F1; border-color: #EBAEB3; }
QComboBox#mappingModeCombo { min-width: 150px; max-width: 190px; padding-top: 5px; padding-bottom: 5px; }

QTableWidget { background: #FFFFFF; border: 1px solid #E5EBF3; border-radius: 9px; gridline-color: #EDF1F6; alternate-background-color: #FAFCFF; selection-background-color: #E7F0FF; selection-color: #1F4FBF; outline: 0; }
QTableWidget::item { padding: 6px; border-bottom: 1px solid #F0F3F7; }
QTableWidget::item:hover { background: #F1F6FF; }
QHeaderView::section { background: #EDF3FF; color: #536784; border: none; border-bottom: 1px solid #DDE7F5; padding: 9px; font-weight: 650; }
QTableCornerButton::section { background: #EDF3FF; border: none; border-bottom: 1px solid #DDE7F5; }

QProgressBar { background: #E5EBF4; border: none; border-radius: 6px; min-height: 10px; max-height: 10px; text-align: center; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3370FF, stop:1 #22C3D6); border-radius: 6px; }
QTextEdit { background: #F7FAFE; border: 1px solid #E1E8F2; border-radius: 9px; padding: 9px; selection-background-color: #3370FF; }
QTextEdit:focus { border-color: #3370FF; background: #FFFFFF; }
QScrollArea { border: none; background: transparent; }
QCheckBox { spacing: 7px; color: #263552; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #BCC9DA; border-radius: 4px; background: #FFFFFF; }
QCheckBox::indicator:hover { border-color: #3370FF; }
QCheckBox::indicator:checked { background: #3370FF; border-color: #3370FF; image: none; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #C7D2E2; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #9EADC2; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #C7D2E2; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QToolTip { color: #EAF2FF; background: #13213B; border: 1px solid #2C4165; padding: 6px; }
"""
