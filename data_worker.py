import time
import requests
from PyQt5.QtCore import QThread, pyqtSignal

NAVER_API = "https://m.stock.naver.com/api/stock/{code}/basic"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# 네이버 금융 API 부호 코드: "1"=상한가, "2"=상승, "3"=보합, "4"=하한가, "5"=하락
_RISING_CODES  = {"1", "2", "RISE", "RISING"}
_FALLING_CODES = {"4", "5", "FALL", "FALLING"}


def _to_float(val) -> float:
    if val is None:
        return 0.0
    s = str(val).replace(",", "").strip()
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def _apply_sign(sign_code: str, change: float, change_pct: float):
    if sign_code in _RISING_CODES:
        return abs(change), abs(change_pct)
    if sign_code in _FALLING_CODES:
        return -abs(change), -abs(change_pct)
    return change, change_pct   # 보합(3): API가 이미 0 반환


def _get_sign_code(obj) -> str:
    if isinstance(obj, dict):
        return obj.get("code", "3")
    return "3"


def fetch_stock(code: str) -> dict:
    try:
        url = NAVER_API.format(code=code)
        resp = requests.get(url, headers=HEADERS, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        name = data.get("stockName", code)

        # 시간외 단일가 확인 (overMarketPriceInfo.overMarketStatus == "OPEN")
        ovtm = data.get("overMarketPriceInfo") or {}
        is_overtime = (
            ovtm.get("overMarketStatus") == "OPEN"
            and bool((ovtm.get("overPrice") or "").strip())
        )

        if is_overtime:
            price      = _to_float(ovtm.get("overPrice"))
            sign_code  = _get_sign_code(ovtm.get("compareToPreviousPrice"))
            change     = _to_float(ovtm.get("compareToPreviousClosePrice"))
            change_pct = _to_float(ovtm.get("fluctuationsRatio"))
        else:
            price      = _to_float(data.get("closePrice"))
            sign_code  = _get_sign_code(data.get("compareToPreviousPrice"))
            change     = _to_float(data.get("compareToPreviousClosePrice"))
            change_pct = _to_float(data.get("fluctuationsRatio"))

        change, change_pct = _apply_sign(sign_code, change, change_pct)

        return {
            "code":        code,
            "name":        name,
            "price":       price,
            "change":      change,
            "change_pct":  change_pct,
            "is_overtime": is_overtime,
            "error":       False,
        }
    except Exception as e:
        print(f"[ERROR] {code}: {e}")
        return {
            "code":        code,
            "name":        code,
            "price":       0.0,
            "change":      0.0,
            "change_pct":  0.0,
            "is_overtime": False,
            "error":       True,
        }


class StockWorker(QThread):
    data_ready = pyqtSignal(list)

    def __init__(self, codes: list, interval: int):
        super().__init__()
        self._codes    = list(codes)
        self._interval = interval
        self._stop_flag = False

    def run(self):
        while not self._stop_flag:
            records = [fetch_stock(code) for code in self._codes]
            self.data_ready.emit(records)
            for _ in range(self._interval * 2):
                if self._stop_flag:
                    return
                time.sleep(0.5)

    def update_codes(self, codes: list):
        self._codes = list(codes)

    def update_interval(self, interval: int):
        self._interval = interval

    def stop(self):
        self._stop_flag = True
        self.wait()
