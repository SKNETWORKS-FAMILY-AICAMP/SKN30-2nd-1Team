# app/

튜브어때 (TubeEottae) — Streamlit 대시보드.

광고주가 5초 이내에 YouTube 채널의 이탈 위험도와 추천 결과를 직관적으로 이해할 수 있도록 설계된 SaaS 스타일 대시보드입니다.

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
