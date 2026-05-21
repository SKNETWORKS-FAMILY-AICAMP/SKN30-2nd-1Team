# 튜브어때 발표 슬라이드

SKN30 2차 단위 프로젝트 · 팀 너놀자

## 실행 방법

### 1) 슬라이드 보기
프로젝트 루트에서:

```bash
python -m http.server 8000 --directory reports/presentation
```

브라우저: <http://localhost:8000>

> `file://`로 직접 열면 `fetch()`가 차단되어 슬라이드가 로드되지 않습니다. 반드시 로컬 서버로 띄우세요.

### 2) Streamlit 앱 데모 (슬라이드 17번에서 사용)
별도 터미널에서:

```bash
uv run streamlit run app/main.py
```

iframe 임베드가 차단되면:

```bash
uv run streamlit run app/main.py \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false
```

## 조작

| 키 | 동작 |
|---|---|
| `←` / `→` / `PgUp` / `PgDn` / `Space` | 이전·다음 슬라이드 |
| `Home` / `End` | 첫·마지막 슬라이드 |
| `P` | 인쇄(PDF) 모드 토글 — 모든 슬라이드 세로로 펼침 |
| 좌상단 드롭다운 | 슬라이드 점프 |
| URL `#3` | 3번 슬라이드로 직접 이동 |
| URL `?print=true` | 인쇄 모드로 시작 |

## 파일 구조

```
reports/presentation/
├── index.html           # 메인 컨테이너
├── README.md
├── assets/
│   ├── styles.css       # 디자인 토큰
│   ├── slides.js        # 슬라이드 로더 + 네비
│   ├── eda/             # 📌 EDA 차트 이미지 자리 (발표자가 노트북에서 캡처해 넣기)
│   └── screenshots/     # 📌 데모 fallback 스크린샷 자리
└── slides/
    ├── 01-title.html
    ├── 02-team.html
    ├── ...
    └── 20-references.html
```

## 슬라이드 수정 방법

- 한 슬라이드만 수정하려면 `slides/NN-name.html`만 열어서 편집 → 저장 → 새로고침
- 슬라이드 추가/순서 변경: `assets/slides.js` 상단의 `SLIDES` 배열 수정
- 스타일 전역 변경: `assets/styles.css`의 `:root` CSS 변수
- 같은 컴포넌트 패턴(card, kpi, flow-node 등) 재사용 권장 — `styles.css` 참고

## 채워야 할 placeholder

| 슬라이드 | 항목 | 위치 |
|---|---|---|
| 02 팀 소개 | 한 줄 소개 5명 | `slides/02-team.html` 의 `<div class="intro">` |
| 10 EDA | 차트 이미지 3개 | `assets/eda/category_dist.png`, `churn_label.png`, `corr_heatmap.png` |
| 17 화면 시연 | fallback 스크린샷 | `assets/screenshots/demo.png` |
| 19 회고 | 한 줄 회고 5명 | `slides/19-results-retrospective.html` 의 `<!-- 한 줄 회고 입력 -->` |

## PDF로 내보내기

브라우저에서 `?print=true`를 붙여 열거나 `P`를 눌러 인쇄 모드 → `Ctrl/Cmd + P` → PDF 저장.

```
http://localhost:8000/?print=true
```
