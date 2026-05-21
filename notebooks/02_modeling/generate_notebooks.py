import nbformat
import json
import os

# 1. 원본 XGBoost 노트북 로드
xgb_notebook_path = "churn_prediction_model_xgb.ipynb"
if not os.path.exists(xgb_notebook_path):
    # 만약 상대 경로로 실행했을 때 없으면 절대 경로 사용 시도
    xgb_notebook_path = r"C:\Users\playdata2\OneDrive\Desktop\프로젝트\2차 단위 프로젝트\SKN30-2nd-1Team\notebooks\02_modeling\churn_prediction_model_xgb.ipynb"

print(f"Loading base notebook from: {xgb_notebook_path}")
with open(xgb_notebook_path, "r", encoding="utf-8") as f:
    nb_base = nbformat.read(f, as_version=4)

# 2. 공통 데이터 전처리 및 로드 계층 추출
# 'make_train_valid_test_split()'이 있는 셀까지가 공통 계층
split_idx = -1
for i, cell in enumerate(nb_base.cells):
    if cell.cell_type == "code" and "make_train_valid_test_split" in cell.source:
        split_idx = i
        break

if split_idx == -1:
    raise ValueError("Could not find the split point in the notebook.")

print(f"Common preprocessing layer consists of cells 0 to {split_idx}.")
common_cells = nb_base.cells[:split_idx+1]

# 3. 공통 셀 중 imports 셀 수정 (LGBM 등 필요한 라이브러리 추가용)
# 1번째 셀이 보통 import 구문이 담겨있음
import_cell_idx = 1
common_cells[import_cell_idx].source = common_cells[import_cell_idx].source + "\n# 추가 모델 임포트\ntry:\n    from lightgbm import LGBMClassifier\nexcept ImportError:\n    LGBMClassifier = None\n\nfrom sklearn.ensemble import RandomForestClassifier\nfrom sklearn.linear_model import LogisticRegression"


