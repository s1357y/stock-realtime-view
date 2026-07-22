"""OS별 분기 로직 모음 — 폰트, 자동 시작, 설정 디렉터리."""
import os
import sys
from pathlib import Path
from typing import Optional

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS   = sys.platform == "darwin"
IS_LINUX   = sys.platform.startswith("linux")

APP_NAME  = "StockViewer"
BUNDLE_ID = "com.stockviewer.app"

_mono_family: Optional[str] = None


def monospace_font_family() -> str:
    """OS에 맞는 고정폭 폰트 패밀리. 첫 호출 시 계산 후 캐시.

    QApplication 생성 이후(위젯 빌드 시점)에만 호출할 것.
    """
    global _mono_family
    if _mono_family is not None:
        return _mono_family

    if IS_WINDOWS:
        _mono_family = "Consolas"
    elif IS_MACOS:
        _mono_family = "Menlo"
    else:
        try:
            from PyQt5.QtGui import QFontDatabase
            _mono_family = QFontDatabase.systemFont(QFontDatabase.FixedFont).family()
        except Exception:
            _mono_family = "Monospace"
    return _mono_family


# ── 자동 시작 ────────────────────────────────────────────────────

def set_auto_start(enable: bool) -> None:
    """OS 로그인 시 자동 실행 등록/해제. frozen 빌드에서만 동작."""
    if not getattr(sys, "frozen", False):
        return
    try:
        if IS_WINDOWS:
            _auto_start_windows(enable)
        elif IS_MACOS:
            _auto_start_macos(enable)
        elif IS_LINUX:
            _auto_start_linux(enable)
    except Exception as e:
        print(f"[autostart] {e}")


def _auto_start_windows(enable: bool) -> None:
    import winreg
    key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                        winreg.KEY_SET_VALUE) as key:
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ,
                              f'"{sys.executable}"')
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass


def _macos_launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{BUNDLE_ID}.plist"


def _auto_start_macos(enable: bool) -> None:
    import plistlib
    plist = _macos_launch_agent_path()
    if not enable:
        plist.unlink(missing_ok=True)
        return
    plist.parent.mkdir(parents=True, exist_ok=True)
    with plist.open("wb") as f:
        plistlib.dump({
            "Label": BUNDLE_ID,
            "ProgramArguments": [sys.executable],
            "RunAtLoad": True,
        }, f)


def _auto_start_linux(enable: bool) -> None:
    desktop = Path(os.environ.get("XDG_CONFIG_HOME",
                                  Path.home() / ".config")) / "autostart" / "stockviewer.desktop"
    if not enable:
        desktop.unlink(missing_ok=True)
        return
    desktop.parent.mkdir(parents=True, exist_ok=True)
    # Desktop Entry Exec 규격: 공백 포함 경로는 따옴표로 감싸고 내부 특수문자는 escape
    exec_path = sys.executable.replace("\\", "\\\\").replace('"', '\\"')
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f'Exec="{exec_path}"\n'
        "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )


# ── 설정 디렉터리 ────────────────────────────────────────────────

def config_dir() -> Path:
    """settings.json이 위치할 디렉터리.

    - 비-frozen(소스 실행): 프로젝트 디렉터리 (현행 유지)
    - frozen Windows: 실행 파일 옆 (포터블 exe 관행)
    - frozen macOS: ~/Library/Application Support/StockViewer
    - frozen Linux: $XDG_CONFIG_HOME/StockViewer
    """
    if not getattr(sys, "frozen", False):
        return Path(__file__).parent
    if IS_MACOS:
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if IS_LINUX:
        return Path(os.environ.get("XDG_CONFIG_HOME",
                                   Path.home() / ".config")) / APP_NAME
    return Path(sys.executable).parent
