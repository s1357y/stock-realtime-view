from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QMenu, QAction,
    QWidgetAction, QSlider, QInputDialog, QMessageBox,
    QSystemTrayIcon, QApplication
)
from PyQt5.QtCore import Qt, QDateTime
from datetime import datetime, timezone, timedelta, time as dtime
from PyQt5.QtGui import QPainter, QColor, QFont, QKeySequence, QPixmap, QIcon
from PyQt5.QtWidgets import QShortcut

from config import load_config, save_config
from ticker_widget import TickerWidget
from data_worker import StockWorker, fetch_stock

BG_COLOR = QColor(18, 18, 18, 210)
HEADER_COLOR = "#606060"
MENU_STYLE = (
    "QMenu { background: #1e1e1e; color: #e0e0e0; border: 1px solid #444; }"
    "QMenu::item:selected { background: #333; }"
)


def _make_tray_icon() -> QIcon:
    px = QPixmap(16, 16)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(60, 200, 60))
    p.setPen(Qt.NoPen)
    p.drawEllipse(1, 1, 14, 14)
    p.end()
    return QIcon(px)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._cfg = load_config()
        self._drag_pos = None
        self._widgets: dict[str, TickerWidget] = {}

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        opacity = max(0.15, min(0.95, self._cfg["opacity"]))
        self.setWindowOpacity(opacity)
        self._restore_position()

        self._build_ui()
        self._setup_shortcuts()
        self._setup_tray()
        self._start_worker()

    def _restore_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = self._cfg["window_x"]
        y = self._cfg["window_y"]
        x = max(screen.left(), min(x, screen.right() - 280))
        y = max(screen.top(), min(y, screen.bottom() - 60))
        self.move(x, y)

    def _build_ui(self):
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(2, 4, 2, 4)
        self._main_layout.setSpacing(1)

        header = QLabel("▣ STOCK")
        header.setFont(QFont("Consolas", 8))
        header.setStyleSheet(f"color: {HEADER_COLOR}; background: transparent;")
        header.setAlignment(Qt.AlignCenter)
        header.setFixedHeight(16)
        self._main_layout.addWidget(header)

        self._time_lbl = QLabel("--:--:--")
        self._time_lbl.setFont(QFont("Consolas", 7))
        self._time_lbl.setStyleSheet("color: #444444; background: transparent;")
        self._time_lbl.setAlignment(Qt.AlignCenter)
        self._time_lbl.setFixedHeight(12)
        self._main_layout.addWidget(self._time_lbl)

        for code in self._cfg["stocks"]:
            self._add_ticker_widget(code)

        self._update_size()

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(_make_tray_icon(), self)
        self._tray.setToolTip("StockViewer")

        tray_menu = QMenu()
        tray_menu.setStyleSheet(MENU_STYLE)
        tray_menu.addAction("보이기 / 숨기기", self._toggle_visibility)
        tray_menu.addSeparator()
        tray_menu.addAction("완전 종료", self._quit_app)
        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_visibility()

    def _add_ticker_widget(self, code: str):
        w = TickerWidget(code, self)
        self._widgets[code] = w
        self._main_layout.addWidget(w)

    def _remove_ticker_widget(self, code: str):
        w = self._widgets.pop(code, None)
        if w:
            self._main_layout.removeWidget(w)
            w.deleteLater()

    def _update_size(self):
        count = len(self._widgets)
        h = 36 + count * 23 + 8
        self.setFixedSize(280, h)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl++"), self).activated.connect(self._opacity_up)
        QShortcut(QKeySequence("Ctrl+="), self).activated.connect(self._opacity_up)
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(self._opacity_down)
        QShortcut(QKeySequence("Ctrl+H"), self).activated.connect(self._toggle_visibility)
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self._refresh_now)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self._quit_app)

    def _start_worker(self):
        self._worker = StockWorker(self._cfg["stocks"], self._cfg["update_interval"])
        self._worker.data_ready.connect(self._on_data)
        self._worker.start()

    def _on_data(self, records: list):
        for rec in records:
            w = self._widgets.get(rec["code"])
            if w:
                w.update_data(rec)

        KST = timezone(timedelta(hours=9))
        now_kst = datetime.now(KST)
        is_weekday = now_kst.weekday() < 5
        t = now_kst.time()
        market_open = is_weekday and dtime(9, 0) <= t <= dtime(15, 30)
        any_overtime = any(r.get("is_overtime") for r in records)

        if market_open:
            status = "장중"
        elif any_overtime:
            status = "시외"
        else:
            status = "마감"

        now_str = QDateTime.currentDateTime().toString("HH:mm:ss")
        self._time_lbl.setText(f"{now_str} {status}")

    def _opacity_up(self):
        val = min(0.95, self.windowOpacity() + 0.1)
        self.setWindowOpacity(val)

    def _opacity_down(self):
        val = max(0.10, self.windowOpacity() - 0.1)
        self.setWindowOpacity(val)

    def _toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()

    def _refresh_now(self):
        self._worker.stop()
        self._worker = StockWorker(self._cfg["stocks"], self._cfg["update_interval"])
        self._worker.data_ready.connect(self._on_data)
        self._worker.start()

    def _quit_app(self):
        cfg = load_config()
        cfg["window_x"] = self.x()
        cfg["window_y"] = self.y()
        cfg["opacity"] = self.windowOpacity()
        cfg["stocks"] = self._cfg["stocks"]
        cfg["update_interval"] = self._cfg["update_interval"]
        save_config(cfg)
        self._tray.hide()
        self._worker.stop()
        QApplication.quit()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)

        menu.addAction("종목 추가...", self._add_stock)
        menu.addAction("종목 제거...", self._remove_stock)
        menu.addSeparator()

        opacity_menu = menu.addMenu(f"투명도 ({int(self.windowOpacity() * 100)}%)")
        slider_action = QWidgetAction(opacity_menu)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(10, 95)
        slider.setValue(int(self.windowOpacity() * 100))
        slider.setFixedWidth(140)
        slider.setStyleSheet("QSlider { margin: 4px 8px; }")
        slider.valueChanged.connect(lambda v: self.setWindowOpacity(v / 100))
        slider_action.setDefaultWidget(slider)
        opacity_menu.addAction(slider_action)

        interval_menu = menu.addMenu(f"갱신 주기 ({self._cfg['update_interval']}초)")
        for sec in [5, 10, 30, 60]:
            act = QAction(f"{sec}초", self)
            act.setCheckable(True)
            act.setChecked(self._cfg["update_interval"] == sec)
            act.triggered.connect(lambda _, s=sec: self._set_interval(s))
            interval_menu.addAction(act)

        menu.addSeparator()
        menu.addAction("완전 종료", self._quit_app)
        menu.exec(event.globalPos())

    def _add_stock(self):
        code, ok = QInputDialog.getText(
            self, "종목 추가", "종목 코드 입력 (예: 005930):",
        )
        if not ok or not code.strip():
            return
        code = code.strip()
        if code in self._cfg["stocks"]:
            QMessageBox.information(self, "알림", f"{code}는 이미 추가되어 있습니다.")
            return

        rec = fetch_stock(code)
        if rec["error"] or rec["price"] == 0.0:
            QMessageBox.warning(self, "오류", f"'{code}' 종목을 찾을 수 없습니다.\n코드를 다시 확인해 주세요.")
            return

        self._cfg["stocks"].append(code)
        save_config(self._cfg)
        self._add_ticker_widget(code)
        self._update_size()
        self._on_data([rec])
        self._worker.update_codes(self._cfg["stocks"])

    def _remove_stock(self):
        if not self._cfg["stocks"]:
            return
        code, ok = QInputDialog.getItem(
            self, "종목 제거", "제거할 종목 선택:", self._cfg["stocks"], 0, False
        )
        if not ok:
            return
        self._cfg["stocks"].remove(code)
        save_config(self._cfg)
        self._remove_ticker_widget(code)
        self._update_size()
        self._worker.update_codes(self._cfg["stocks"])

    def _set_interval(self, sec: int):
        self._cfg["update_interval"] = sec
        save_config(self._cfg)
        self._worker.update_interval(sec)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(BG_COLOR)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 7, 7)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def closeEvent(self, event):
        # 닫기 버튼 → 창만 숨김, 트레이에서 계속 실행
        event.ignore()
        self.hide()
