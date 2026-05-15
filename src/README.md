# src/

프로덕션 소스코드. `notebooks/` 에서 검증된 코드를 정제해서 이곳에 모듈로 작성합니다.

## 서브패키지 구조

### data/
데이터 수집 모듈

| 파일 | 역할 |
|---|---|
| `scraper.py` | youtube-rank.com 채널 목록 크롤러 |
| `youtube_api.py` | YouTube Data API v3 클라이언트 (Round-Robin 키 교체 포함) |
| `loader.py` | CSV/JSON 로드·저장 공통 유틸리티 |

### preprocessing/
전처리 모듈

| 파일 | 역할 |
|---|---|
| `cleaner.py` | 결측치·이상치 처리 |
| `encoder.py` | 범주형 인코딩, 수치형 스케일링 |
| `splitter.py` | stratified train/val/test 분리 |

### features/
피처 엔지니어링 모듈 (pdf 피처 목록 카테고리별)

| 파일 | 카테고리 | 주요 피처 |
|---|---|---|
| `activity.py` | A — 업로드 활동성 | 평균 업로드 간격, 주기 표준편차, 빈도 변화율, 영상 길이, Shorts 비율 |
| `performance.py` | B — 성과 지표 | 평균 조회수, 조회수 추세, 참여율(좋아요+댓글/조회수) |
| `engagement.py` | C — 구독자 반응 | 평균 댓글 수, 반응 안정성, KoBERT 감성 점수 연계 |
| `monetization.py` | D — 광고·수익 | 광고 영상 비율, 협찬 태그 여부, 광고 조회수 성과 |
| `stability.py` | E — 성장·안정성 | 최대 공백 기간, 휴지기 횟수, 최근 3개월 업로드 증가율 |
| `pipeline.py` | 통합 | 전체 피처 빌드 파이프라인 |

### models/
모델 모듈

- `base.py` — 공통 인터페이스 (fit, predict, predict_proba, save, load)
- `ml/` — Logistic Regression, Random Forest, XGBoost, LightGBM
- `dl/` — KoBERT 감성 분석(`sentiment.py`), 독립 이탈 분류 모델(`classifier.py`), 학습 루프(`trainer.py`)

### evaluation/
평가·해석 모듈

| 파일 | 역할 |
|---|---|
| `metrics.py` | ROC-AUC, F1, Precision, Recall, Confusion Matrix, 모델 비교 테이블 |
| `visualizer.py` | ROC Curve, 피처 중요도, 신용등급 분포 시각화 |
| `shap_analysis.py` | SHAP Summary/Beeswarm/Waterfall plot |

### utils/
공통 유틸리티

| 파일 | 역할 |
|---|---|
| `config.py` | configs/config.yaml 로드 |
| `logger.py` | 프로젝트 공통 로거 |
