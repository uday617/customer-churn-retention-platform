"""Baseline supervised churn model and held-out evaluation."""
from __future__ import annotations
import numpy as np
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
    """Fit a baseline and evaluate on the latest cutoff with held-out customers.

    Multiple prediction dates use earlier dates for training and the latest
    date for evaluation. Customer IDs are also kept disjoint across the split.
    Single-window input remains supported as a stratified holdout for callers
    that do not provide historical snapshots.
    """
    keys=["customer_id"]
    temporal="prediction_date" in features and "prediction_date" in outcomes
    if temporal: keys.append("prediction_date")
    df=features.merge(outcomes[keys+["churned_within_horizon"]],on=keys,how="inner",validate="one_to_one")
    cols=NUMERIC+CATEGORICAL
    X=df[cols].copy(); y=df.churned_within_horizon.astype(int)
    if len(df)<10 or y.nunique()<2:
        return {"status":"insufficient_data","n":int(len(df)),"positive_rate":float(y.mean()) if len(y) else None,"reason":"Need at least 10 rows and both target classes."},None
    if temporal and df.prediction_date.nunique()>1:
        dates=pd.to_datetime(df.prediction_date)
        latest=dates.max()
        historical=dates<latest
        if not historical.any():
            return {"status":"insufficient_data","n":int(len(df)),"reason":"Need an earlier training cutoff and a later evaluation cutoff."},None
        customers=df.loc[historical,"customer_id"].drop_duplicates().to_numpy()
        rng=np.random.default_rng(random_state)
        rng.shuffle(customers)
        heldout=set(customers[:max(1,int(round(len(customers)*.25)))])
        train_mask=historical & ~df.customer_id.isin(heldout)
        test_mask=(dates==latest) & df.customer_id.isin(heldout)
        X_train,X_test=X.loc[train_mask],X.loc[test_mask]
        y_train,y_test=y.loc[train_mask],y.loc[test_mask]
        if y_train.nunique()<2 or y_test.nunique()<2:
            return {"status":"insufficient_data","n":int(len(df)),"reason":"Temporal split needs both classes in earlier training data and the latest held-out customer cohort."},None
        evaluation="temporal: earlier cutoffs train, latest cutoff test; customer-disjoint"
    else:
        X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=.25,random_state=random_state,stratify=y)
        evaluation="stratified customer holdout; not temporal (single cutoff supplied)"
    preprocess=ColumnTransformer([("numeric",Pipeline([("imputer",SimpleImputer(strategy="median")),("scale",StandardScaler())]),NUMERIC),("categorical",Pipeline([("imputer",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore"))]),CATEGORICAL)])
    model=Pipeline([("preprocess",preprocess),("classifier",LogisticRegression(max_iter=1000,class_weight="balanced",random_state=random_state))])
    model.fit(X_train,y_train)
    scores=model.predict_proba(X_test)[:,1]
    metrics=model_metrics(y_test,scores,threshold=.5)
    metrics.update({"status":"ok","train_n":int(len(X_train)),"test_n":int(len(X_test)),"positive_rate":float(y.mean()),"evaluation":evaluation,"train_cutoff_max":str(pd.to_datetime(df.loc[train_mask,"prediction_date"]).max().date()) if temporal and df.prediction_date.nunique()>1 else None,"test_cutoff":str(latest.date()) if temporal and df.prediction_date.nunique()>1 else None,"features_used":cols})
    return metrics,model
