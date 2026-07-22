# 멀티 OS (macOS/Windows/Linux) 지원 계획

## 요청

현재 Windows 환경 전용으로 구성된 StockViewer(PyQt5 위젯)를
macOS에서도 동작하도록, 멀티 OS 적용 가능한 형태로 수정한다.

## 현재 Windows 종속 지점

| # | 위치 | 내용 |
|---|------|------|
| 1 | window.py `_apply_auto_start` | `winreg` HKCU Run 키 등록. macOS/Linux에서 동작 불가 |
| 2 | window.py / ticker_widget.py / settings_dialog.py | `QFont("Consolas", ...)` 하드코딩. macOS에 Consolas 없음 -> 폰트 대체로 레이아웃 깨짐 |
| 3 | config.py `get_config_path` | frozen 시 실행 파일 옆에 settings.json 저장. macOS .app 번들 내부는 쓰기 부적합 |
| 4 | build.spec | Windows exe 전용. macOS .app 번들(BUNDLE) 없음 |
| 5 | settings_dialog.py 문구 | "Windows 시작 시 자동 실행", "Windows 트레이 알림", ".exe 빌드" 안내 |
| 6 | README.md | "Windows 전용" 표기, `dist\StockViewer.exe` 경로 안내 |

## 수정 계획

### 1. platform_utils.py 신규 생성

OS 분기 로직을 한 파일로 모은다.

- `IS_WINDOWS / IS_MACOS / IS_LINUX` 상수 (sys.platform 기반)
- `monospace_font_family() -> str`
  - Windows: "Consolas"
  - macOS: "Menlo"
  - Linux/기타: QFontDatabase.systemFont(FixedFont) 계열 폴백
  - 모듈 레벨 계산 금지. 첫 호출 시 lazy 계산 + 캐시
    (QApplication 생성 이후인 위젯 빌드 시점에만 호출되도록)
- `set_auto_start(enable: bool, app_name: str) -> None`
  - frozen 빌드에서만 동작 (현행 제한 유지, 비-frozen은 no-op)
  - Windows: 기존 winreg 로직 이동 (함수 내부 import winreg)
  - macOS: `~/Library/LaunchAgents/com.stockviewer.plist` 생성/삭제 (RunAtLoad)
  - Linux: `~/.config/autostart/stockviewer.desktop` 생성/삭제 (기본 호환 처리)
- `config_dir() -> Path`
  - 비-frozen: 프로젝트 디렉터리 (현행 유지)
  - frozen Windows: 실행 파일 옆 (현행 유지, 포터블 exe 관행)
  - frozen macOS: `~/Library/Application Support/StockViewer`
  - frozen Linux: `~/.config/StockViewer` (XDG_CONFIG_HOME 우선)

### 2. config.py

- `get_config_path`가 `platform_utils.config_dir()`를 사용하도록 변경
- 디렉터리가 없으면 생성 (mkdir parents/exist_ok)

### 3. window.py

- `QFont("Consolas", ...)` -> `QFont(monospace_font_family(), ...)`
- `_apply_auto_start` -> `platform_utils.set_auto_start` 위임으로 축소
- 창 플래그(Frameless + StaysOnTop + Tool), WA_TranslucentBackground,
  QSystemTrayIcon은 macOS에서 실제 실행으로 동작 검증하고,
  문제 발견 시 OS별 조건부 플래그로 대응 (검증 섹션 참고)
- QKeySequence "Ctrl+..."는 macOS에서 Cmd로 자동 매핑되므로 유지

### 4. ticker_widget.py / settings_dialog.py

- Consolas -> monospace_font_family() 치환
- settings_dialog 문구 OS 중립화:
  - "Windows 시작 시 자동 실행" -> "OS 로그인 시 자동 실행"
  - "알림 기능 활성화 (Windows 트레이 알림)" -> "알림 기능 활성화 (시스템 트레이 알림)"
  - ".exe 빌드 실행 시에만 적용" -> "패키징 빌드 실행 시에만 적용" (frozen 제한 유지)

### 5. build.spec

- deprecated Windows 전용 인자(win_no_prefer_redirects, win_private_assemblies) 제거
- `sys.platform == 'darwin'`일 때 `BUNDLE(...)` 추가 -> `dist/StockViewer.app` 생성
  (bundle_identifier: com.stockviewer.app, LSUIElement=True로 Dock 아이콘 숨김 --
  트레이 상주형 앱이므로)
- Windows에서는 기존과 동일하게 exe만 생성

### 6. README.md

- "Windows 전용" -> 멀티 OS 표기
- 빌드/실행 안내를 OS별로 분리 (Windows: StockViewer.exe, macOS: StockViewer.app)
- 제약 사항 섹션 갱신

## 하지 않는 것 (스코프 제외)

- 데이터 소스(네이버 API), 갱신 로직, UI 레이아웃 변경 없음
- data_worker.py의 User-Agent 문자열 변경 없음
  (API 호출용 브라우저 위장 문자열로 실행 OS와 무관)
- 코드 서명 / 공증(notarization) 등 macOS 배포 자동화는 다루지 않음
- Linux는 기본 호환 처리 (font 폴백 + autostart .desktop)이며 별도 테스트 안 함
- 비-frozen(개발 실행) 상태의 자동 시작 지원 안 함 (현행 제한 유지)

## 검증

- macOS(현재 환경)에서 `python main.py` 실제 실행:
  - 프레임리스 + 반투명 + 항상 위 창이 정상 표시되는지
  - 메뉴바(트레이) 아이콘 표시 및 메뉴 동작
  - monospace 폰트(Menlo) 적용으로 레이아웃 정렬 유지
  - 설정 저장/로드 경로 동작
- `python -m py_compile` 전체 파일 통과
- Windows 동작은 코드 경로 보존으로 확인 (winreg 로직 동일 유지, frozen 제한 동일)

## 작업 흐름

```
[plan] -> [codex review #1] -> [implement] -> [verify on macOS]
      -> [codex review #2] -> [final review]
```
