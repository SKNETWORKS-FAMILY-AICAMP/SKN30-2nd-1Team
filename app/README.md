# app/

Streamlit 기반 크리에이터 이탈 위험도 데모 앱.

## 실행 방법

```bash
uv run streamlit run app/main.py
```

## 주요 파일

| 파일 | 역할 |
|---|---|
| `main.py` | 앱 진입점, 페이지 라우팅 |
| `pages/01_overview.py` | 데이터 현황 및 이탈률 분포 요약 |
| `pages/02_predict.py` | channel_id 입력 → 이탈 위험도 예측 결과 출력 |
| `pages/03_analysis.py` | SHAP 피처 중요도, 신용등급(A/B/C) 분포 |
| `components/` | 재사용 UI 컴포넌트 |

## 신용등급 시스템

| 등급 | 이탈 위험도 | 광고주 액션 |
|---|---|---|
| A | 낮음 (0~20%) | 장기 계약 적합 |
| B | 중간 (20~50%) | 단기 계약 권장 |
| C | 높음 (50%~) | 계약 재고 권장 |
