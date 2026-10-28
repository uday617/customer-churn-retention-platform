"""Baseline supervised churn model and held-out evaluation."""
from __future__ import annotations
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from .evaluation import model_metrics

NUMERIC=["last_usage","usage_change_pct","late_or_failed_payments","support_case_count","monthly_price"]
CATEGORICAL=["plan"]

def train_evaluate_model(features: pd.DataFrame, outcomes: pd.DataFrame, random_state: int=20261022):
    """Fit logistic regression on pre-cutoff features; returns a stratified customer holdout report.

    This is a baseline customer-level holdout, not a true multi-cutoff temporal backtest.
    The generator currently emits one prediction window per customer; production evaluation
    should use multiple historical prediction dates and a strictly later test period.
    """
    df=features.merge(outcomes[["customer_id","churned_within_horizon"]],on="customer_id",how="inner",validate="one_to_one")
    cols=NUMERIC+CATEGORICAL
    X=df[cols].copy(); y=df.churned_within_horizon.astype(int)
    if len(df)<10 or y.nunique()<2:
        return {"status":"insufficient_data","n":int(len(df)),"positive_rate":float(y.mean()) if len(y) else None,"reason":"Need at least 10 rows and both target classes."},None
    X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=.25,random_state=random_state,stratify=y)
    preprocess=ColumnTransformer([("numeric",Pipeline([("imputer",SimpleImputer(strategy="median")),("scale",StandardScaler())]),NUMERIC),("categorical",Pipeline([("imputer",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore"))]),CATEGORICAL)])
    model=Pipeline([("preprocess",preprocess),("classifier",LogisticRegression(max_iter=1000,class_weight="balanced",random_state=random_state))])
    model.fit(X_train,y_train)
    scores=model.predict_proba(X_test)[:,1]
    metrics=model_metrics(y_test,scores,threshold=.5)
    metrics.update({"status":"ok","train_n":int(len(X_train)),"test_n":int(len(X_test)),"positive_rate":float(y.mean()),"evaluation":"stratified customer holdout; not temporal backtest","features_used":cols})
    return metrics,model