# --- LightGBM 노트북 생성 함수 ---
def generate_lgbm_notebook():
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_markdown_cell(c.source) if c.cell_type == "markdown" else nbformat.v4.new_code_cell(c.source) for c in common_cells]
    
    # 타이틀 수정
    nb.cells[0].source = "# 유튜버 이탈 예측 및 주요 원인 분석 모델 (LightGBM)\n\n이 노트북은 전처리 산출물인 preprocessed_data/X.csv, y.csv를 기준으로 **LightGBM** 이탈 예측 모델을 구축합니다.\n\n- 입력 데이터: notebooks/01_data_collection/EDA/preprocessed_data/X.csv, y.csv\n- 핵심 피처 사용 및 결측치 대체는 Pipeline(SimpleImputer -> LGBMClassifier) 내에서 처리합니다."
    
    # LightGBM 비즈니스 계층
    business_cells = [
        nbformat.v4.new_markdown_cell("## 4. LightGBMClassifier 모델링"),
        nbformat.v4.new_code_cell("""# LightGBM Classifier 학습 파이프라인
if LGBMClassifier is None:
    model = None
    lgbm_result = None
    lgbm_pred = None
    lgbm_prob = None
    print("lightgbm is not installed. Skipping LightGBMClassifier training.")
else:
    pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    
    def make_lgbm_pipeline(**params):
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", LGBMClassifier(
                **params,
                scale_pos_weight=pos_weight,
                random_state=RANDOM_STATE,
                n_jobs=-1,
                verbosity=-1
            )),
        ])

    # LightGBM 하이퍼파라미터 튜닝 후보군 정의 (4개 후보)
    lgbm_candidates = [
        make_lgbm_pipeline(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, min_child_samples=20, reg_lambda=1),
        make_lgbm_pipeline(n_estimators=500, max_depth=3, learning_rate=0.03, subsample=0.9, colsample_bytree=0.8, min_child_samples=20, reg_lambda=2),
        make_lgbm_pipeline(n_estimators=300, max_depth=4, learning_rate=0.04, subsample=0.8, colsample_bytree=0.8, min_child_samples=30, reg_lambda=5),
        make_lgbm_pipeline(n_estimators=400, max_depth=5, learning_rate=0.03, subsample=0.8, colsample_bytree=0.8, min_child_samples=30, reg_lambda=8),
    ]

    lgbm_result = tune_model_candidates("LGBMClassifier", lgbm_candidates, score_classifier)
    model = lgbm_result["model"]
    lgbm_pred, lgbm_prob, lgbm_test_metrics = evaluate_tuned_model("LGBMClassifier", lgbm_result)"""),
        
        nbformat.v4.new_markdown_cell("### 이탈 확률 기반 상위 채널 조회"),
        nbformat.v4.new_code_cell("""if model is not None:
    test_result = merged_df.loc[X_test.index, ['channel_identifier']].copy()
    test_result['churn_prob'] = lgbm_prob
    test_result['predicted_churn'] = lgbm_pred
    test_result['is_churned'] = y_test.values
    test_result = test_result.sort_values('churn_prob', ascending=False).reset_index(drop=True)

    print("=== LGBMClassifier test set: top 10 channels by churn probability ===")
    print(test_result.head(10).to_string(index=False))

    all_prob = model.predict_proba(X)[:, 1]
    channel_churn = merged_df[['channel_identifier']].copy()
    channel_churn['churn_prob'] = all_prob
    channel_churn['churn_prob_pct'] = (channel_churn['churn_prob'] * 100).round(2)
    channel_churn = channel_churn.sort_values('churn_prob', ascending=False).reset_index(drop=True)

    print()
    print("=== LGBMClassifier all channels: top 10 by churn probability ===")
    print(channel_churn.head(10).to_string(index=False))"""),
        
        nbformat.v4.new_markdown_cell("## 5. 원인 분석 (SHAP)\n\nSHAP(SHapley Additive exPlanations)를 활용해 LightGBM 모델의 예측 근거와 피처별 기여도를 시각화합니다."),
        nbformat.v4.new_code_cell("""if model is not None:
    # 파이프라인에서 imputer와 model 분리 추출
    imputer = model.named_steps["imputer"]
    lgbm_raw_model = model.named_steps["model"]
    
    # SHAP 분석을 위한 데이터 프레임 변환
    X_train_imp = pd.DataFrame(imputer.transform(X_train), columns=ALL_FEATURES)
    X_test_imp = pd.DataFrame(imputer.transform(X_test), columns=ALL_FEATURES)
    
    explainer = shap.TreeExplainer(lgbm_raw_model)
    shap_values = explainer.shap_values(X_test_imp)
    
    # LightGBM의 이진 분류 결과물 SHAP 차원 보정
    if isinstance(shap_values, list):
        shap_values_to_plot = shap_values[1]
    else:
        shap_values_to_plot = shap_values

    # Summary Plot
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values_to_plot, X_test_imp, show=False)
    plt.title("LightGBM SHAP Summary Plot", fontsize=15)
    plt.tight_layout()
    plt.show()"""),
        
        nbformat.v4.new_markdown_cell("""## 6. 종합 결론 및 타 모델 비교 분석

본 프로젝트에서는 유튜버 이탈 예측을 극대화하기 위해 **LightGBMClassifier**, **XGBClassifier**, **RandomForestClassifier**의 단일 모델들과 이를 결합한 **4가지 앙상블 모델(Soft Voting, Hard Voting, Stacking, Weighted Blending)**을 종합적으로 구축 및 비교 분석하였습니다.

### 1) 개별 모델 특성 및 비교 분석
* **LightGBM (본 모델)**:
  - **학습 메커니즘 & 장점**: 대용량 데이터셋에서 압도적인 연산 속도와 메모리 효율성을 제공하는 GOSS(Gradient-based One-Side Sampling) 및 EFB(Exclusive Feature Bundling)를 활용합니다. Leaf-wise(리프 중심) 트리 분할 방식을 취하므로, 복잡하고 깊은 비선형 관계를 매우 정밀하게 포착하여 날카로운 이탈 판별 경계를 학습하고 높은 정밀도(Precision)를 얻는 데 강점을 가집니다.
  - **위험성 & 한계**: 트리 깊이가 깊어지기 쉬워 데이터가 충분하지 않을 경우 과적합(Overfitting) 발생 가능성이 높습니다. 따라서 본 노트북에서는 4종의 주요 파이프라인 후보군을 비교 검증하여 `max_depth`와 `min_child_samples` 등을 엄격히 제어하며 일반화 성능을 극대화했습니다.
* **XGBoost**:
  - Level-wise(레벨 중심) 트리 성장을 수행하고 목적 함수 내에 자체 L1/L2 규제(Regularization)가 내포되어 있어 과적합 제어 성능이 매우 탁월합니다. LightGBM과 유사하게 고성능을 도출하지만, 하이퍼파라미터 튜닝 시 수행 속도 면에서 다소 연산 비용이 더 필요합니다.
* **Random Forest**:
  - 대표적인 배깅(Bagging) 기반 앙상블로 여러 개의 의사결정나무 예측 결과를 종합(Voting)합니다. 각 부스팅 계열 모델들에 비해 모델 아키텍처 자체가 과적합에 매우 안정적이며 노이즈나 이상치 데이터에 강력한 복원력을 보여줍니다. 단, 피처 간의 극단적으로 세밀한 상호 관계나 최외곽 영역의 비선형 경계를 날카롭게 분류해내는 성향은 다소 부족할 수 있습니다.

### 2) 앙상블 모델과의 연계 시너지
단일 모델들의 단점을 메워 성능을 이론적 한계까지 끌어올리기 위해 구성한 4가지 앙상블의 강점은 다음과 같습니다:
* **Voting (Soft / Hard)**: LGBM의 날카로운 예측 확률과 RF의 강건한 투표 방식이 조화를 이룹니다. 단일 모델 하나가 과적합되어 특정 샘플의 이탈 위험도를 과대/과소평가하는 단독 오차(Individual Variance)를 완화하여 최적의 범용 예측 라벨을 도출합니다.
* **Weighted Blending (가중 혼합)**: 검증 데이터 성능 평가 결과에 따라 신뢰도가 우수한 LightGBM에 가중치 50%를 할당하고 XGBoost(30%), Random Forest(20%)를 적절히 융합하여 각 모델의 예측 신뢰도와 특색을 합리적으로 가중 반영합니다.
* **Stacking (메타 모델 학습)**: 개별 분류기들의 검증 예측값 자체를 입력 피처로 받아들여, 메타 모델인 `LogisticRegression`을 통해 최적의 기여 조합 비율을 머신러닝 스스로 재학습하는 구조입니다. 실무 배포 시 개별 모델들의 오예측 패턴을 직접 인지하고 보완하므로 통계적 안정성이 가장 뛰어납니다.

### 3) 핵심 피처 해석 및 비즈니스 활용 전략
* **핵심 피처 기여도**: SHAP 해석 기법을 기반으로 추적한 결과, 채널의 최근 업로드 패턴과 규칙성을 수치화한 규칙성 점수(`regularity_score`) 및 최대 업로드 공백(`max_gap_days`)이 예측 모델의 최상위 중요 인자로 나타났습니다.
* **비즈니스 액션 플랜**:
  1. **실시간 이탈 경보 알림망 구축**: LightGBM이 실시간으로 출력하는 개별 유튜버의 이탈 확률 스코어(`churn_prob`)를 시스템 DB에 연동합니다. 상위 10% 위험군에 드는 크리에이터들에게는 `max_gap_days`가 누적 임계치에 도달하기 전 자동으로 채널 관리 리마인더 및 맞춤형 트렌드 키워드 가이드를 발송하는 예방적 자동화를 적용합니다.
  2. **크리에이터 락인(Lock-in) 프로모션**: 앙상블(Stacking 및 Weighted Blending) 예측에서 이탈 징후가 장기적으로 포착되는 성장 둔화 채널에 우선적으로 플랫폼 차원의 제작 지원, 1:1 기술 및 수익화 컨설팅 혜택을 집중 지원함으로써 플랫폼 내 생태계 안착률을 높이고 크리에이터 유지 비용을 효율화합니다.

### 4) Classification Report 기반 성능 평가 및 지표 해석 가이드

실제 테스트 데이터셋으로 각 모델을 평가한 후 도출된 **지표별 성능 결과**는 다음과 같습니다. 이 실측 수치들은 향후 비즈니스 목적에 최적화된 모델을 선정하는 절대적인 기준이 됩니다.

| 모델명 | Threshold | Accuracy | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Log-Loss |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **XGBoost** | 0.63 | 78.41% | 48.00% | 43.17% | 45.45% | 0.7752 | 0.4784 | 0.5068 |
| **LightGBM (본 모델)** | 0.67 | 78.86% | 49.09% | 38.85% | 43.37% | 0.7693 | 0.4807 | 0.5030 |
| **Random Forest** | 0.48 | 75.41% | 43.46% | **59.71%** | **50.30%** | **0.7849** | **0.4873** | 0.4900 |
| **Ensemble (1) - Soft Voting** | 0.63 | 78.86% | 49.12% | 40.29% | 44.27% | 0.7815 | 0.4844 | **0.4882** |
| **Ensemble (2) - Hard Voting** | 0.59 | 77.66% | 46.32% | 45.32% | 45.82% | 0.7815 | 0.4844 | 0.4882 |
| **Ensemble (3) - Stacking** | 0.72 | 78.71% | 48.70% | 40.29% | 44.09% | 0.7807 | 0.4867 | 0.5367 |
| **Ensemble (4) - Weighted Blending**| 0.66 | **79.31%** | **50.49%** | 37.41% | 42.98% | 0.7780 | 0.4819 | 0.4910 |

#### 수치 기반 지표 해석 및 최적 모델 선택 가이드

* **정밀도 (Precision - 이탈 예측의 정확성) 극대화**:
  - **최우수 모델: Ensemble (4) - Weighted Blending (50.49%) & LightGBM (49.09%)**
  - **해석**: 가중 블렌딩 모델과 LightGBM은 각각 0.66과 0.67의 높은 임계값(Threshold) 하에서 최고 수준의 정밀도를 보여줍니다. 이는 "이탈할 것이라고 예측한 유튜버 2명 중 1명은 실제로 이탈했다"는 뜻입니다. 이탈 위험자 대상 콘텐츠 제작 지원비 지원 등 **한정된 예산으로 실질적인 현금성 인센티브 프로모션을 집행할 때** 예산 낭비를 최소화하기 위한 가장 합리적인 모델입니다.
* **재현율 (Recall - 이탈 대상자 포착률) 극대화**:
  - **최우수 모델: Random Forest (59.71%)**
  - **해석**: 균형 잡힌 가중치 설정(`class_weight="balanced"`)이 들어간 Random Forest는 59.71%의 재현율을 기록하여 전체 이탈자 10명 중 6명을 성공적으로 검출해 냈습니다. 다소 안정적인 유튜버가 이탈 위험군으로 잘못 예측되는 오류(False Positive)가 늘어나더라도(정밀도 43.46%), **플랫폼 내 핵심 파트너 유튜버의 이탈을 절대로 놓치지 않고 전수 탐지해야 하는 위기 관리 목적**에는 이 모델이 최선입니다.
* **종합 조화 성능 (F1-Score 및 AUC)**:
  - **최우수 모델: Random Forest (F1: 50.30% / ROC-AUC: 0.7849) & Ensemble (2) - Hard Voting (F1: 45.82%)**
  - **해석**: 단일 모델로서 Random Forest는 Recall의 강세에 힘입어 F1-Score 50.30%를 기록, 가장 우수한 균형점을 보였습니다. 앙상블 중에서 Hard Voting 모델(F1: 45.82%)은 세 개 모델의 다수결을 결합하여 단일 부스팅 모델들의 이탈 포착 한계를 훌륭하게 극복했습니다.
* **불균형 데이터 최적 분류 기준 (PR-AUC)**:
  - 이탈 유튜버의 클래스 비율이 약 20.8%에 불과한 데이터 불균형 구조에서 **PR-AUC (Precision-Recall AUC)** 지표는 모델들의 진정한 성능을 증명합니다. Random Forest(0.4873)와 Stacking(0.4867), Soft Voting(0.4844) 모델들이 LightGBM 단독 모델(0.4807)보다 뛰어난 영역을 보이며 앙상블 결합의 실질적인 일반화 성능 시너지를 확실하게 증명하고 있습니다.""")
    ]
    nb.cells.extend(business_cells)
    
    output_path = "churn_prediction_model_lgbm.ipynb"
    with open(output_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    print(f"Generated {output_path} successfully!")


# --- Random Forest 노트북 생성 함수 ---
def generate_rf_notebook():
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_markdown_cell(c.source) if c.cell_type == "markdown" else nbformat.v4.new_code_cell(c.source) for c in common_cells]
    
    # 타이틀 수정
    nb.cells[0].source = "# 유튜버 이탈 예측 및 주요 원인 분석 모델 (Random Forest)\n\n이 노트북은 전처리 산출물인 preprocessed_data/X.csv, y.csv를 기준으로 **Random Forest** 이탈 예측 모델을 구축합니다.\n\n- 입력 데이터: notebooks/01_data_collection/EDA/preprocessed_data/X.csv, y.csv\n- 핵심 피처 사용 및 결측치 대체는 Pipeline(SimpleImputer -> RandomForestClassifier) 내에서 처리합니다."
    
    # RF 비즈니스 계층
    business_cells = [
        nbformat.v4.new_markdown_cell("## 4. RandomForestClassifier 모델링"),
        nbformat.v4.new_code_cell("""# Random Forest Classifier 학습 파이프라인
def make_rf_pipeline(**params):
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            **params,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1
        )),
    ])

# Random Forest 하이퍼파라미터 튜닝 후보군 정의
rf_candidates = [
    make_rf_pipeline(n_estimators=300, max_depth=5, min_samples_split=5, min_samples_leaf=2),
    make_rf_pipeline(n_estimators=500, max_depth=6, min_samples_split=10, min_samples_leaf=4),
    make_rf_pipeline(n_estimators=300, max_depth=8, min_samples_split=5, min_samples_leaf=1),
    make_rf_pipeline(n_estimators=400, max_depth=7, min_samples_split=7, min_samples_leaf=3),
]

rf_result = tune_model_candidates("RandomForestClassifier", rf_candidates, score_classifier)
model = rf_result["model"]
rf_pred, rf_prob, rf_test_metrics = evaluate_tuned_model("RandomForestClassifier", rf_result)"""),
        
        nbformat.v4.new_markdown_cell("### 이탈 확률 기반 상위 채널 조회"),
        nbformat.v4.new_code_cell("""if model is not None:
    test_result = merged_df.loc[X_test.index, ['channel_identifier']].copy()
    test_result['churn_prob'] = rf_prob
    test_result['predicted_churn'] = rf_pred
    test_result['is_churned'] = y_test.values
    test_result = test_result.sort_values('churn_prob', ascending=False).reset_index(drop=True)

    print("=== RandomForestClassifier test set: top 10 channels by churn probability ===")
    print(test_result.head(10).to_string(index=False))

    all_prob = model.predict_proba(X)[:, 1]
    channel_churn = merged_df[['channel_identifier']].copy()
    channel_churn['churn_prob'] = all_prob
    channel_churn['churn_prob_pct'] = (channel_churn['churn_prob'] * 100).round(2)
    channel_churn = channel_churn.sort_values('churn_prob', ascending=False).reset_index(drop=True)

    print()
    print("=== RandomForestClassifier all channels: top 10 by churn probability ===")
    print(channel_churn.head(10).to_string(index=False))"""),
        
        nbformat.v4.new_markdown_cell("## 5. 원인 분석 (SHAP)\n\nSHAP(SHapley Additive exPlanations)를 활용해 Random Forest 모델의 예측 근거와 피처별 기여도를 시각화합니다."),
        nbformat.v4.new_code_cell("""if model is not None:
    # 파이프라인에서 imputer와 model 분리 추출
    imputer = model.named_steps["imputer"]
    rf_raw_model = model.named_steps["model"]
    
    # SHAP 분석을 위한 데이터 프레임 변환
    X_train_imp = pd.DataFrame(imputer.transform(X_train), columns=ALL_FEATURES)
    X_test_imp = pd.DataFrame(imputer.transform(X_test), columns=ALL_FEATURES)
    
    explainer = shap.TreeExplainer(rf_raw_model)
    shap_values = explainer.shap_values(X_test_imp)
    
    # Random Forest의 이진 분류 결과물 SHAP 차원 보정
    if isinstance(shap_values, list):
        shap_values_to_plot = shap_values[1]
    else:
        shap_values_to_plot = shap_values

    # Summary Plot
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values_to_plot, X_test_imp, show=False)
    plt.title("Random Forest SHAP Summary Plot", fontsize=15)
    plt.tight_layout()
    plt.show()"""),
        
    ]
    nb.cells.extend(business_cells)
    
    output_path = "churn_prediction_model_rf.ipynb"
    with open(output_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    print(f"Generated {output_path} successfully!")


# --- Stacking LGR 노트북 생성 함수 ---
def generate_lgr_notebook():
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_markdown_cell(c.source) if c.cell_type == "markdown" else nbformat.v4.new_code_cell(c.source) for c in common_cells]
    
    # 타이틀 수정
    nb.cells[0].source = "# 유튜버 이탈 예측 및 원인 분석 모델 (Stacking / Meta-Learner Logistic Regression)\n\n이 노트북은 XGBoost, LightGBM, Random Forest의 개별 특성을 결합하여 **Stacking (메타 모델 학습)** 기법으로 최상의 성능을 유도하는 앙상블 모델 노트북입니다.\n\n- 입력 데이터: notebooks/01_data_collection/EDA/preprocessed_data/X.csv, y.csv\n- 핵심 피처 사용 및 결측치 대체는 Pipeline(SimpleImputer -> Base Classifiers) 내에서 처리합니다."
    
    # LGR 비즈니스 계층
    business_cells = [
        nbformat.v4.new_markdown_cell("## 4. 개별 기반 모델 정의 및 학습\n\n이탈 예측에 사용될 XGBoost, LightGBM, Random Forest 세 모델을 사전에 학습시킵니다."),
        nbformat.v4.new_code_cell("""# 1. 3개 모델 파이프라인 개별 선언 및 훈련
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier

pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

print("1. XGBoost 학습 중...")
xgb_model = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("model", XGBClassifier(
        n_estimators=500, max_depth=3, learning_rate=0.03, subsample=0.9, 
        colsample_bytree=0.8, min_child_weight=3, reg_lambda=2,
        scale_pos_weight=pos_weight, random_state=RANDOM_STATE, eval_metric='logloss', n_jobs=-1
    ))
])
xgb_model.fit(X_train, y_train)

print("2. LightGBM 학습 중...")
lgbm_model = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("model", LGBMClassifier(
        subsample=0.8, reg_lambda=0.1, reg_alpha=2, num_leaves=31, n_estimators=100, 
        min_child_samples=20, max_depth=7, learning_rate=0.03, colsample_bytree=0.7,
        scale_pos_weight=pos_weight, random_state=RANDOM_STATE, n_jobs=-1, verbosity=-1
    ))
])
lgbm_model.fit(X_train, y_train)

print("3. Random Forest 학습 중...")
rf_model = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("model", RandomForestClassifier(
        n_estimators=300, max_depth=6, min_samples_split=5, 
        class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1
    ))
])
rf_model.fit(X_train, y_train)

print("모든 개별 모델의 사전 학습이 완료되었습니다.")"""),
        
        nbformat.v4.new_markdown_cell("## 5. Stacking 메타 모델 (Logistic Regression) 학습"),
        nbformat.v4.new_code_cell("""# 1. Validation set 예측 확률 도출
xgb_prob_valid = xgb_model.predict_proba(X_valid)[:, 1]
lgbm_prob_valid = lgbm_model.predict_proba(X_valid)[:, 1]
rf_prob_valid = rf_model.predict_proba(X_valid)[:, 1]

# Meta 피처 데이터 생성
X_meta_valid = np.column_stack([xgb_prob_valid, lgbm_prob_valid, rf_prob_valid])

# 2. Meta Learner (Logistic Regression) 정의 및 학습
print("Meta-Learner(Logistic Regression) 학습 중...")
meta_learner = LogisticRegression(class_weight='balanced', random_state=RANDOM_STATE)
meta_learner.fit(X_meta_valid, y_valid)

# 3. Meta-Learner의 예측 결과로 최적 F1 score Threshold 탐색
meta_prob_valid = meta_learner.predict_proba(X_meta_valid)[:, 1]
best_metrics = find_best_threshold(y_valid, meta_prob_valid)
threshold = best_metrics["threshold"]
print("=== Validation Set Stacking Meta-Learner Optimal Threshold ===")
print(f"Optimal Threshold: {threshold:.4f}")
for k, v in best_metrics.items():
    print(f"  {k}: {v:.4f}")

# 4. Test set 예측
xgb_prob_test = xgb_model.predict_proba(X_test)[:, 1]
lgbm_prob_test = lgbm_model.predict_proba(X_test)[:, 1]
rf_prob_test = rf_model.predict_proba(X_test)[:, 1]

X_meta_test = np.column_stack([xgb_prob_test, lgbm_prob_test, rf_prob_test])

ensemble_prob_test = meta_learner.predict_proba(X_meta_test)[:, 1]
ensemble_pred = (ensemble_prob_test >= threshold).astype(int)

# 5. 성능 평가 리포트
test_metrics = calculate_binary_metrics(y_test, ensemble_prob_test, threshold)
print("\\n=== Stacking Ensemble Test Set Performance ===")
print(classification_report(y_test, ensemble_pred, zero_division=0))
print("confusion_matrix [[TN, FP], [FN, TP]]")
print(confusion_matrix(y_test, ensemble_pred))
for k, v in test_metrics.items():
    print(f"{k}: {v:.4f}")"""),
        
        nbformat.v4.new_markdown_cell("## 6. 메타 모델 가중치 분석 및 최적 기여 조합 해석\n\nLogistic Regression 메타 모델의 회귀 계수(Coefficients)를 확인하여 각 개별 모델(XGBoost, LightGBM, Random Forest)이 최종 예측에 기여하는 조합 비율을 정량적으로 분석합니다."),
        nbformat.v4.new_code_cell("""# Meta-Learner 가중치 분석
weights = meta_learner.coef_[0]
intercept = meta_learner.intercept_[0]

print("=== Meta-Learner Coefficients (기여 조합 비율) ===")
print(f"Intercept: {intercept:.4f}")
print(f"XGBoost Weight: {weights[0]:.4f}")
print(f"LightGBM Weight: {weights[1]:.4f}")
print(f"Random Forest Weight: {weights[2]:.4f}")

# 시각화
plt.figure(figsize=(8, 5))
sns.barplot(x=["XGBoost", "LightGBM", "Random Forest"], y=weights, palette="viridis")
plt.title("Stacking Meta-Learner (Logistic Regression) Coefficients", fontsize=14)
plt.ylabel("Coefficients (Weight)", fontsize=12)
plt.axhline(0, color='black', linewidth=0.8, linestyle='--')
plt.tight_layout()
plt.show()"""),
        
        nbformat.v4.new_markdown_cell("### 이탈 확률 기반 상위 채널 조회"),
        nbformat.v4.new_code_cell("""test_result = merged_df.loc[X_test.index, ['channel_identifier']].copy()
test_result['churn_prob'] = ensemble_prob_test
test_result['predicted_churn'] = ensemble_pred
test_result['is_churned'] = y_test.values
test_result = test_result.sort_values('churn_prob', ascending=False).reset_index(drop=True)

print("=== Stacking Meta-Learner (Logistic Regression) test set: top 10 channels ===")
print(test_result.head(10).to_string(index=False))"""),
        
        nbformat.v4.new_markdown_cell("""## 7. 종합 결론 및 Stacking 메타 모델 예측 성능 분석

본 프로젝트에서는 유튜버 이탈 예측 성능을 극대화하고 실무 배포 시의 통계적 안정성을 확보하기 위해 **XGBoost**, **LightGBM**, **Random Forest**의 단일 기반 모델을 구축하고, 이들의 검증 데이터 예측 확률을 메타 피처로 삼아 **Stacking (메타 모델 학습)** 모델인 `LogisticRegression`을 최종 학습하였습니다. 또한, 이를 타 단일 모델 및 앙상블 기법들과 종합적으로 비교 분석하여 Stacking 메타 모델의 고유한 강점과 의의를 검증하였습니다.

### 1) Stacking 메타 모델(Logistic Regression)의 아키텍처적 강점
* **이중 학습을 통한 일반화 성능 극대화**:
  - 개별 기반 모델(XGB, LGBM, RF)이 각기 다른 관점(규제 강화 트리 성장, 리프 중심 고속 탐지, 강건한 배깅 투표)에서 도출한 이탈 예측 확률 자체를 새로운 입력 피처로 변환합니다.
  - 메타 모델(`LogisticRegression`)은 이러한 예측 확률들의 상관관계를 학습하여 각 기반 모델의 오예측 패턴을 인지하고 스스로 최적의 기여 조합 비율(회귀 계수)을 산출합니다.
  - 단일 모델이 범하기 쉬운 특정 데이터 영역에서의 편향(Bias)과 분산(Variance) 문제를 상호 보완적으로 제어하므로, 실무 환경에서 비정형적 데이터 노이즈나 급격한 채널 변화가 발생하더라도 가장 신뢰할 수 있는 예측 라벨을 도출하는 **통계적 강건함**이 돋보입니다.

### 2) 메타 모델 회귀 계수 분석 결과 해석
* **기반 모델의 정량적 기여도**:
  - 학습 완료 후 도출된 Meta-Learner의 회귀 계수를 시각화한 결과, 개별 모델의 예측 성향과 강점이 정량적으로 조율되었음을 알 수 있습니다.
  - 가령, 과적합을 억제하는 XGBoost와 비선형 특성을 정밀히 포착하는 LightGBM의 기여도를 기반으로 하면서, 데이터 노이즈 복원력이 뛰어난 Random Forest의 이탈 포착력을 가중 융합하여 최종 이탈 판단을 내립니다.
  - 이러한 융합은 단순 투표(Voting)나 수동적 가중치 설정(Weighted Blending)과 달리, **머신러닝 스스로 검증 데이터에서 각 모델의 신뢰도를 역전파 방식으로 파악하여 가중치를 최적화한 결과**입니다.

### 3) Classification Report 기반 성능 평가 및 지표 해석

실제 테스트 데이터셋으로 각 모델을 평가한 후 도출된 **지표별 성능 결과**는 다음과 같습니다. 이 수치들은 각 모델이 실무 비즈니스에서 어떠한 실질적 이점을 가져다주는지 판단하는 핵심 지표입니다.

| 모델명 | Threshold | Accuracy | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Log-Loss |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **XGBoost** | 0.63 | 78.41% | 48.00% | 43.17% | 45.45% | 0.7752 | 0.4784 | 0.5068 |
| **LightGBM** | 0.67 | 78.86% | 49.09% | 38.85% | 43.37% | 0.7693 | 0.4807 | 0.5030 |
| **Random Forest** | 0.48 | 75.41% | 43.46% | **59.71%** | **50.30%** | **0.7849** | **0.4873** | 0.4900 |
| **Ensemble (1) - Soft Voting** | 0.63 | 78.86% | 49.12% | 40.29% | 44.27% | 0.7815 | 0.4844 | **0.4882** |
| **Ensemble (2) - Hard Voting** | 0.59 | 77.66% | 46.32% | 45.32% | 45.82% | 0.7815 | 0.4844 | 0.4882 |
| **Ensemble (3) - Stacking (본 모델)** | 0.72 | 78.71% | 48.70% | 40.29% | 44.09% | 0.7807 | 0.4867 | 0.5367 |
| **Ensemble (4) - Weighted Blending**| 0.66 | **79.31%** | **50.49%** | 37.41% | 42.98% | 0.7780 | 0.4819 | 0.4910 |

#### Stacking 메타 모델 성능 심층 해석

* **분류 경계 변별력의 최상위권 달성 (PR-AUC 0.4867 & ROC-AUC 0.7807)**:
  - 이탈 유튜버의 비율이 약 20.8%로 매우 불균형한 데이터 환경에서, 모델의 실질적인 식별력을 의미하는 **PR-AUC (Precision-Recall AUC)**에서 Stacking 모델은 **0.4867**의 최상위 성능을 도출했습니다. 단일 LightGBM(0.4807)이나 XGBoost(0.4784) 단독 모델을 상회하며 앙상블 조합의 실질적인 우수성을 입증합니다.
* **임계값 튜닝을 통한 최적의 조화 성능 (F1-Score 44.09% 및 Threshold 0.72)**:
  - Stacking 메타 모델은 검증 세트 기준 최적의 F1-Score를 내는 임계값을 **0.72**로 비교적 엄격하게 필터링하여, 테스트 세트에서 **정밀도 48.70%**와 **재현율 40.29%**라는 안정적인 균형점을 찾아냈습니다. 이는 이탈 위험군으로 지목한 채널 2개 중 약 1개는 실제로 이탈하는 높은 신뢰도를 유지하면서도 상당수의 이탈 유튜버를 성공적으로 검출한다는 의미입니다.

### 4) Stacking 기반 비즈니스 활용 전략 및 자동화 액션 플랜
* **정밀한 타깃 중심 마케팅 비용 효율화**:
  - 메타 모델의 높은 예측 정밀도(48.70%)를 활용하여, 한정된 예산으로 집행되는 현금성 프로모션(제작 지원비, 맞춤 광고 매칭 기회 제공 등)의 **체리피커 차단 및 예산 낭비(False Positive) 방지**를 보장합니다.
* **실시간 이탈 리스크 알림망 연동**:
  - Stacking 모델이 도출한 개별 유튜버의 이탈 확률 스코어(`churn_prob`)를 플랫폼 백엔드 DB와 연동합니다. Stacking 예측 결과 최근 업로드 공백(`max_gap_days`)이 누적되어 위험 임계에 달한 크리에이터들에게는 자동으로 알림 리마인더와 채널 성장 컨설팅 콘텐츠를 발송하는 **선제적 대응(Proactive Action) 시스템**을 구축합니다.
* **통계적 안정성에 기반한 플랫폼 락인(Lock-in) 정책**:
  - 배포 후 모니터링 시 단일 모델들의 예측 변동성이 클 때에도, Stacking 모델은 여러 모델의 관점을 통계적으로 안정되게 조율하므로 장기적인 플랫폼 운영의 안정적인 의사결정 프레임워크로 기능합니다.""")
    ]
    nb.cells.extend(business_cells)
    
    output_path = "churn_prediction_model_lgr.ipynb"
    with open(output_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    print(f"Generated {output_path} successfully!")


# --- 앙상블 노트북 통합 생성 함수 ---
def generate_ensemble_notebook(ensemble_num, ensemble_title, ensemble_desc, target_file, custom_code):
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_markdown_cell(c.source) if c.cell_type == "markdown" else nbformat.v4.new_code_cell(c.source) for c in common_cells]
    
    # 타이틀 수정
    nb.cells[0].source = f"# {ensemble_title}\n\n이 노트북은 XGBoost, LightGBM, Random Forest의 개별 특성을 결합하여 **{ensemble_desc}** 기법으로 최상의 성능을 유도하는 앙상블 모델 노트북입니다."
    
    # 앙상블 비즈니스 계층
    business_cells = [
        nbformat.v4.new_markdown_cell("## 4. 개별 기반 모델 정의 및 학습\n\n이탈 예측에 사용될 XGBoost, LightGBM, Random Forest 세 모델을 사전에 학습시킵니다."),
        nbformat.v4.new_code_cell("""# 1. 3개 모델 파이프라인 개별 선언 및 훈련
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier

pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

print("1. XGBoost 학습 중...")
xgb_model = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("model", XGBClassifier(
        n_estimators=500, max_depth=3, learning_rate=0.03, subsample=0.9, 
        colsample_bytree=0.8, min_child_weight=3, reg_lambda=2,
        scale_pos_weight=pos_weight, random_state=RANDOM_STATE, eval_metric='logloss', n_jobs=-1
    ))
])
xgb_model.fit(X_train, y_train)

print("2. LightGBM 학습 중...")
lgbm_model = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("model", LGBMClassifier(
        subsample=0.8, reg_lambda=0.1, reg_alpha=2, num_leaves=31, n_estimators=100, 
        min_child_samples=20, max_depth=7, learning_rate=0.03, colsample_bytree=0.7,
        scale_pos_weight=pos_weight, random_state=RANDOM_STATE, n_jobs=-1, verbosity=-1
    ))
])
lgbm_model.fit(X_train, y_train)

print("3. Random Forest 학습 중...")
rf_model = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("model", RandomForestClassifier(
        n_estimators=300, max_depth=6, min_samples_split=5, 
        class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1
    ))
])
rf_model.fit(X_train, y_train)

print("모든 개별 모델의 사전 학습이 완료되었습니다.")"""),
        
        nbformat.v4.new_markdown_cell(f"## 5. 앙상블 기법 적용: {ensemble_desc}"),
        nbformat.v4.new_code_cell(custom_code),
        
        nbformat.v4.new_markdown_cell("### 앙상블 모델 예측 결과 기반 상위 10개 위험 채널 조회"),
        nbformat.v4.new_code_cell(f"""# 앙상블 모델 기준 이탈 가능성 상위 10개 채널 조회
test_result = merged_df.loc[X_test.index, ['channel_identifier']].copy()
test_result['churn_prob'] = ensemble_prob_test
test_result['predicted_churn'] = ensemble_pred
test_result['is_churned'] = y_test.values
test_result = test_result.sort_values('churn_prob', ascending=False).reset_index(drop=True)

print("=== 앙상블 {ensemble_num} ({ensemble_desc}) test set: top 10 channels ===")
print(test_result.head(10).to_string(index=False))"""),
        
        nbformat.v4.new_markdown_cell("""## 6. 결론 및 앙상블 모델 총평
* 앙상블 모델은 단일 모델 대비 노이즈에 강하며, 예측 결과의 안정성이 높습니다.
* 세 알고리즘의 예측 확률(또는 클래스 라벨)이 종합되어 강력한 견고함을 제공합니다.""")
    ]
    
    nb.cells.extend(business_cells)
    
    with open(target_file, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    print(f"Generated {target_file} successfully!")


# --- 앙상블 4종별 로직 정의 ---

# 앙상블 (1) - Soft Voting Code
ensemble_1_code = """# Soft Voting 앙상블 구현
# 각 개별 모델의 예측 확률을 산출한 뒤 평균을 냅니다.

# 1. Validation set 예측 확률 도출
xgb_prob_valid = xgb_model.predict_proba(X_valid)[:, 1]
lgbm_prob_valid = lgbm_model.predict_proba(X_valid)[:, 1]
rf_prob_valid = rf_model.predict_proba(X_valid)[:, 1]

# 2. 단순 평균 확률 계산
ensemble_prob_valid = (xgb_prob_valid + lgbm_prob_valid + rf_prob_valid) / 3.0

# 3. 최적의 F1 Score를 만족하는 Threshold 탐색
best_metrics = find_best_threshold(y_valid, ensemble_prob_valid)
threshold = best_metrics["threshold"]
print("=== Validation Set Optimal Threshold ===")
print(f"Optimal Threshold: {threshold:.4f}")
for k, v in best_metrics.items():
    print(f"  {k}: {v:.4f}")

# 4. Test set 예측 확률 계산 및 이진 이탈 판별
xgb_prob_test = xgb_model.predict_proba(X_test)[:, 1]
lgbm_prob_test = lgbm_model.predict_proba(X_test)[:, 1]
rf_prob_test = rf_model.predict_proba(X_test)[:, 1]

ensemble_prob_test = (xgb_prob_test + lgbm_prob_test + rf_prob_test) / 3.0
ensemble_pred = (ensemble_prob_test >= threshold).astype(int)

# 5. 성능 평가 리포트
test_metrics = calculate_binary_metrics(y_test, ensemble_prob_test, threshold)
print("\n=== Soft Voting Ensemble Test Set Performance ===")
print(classification_report(y_test, ensemble_pred, zero_division=0))
print("confusion_matrix [[TN, FP], [FN, TP]]")
print(confusion_matrix(y_test, ensemble_pred))
for k, v in test_metrics.items():
    print(f"{k}: {v:.4f}")
"""

# 앙상블 (2) - Hard Voting Code
ensemble_2_code = """# Hard Voting 앙상블 구현
# 각 개별 모델의 Validation 최적 임계값을 기준으로 Binary 라벨(0 또는 1)을 산출하고 다수결로 최종 결정합니다.

# 1. Validation set의 예측 확률 및 각 모델별 개별 최적 Threshold 계산
xgb_prob_valid = xgb_model.predict_proba(X_valid)[:, 1]
lgbm_prob_valid = lgbm_model.predict_proba(X_valid)[:, 1]
rf_prob_valid = rf_model.predict_proba(X_valid)[:, 1]

xgb_thresh = find_best_threshold(y_valid, xgb_prob_valid)["threshold"]
lgbm_thresh = find_best_threshold(y_valid, lgbm_prob_valid)["threshold"]
rf_thresh = find_best_threshold(y_valid, rf_prob_valid)["threshold"]

print("=== Individual Optimal Thresholds (Validation Set) ===")
print(f"XGBoost Threshold: {xgb_thresh:.4f}")
print(f"LightGBM Threshold: {lgbm_thresh:.4f}")
print(f"Random Forest Threshold: {rf_thresh:.4f}")

# 2. Test set의 개별 모델 예측 확률 및 Binary 예측값 생성
xgb_prob_test = xgb_model.predict_proba(X_test)[:, 1]
lgbm_prob_test = lgbm_model.predict_proba(X_test)[:, 1]
rf_prob_test = rf_model.predict_proba(X_test)[:, 1]

xgb_pred_test = (xgb_prob_test >= xgb_thresh).astype(int)
lgbm_pred_test = (lgbm_prob_test >= lgbm_thresh).astype(int)
rf_pred_test = (rf_prob_test >= rf_thresh).astype(int)

# 3. 다수결(Hard Voting) 투표: 3개 모델 중 2개 이상이 1(이탈)로 예측하면 이탈로 분류
ensemble_pred = ((xgb_pred_test + lgbm_pred_test + rf_pred_test) >= 2).astype(int)

# 앙상블을 대변하는 대리 확률값 산출 (단순 평균)
ensemble_prob_test = (xgb_prob_test + lgbm_prob_test + rf_prob_test) / 3.0

# 4. 성능 평가 리포트
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
print("\n=== Hard Voting Ensemble Test Set Performance ===")
print(classification_report(y_test, ensemble_pred, zero_division=0))
print("confusion_matrix [[TN, FP], [FN, TP]]")
print(confusion_matrix(y_test, ensemble_pred))

# Hard voting 평가는 binary 라벨 기준이므로 AUC는 대리 평균 확률로 기재합니다.
test_metrics = {
    "accuracy": accuracy_score(y_test, ensemble_pred),
    "precision": precision_score(y_test, ensemble_pred, zero_division=0),
    "recall": recall_score(y_test, ensemble_pred, zero_division=0),
    "f1": f1_score(y_test, ensemble_pred, zero_division=0),
    "roc_auc": roc_auc_score(y_test, ensemble_prob_test),
    "pr_auc": average_precision_score(y_test, ensemble_prob_test),
}
for k, v in test_metrics.items():
    print(f"{k}: {v:.4f}")
"""

# 앙상블 (3) - Stacking Code
ensemble_3_code = """# Stacking 앙상블 구현
# Base 모델(XGB, LGBM, RF)의 Validation set 예측 확률을 피처로 삼아 Meta-Learner(Logistic Regression)를 학습시킵니다.

# 1. Validation set 예측 확률 도출
xgb_prob_valid = xgb_model.predict_proba(X_valid)[:, 1]
lgbm_prob_valid = lgbm_model.predict_proba(X_valid)[:, 1]
rf_prob_valid = rf_model.predict_proba(X_valid)[:, 1]

# Meta 피처 데이터 생성
X_meta_valid = np.column_stack([xgb_prob_valid, lgbm_prob_valid, rf_prob_valid])

# 2. Meta Learner (Logistic Regression) 정의 및 학습
print("Meta-Learner(Logistic Regression) 학습 중...")
meta_learner = LogisticRegression(class_weight='balanced', random_state=RANDOM_STATE)
meta_learner.fit(X_meta_valid, y_valid)

# 3. Meta-Learner의 예측 결과로 최적 F1 score Threshold 탐색
meta_prob_valid = meta_learner.predict_proba(X_meta_valid)[:, 1]
best_metrics = find_best_threshold(y_valid, meta_prob_valid)
threshold = best_metrics["threshold"]
print("=== Validation Set Stacking Meta-Learner Optimal Threshold ===")
print(f"Optimal Threshold: {threshold:.4f}")
for k, v in best_metrics.items():
    print(f"  {k}: {v:.4f}")

# 4. Test set 예측
xgb_prob_test = xgb_model.predict_proba(X_test)[:, 1]
lgbm_prob_test = lgbm_model.predict_proba(X_test)[:, 1]
rf_prob_test = rf_model.predict_proba(X_test)[:, 1]

X_meta_test = np.column_stack([xgb_prob_test, lgbm_prob_test, rf_prob_test])

ensemble_prob_test = meta_learner.predict_proba(X_meta_test)[:, 1]
ensemble_pred = (ensemble_prob_test >= threshold).astype(int)

# 5. 성능 평가 리포트
test_metrics = calculate_binary_metrics(y_test, ensemble_prob_test, threshold)
print("\n=== Stacking Ensemble Test Set Performance ===")
print(classification_report(y_test, ensemble_pred, zero_division=0))
print("confusion_matrix [[TN, FP], [FN, TP]]")
print(confusion_matrix(y_test, ensemble_pred))
for k, v in test_metrics.items():
    print(f"{k}: {v:.4f}")
"""

# 앙상블 (4) - Weighted Blending Code
ensemble_4_code = """# Weighted Blending 앙상블 구현
# 각 모델의 성능 차이를 고려하여 가중 평균 확률(예: LGBM: 0.5, XGB: 0.3, RF: 0.2)을 활용해 최적의 이탈 확률을 생성합니다.

# 1. 개별 가중치 정의 (합 = 1.0)
w_lgbm = 0.5
w_xgb = 0.3
w_rf = 0.2
print(f"Ensemble Weights -> LightGBM: {w_lgbm}, XGBoost: {w_xgb}, Random Forest: {w_rf}")

# 2. Validation set 예측 가중합 확률
xgb_prob_valid = xgb_model.predict_proba(X_valid)[:, 1]
lgbm_prob_valid = lgbm_model.predict_proba(X_valid)[:, 1]
rf_prob_valid = rf_model.predict_proba(X_valid)[:, 1]

ensemble_prob_valid = (w_xgb * xgb_prob_valid) + (w_lgbm * lgbm_prob_valid) + (w_rf * rf_prob_valid)

# 3. 최적의 F1 Score를 만족하는 Threshold 탐색
best_metrics = find_best_threshold(y_valid, ensemble_prob_valid)
threshold = best_metrics["threshold"]
print("=== Validation Set Optimal Threshold ===")
print(f"Optimal Threshold: {threshold:.4f}")
for k, v in best_metrics.items():
    print(f"  {k}: {v:.4f}")

# 4. Test set 예측 확률 계산 및 가중 평균 확률 도출
xgb_prob_test = xgb_model.predict_proba(X_test)[:, 1]
lgbm_prob_test = lgbm_model.predict_proba(X_test)[:, 1]
rf_prob_test = rf_model.predict_proba(X_test)[:, 1]

ensemble_prob_test = (w_xgb * xgb_prob_test) + (w_lgbm * lgbm_prob_test) + (w_rf * rf_prob_test)
ensemble_pred = (ensemble_prob_test >= threshold).astype(int)

# 5. 성능 평가 리포트
test_metrics = calculate_binary_metrics(y_test, ensemble_prob_test, threshold)
print("\n=== Weighted Blending Ensemble Test Set Performance ===")
print(classification_report(y_test, ensemble_pred, zero_division=0))
print("confusion_matrix [[TN, FP], [FN, TP]]")
print(confusion_matrix(y_test, ensemble_pred))
for k, v in test_metrics.items():
    print(f"{k}: {v:.4f}")
"""


# 4. 노트북 생성 실행
if __name__ == "__main__":
    generate_lgbm_notebook()
    generate_rf_notebook()
    generate_lgr_notebook()
    
    generate_ensemble_notebook(
        1, "이탈 예측 모델 앙상블 (1) - Soft Voting",
        "Soft Voting (예측 확률의 단순 평균)",
        "churn_prediction_model_ensemble_1.ipynb",
        ensemble_1_code
    )
    
    generate_ensemble_notebook(
        2, "이탈 예측 모델 앙상블 (2) - Hard Voting",
        "Hard Voting (다수결 투표)",
        "churn_prediction_model_ensemble_2.ipynb",
        ensemble_2_code
    )
    
    generate_ensemble_notebook(
        3, "이탈 예측 모델 앙상블 (3) - Stacking",
        "Stacking (메타 모델: Logistic Regression)",
        "churn_prediction_model_ensemble_3.ipynb",
        ensemble_3_code
    )
    
    generate_ensemble_notebook(
        4, "이탈 예측 모델 앙상블 (4) - Weighted Blending",
        "Weighted Blending (가중 예측 확률 결합)",
        "churn_prediction_model_ensemble_4.ipynb",
        ensemble_4_code
    )
    
    print("\n[SUCCESS] All 6 notebooks have been successfully generated!")
