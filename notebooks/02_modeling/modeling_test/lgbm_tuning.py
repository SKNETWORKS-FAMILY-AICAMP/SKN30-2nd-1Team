import sys
import subprocess
import importlib.util

if importlib.util.find_spec("shap") is None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "shap"])

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import shap

try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except ImportError:
    LGBMClassifier = None

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    log_loss,
)
from scipy.stats import linregress
from functools import reduce
import warnings

warnings.filterwarnings('ignore')
available_fonts = {font.name for font in fm.fontManager.ttflist}
if 'Malgun Gothic' in available_fonts:
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif 'AppleGothic' in available_fonts:
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False


# 데이터 로드
wide_df = pd.read_csv('../../data/raw/filtered_dataset_wide.csv')
long_df = pd.read_csv('../../data/raw/filtered_dataset_long.csv')
view_volatility_df = pd.read_csv('../../data/raw/view_volatility_output.csv')
upload_regularity_df = pd.read_csv('../../data/raw/upload_regularity_score.csv')
active_viewer_df = pd.read_csv('../../data/raw/active_viewer_score.csv')
sensitive_keyword_df = pd.read_csv('../../data/raw/sensitive_keyword_score.csv')

print(f"Wide dataset shape: {wide_df.shape}")
print(f"Long dataset shape: {long_df.shape}")

CHURN_THRESHOLD = 180
wide_df['is_churned'] = (wide_df['days_since_last_upload'] >= CHURN_THRESHOLD).astype(int)


print("이탈 여부 분포 :")
print(wide_df['is_churned'].value_counts())
print(f"이탈 비율 : {wide_df['is_churned'].mean():.2%}")

long_df['published_at'] = pd.to_datetime(long_df['published_at'])
NOW = long_df['published_at'].max()

def extract_long_features(group):
    g = group.sort_values("published_at")

    # 1. upload_slope: 월별 업로드 수 선형 기울기
    g["ym"] = g["published_at"].dt.to_period("M")
    monthly = g.groupby("ym").size().reset_index(name="cnt")
    if len(monthly) >= 3:
        slope, *_ = linregress(range(len(monthly)), monthly["cnt"])
    else:
        slope = np.nan

    # 2. recent_3m_upload_count
    t3 = NOW - pd.Timedelta(days=90)
    recent_3m = (g["published_at"] >= t3).sum()

    # 3. recent_view_ratio (최신 10개 평균 / 전체 평균)
    views = g["view_count"].dropna().tolist()
    if len(views) >= 10:
        recent_avg = np.mean(views[-10:])
        total_avg  = np.mean(views)
        view_ratio = round(recent_avg / (total_avg + 1e-9), 4)
    else:
        
        view_ratio = np.nan

    # 4. days_between_last2: 마지막 두 영상 사이 간격
    dates = g["published_at"].dropna().tolist()
    if len(dates) >= 2:
        days_last2 = (dates[-1] - dates[-2]).days
    else:
        days_last2 = np.nan

    return pd.Series({
        "upload_slope": slope,
        "recent_3m_upload_count": int(recent_3m),
        "recent_view_ratio": view_ratio,
        "days_between_last2": days_last2,
    })

long_features = long_df.groupby("channel_id").apply(extract_long_features).reset_index()

WIDE_FEATURES = [
    "subscriber_count",            # 구독자 수
    "view_count",                  # 채널 누적 조회수
    "total_video_count",           # 채널 전체 영상 수
    "avg_upload_interval_days",    # 평균 업로드 간격(일)
    "std_upload_interval_days",    # 업로드 간격 표준편차 (들쭉날쭉함)
    "max_gap_days",                # 최대 업로드 공백 기간
    "hiatus_count_30d",            # 30일 이상 쉰 횟수 (휴지기 빈도)
   # "upload_freq_change_rate",    # 업로드 빈도 변화율 (미사용)
    "avg_view_count",              # 영상당 평균 조회수
    "std_view_count",              # 영상당 조회수 변동성
    "avg_like_count",              # 영상당 평균 좋아요 수
    "avg_comment_count",           # 영상당 평균 댓글 수
    "avg_engagement_rate",         # 평균 참여율 ((좋아요+댓글)/조회수)
    "shorts_ratio",                # 전체 영상 중 쇼츠 비중
    "avg_shorts_view",             # 쇼츠 영상 평균 조회수
    "avg_normal_view"              # 일반 영상 평균 조회수
]
LONG_FEATURES = [
    "upload_slope",                # 월별 업로드 수 선형회귀 기울기 (음수=활동 감소)
    # "recent_3m_upload_count",    # 최근 90일 업로드 수 (미사용)
    "recent_view_ratio",           # 최근 10개 평균 조회수 / 전체 평균 조회수
    "days_between_last2"           # 마지막 두 영상 사이 간격(일)
]

df = wide_df.merge(long_features, on="channel_id", how="left")


