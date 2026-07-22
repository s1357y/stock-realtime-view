# StockViewer

화면 위에 항상 떠있는 반투명 한국 주식 실시간 모니터링 위젯 (Windows / macOS 지원, Linux 기본 호환)

## 특징

- 항상 최상위 표시 — 다른 창 위에 떠있음
- 반투명 배경 — 투명도 10~95% 자유 조절
- 테두리 없는 플로팅 창 — 화면 어디든 드래그하여 배치
- 네이버 금융 실시간 데이터 — 로그인 없이 조회
- 시간외 단일가 감지 — 장 마감 후 시간외 거래 가격 표시
- 시스템 트레이 상주 — 닫아도 백그라운드에서 계속 실행

## 화면 구성

```
┌─────────────────────────────┐
│          ▣ STOCK            │
│         15:23:41 장중       │
│ 삼성전자   ₩75,400  ▲1.23% │
│ SK하이닉스 ₩182,500 ▼0.55% │
│ NAVER     ₩195,000 ━0.00%  │
└─────────────────────────────┘
```

- **상승** — 빨간색 ▲
- **하락** — 파란색 ▼
- **보합** — 회색 ━
- **시간외** — 등락률 뒤에 `외` 표시

## 설치 및 실행

### 실행 파일 사용 (권장)

- **Windows**: `dist\StockViewer.exe`
- **macOS**: `dist/StockViewer.app`

별도 설치 없이 바로 실행됩니다.

### 소스에서 실행

**요구사항:** Python 3.9+

```bash
pip install -r requirements.txt
python main.py
```

터미널에서 실행하면 터미널 종료 시 앱도 함께 종료됩니다.
터미널 없이 상시 실행하려면 아래 빌드로 만든 실행 파일(`StockViewer.app` / `StockViewer.exe`)을 사용하세요.

### 빌드

```bash
python -m PyInstaller build.spec --clean
```

빌드 결과물 (빌드를 실행한 OS 기준):

- Windows: `dist\StockViewer.exe`
- macOS: `dist/StockViewer.app`

## 사용 방법

### 종목 관리

창에서 **우클릭** → 컨텍스트 메뉴

| 메뉴 항목 | 설명 |
|-----------|------|
| 종목 추가 | 6자리 종목 코드 입력 (예: `005930`) |
| 종목 제거 | 목록에서 선택하여 제거 |
| 투명도 | 슬라이더로 10~95% 조절 |
| 갱신 주기 | 5 / 10 / 30 / 60초 선택 |

### 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl` + `+` | 투명도 높이기 (+10%) |
| `Ctrl` + `-` | 투명도 낮추기 (-10%) |
| `Ctrl` + `H` | 창 보이기 / 숨기기 |
| `Ctrl` + `R` | 즉시 새로고침 |
| `Ctrl` + `Q` | 완전 종료 |

macOS에서는 `Ctrl` 대신 `Cmd`를 사용합니다.

### 트레이 아이콘

- **더블클릭** — 창 보이기 / 숨기기
- **우클릭** → 보이기/숨기기, 완전 종료

## 설정 파일

`settings.json` 저장 위치:

- 소스 실행: 프로젝트 폴더
- Windows 빌드: 실행 파일과 같은 폴더
- macOS 빌드: `~/Library/Application Support/StockViewer/`
- Linux 빌드: `~/.config/StockViewer/`

```json
{
  "stocks": ["005930", "000660", "035420"],
  "opacity": 0.75,
  "update_interval": 10,
  "window_x": 100,
  "window_y": 100
}
```

| 키 | 설명 | 기본값 |
|----|------|--------|
| `stocks` | 종목 코드 목록 (KOSPI/KOSDAQ 6자리) | `[]` |
| `opacity` | 창 투명도 (0.10 ~ 0.95) | `0.75` |
| `update_interval` | 데이터 갱신 주기 (초) | `10` |
| `window_x` / `window_y` | 창 위치 (픽셀) | `100` |

## 프로젝트 구조

```
stock-realtime-view/
├── main.py           # 진입점
├── window.py         # MainWindow — 반투명·항상위·드래그
├── ticker_widget.py  # 종목 1행 위젯
├── data_worker.py    # QThread 기반 네이버 API 폴링
├── config.py         # settings.json 로드/저장
├── platform_utils.py # OS별 분기 (폰트·자동시작·설정 경로)
├── build.spec        # PyInstaller 빌드 명세 (Windows exe / macOS app)
├── requirements.txt
├── settings.json     # 사용자 설정 (자동 저장)
└── dist/
    ├── StockViewer.exe   # Windows 빌드 시
    └── StockViewer.app   # macOS 빌드 시
```

## 데이터 출처

네이버 금융 비공개 API (`m.stock.naver.com`) 사용 — 계정 불필요.
API 구조 변경 시 `data_worker.py`의 `fetch_stock()` 함수를 수정해야 합니다.

## 주의사항

- Windows / macOS에서 동작 확인. Linux는 기본 호환 처리만 되어 있으며 별도 테스트되지 않음
- macOS 빌드는 코드 서명/공증이 없어 첫 실행 시 Gatekeeper 경고가 나올 수 있음 (우클릭 → 열기)
- 비공식 API 사용이므로 서비스 정책에 따라 동작이 변경될 수 있음
- 투자 판단의 근거로 사용하지 말 것
