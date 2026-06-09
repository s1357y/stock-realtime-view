import json
import sys
from pathlib import Path

DEFAULT_CONFIG = {
    "stocks": ["005930", "000660", "035420", "009150", "005380", "006400"],
    "opacity": 0.75,
    "update_interval": 10,
    "window_x": 100,
    "window_y": 100,
    # 표시 설정
    "window_width": 280,
    "font_size": 10,
    "show_change_amount": False,
    "sort_by_change": False,
    # 포지션 (손익 계산)
    "show_positions": False,
    "positions": {},   # { "005930": {"qty": 10, "buy_price": 70000} }
    # 알림
    "alerts_enabled": False,
    "alert_min_pct": 3.0,  # 변동률 이 값 이상(절댓값)이면 알림
    # 시스템
    "auto_start": False,
    "start_hidden": False,
}


def get_config_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent
    return base / "settings.json"


def load_config() -> dict:
    path = get_config_path()
    cfg = DEFAULT_CONFIG.copy()
    cfg["positions"] = {}
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            cfg.update(saved)
        except Exception:
            pass
    return cfg


def save_config(cfg: dict) -> None:
    path = get_config_path()
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        if path.exists():
            path.unlink()
        tmp.rename(path)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
