# app/

튜브어때 (TubeEottae) — Streamlit 대시보드.

광고주가 5초 이내에 YouTube 채널의 이탈 위험도와 추천 결과를 직관적으로 이해할 수 있도록 설계된 SaaS 스타일 대시보드입니다.

## 디자인 시안 안내

현재 코드는 **디자인 시안(visual mockup)** 단계입니다.

- 모든 수치는 `app/dummy_data.py`에 하드코딩되어 있습니다.
- 모델 호출/CSV 로딩/YouTube API 호출은 **하지 않습니다** (`designer SKILL.md` §Boundary Rules 준수).
- 실제 데이터 연결은 Business Logic / DBA 계층이 산출한 결과(`data/predictions/predictions_YYYYMMDD.csv` 등)를 import해 dummy_data를 대체하면 됩니다.

## 페이지 구성

| # | 파일 | 설명 |
|---|---|---|
| 1 | `main.py` | 대시보드(메인) — KPI · 이탈 위험도 분포 · 추이 · TOP 5 · 주요 위험 신호 |
| 2 | `pages/1_채널_조회.py` | 채널 조회 + 이탈 예측 (핵심 페이지) |
| 3 | `pages/2_위험_분석_상세.py` | 위험 분석 상세 (업로드 / 조회수 / 감성 / 참여율 / SHAP) |
| 4 | `pages/3_광고주_추천.py` | 광고주 추천 (장기 / 단기 / 카테고리) |

> 이미지의 ④ "위험 채널 랭킹" 페이지는 시안에서는 제외했습니다 (추후 추가 예정).

## 디자인 토큰

- 배경: `#F7F8FA` (soft white) · 사이드바: `#0F172A` (다크)
- 메인 액센트: `#6366F1` (인디고)
- 등급 색상: A `#10B981` · B `#F59E0B` · C `#EF4444`
- 폰트: Pretendard (웹 CDN)

## 실행 방법

```bash
# 1. 의존성 설치 (uv 권장)
uv sync

# 2. Streamlit 실행 (반드시 프로젝트 루트에서 실행)
uv run streamlit run app/main.py

# 또는 pip 환경에서:
pip install -e .
streamlit run app/main.py
```

브라우저에서 `http://localhost:8501` 접속 후 좌측 사이드바로 페이지를 전환합니다.

## 파일 구조

```
app/
├── main.py                  # 엔트리 + 대시보드(메인)
├── pages/
│   ├── 1_채널_조회.py
│   ├── 2_위험_분석_상세.py
│   └── 3_광고주_추천.py
├── styles.py                # 전역 CSS (st.markdown 주입)
├── components.py            # 사이드바, 카드, 배지, 푸터 등 공용 컴포넌트
└── dummy_data.py            # 디자인 시안용 하드코딩 데이터
```

## 주의 사항 (designer SKILL.md)

- 본 계층(UI)에서는 모델 학습/추론, SHAP 계산, CSV 가공을 **수행하지 않습니다**.
- 모든 분석 화면에는 **데이터 기준일(2026-05-17)** 과 **윤리/면책 문구**가 노출됩니다 (PRD §20).
- 등급 색상·라벨은 전 페이지에서 동일하게 유지됩니다.
