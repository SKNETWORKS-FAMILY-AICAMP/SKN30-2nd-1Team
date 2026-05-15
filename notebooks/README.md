# notebooks/

탐색·실험용 Jupyter 노트북. 아이디어를 빠르게 검증하고, 완성된 코드는 `src/` 로 이동합니다.

## 번호 규칙

파일명 앞에 번호를 붙여 작업 순서대로 정렬합니다.

| 번호 | 단계 | 예시 파일명 |
|---|---|---|
| 01 | 데이터 수집 탐색 | `01_data_collection/01a_channel_info.ipynb` |
| | | `01_data_collection/01b_video_info.ipynb` |
| | | `01_data_collection/01c_comments.ipynb` (DL팀 선택) |
| 02 | EDA | `02_eda_churn_distribution.ipynb` |
| 03 | 전처리 | `03_preprocessing_missing_values.ipynb` |
| 04 | 피처 엔지니어링 | `04_feature_upload_interval.ipynb` |
| 05 | ML 모델링 | `05_ml_xgboost_baseline.ipynb` |
| 06 | DL 모델링 | `06_dl_kobert_sentiment.ipynb` |
| 07 | 평가·해석 | `07_evaluation_shap.ipynb` |

## 담당자 표

| 단계 | 담당 | 비고 |
|---|---|---|
| 01~04 | 전원 | 함께 진행 |
| 05 | ML팀 (3명) | LR, RF, XGBoost, LightGBM |
| 06 | DL팀 (2명) | KoBERT 감성 분석, 독립 분류 모델 |
| 07 | 전원 | SHAP, 신용등급, 발표 자료 |

## 주의사항

- 노트북은 실험용. 재현 가능하도록 셀을 위에서 아래로 순서대로 실행 가능하게 유지
- 완성된 함수/클래스는 반드시 `src/` 로 옮겨서 재사용