VIEW_VOLATILITY_FEATURES = [
    "volatility_prob"
]
UPLOAD_REGULARITY_FEATURES = [
    "regularity_score"
]
ACTIVE_VIEWER_FEATURES = [
    "active_viewer_score",
    "view_per_sub"
]
SENSITIVE_KEYWORD_FEATURES = [
    "sensitive_score"
]


view_volatility_df = view_volatility_df[["channel_id", "volatility_prob"]]
upload_regularity_df = upload_regularity_df[["channel_id", "regularity_score"]]
active_viewer_df = active_viewer_df[["channel_id", "active_viewer_score", "view_per_sub"]]
sensitive_keyword_df = sensitive_keyword_df[["channel_id", "sensitive_score"]]

dfs = [df, view_volatility_df, upload_regularity_df, active_viewer_df, sensitive_keyword_df]

# channel_id 기준으로 전부 join

merged_df = reduce(

    lambda left, right: pd.merge(left, right, on='channel_id', how='inner'),

    dfs

)

merged_df.head()

ALL_FEATURES = (
    WIDE_FEATURES
    + LONG_FEATURES
    + VIEW_VOLATILITY_FEATURES
    + UPLOAD_REGULARITY_FEATURES
    + ACTIVE_VIEWER_FEATURES
    + SENSITIVE_KEYWORD_FEATURES
)

for feat in ALL_FEATURES:
    merged_df[feat] = merged_df[feat].fillna(merged_df[feat].median())

X = merged_df[ALL_FEATURES]
y = merged_df['is_churned']

print(f"Feature count: {len(ALL_FEATURES)}")
print(ALL_FEATURES)


RANDOM_STATE = 42
THRESHOLD_GRID = np.arange(0.05, 0.951, 0.01)
model_results = {}


def make_train_valid_test_split(test_size=0.2, valid_size=0.25):
    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=RANDOM_STATE,
        stratify=y,
    )
    X_train, X_valid, y_train, y_valid = train_test_split(
        X_train_full,
        y_train_full,
        test_size=valid_size,
        random_state=RANDOM_STATE,
        stratify=y_train_full,
    )
    return X_train, X_valid, X_test, y_train, y_valid, y_test


def score_classifier(model, X_data):
    return model.predict_proba(X_data)[:, 1]


def score_regressor(model, X_data):
    return np.clip(model.predict(X_data), 0, 1)


def calculate_binary_metrics(y_true, y_score, threshold):
    y_pred = (y_score >= threshold).astype(int)
    return {
        "threshold": float(threshold),
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_score),
        "log_loss": log_loss(y_true, y_score),
    }


def find_best_threshold(y_true, y_score):
    best_metrics = None
    best_key = None

    for threshold in THRESHOLD_GRID:
        metrics = calculate_binary_metrics(y_true, y_score, threshold)
        key = (metrics["accuracy"], metrics["roc_auc"], metrics["f1"], metrics["recall"])
        if best_key is None or key > best_key:
            best_key = key
            best_metrics = metrics

    return best_metrics


def show_table(df):
    print(df.to_string(index=False))


def tune_model_candidates(model_name, candidates, score_func):
    rows = []
    best = None

    for idx, model_candidate in enumerate(candidates, start=1):
        model_candidate.fit(X_train, y_train)
        valid_score = np.clip(score_func(model_candidate, X_valid), 0, 1)
        valid_metrics = find_best_threshold(y_valid, valid_score)
        row = {"candidate": idx, **valid_metrics}
        rows.append(row)

        key = (valid_metrics["accuracy"], valid_metrics["roc_auc"], valid_metrics["f1"], valid_metrics["recall"])
        if best is None or key > best["key"]:
            best = {
                "key": key,
                "candidate": idx,
                "model": model_candidate,
                "threshold": valid_metrics["threshold"],
                "valid_metrics": valid_metrics,
                "score_func": score_func,
            }

    summary = pd.DataFrame(rows).sort_values(
        ["accuracy", "roc_auc", "f1", "recall"], ascending=False
    ).reset_index(drop=True)
    print(f"=== {model_name}: validation tuning summary ===")
    show_table(summary)

    return best


def evaluate_tuned_model(model_name, result):
    y_score = np.clip(result["score_func"](result["model"], X_test), 0, 1)
    threshold = result["threshold"]
    y_pred = (y_score >= threshold).astype(int)
    test_metrics = calculate_binary_metrics(y_test, y_score, threshold)

    print(f"=== {model_name}: test metrics ===")
    print(classification_report(y_test, y_pred, zero_division=0))
    print(pd.Series(test_metrics).to_string())

    model_results[model_name] = {
        "candidate": result["candidate"],
        "threshold": threshold,
        "valid_metrics": result["valid_metrics"],
        "test_metrics": test_metrics,
    }
    return y_pred, y_score, test_metrics


X_train, X_valid, X_test, y_train, y_valid, y_test = make_train_valid_test_split()
print(f"Train: {X_train.shape}, Valid: {X_valid.shape}, Test: {X_test.shape}")



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
