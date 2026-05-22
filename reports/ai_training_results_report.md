# 유튜버 이탈 예측 앙상블 모델 학습 결과 보고서

기준 노트북: `notebooks/02_modeling/best_ensemble_tuning_pipeline.ipynb`

본 보고서는 전처리 완료 데이터와 DB 채널 정보를 병합한 뒤, 여러 분류 모델을 `RandomizedSearchCV`로 튜닝하고 ROC-AUC 기준 상위 3개 모델을 Soft Voting 방식으로 앙상블한 결과를 정리한다.

---

## 1. 데이터 및 학습 설정

### 데이터 구성

- 입력 데이터: `../../notebooks/01_data_collection/EDA/preprocessed_data/preprocessed.csv`
- DB 병합 후 데이터 형태: `(3331, 47)`
- 타깃 컬럼: `is_churned`
- 클래스 분포:
  - 정상/활성 채널 `0`: 2,637개
  - 이탈 채널 `1`: 694개
  - 이탈 비율: 20.83%

### 학습/평가 분할

- 분할 방식: `train_test_split(..., test_size=0.2, random_state=42, stratify=y)`
- Train: `(2664, 41)`
- Test: `(667, 41)`
- 별도 Validation set은 사용하지 않고, 학습 데이터 내부에서 `cv=3` 교차검증으로 튜닝했다.

### 주요 피처

총 41개 피처를 사용했다.

- 채널 규모: `subscriber_count`, `total_views`, `video_count`, `channel_age_days`
- 업로드 패턴: `collected_video_count`, `avg_upload_interval_days`, `std_upload_interval_days`, `max_gap_days`, `hiatus_count_30d`
- 조회/반응 지표: `avg_view_count`, `std_view_count`, `avg_like_count`, `avg_comment_count`, `avg_normal_view`
- 업로드 규칙성: `regularity_score`, `cv`, `outlier_ratio`, `gap_ratio`
- 민감 콘텐츠 지표: `sensitive_score`, `n_sensitive_videos`, `sensitive_video_ratio`, `cat_politics`, `cat_hate`, `cat_aggro`, `cat_adult_illegal`
- 장르 원핫 피처: `genre_*`

---

## 2. 후보 모델 및 튜닝 방식

후보 모델 5개를 정의하고, 각 모델별 하이퍼파라미터 공간에서 `RandomizedSearchCV`를 수행했다.

- 탐색 방식: `RandomizedSearchCV`
- 평가 기준: `scoring="roc_auc"`
- 교차검증: `cv=3`
- 반복 수: `n_iter=10`
- 병렬 처리: `n_jobs=-1`

후보 모델:

- `XGBClassifier`
- `LGBMClassifier`
- `RandomForestClassifier`
- `GradientBoostingClassifier`
- `LogisticRegression`

---

## 3. 개별 모델 튜닝 결과

| 모델 | 최적 파라미터 | Test Accuracy | Test ROC-AUC |
|---|---|---:|---:|
| XGBoost | `n_estimators=300`, `max_depth=3`, `learning_rate=0.05` | 0.8036 | 0.7789 |
| LightGBM | `n_estimators=200`, `max_depth=5`, `learning_rate=0.05` | 0.8036 | 0.7837 |
| RandomForest | `n_estimators=300`, `max_depth=10`, `min_samples_split=2` | 0.8096 | 0.7996 |
| GradientBoosting | `n_estimators=100`, `max_depth=3`, `learning_rate=0.1` | 0.8066 | 0.7856 |
| LogisticRegression | `C=0.1` | 0.7946 | 0.6740 |

`LogisticRegression`은 학습 중 `lbfgs failed to converge` 경고가 발생했으며, ROC-AUC도 다른 후보 모델보다 낮았다.

---

## 4. 최종 앙상블 구성

ROC-AUC 기준 상위 3개 모델을 선정했다.

| 순위 | 모델 | ROC-AUC |
|---:|---|---:|
| 1 | RandomForest | 0.7996 |
| 2 | GradientBoosting | 0.7856 |
| 3 | LightGBM | 0.7837 |

최종 앙상블은 위 3개 모델을 `VotingClassifier(voting="soft")`로 결합했다.

```python
VotingClassifier(
    estimators=[
        ("RandomForest", RandomForestClassifier(max_depth=10, n_estimators=300, random_state=42)),
        ("GradientBoosting", GradientBoostingClassifier(random_state=42)),
        ("LightGBM", LGBMClassifier(learning_rate=0.05, max_depth=5, n_estimators=200, random_state=42, verbose=-1)),
    ],
    voting="soft",
)
```

Soft Voting이므로 각 모델의 클래스 확률(`predict_proba`)을 평균해 최종 예측을 산출한다.

---

## 5. 최종 앙상블 성능

### 요약 지표

| 지표 | 값 |
|---|---:|
| Accuracy | 0.8096 |
| ROC-AUC | 0.7962 |

### Classification Report

```text
              precision    recall  f1-score   support

           0       0.84      0.94      0.89       528
           1       0.58      0.32      0.41       139

    accuracy                           0.81       667
   macro avg       0.71      0.63      0.65       667
weighted avg       0.79      0.81      0.79       667
```

### 혼동행렬

| 실제 \ 예측 | 0 | 1 |
|---|---:|---:|
| 0 | 496 | 32 |
| 1 | 95 | 44 |

이탈 채널(`1`) 기준으로 Precision은 0.58이지만 Recall은 0.32로 낮다. 즉, 이탈로 예측한 채널의 정밀도는 어느 정도 확보됐지만 실제 이탈 채널을 많이 놓치는 경향이 있다.

---

## 6. 해석 및 산출물

### SHAP 해석

앙상블 모델 전체를 직접 SHAP으로 해석하지 않고, ROC-AUC 1위 모델인 `RandomForest`를 기준으로 SHAP 분석을 수행했다.

```python
top1_model_name = top_models[0][0]  # RandomForest
top1_model = best_estimators[top1_model_name]
```

따라서 보고서의 설명 가능한 피처 중요도는 최종 Soft Voting 앙상블 전체가 아니라, Top 1 단일 모델인 RandomForest 기준 해석이다.

### 모델 저장

최종 앙상블 모델은 다음 파일명으로 저장했다.

```python
joblib.dump(ensemble_model, "best_ensemble_model.pkl")
```

---

## 7. 결론 및 주의사항

최종 선택 모델은 **RandomForest + GradientBoosting + LightGBM Soft Voting 앙상블**이다. 후보 모델 중 가장 높은 단일 ROC-AUC는 RandomForest의 0.7996이었고, 최종 앙상블은 Accuracy 0.8096, ROC-AUC 0.7962를 기록했다.

다만 이탈 채널 기준 Recall이 0.32로 낮아, PRD의 이탈 탐지 KPI인 Recall 80% 및 ROC-AUC 0.85 기준에는 도달하지 못했다. 운영 모델로 채택하려면 클래스 불균형 처리, threshold tuning, 피처 보강, 비용 민감 학습 등을 추가로 검토해야 한다.
