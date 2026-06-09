import sys
import copy
from PyQt5.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QDialogButtonBox,
    QSpinBox, QDoubleSpinBox, QSlider
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

DIALOG_STYLE = """
QDialog { background: #1e1e1e; color: #e0e0e0; }
QTabWidget::pane { border: 1px solid #444; background: #1e1e1e; }
QTabBar::tab { background: #2a2a2a; color: #aaa; padding: 6px 14px; border: 1px solid #444; }
QTabBar::tab:selected { background: #1e1e1e; color: #e0e0e0; border-bottom: none; }
QCheckBox { color: #e0e0e0; spacing: 6px; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #666; background: #2a2a2a; }
QCheckBox::indicator:checked { background: #4CAF50; border-color: #4CAF50; }
QLabel { color: #e0e0e0; }
QPushButton {
    background: #2a2a2a; color: #e0e0e0; border: 1px solid #555;
    padding: 4px 12px; border-radius: 3px;
}
QPushButton:hover { background: #3a3a3a; }
QTableWidget {
    background: #141414; color: #e0e0e0; gridline-color: #333;
    border: 1px solid #444; selection-background-color: #2a5a8a;
}
QHeaderView::section { background: #2a2a2a; color: #aaa; border: 1px solid #444; padding: 4px; }
QSpinBox, QDoubleSpinBox {
    background: #2a2a2a; color: #e0e0e0; border: 1px solid #555; padding: 2px 4px;
}
QSlider::groove:horizontal { background: #333; height: 4px; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #4CAF50; width: 12px; height: 12px;
    border-radius: 6px; margin: -4px 0;
}
QDialogButtonBox QPushButton { min-width: 70px; }
"""


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Consolas", 9, QFont.Bold))
    lbl.setStyleSheet("color: #888; background: transparent; margin-top: 8px;")
    return lbl


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color: #333;")
    return line


