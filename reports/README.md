# reports/

평가 단계에서 자동 생성되는 그래프와 리포트 저장 폴더.

## 파일명 규칙

```
{모델명}_{그래프종류}_{날짜}.png
예) xgboost_roc_curve_20260521.png
    all_models_comparison_20260521.png
    shap_summary_20260521.png
```

## 주요 생성 파일

| 파일 | 생성 위치 |
|---|---|
| `*_roc_curve.png` | `src/evaluation/visualizer.py` |
| `*_feature_importance.png` | `src/evaluation/visualizer.py` |
| `shap_summary.png` | `src/evaluation/shap_analysis.py` |
| `credit_grade_distribution.png` | `src/evaluation/visualizer.py` |
| `model_comparison_table.csv` | `src/evaluation/metrics.py` |
