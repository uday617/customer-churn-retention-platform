from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import streamlit as st
import pandas as pd
import plotly.express as px
from churn_platform.generator import GeneratorConfig, generate_dataset
from churn_platform.validation import validate_data
from churn_platform.evaluation import campaign_metrics
from churn_platform.model import train_evaluate_model

st.set_page_config(page_title="Churn & Retention Platform", page_icon="📉", layout="wide")
st.title("Customer Churn & Retention Platform")
st.caption("Synthetic, reproducible demo data · no real customer information")
with st.sidebar:
    st.header("Run configuration")
    n=st.select_slider("Customers", options=[250, 500, 1000, 2500, 5000], value=1000)
    months=st.select_slider("History months", options=[6, 12, 18], value=18)
    seed=st.number_input("Fixed random seed", value=20261022, step=1)
    anomalies=st.checkbox("Inject labelled anomalies", value=True)
    run=st.button("Generate / refresh data", type="primary")
if "data" not in st.session_state or run:
    with st.spinner("Generating synthetic data and validating relationships..."):
        st.session_state.data=generate_dataset(GeneratorConfig(customers=int(n),months=int(months),seed=int(seed)),inject_anomalies=anomalies)
        st.session_state.model_metrics,_=train_evaluate_model(st.session_state.data["temporal_features"],st.session_state.data["temporal_outcomes"],random_state=int(seed))
elif "model_metrics" not in st.session_state:
    st.session_state.model_metrics,_=train_evaluate_model(st.session_state.data["temporal_features"],st.session_state.data["temporal_outcomes"],random_state=int(seed))
data=st.session_state.data
features=data["features"].copy(); contacts=data["campaign_contacts"]; retention=data["retention_outcomes"]
issues=validate_data(data)
churn=data["churn_outcomes"]
col1,col2,col3,col4=st.columns(4)
col1.metric("Customers",f"{len(data['customers']):,}")
col2.metric("Subscriptions",f"{len(data['subscriptions']):,}")
col3.metric("Scored customers",f"{len(features):,}")
col4.metric("Validation findings",f"{len(issues):,}")
tabs=st.tabs(["Overview","Churn risk","Campaign experiment","Data quality & audit","Data explorer"])
with tabs[0]:
    left,right=st.columns(2)
    with left:
        st.subheader("Subscription status")
        st.plotly_chart(px.pie(data["subscriptions"],names="status",hole=.45),use_container_width=True)
    with right:
        st.subheader("Risk distribution")
        if len(features): st.plotly_chart(px.histogram(features,x="risk_score",nbins=20,title="Heuristic risk score (0–1)"),use_container_width=True)
    st.info("This demo uses a transparent heuristic score. It is a baseline, not a validated production prediction model.")
    st.subheader("Temporal model evaluation")
    model_report=st.session_state.model_metrics
    if model_report.get("status")=="ok":
        a,b,c,d=st.columns(4)
        a.metric("PR-AUC", "N/A" if model_report.get("pr_auc") is None else f"{model_report['pr_auc']:.3f}")
        b.metric("Precision",f"{model_report['precision']:.3f}")
        c.metric("Recall",f"{model_report['recall']:.3f}")
        d.metric("F1",f"{model_report['f1']:.3f}")
        st.caption(f"{model_report['evaluation']} · train through {model_report['train_cutoff_max']} · test {model_report['test_cutoff']} · n={model_report['test_n']:,}")
    else:
        st.info(f"Model metrics unavailable: {model_report.get('reason','insufficient data for temporal evaluation')}")
with tabs[1]:
    if len(features):
        threshold=st.slider("High-risk threshold",0.0,1.0,0.45,0.01)
        view=features.assign(risk_band=features.risk_score.map(lambda x:"High" if x>=threshold else "Lower"))
        st.metric("High-risk customers",f"{int((view.risk_score>=threshold).sum()):,}")
        st.dataframe(view.sort_values("risk_score",ascending=False).head(100),use_container_width=True)
with tabs[2]:
    if len(contacts) and len(retention):
        # Join monthly price for transparent contribution proxy; the metric function does not assume this exists.
        contact_metrics=contacts.merge(data["subscriptions"][["subscription_id","monthly_price"]],on="subscription_id",how="left")
        metrics=campaign_metrics(contact_metrics,retention)
        a,b,c,d=st.columns(4)
        a.metric("Treatment assigned",metrics["treatment_n"])
        b.metric("Control assigned",metrics["control_n"])
        b2=metrics["retention_lift"]
        c.metric("Retention lift", "N/A" if b2 is None else f"{b2*100:.2f} pp")
        d.metric("Offer cost",f"₹{metrics['offer_cost']:,.2f}")
        st.json(metrics)
        responses=data["offer_response_events"]
        counts=responses.response_status.value_counts() if len(responses) else pd.Series(dtype=int)
        response_n=int(counts.get("accepted",0)+counts.get("declined",0)+counts.get("no_response",0))
        accepted_rate=int(counts.get("accepted",0))/response_n if response_n else None
        r1,r2,r3=st.columns(3)
        r1.metric("Offer acceptance rate", "N/A" if accepted_rate is None else f"{accepted_rate*100:.1f}%")
        r2.metric("No response",int(counts.get("no_response",0)))
        r3.metric("Delivery failures",int(counts.get("delivery_failed",0)))
        st.caption("Synthetic experiment only. Lift can be noisy at small sample sizes; report confidence intervals before business decisions.")
    else: st.warning("No eligible campaign contacts were generated for this configuration.")
with tabs[3]:
    st.subheader("Validation findings")
    st.write("The anomaly ground-truth table is for evaluation only and must not be used as a model feature.")
    if len(issues): st.dataframe(issues,use_container_width=True)
    else: st.success("No validation findings detected in the current generated data.")
    st.subheader("Injected anomaly ground truth")
    st.dataframe(data.get("anomaly_ground_truth",pd.DataFrame()),use_container_width=True)
with tabs[4]:
    table=st.selectbox("Table",list(data.keys()))
    st.write(f"Rows: {len(data[table]):,}")
    st.dataframe(data[table].head(500),use_container_width=True)
    st.download_button("Download selected table as CSV",data[table].to_csv(index=False).encode(),file_name=f"{table}.csv",mime="text/csv")
