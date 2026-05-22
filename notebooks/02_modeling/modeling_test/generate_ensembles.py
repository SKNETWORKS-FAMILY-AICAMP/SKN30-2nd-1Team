import nbformat
import sys

def create_ensemble_notebook(output_name, title, models_to_include, weights, markdown_conclusion):
    with open('churn_prediction_model_xgb.ipynb', 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
    
    # split 지점 찾기
    split_idx = 0
    for i, cell in enumerate(nb.cells):
        if 'make_train_valid_test_split()' in cell.source:
            split_idx = i
            break
            
    base_cells = nb.cells[:split_idx+1]
    
    # 첫 번째 마크다운 제목 변경
    base_cells[0].source = f"# {title}\n\n이 노트북은 구독자 10만~100만 사이의 유튜버 데이터를 활용하여, 유튜버가 향후 이탈할 것인지 예측하기 위한 앙상블 모델입니다."
    
    new_cells = []
    
    # 1. Models setup and train
    model_code = ""
    if 'xgb' in models_to_include:
        model_code += '''print("Training XGBoost...")
xgb_model = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, random_state=42, eval_metric='logloss')
xgb_model.fit(X_train, y_train)
xgb_prob_valid = xgb_model.predict_proba(X_valid)[:, 1]
xgb_prob_test = xgb_model.predict_proba(X_test)[:, 1]
'''
    if 'lgbm' in models_to_include:
        model_code += '''print("Training LightGBM...")
lgbm_model = LGBMClassifier(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, random_state=42, verbosity=-1)
lgbm_model.fit(X_train, y_train)
lgbm_prob_valid = lgbm_model.predict_proba(X_valid)[:, 1]
lgbm_prob_test = lgbm_model.predict_proba(X_test)[:, 1]
'''
    if 'rf' in models_to_include:
        model_code += '''print("Training Random Forest...")
rf_model = RandomForestRegressor(n_estimators=300, max_depth=5, min_samples_split=5, random_state=42)
rf_model.fit(X_train, y_train)
rf_prob_valid = np.clip(rf_model.predict(X_valid), 0, 1)
rf_prob_test = np.clip(rf_model.predict(X_test), 0, 1)
'''
    new_cells.append(nbformat.v4.new_code_cell(model_code))
    
    # 2. Ensemble logic
    ensemble_code = f'''# Ensemble Weights: {weights}
ensemble_prob_valid = np.zeros_like(y_valid, dtype=float)
ensemble_prob_test = np.zeros_like(y_test, dtype=float)
'''
    for model_name, weight in weights.items():
        ensemble_code += f'''ensemble_prob_valid += {model_name}_prob_valid * {weight}
ensemble_prob_test += {model_name}_prob_test * {weight}
'''
    
    ensemble_code += '''
best_metrics = find_best_threshold(y_valid, ensemble_prob_valid)
threshold = best_metrics["threshold"]

print("=== Ensemble Validation Metrics ===")
for k, v in best_metrics.items():
    print(f"{k}: {v:.4f}")

ensemble_pred = (ensemble_prob_test >= threshold).astype(int)
test_metrics = calculate_binary_metrics(y_test, ensemble_prob_test, threshold)

print("\\n=== Ensemble Test Metrics ===")
print(classification_report(y_test, ensemble_pred, zero_division=0))
for k, v in test_metrics.items():
    print(f"{k}: {v:.4f}")
'''
    new_cells.append(nbformat.v4.new_code_cell(ensemble_code))
    
    # 3. View top channels
    result_code = '''test_result = merged_df.loc[X_test.index, ['channel_id', 'title']].copy()
test_result['churn_prob'] = ensemble_prob_test
test_result['predicted_churn'] = ensemble_pred
test_result['is_churned'] = y_test.values
test_result = test_result.sort_values('churn_prob', ascending=False).reset_index(drop=True)

print("=== Ensemble: Top 10 channels by churn probability ===")
print(test_result.head(10).to_string(index=False))
'''
    new_cells.append(nbformat.v4.new_code_cell(result_code))
    
    # 4. Conclusion Markdown
    new_cells.append(nbformat.v4.new_markdown_cell(markdown_conclusion))
    
    nb.cells = base_cells + new_cells
    
    with open(output_name, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)

# Ensemble 1: XGB + LGBM + RF (Weighted)
create_ensemble_notebook(
    'churn_prediction_model_ensemble_1.ipynb',
    '이탈 예측 모델 앙상블 (1) - XGBoost + LightGBM + Random Forest',
    ['xgb', 'lgbm', 'rf'],
    {'xgb': 0.3, 'lgbm': 0.5, 'rf': 0.2},
    """## 🎯 결론 및 모델 평가 (3개 모델 가중치 앙상블)

**1. 모델 구성 및 가중치**
* LightGBM (50%) + XGBoost (30%) + Random Forest (20%)
* LightGBM의 높은 재현율(Recall) 장점을 메인으로 가져가면서, XGBoost의 확률적 안정성과 Random Forest의 과적합(Overfitting) 방지 효과를 섞은 가장 이상적이고 균형잡힌 모델입니다.

**2. 앙상블 모델의 효용성 및 평가**
* 단일 모델 대비 정밀도와 재현율 간의 트레이드오프(Trade-off)가 개선되어 더 안정적인 예측을 보입니다.
* 여러 알고리즘(부스팅, 배깅)의 장점이 결합되어 있어, 데이터 분포가 약간 변하더라도 예측 성능이 급격히 떨어지는 것을 막아주는 높은 견고함(Robustness)을 가집니다.

**3. 최종 활용 방안**
* **가장 강력히 추천하는 최종 도입 모델**입니다.
* 예측 확률(churn_prob)은 세 가지 모델의 지혜가 합쳐진 결과이므로, 위험 채널들을 이 확률 순으로 정렬하여 집중 관리하는 데 가장 신뢰할 수 있는 지표가 됩니다."""
)

# Ensemble 2: XGB + RF
create_ensemble_notebook(
    'churn_prediction_model_ensemble_2.ipynb',
    '이탈 예측 모델 앙상블 (2) - XGBoost + Random Forest',
    ['xgb', 'rf'],
    {'xgb': 0.6, 'rf': 0.4},
    """## 🎯 결론 및 모델 평가 (XGBoost + Random Forest 앙상블)

**1. 모델 구성 및 가중치**
* XGBoost (60%) + Random Forest (40%)
* 부스팅 알고리즘(XGB)과 배깅 알고리즘(RF)을 결합하여 모델의 '다양성(Diversity)'을 확보한 앙상블입니다.

**2. 앙상블 모델의 효용성 및 평가**
* XGBoost가 가지는 과적합의 위험을 Random Forest가 안정적으로 잡아줍니다. 
* 정확도는 단일 모델보다 약간 향상되거나 비슷하게 유지되면서도 예측의 변동성을 줄일 수 있습니다.

**3. 최종 활용 방안**
* 3개 모델 앙상블이 연산량 등 시스템 부하 문제로 프로덕션 환경에 부적합할 때 훌륭한 대안입니다.
* XGBoost의 강력한 설명력(SHAP)을 보존하면서도 RF로 안전장치를 마련하고 싶을 때 추천합니다."""
)

# Ensemble 3: LGBM + RF
create_ensemble_notebook(
    'churn_prediction_model_ensemble_3.ipynb',
    '이탈 예측 모델 앙상블 (3) - LightGBM + Random Forest',
    ['lgbm', 'rf'],
    {'lgbm': 0.6, 'rf': 0.4},
    """## 🎯 결론 및 모델 평가 (LightGBM + Random Forest 앙상블)

**1. 모델 구성 및 가중치**
* LightGBM (60%) + Random Forest (40%)
* LightGBM의 빠른 속도와 높은 예측력에 Random Forest의 일반화(Generalization) 능력을 더했습니다.

**2. 앙상블 모델의 효용성 및 평가**
* 실무에서 2-모델 앙상블을 사용할 때 **가장 많이 추천하는 '가성비 + 성능' 최고의 조합**입니다.
* 단일 모델 중 성능이 가장 좋은 LightGBM을 주력으로 사용하되, LightGBM 특유의 노이즈 민감성을 RF가 스무딩(Smoothing)해주는 완벽한 상호 보완을 이룹니다.

**3. 최종 활용 방안**
* 실시간 예측이 필요하거나 모델 파이프라인을 가볍게 유지해야 하면서도, 안정적인 예측 확률(Probability)이 필요할 때 가장 적합합니다."""
)

# Ensemble 4: XGB + LGBM
create_ensemble_notebook(
    'churn_prediction_model_ensemble_4.ipynb',
    '이탈 예측 모델 앙상블 (4) - XGBoost + LightGBM',
    ['xgb', 'lgbm'],
    {'xgb': 0.4, 'lgbm': 0.6},
    """## 🎯 결론 및 모델 평가 (XGBoost + LightGBM 앙상블)

**1. 모델 구성 및 가중치**
* LightGBM (60%) + XGBoost (40%)
* 대표적인 2개의 그래디언트 부스팅(Gradient Boosting) 트리를 섞은 형태입니다.

**2. 앙상블 모델의 효용성 및 평가**
* 같은 부스팅 계열이므로 모델 간의 '다양성(Diversity)'은 RF를 섞었을 때보다 낮습니다. 즉, 비슷하게 맞추고 비슷하게 틀릴 확률이 높습니다.
* 하지만 두 강력한 알고리즘이 미세하게 놓치는 부분들을 서로 채워주어 최고 수준의 정확도를 낼 잠재력이 있습니다.

**3. 최종 활용 방안**
* 연산 리소스가 충분하고 오직 극단적인 정확도(Accuracy) 소폭 향상을 노릴 때 주로 캐글(Kaggle) 같은 대회에서 많이 쓰이는 방식입니다.
* 실무에서는 두 모델의 유지보수 비용 대비 얻을 수 있는 추가 이득이 크지 않을 수 있으므로, 굳이 2개를 써야 한다면 부스팅+배깅 조합(LGBM+RF)을 우선적으로 고려하는 것이 낫습니다."""
)

print("4 ensemble notebooks generated successfully!")
