from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# 한국 HTS 표준: 상승=빨강, 하락=파랑
COLOR_UP       = "#FF4444"
COLOR_DOWN     = "#4499FF"
COLOR_FLAT     = "#AAAAAA"
COLOR_TEXT     = "#E0E0E0"
COLOR_ERROR    = "#888888"

FONT = QFont("Consolas", 10)
FONT.setBold(False)


def _make_label(text: str, width: int, align=Qt.AlignRight) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(FONT)
    lbl.setFixedWidth(width)
    lbl.setAlignment(align | Qt.AlignVCenter)
    lbl.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")
    return lbl


class TickerWidget(QWidget):
    def __init__(self, code: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(22)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(4)

        self._name_lbl  = _make_label(code,  90, Qt.AlignLeft)
        self._price_lbl = _make_label("---", 80, Qt.AlignRight)
        self._change_lbl = _make_label("",   80, Qt.AlignRight)

        layout.addWidget(self._name_lbl)
        layout.addWidget(self._price_lbl)
        layout.addWidget(self._change_lbl)

    def update_data(self, record: dict):
        if record["error"]:
            self._name_lbl.setText(record["code"])
            self._price_lbl.setText("오류")
            self._price_lbl.setStyleSheet(f"color: {COLOR_ERROR}; background: transparent;")
            self._change_lbl.setText("")
            return

        name = record["name"]
        if len(name) > 8:
            name = name[:7] + "…"
        self._name_lbl.setText(name)

        price = record["price"]
        is_overtime = record.get("is_overtime", False)

        price_str = f"₩{int(price):,}" if price > 0 else "---"
        self._price_lbl.setText(price_str)
        self._price_lbl.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")

        pct = record["change_pct"]
        if pct > 0:
            color = COLOR_UP
            arrow = "▲"
        elif pct < 0:
            color = COLOR_DOWN
            arrow = "▼"
        else:
            color = COLOR_FLAT
            arrow = "━"

        change_text = f"{arrow}{abs(pct):.2f}%"
        if is_overtime:
            change_text += " 외"

        self._change_lbl.setText(change_text)
        self._change_lbl.setStyleSheet(f"color: {color}; background: transparent;")