def _spin_row(label: str, widget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(QLabel(label))
    row.addStretch()
    row.addWidget(widget)
    return row


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, stock_names: dict, parent=None):
        super().__init__(parent)
        self._cfg = copy.deepcopy(cfg)
        self._stock_names = stock_names

        self.setWindowTitle("StockViewer 설정")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setFixedSize(460, 420)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_display_tab(), "표시")
        self._tabs.addTab(self._build_position_tab(), "포지션")
        self._tabs.addTab(self._build_alert_tab(), "알림")
        self._tabs.addTab(self._build_system_tab(), "시스템")
        layout.addWidget(self._tabs)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    # ── 탭 1: 표시 ──────────────────────────────────────────────
    def _build_display_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        # 너비
        lay.addWidget(_section_label("창 너비 (px)"))
        self._spin_width = QSpinBox()
        self._spin_width.setRange(200, 600)
        self._spin_width.setValue(self._cfg.get("window_width", 280))
        self._spin_width.setSuffix(" px")
        lay.addLayout(_spin_row("너비", self._spin_width))

        note_w = QLabel("폰트·표시 설정에 따라 최솟값이 자동 보장됩니다")
        note_w.setStyleSheet("color: #666; font-size: 8pt;")
        lay.addWidget(note_w)

        lay.addWidget(_separator())

        # 폰트 크기
        lay.addWidget(_section_label("폰트 크기"))
        self._spin_font = QSpinBox()
        self._spin_font.setRange(8, 18)
        self._spin_font.setValue(self._cfg.get("font_size", 10))
        self._spin_font.setSuffix(" pt")
        lay.addLayout(_spin_row("폰트 크기", self._spin_font))

        lay.addWidget(_separator())

        # 기능 토글
        lay.addWidget(_section_label("표시 옵션"))
        self._chk_amount = QCheckBox("변동액 절대값 표시  (▲₩1,750 2.50%)")
        self._chk_amount.setChecked(self._cfg.get("show_change_amount", False))
        lay.addWidget(self._chk_amount)

        self._chk_sort = QCheckBox("변동률 높은순 자동 정렬")
        self._chk_sort.setChecked(self._cfg.get("sort_by_change", False))
        lay.addWidget(self._chk_sort)

        lay.addStretch()
        return w

    # ── 탭 2: 포지션 ────────────────────────────────────────────
    def _build_position_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        self._chk_pos = QCheckBox("손익 계산 활성화")
        self._chk_pos.setChecked(self._cfg.get("show_positions", False))
        lay.addWidget(self._chk_pos)

        note = QLabel("수량과 매수가를 입력하면 실시간 손익을 계산합니다.")
        note.setStyleSheet("color: #666; font-size: 9pt;")
        lay.addWidget(note)

        self._pos_table = QTableWidget()
        self._pos_table.setColumnCount(3)
        self._pos_table.setHorizontalHeaderLabels(["종목", "수량", "매수가 (₩)"])
        self._pos_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._pos_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._pos_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._pos_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._pos_table.verticalHeader().setVisible(False)
        self._populate_pos_table()
        lay.addWidget(self._pos_table)
        return w

    def _populate_pos_table(self):
        stocks    = self._cfg.get("stocks", [])
        positions = self._cfg.get("positions", {})
        self._pos_table.setRowCount(len(stocks))
        for i, code in enumerate(stocks):
            name = self._stock_names.get(code, code)
            item = QTableWidgetItem(f"{name} ({code})")
            item.setFlags(Qt.ItemIsEnabled)
            self._pos_table.setItem(i, 0, item)

            pos = positions.get(code, {})

            qty_spin = QSpinBox()
            qty_spin.setRange(0, 9_999_999)
            qty_spin.setValue(pos.get("qty", 0))
            qty_spin.setStyleSheet("background: #2a2a2a; color: #e0e0e0; border: none;")
            self._pos_table.setCellWidget(i, 1, qty_spin)

            buy_spin = QDoubleSpinBox()
            buy_spin.setRange(0, 99_999_999)
            buy_spin.setDecimals(0)
            buy_spin.setValue(pos.get("buy_price", 0))
            buy_spin.setStyleSheet("background: #2a2a2a; color: #e0e0e0; border: none;")
            self._pos_table.setCellWidget(i, 2, buy_spin)

    def _collect_positions(self) -> dict:
        stocks = self._cfg.get("stocks", [])
        result = {}
        for i, code in enumerate(stocks):
            qty_w = self._pos_table.cellWidget(i, 1)
            buy_w = self._pos_table.cellWidget(i, 2)
            if qty_w and buy_w:
                qty = qty_w.value()
                buy = int(buy_w.value())
                if qty > 0 or buy > 0:
                    result[code] = {"qty": qty, "buy_price": buy}
        return result

    # ── 탭 3: 알림 ──────────────────────────────────────────────
    def _build_alert_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        self._chk_alert = QCheckBox("알림 기능 활성화 (Windows 트레이 알림)")
        self._chk_alert.setChecked(self._cfg.get("alerts_enabled", False))
        lay.addWidget(self._chk_alert)

        lay.addWidget(_separator())
        lay.addWidget(_section_label("알림 조건"))

        note = QLabel("변동률(절댓값)이 아래 값 이상이면 알림을 보냅니다.\n"
                      "예) 3.0 → ±3% 이상 변동 시 알림")
        note.setStyleSheet("color: #888; font-size: 9pt;")
        lay.addWidget(note)

        self._spin_pct = QDoubleSpinBox()
        self._spin_pct.setRange(0.1, 30.0)
        self._spin_pct.setDecimals(1)
        self._spin_pct.setSingleStep(0.5)
        self._spin_pct.setSuffix(" %")
        self._spin_pct.setValue(self._cfg.get("alert_min_pct", 3.0))
        lay.addLayout(_spin_row("최소 변동률", self._spin_pct))

        lay.addStretch()
        return w

    # ── 탭 4: 시스템 ────────────────────────────────────────────
    def _build_system_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        lay.addWidget(_section_label("시작 옵션"))

        self._chk_autostart = QCheckBox("Windows 시작 시 자동 실행")
        self._chk_autostart.setChecked(self._cfg.get("auto_start", False))
        lay.addWidget(self._chk_autostart)

        self._chk_hidden = QCheckBox("시작 시 숨긴 상태로 (트레이에만 표시)")
        self._chk_hidden.setChecked(self._cfg.get("start_hidden", False))
        lay.addWidget(self._chk_hidden)

        if not getattr(sys, "frozen", False):
            note = QLabel("※ 자동 시작은 .exe 빌드 실행 시에만 적용됩니다.")
            note.setStyleSheet("color: #666; font-size: 9pt;")
            lay.addWidget(note)

        lay.addStretch()
        return w

    # ── 저장 ────────────────────────────────────────────────────
    def _on_accept(self):
        self._cfg["window_width"]      = self._spin_width.value()
        self._cfg["font_size"]         = self._spin_font.value()
        self._cfg["show_change_amount"] = self._chk_amount.isChecked()
        self._cfg["sort_by_change"]    = self._chk_sort.isChecked()
        self._cfg["show_positions"]    = self._chk_pos.isChecked()
        self._cfg["positions"]         = self._collect_positions()
        self._cfg["alerts_enabled"]    = self._chk_alert.isChecked()
        self._cfg["alert_min_pct"]     = self._spin_pct.value()
        self._cfg["auto_start"]        = self._chk_autostart.isChecked()
        self._cfg["start_hidden"]      = self._chk_hidden.isChecked()
        self.accept()

    def get_config(self) -> dict:
        return self._cfg
