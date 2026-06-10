from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QMenu
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

COLOR_UP    = "#FF4444"
COLOR_DOWN  = "#4499FF"
COLOR_FLAT  = "#AAAAAA"
COLOR_TEXT  = "#E0E0E0"
COLOR_ERROR = "#888888"
COLOR_PNL_P = "#66DD66"
COLOR_PNL_N = "#FF7777"
COLOR_PNL_0 = "#888888"

MENU_STYLE = (
    "QMenu { background: #1e1e1e; color: #e0e0e0; border: 1px solid #444; }"
    "QMenu::item:selected { background: #333; }"
)


def calc_row_heights(font_size: int):
    """Returns (normal_height, position_height, pnl_label_height)"""
    normal  = max(font_size + 12, 18)
    pnl_h   = max(font_size + 4,  14)
    position = normal + pnl_h + 2
    return normal, position, pnl_h


class TickerWidget(QWidget):
    move_requested = pyqtSignal(str, int)   # (code, direction: -1 or +1)

    def __init__(self, code: str, cfg: dict, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._code = code
        self._cfg = cfg
        self._last_record: dict = {}
        self._setup_ui()

    def _font(self, size=None, bold=False) -> QFont:
        fs = size if size is not None else self._cfg.get("font_size", 10)
        f = QFont("Consolas", fs)
        f.setBold(bold)
        return f

    def _setup_ui(self):
        font_size = self._cfg.get("font_size", 10)
        normal_h, pos_h, pnl_h = calc_row_heights(font_size)
        show_pos = self._cfg.get("show_positions", False)
        self.setFixedHeight(pos_h if show_pos else normal_h)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 0, 6, 0)
        outer.setSpacing(0)

        # 메인 행
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(4)

        self._name_lbl  = QLabel("")
        self._price_lbl = QLabel("---")
        self._change_lbl = QLabel("")

        for lbl, align in [
            (self._name_lbl,  Qt.AlignLeft),
            (self._price_lbl, Qt.AlignRight),
        ]:
            lbl.setFont(self._font())
            lbl.setAlignment(align | Qt.AlignVCenter)
            lbl.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")

        self._change_lbl.setFont(self._font())
        self._change_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._change_lbl.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")

        row1.addWidget(self._name_lbl)
        row1.addWidget(self._price_lbl)
        row1.addWidget(self._change_lbl)
        outer.addLayout(row1)

        # 손익 행
        self._pnl_lbl = QLabel("")
        self._pnl_lbl.setFont(self._font(max(font_size - 2, 7)))
        self._pnl_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._pnl_lbl.setStyleSheet(f"color: {COLOR_PNL_0}; background: transparent;")
        self._pnl_lbl.setFixedHeight(pnl_h)
        self._pnl_lbl.setVisible(show_pos)
        outer.addWidget(self._pnl_lbl)

    def set_column_widths(self, name_w: int, price_w: int):
        self._name_lbl.setFixedWidth(name_w)
        self._price_lbl.setFixedWidth(price_w)

    def apply_config(self, cfg: dict):
        self._cfg = cfg
        font_size = cfg.get("font_size", 10)
        normal_h, pos_h, pnl_h = calc_row_heights(font_size)
        show_pos = cfg.get("show_positions", False)

        self.setFixedHeight(pos_h if show_pos else normal_h)
        self._pnl_lbl.setVisible(show_pos)
        self._pnl_lbl.setFixedHeight(pnl_h)

        f = self._font()
        for lbl in (self._name_lbl, self._price_lbl, self._change_lbl):
            lbl.setFont(f)
        self._pnl_lbl.setFont(self._font(max(font_size - 2, 7)))

        if self._last_record:
            self.update_data(self._last_record)

    def update_data(self, record: dict):
        self._last_record = record
        show_amount = self._cfg.get("show_change_amount", False)

        if record["error"]:
            self._name_lbl.setText(record["code"])
            self._price_lbl.setText("오류")
            self._price_lbl.setStyleSheet(f"color: {COLOR_ERROR}; background: transparent;")
            self._change_lbl.setText("")
            self._pnl_lbl.setText("")
            return

        name = record["name"]
        self._name_lbl.setToolTip(name)
        if len(name) > 7:
            name = name[:6] + "…"
        self._name_lbl.setText(name)

        price = record["price"]
        price_str = f"₩{int(price):,}" if price > 0 else "---"
        self._price_lbl.setText(price_str)
        self._price_lbl.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")

        pct = record["change_pct"]
        amt = record["change"]
        if pct > 0:
            color, arrow = COLOR_UP, "▲"
        elif pct < 0:
            color, arrow = COLOR_DOWN, "▼"
        else:
            color, arrow = COLOR_FLAT, "━"

        if show_amount and price > 0:
            change_text = f"{arrow}₩{abs(int(amt)):,} {abs(pct):.2f}%"
        else:
            change_text = f"{arrow}{abs(pct):.2f}%"

        if record.get("is_overtime"):
            _overtime_color = "#FFE066"
            html = (
                f'<span style="color:{color};">{change_text}</span>'
                f' <span style="color:{_overtime_color};">장외</span>'
            )
            self._change_lbl.setText(html)
            self._change_lbl.setStyleSheet("background: transparent;")
        else:
            self._change_lbl.setText(change_text)
            self._change_lbl.setStyleSheet(f"color: {color}; background: transparent;")

        # 손익
        if self._cfg.get("show_positions") and price > 0:
            pos = self._cfg.get("positions", {}).get(record["code"])
            if pos:
                qty = pos.get("qty", 0)
                buy = pos.get("buy_price", 0)
                if qty > 0 and buy > 0:
                    pnl = (price - buy) * qty
                    pnl_pct = (price - buy) / buy * 100
                    sign = "+" if pnl >= 0 else ""
                    pnl_color = COLOR_PNL_P if pnl > 0 else (COLOR_PNL_N if pnl < 0 else COLOR_PNL_0)
                    self._pnl_lbl.setText(f"{sign}₩{int(pnl):,} ({sign}{pnl_pct:.1f}%)")
                    self._pnl_lbl.setStyleSheet(f"color: {pnl_color}; background: transparent;")
                    return
            self._pnl_lbl.setText("수량 미입력")
            self._pnl_lbl.setStyleSheet(f"color: {COLOR_PNL_0}; background: transparent;")

    def contextMenuEvent(self, event):
        stocks = self._cfg.get("stocks", [])
        idx = stocks.index(self._code) if self._code in stocks else -1

        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        up_act   = menu.addAction("↑ 위로")
        down_act = menu.addAction("↓ 아래로")
        up_act.setEnabled(idx > 0)
        down_act.setEnabled(0 <= idx < len(stocks) - 1)

        action = menu.exec_(event.globalPos())
        if action == up_act:
            self.move_requested.emit(self._code, -1)
        elif action == down_act:
            self.move_requested.emit(self._code, +1)
        event.accept()
