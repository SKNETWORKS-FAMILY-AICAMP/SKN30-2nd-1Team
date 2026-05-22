import nbformat

with open('churn_prediction_model_lgbm.ipynb', 'r', encoding='utf-8') as f:
    nb = nbformat.read(f, as_version=4)

code_cells = []
for cell in nb.cells:
    if cell.cell_type == 'code':
        code_cells.append(cell.source)
        if 'make_train_valid_test_split()' in cell.source and 'print(f"Train' in cell.source:
            break

with open('lgbm_tuning.py', 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(code_cells))
    f.write('\n\n')
    f.write('''
import numpy as np
from sklearn.model_selection import RandomizedSearchCV
from lightgbm import LGBMClassifier
from sklearn.metrics import make_scorer, accuracy_score

# Parameter grid for RandomizedSearchCV
param_distributions = {
    'n_estimators': [100, 200, 300, 400, 500, 600],
    'max_depth': [3, 4, 5, 6, 7, -1],
    'learning_rate': [0.01, 0.03, 0.05, 0.1, 0.2],
    'subsample': [0.6, 0.7, 0.8, 0.9, 1.0],
    'colsample_bytree': [0.6, 0.7, 0.8, 0.9, 1.0],
    'min_child_samples': [5, 10, 20, 30],
    'num_leaves': [15, 31, 50, 100],
    'reg_alpha': [0, 0.1, 0.5, 1, 2],
    'reg_lambda': [0, 0.1, 0.5, 1, 2],
}

# We can tune on X_train, y_train and validate on X_valid, but RandomizedSearchCV uses CV.
# To match the notebook's approach, we combine train+valid for CV, or just use X_train_full.
# Here we will use X_train_full and y_train_full which are created inside make_train_valid_test_split.
# Let's recreate X_train_full and y_train_full
from sklearn.model_selection import train_test_split
X_train_full, X_test, y_train_full, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y,
)

lgbm = LGBMClassifier(random_state=42, verbosity=-1)

# Run Randomized Search (100 iterations)
random_search = RandomizedSearchCV(
    estimator=lgbm,
    param_distributions=param_distributions,
    n_iter=100,
    scoring='accuracy',
    cv=3,
    verbose=1,
    random_state=42,
    n_jobs=-1
)

random_search.fit(X_train_full, y_train_full)

print("Best Parameters:", random_search.best_params_)
print("Best CV Accuracy:", random_search.best_score_)

# Write best params to a file so we can read it later
import json
with open('best_lgbm_params.json', 'w') as f:
    json.dump(random_search.best_params_, f)
''')
