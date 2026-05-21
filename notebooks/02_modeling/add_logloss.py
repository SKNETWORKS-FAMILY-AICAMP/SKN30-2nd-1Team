import nbformat
import glob

notebooks = [
    'churn_prediction_model_xgb.ipynb',
    'churn_prediction_model_lgbm.ipynb',
    'churn_prediction_model_rf.ipynb',
    'churn_prediction_model_ensemble_1.ipynb',
    'churn_prediction_model_ensemble_2.ipynb',
    'churn_prediction_model_ensemble_3.ipynb',
    'churn_prediction_model_ensemble_4.ipynb'
]

for nb_path in notebooks:
    try:
        with open(nb_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        modified = False
        for cell in nb.cells:
            if cell.cell_type == 'code':
                # Add import log_loss
                if 'from sklearn.metrics import (' in cell.source and 'log_loss' not in cell.source:
                    cell.source = cell.source.replace(
                        'roc_auc_score,\n)',
                        'roc_auc_score,\n    log_loss,\n)'
                    )
                    modified = True
                
                # Add log_loss to calculate_binary_metrics
                if 'calculate_binary_metrics' in cell.source and '"log_loss"' not in cell.source:
                    cell.source = cell.source.replace(
                        '"roc_auc": roc_auc_score(y_true, y_score),',
                        '"roc_auc": roc_auc_score(y_true, y_score),\n        "log_loss": log_loss(y_true, y_score),'
                    )
                    modified = True
        
        if modified:
            with open(nb_path, 'w', encoding='utf-8') as f:
                nbformat.write(nb, f)
            print(f"Updated {nb_path}")
        else:
            print(f"No changes needed or pattern not found in {nb_path}")
    except Exception as e:
        print(f"Error processing {nb_path}: {e}")
