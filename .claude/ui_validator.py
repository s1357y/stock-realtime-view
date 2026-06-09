#!/usr/bin/env python3
"""
PyQt5 UI layout validator. Called as a Claude Code Stop hook.
Exits 1 (re-invokes Claude) if antipatterns found, exits 0 if clean.
"""
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Per-file antipatterns: list of (regex, description)
# Only literal-integer violations are flagged — variable arguments are fine.
CHECKS = {
    "ticker_widget.py": [
        (
            r'\bsetFixedWidth\(\s*\d+\s*\)',
            "setFixedWidth()에 리터럴 정수 사용됨.\n"
            "    → 폰트 크기 변경 시 텍스트 잘림 발생. "
            "QFontMetrics.horizontalAdvance() 기반 계산값을 변수로 전달하세요."
        ),
    ],
    "window.py": [
        (
            r'\bsetFixedSize\(\s*\d+\s*,\s*\d+\s*\)',
            "setFixedSize()에 리터럴 정수 사용됨.\n"
            "    → 창 크기가 폰트/콘텐츠와 무관하게 고정됨. "
            "QFontMetrics 기반으로 min_w를 계산하고 max(user_pref, min_w) 패턴을 사용하세요."
        ),
    ],
}


def main():
    issues = []

    for fname, patterns in CHECKS.items():
        fpath = ROOT / fname
        if not fpath.exists():
            continue
        lines = fpath.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, msg in patterns:
                if re.search(pattern, line):
                    issues.append(f"[{fname}:{lineno}] {msg}\n    코드: {stripped}")

    if issues:
        print("=" * 64)
        print("[UI 레이아웃 검증 실패] 다음 안티패턴이 감지되었습니다:\n")
        for issue in issues:
            print(f"  {issue}\n")
        print("=" * 64)
        print("위 문제를 수정한 뒤 응답을 완료하세요.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[UI 검증 오류] {e}", file=sys.stderr)
        sys.exit(0)
