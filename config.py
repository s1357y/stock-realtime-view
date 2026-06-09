import json
import sys
from pathlib import Path

DEFAULT_CONFIG = {
    "stocks": ["005930", "000660", "035420", "009150", "005380", "006400"],
    "opacity": 0.75,
    "update_interval": 10,
    "window_x": 100,
    "window_y": 100,
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
        tmp.replace(path)
    except Exception:
        pass
