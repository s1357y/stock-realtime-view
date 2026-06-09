import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QMenu, QAction,
    QWidgetAction, QSlider, QInputDialog, QMessageBox,
    QSystemTrayIcon, QApplication
)
from PyQt5.QtCore import Qt, QDateTime, QPoint
from datetime import datetime, timezone, timedelta, time as dtime
from PyQt5.QtGui import QPainter, QColor, QFont, QKeySequence, QPixmap, QIcon
from PyQt5.QtWidgets import QShortcut

from config import load_config, save_config
from ticker_widget import TickerWidget, calc_row_heights
from data_worker import StockWorker, fetch_stock
from settings_dialog import SettingsDialog

BG_COLOR     = QColor(18, 18, 18, 210)
HEADER_COLOR = "#606060"
MENU_STYLE = (
    "QMenu { background: #1e1e1e; color: #e0e0e0; border: 1px solid #444; }"
    "QMenu::item:selected { background: #333; }"
)


def _make_tray_icon() -> QIcon:
    px = QPixmap(16, 16)
    px.fill(Qt.transparent)
    p = QPainter(px)
    try:
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(60, 200, 60))
        p.setPen(Qt.NoPen)
        p.drawEllipse(1, 1, 14, 14)
    finally:
        p.end()
    return QIcon(px)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._cfg = load_config()
        self._drag_pos = None
        self._widgets: dict[str, TickerWidget] = {}
        self._stock_names: dict[str, str] = {}
        self._stealth = False
        self._last_records: list = []
        self._fired_alerts: set = set()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(max(0.15, min(0.95, self._cfg["opacity"])))
        self._restore_position()

        self._build_ui()
        self._setup_shortcuts()
        self._setup_tray()
        self._start_worker()

        if self._cfg.get("start_hidden"):
            self.hide()

    def _restore_position(self):
        x = self._cfg["window_x"]
        y = self._cfg["window_y"]
        screen = QApplication.screenAt(QPoint(x, y)) or QApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = max(geo.left(), min(x, geo.right()  - self._cfg.get("window_width", 280)))
        y = max(geo.top(),  min(y, geo.bottom() - 60))
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
        w = TickerWidget(code, self._cfg, self)
        w.move_requested.connect(self._move_stock)
        self._widgets[code] = w
        self._main_layout.addWidget(w)

    def _remove_ticker_widget(self, code: str):
        w = self._widgets.pop(code, None)
        if w:
            self._main_layout.removeWidget(w)
            w.deleteLater()

    def _update_size(self):
        from PyQt5.QtGui import QFontMetrics
        font_size = self._cfg.get("font_size", 10)
        show_amt  = self._cfg.get("show_change_amount", False)
        show_pos  = self._cfg.get("show_positions", False)

        fm  = QFontMetrics(QFont("Consolas", font_size))
        pad = 6

        name_w    = fm.horizontalAdvance("종목명주식1") + pad
        price_w   = fm.horizontalAdvance("₩9,999,999") + pad
        chg_text  = "▲₩1,234,567 99.99% 외" if show_amt else "▲99.99% 외"
        chg_min_w = fm.horizontalAdvance(chg_text) + pad

        min_w = name_w + price_w + chg_min_w + 12 + 8   # 12=마진 8=스페이싱
        w     = max(self._cfg.get("window_width", 280), min_w)

        for widget in self._widgets.values():
            widget.set_column_widths(name_w, price_w)

        count    = len(self._widgets)
        normal_h, pos_h, _ = calc_row_heights(font_size)
        row_h    = (pos_h + 1) if show_pos else (normal_h + 1)
        h        = 36 + count * row_h + 8
        self.setFixedSize(w, h)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl++"), self).activated.connect(self._opacity_up)
        QShortcut(QKeySequence("Ctrl+="), self).activated.connect(self._opacity_up)
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(self._opacity_down)
        QShortcut(QKeySequence("Ctrl+H"), self).activated.connect(self._toggle_visibility)
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self._refresh_now)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self._quit_app)
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self._toggle_stealth)

    def _start_worker(self):
        self._worker = StockWorker(self._cfg["stocks"], self._cfg["update_interval"])
        self._worker.data_ready.connect(self._on_data)
        self._worker.start()

    def _on_data(self, records: list):
        self._last_records = records
        if self._cfg.get("sort_by_change"):
            records = sorted(records, key=lambda r: abs(r.get("change_pct", 0)), reverse=True)

        for rec in records:
            if not rec["error"] and rec["name"] != rec["code"]:
                self._stock_names[rec["code"]] = rec["name"]
            w = self._widgets.get(rec["code"])
            if w:
                w.setVisible(not self._stealth)
                if not self._stealth:
                    w.update_data(rec)

        if self._cfg.get("alerts_enabled"):
            self._check_alerts(records)

        KST = timezone(timedelta(hours=9))
        now_kst = datetime.now(KST)
        t = now_kst.time()
        market_open = now_kst.weekday() < 5 and dtime(9, 0) <= t <= dtime(15, 30)
        any_overtime = any(r.get("is_overtime") for r in records)
        status = "장중" if market_open else ("시외" if any_overtime else "마감")
        self._time_lbl.setText(f"{QDateTime.currentDateTime().toString('HH:mm:ss')} {status}")

    def _check_alerts(self, records: list):
        min_pct = abs(self._cfg.get("alert_min_pct", 3.0))
        for rec in records:
            if rec["error"] or rec["price"] == 0:
                continue
            code = rec["code"]
            pct  = abs(rec["change_pct"])
            if pct >= min_pct:
                if code not in self._fired_alerts:
                    self._fired_alerts.add(code)
                    name = self._stock_names.get(code, code)
                    sign = "+" if rec["change_pct"] >= 0 else ""
                    self._tray.showMessage(
                        f"StockViewer — {name}",
                        f"₩{int(rec['price']):,}  ({sign}{rec['change_pct']:.2f}%)",
                        QSystemTrayIcon.Information,
                        4000,
                    )
            else:
                self._fired_alerts.discard(code)

    def _opacity_up(self):
        self.setWindowOpacity(min(0.95, self.windowOpacity() + 0.1))

    def _opacity_down(self):
        self.setWindowOpacity(max(0.10, self.windowOpacity() - 0.1))

    def _toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()

    def _toggle_stealth(self):
        self._stealth = not self._stealth
        for w in self._widgets.values():
            w.setVisible(not self._stealth)
        if not self._stealth and self._last_records:
            self._on_data(self._last_records)

    def _refresh_now(self):
        self._worker.data_ready.disconnect(self._on_data)
        self._worker.stop()
        self._start_worker()

    def _quit_app(self):
        self._cfg["window_x"] = self.x()
        self._cfg["window_y"] = self.y()
        self._cfg["opacity"]  = self.windowOpacity()
        save_config(self._cfg)
        self._tray.hide()
        self._worker.stop()
        QApplication.quit()

    # ── 순서 변경 ────────────────────────────────────────────────
    def _move_stock(self, code: str, direction: int):
        stocks = self._cfg["stocks"]
        if code not in stocks:
            return
        idx = stocks.index(code)
        new_idx = idx + direction
        if not (0 <= new_idx < len(stocks)):
            return
        stocks.pop(idx)
        stocks.insert(new_idx, code)
        save_config(self._cfg)
        self._rebuild_ticker_order()
        if self._last_records:
            self._on_data(self._last_records)

    def _rebuild_ticker_order(self):
        for w in self._widgets.values():
            self._main_layout.removeWidget(w)
        for code in self._cfg["stocks"]:
            w = self._widgets.get(code)
            if w:
                self._main_layout.addWidget(w)

    # ── 설정 팝업 ────────────────────────────────────────────────
    def _open_settings(self):
        dlg = SettingsDialog(self._cfg, self._stock_names, self)
        if dlg.exec_() != SettingsDialog.Accepted:
            return

        new_cfg = dlg.get_config()
        changed_autostart = new_cfg.get("auto_start") != self._cfg.get("auto_start")

        self._cfg.update(new_cfg)
        save_config(self._cfg)

        if changed_autostart:
            self._apply_auto_start(self._cfg.get("auto_start", False))

        self.setUpdatesEnabled(False)
        for w in self._widgets.values():
            w.apply_config(self._cfg)
        self._update_size()
        self.layout().activate()
        self.setUpdatesEnabled(True)
        self.update()

        if self._last_records:
            self._on_data(self._last_records)

    def _apply_auto_start(self, enable: bool):
        if not getattr(sys, "frozen", False):
            return
        try:
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                                winreg.KEY_SET_VALUE) as key:
                if enable:
                    winreg.SetValueEx(key, "StockViewer", 0, winreg.REG_SZ,
                                      f'"{sys.executable}"')
                else:
                    try:
                        winreg.DeleteValue(key, "StockViewer")
                    except FileNotFoundError:
                        pass
        except Exception as e:
            print(f"[autostart] {e}")

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
        stealth_act = QAction("스텔스 모드 (Ctrl+L)", self)
        stealth_act.setCheckable(True)
        stealth_act.setChecked(self._stealth)
        stealth_act.triggered.connect(self._toggle_stealth)
        menu.addAction(stealth_act)

        menu.addSeparator()
        menu.addAction("설정...", self._open_settings)
        menu.addSeparator()
        menu.addAction("완전 종료", self._quit_app)
        menu.exec(event.globalPos())

    def _add_stock(self):
        code, ok = QInputDialog.getText(self, "종목 추가", "종목 코드 입력 (예: 005930):")
        if not ok or not code.strip():
            return
        code = code.strip()
        if code in self._cfg["stocks"]:
            QMessageBox.information(self, "알림", f"{code}는 이미 추가되어 있습니다.")
            return
        rec = fetch_stock(code)
        if rec["error"] or rec["price"] == 0.0:
            QMessageBox.warning(self, "오류", f"'{code}' 종목을 찾을 수 없습니다.")
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
            self, "종목 제거", "제거할 종목 선택:", self._cfg["stocks"], 0, False)
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
        event.ignore()
        self.hide()
