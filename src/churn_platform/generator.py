"""Deterministic synthetic data generator. No real customer data is used."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class GeneratorConfig:
    customers: int = 20_000
    months: int = 18
    seed: int = 20261022
    start_month: str = "2025-01-01"
    anomaly_rate: float = 0.002
    def __post_init__(self):
        if self.customers < 1: raise ValueError("customers must be >= 1")
        if self.months < 2: raise ValueError("months must be >= 2")
        if not 0 <= self.anomaly_rate <= 0.1: raise ValueError("anomaly_rate must be between 0 and 0.1")

def generate_dataset(config: GeneratorConfig = GeneratorConfig(), inject_anomalies: bool = True) -> Dict[str, pd.DataFrame]:
    rng = np.random.default_rng(config.seed)
    n, m = config.customers, config.months
    months = pd.date_range(config.start_month, periods=m, freq="MS")
    ids = np.arange(1, n + 1)
    customer_ids = [f"CUS-{i:06d}" for i in ids]
    segments = rng.choice(["standard", "premium", "business"], n, p=[.58, .30, .12])
    regions = rng.choice(["north", "south", "east", "west"], n)
    signup_idx = rng.integers(0, max(1, m - 2), n)
    customers = pd.DataFrame({"customer_id": customer_ids, "signup_date": [months[i].date().isoformat() for i in signup_idx], "segment": segments, "region": regions, "acquisition_channel": rng.choice(["organic", "referral", "paid", "partner"], n), "seasonal_user": rng.random(n) < .12})
    plan = rng.choice(["basic", "plus", "pro"], n, p=[.45, .38, .17])
    monthly_price = pd.Series(plan).map({"basic": 299.0, "plus": 599.0, "pro": 999.0}).to_numpy(copy=True)
    sub_ids = [f"SUB-{cid}-01" for cid in customer_ids]
    churn_hazard = np.clip(rng.beta(2, 180, n) + np.where(segments == "standard", .002, 0), .015, .25)
    churn_month = np.full(n, -1, dtype=int)
    churn_type = np.full(n, "none", dtype=object)
    for i in range(n):
        active_from = signup_idx[i]
        for j in range(active_from + 1, m):
            seasonal_factor = 1.25 if (customers.loc[i, "seasonal_user"] and j % 12 in (0, 1)) else 1.0
            if rng.random() < min(.35, churn_hazard[i] * seasonal_factor):
                churn_month[i] = j
                churn_type[i] = "voluntary" if rng.random() < .72 else "involuntary"
                break
    initial_plan=plan.copy()
    plan_changes=[]
    plan_by_month=np.tile(initial_plan[:,None],(1,m))
    price_by_month=np.tile(monthly_price[:,None],(1,m))
    price_by_plan={"basic":299.0,"plus":599.0,"pro":999.0}
    if m>=3:
        for i,cid in enumerate(customer_ids):
            first_change=signup_idx[i]+1
            last_change=min(m-2, churn_month[i]-1 if churn_month[i]>=0 else m-2)
            if first_change>last_change or rng.random()>=.12: continue
            effective_idx=int(rng.integers(first_change,last_change+1))
            old_plan=str(initial_plan[i])
            new_plan=str(rng.choice([p for p in ("basic","plus","pro") if p!=old_plan]))
            plan_by_month[i,effective_idx:]=new_plan
            new_price=price_by_plan[new_plan]
            price_by_month[i,effective_idx:]=new_price
            plan_changes.append({"plan_change_event_id":f"PLAN-{sub_ids[i]}-{months[effective_idx]:%Y-%m}","customer_id":cid,"subscription_id":sub_ids[i],"effective_month":months[effective_idx].date().isoformat(),"previous_plan":old_plan,"new_plan":new_plan,"previous_monthly_price":float(monthly_price[i]),"new_monthly_price":new_price})
            plan[i]=new_plan
            monthly_price[i]=new_price
    plan_change_events=pd.DataFrame(plan_changes,columns=["plan_change_event_id","customer_id","subscription_id","effective_month","previous_plan","new_plan","previous_monthly_price","new_monthly_price"])
    subscriptions = pd.DataFrame({"subscription_id": sub_ids, "customer_id": customer_ids, "plan": plan, "monthly_price": monthly_price, "start_date": [months[i].date().isoformat() for i in signup_idx], "status": ["churned" if x >= 0 else "active" for x in churn_month], "end_date": [months[x].date().isoformat() if x >= 0 else None for x in churn_month], "churn_type": churn_type})
    usage_rows, billing_rows, support_rows = [], [], []
    snapshot_by_customer_month = {}
    for i, cid in enumerate(customer_ids):
        base = float(rng.lognormal(3.7, .45))
        for j, month in enumerate(months):
            if j < signup_idx[i] or (churn_month[i] >= 0 and j > churn_month[i]): continue
            before_churn = churn_month[i] < 0 or j < churn_month[i]
            trend = max(.08, 1 - .075 * max(0, j - signup_idx[i]))
            usage = max(0.0, base * trend * rng.uniform(.72, 1.25))
            if customers.loc[i, "seasonal_user"] and j % 12 in (0, 1): usage *= 1.6
            if churn_month[i] >= 0 and j == churn_month[i]: usage *= .2
            snap_id = f"SNAP-{sub_ids[i]}-{month:%Y-%m}"
            snapshot_by_customer_month[(i, j)] = (snap_id, usage)
            usage_rows.append({"snapshot_id": snap_id, "subscription_id": sub_ids[i], "customer_id": cid, "snapshot_month": month.date().isoformat(), "usage_units": round(usage, 3), "active_days": int(rng.integers(1, 29)), "feature_window_end": (month + pd.offsets.MonthEnd(0)).date().isoformat()})
            # Monthly invoice: invoice is paid, late, or failed; totals are derived from events.
            p_late = .08 + (.12 if churn_type[i] == "involuntary" and j >= max(0, churn_month[i]-2) else 0)
            status = rng.choice(["paid", "late", "failed"], p=[1-p_late-.025, p_late, .025])
            amount = float(price_by_month[i,j])
            billing_rows.append({"billing_event_id": f"BILL-{cid}-{month:%Y-%m}", "customer_id": cid, "subscription_id": sub_ids[i], "event_date": (month + pd.Timedelta(days=4)).date().isoformat(), "event_type": "invoice", "amount": amount, "payment_status": status, "currency": "INR"})
            if rng.random() < (.08 + (.10 if churn_month[i] == j else 0)):
                support_rows.append({"support_case_id": f"CASE-{cid}-{month:%Y-%m}-01", "customer_id": cid, "subscription_id": sub_ids[i], "created_at": (month + pd.Timedelta(days=int(rng.integers(5, 25)))).date().isoformat(), "category": rng.choice(["technical", "billing", "product", "cancellation"], p=[.38,.28,.24,.10]), "severity": rng.choice(["low", "medium", "high"], p=[.5,.36,.14]), "status": rng.choice(["open", "resolved"], p=[.18,.82])})
    usage = pd.DataFrame(usage_rows, columns=["snapshot_id","subscription_id","customer_id","snapshot_month","usage_units","active_days","feature_window_end"])
    billing = pd.DataFrame(billing_rows, columns=["billing_event_id","customer_id","subscription_id","event_date","event_type","amount","payment_status","currency"])
    support = pd.DataFrame(support_rows, columns=["support_case_id","customer_id","subscription_id","created_at","category","severity","status"])
    offers = pd.DataFrame([
        {"offer_id":"OFF-2026-000001","offer_name":"Retention 10%","discount_rate":.10,"max_cost":120.0,"min_margin_rate":.25,"start_date":months[0].date().isoformat(),"end_date":months[-1].date().isoformat(),"active":True},
        {"offer_id":"OFF-2026-000002","offer_name":"Retention 15%","discount_rate":.15,"max_cost":180.0,"min_margin_rate":.20,"start_date":months[0].date().isoformat(),"end_date":months[-1].date().isoformat(),"active":True},
    ])
    rules = pd.DataFrame([
        {"eligibility_rule_id":"RULE-001","offer_id":"OFF-2026-000001","min_risk":.45,"allowed_plans":"basic,plus,pro","require_active":True,"max_offer_cost":120.0,"effective_from":months[0].date().isoformat(),"effective_to":months[-1].date().isoformat()},
        {"eligibility_rule_id":"RULE-002","offer_id":"OFF-2026-000002","min_risk":.65,"allowed_plans":"plus,pro","require_active":True,"max_offer_cost":180.0,"effective_from":months[0].date().isoformat(),"effective_to":months[-1].date().isoformat()},
    ])
    # Outcomes are derived from a behavioral churn process; treatment effect is applied only after valid assignment.
    # Use last available month as prediction date; outcome is next-month simulated state, not a feature.
    pred_idx = m - 2
    pred_month = months[pred_idx]
    prediction_date = (pred_month + pd.offsets.MonthEnd(0)).date().isoformat()
    feat_rows = []
    # Pre-group once to avoid repeated full-table scans at the 20k-customer scale.
    cutoff = (pred_month + pd.offsets.MonthEnd(0)).date().isoformat()
    usage_pre = usage[usage.snapshot_month <= cutoff]
    usage_groups = {k:g.sort_values("snapshot_month") for k,g in usage_pre.groupby("customer_id", sort=False)}
    billing_pre = billing[billing.event_date <= cutoff]
    billing_counts = billing_pre.assign(is_late=billing_pre.payment_status.isin(["late","failed"])).groupby("customer_id").is_late.sum().to_dict()
    support_pre = support[support.created_at <= cutoff]
    support_counts = support_pre.groupby("customer_id").size().to_dict()
    for i, cid in enumerate(customer_ids):
        rows = usage_groups.get(cid)
        if rows is None or rows.empty: continue
        vals = rows.usage_units.to_numpy()
        last = float(vals[-1]); prev = float(vals[-2]) if len(vals)>1 else last
        late_count = int(billing_counts.get(cid, 0))
        case_count = int(support_counts.get(cid, 0))
        # Explicit heuristic baseline score, bounded to [0,1], uses only pre-cutoff data.
        score = float(np.clip(.12 + max(0, (prev-last)/(prev or 1))*.45 + min(late_count,4)*.055 + min(case_count,5)*.025, .01, .97))
        feat_rows.append({"customer_id":cid,"subscription_id":sub_ids[i],"prediction_date":prediction_date,"risk_score":round(score,6),"last_usage":round(last,3),"usage_change_pct":round((last-prev)/(prev or 1),6),"late_or_failed_payments":late_count,"support_case_count":case_count,"plan":plan_by_month[i,pred_idx],"monthly_price":price_by_month[i,pred_idx],"subscription_active_at_prediction": bool(churn_month[i] < 0 or churn_month[i] > pred_idx)})
    features = pd.DataFrame(feat_rows)
    # Historical snapshots support an honest time-ordered evaluation. Each
    # row uses only source events available by its prediction cutoff and labels
    # churn in the immediately following month.
    temporal_feature_rows=[]
    temporal_outcome_rows=[]
    customer_index=pd.Series(np.arange(n),index=customer_ids)
    for cutoff_idx in range(1,m-1):
        cutoff_month=months[cutoff_idx]
        cutoff_date=(cutoff_month+pd.offsets.MonthEnd(0)).date().isoformat()
        horizon_date=(months[cutoff_idx+1]+pd.offsets.MonthEnd(0)).date().isoformat()
        available=usage[usage.feature_window_end<=cutoff_date].copy()
        if available.empty: continue
        available["previous_usage"]=available.groupby("customer_id",sort=False).usage_units.shift(1)
        last_rows=available.groupby("customer_id",sort=False).tail(1).copy()
        last_rows["previous_usage"]=last_rows.previous_usage.fillna(last_rows.usage_units)
        late=(billing[(billing.event_date<=cutoff_date)&billing.payment_status.isin(["late","failed"])].groupby("customer_id").size().rename("late_count"))
        cases=support[support.created_at<=cutoff_date].groupby("customer_id").size().rename("case_count")
        snapshot=last_rows.set_index("customer_id").join(late).join(cases)
        snapshot[["late_count","case_count"]]=snapshot[["late_count","case_count"]].fillna(0).astype(int)
        idx=customer_index.loc[snapshot.index].to_numpy()
        not_churned=(churn_month[idx]<0)|(churn_month[idx]>cutoff_idx)
        snapshot=snapshot.loc[not_churned]
        idx=customer_index.loc[snapshot.index].to_numpy()
        last=snapshot.usage_units.to_numpy(dtype=float); prev=snapshot.previous_usage.to_numpy(dtype=float)
        late_count=snapshot.late_count.to_numpy(dtype=int); case_count=snapshot.case_count.to_numpy(dtype=int)
        score=np.clip(.12+np.maximum(0,(prev-last)/np.where(prev!=0,prev,1))*.45+np.minimum(late_count,4)*.055+np.minimum(case_count,5)*.025,.01,.97)
        feature_rows=pd.DataFrame({"customer_id":snapshot.index,"subscription_id":np.array(sub_ids,dtype=object)[idx],"prediction_date":cutoff_date,"risk_score":np.round(score,6),"last_usage":np.round(last,3),"usage_change_pct":np.round((last-prev)/np.where(prev!=0,prev,1),6),"late_or_failed_payments":late_count,"support_case_count":case_count,"plan":plan_by_month[idx,cutoff_idx],"monthly_price":price_by_month[idx,cutoff_idx]})
        temporal_feature_rows.append(feature_rows)
        temporal_outcome_rows.append(pd.DataFrame({"customer_id":snapshot.index,"prediction_date":cutoff_date,"outcome_date":horizon_date,"churned_within_horizon":churn_month[idx]==cutoff_idx+1}))
    temporal_features=pd.concat(temporal_feature_rows,ignore_index=True) if temporal_feature_rows else pd.DataFrame(columns=["customer_id","subscription_id","prediction_date","risk_score","last_usage","usage_change_pct","late_or_failed_payments","support_case_count","plan","monthly_price"])
    temporal_outcomes=pd.concat(temporal_outcome_rows,ignore_index=True) if temporal_outcome_rows else pd.DataFrame(columns=["customer_id","prediction_date","outcome_date","churned_within_horizon"])
    # Offer decisions and experiment assignment only for eligible customers.
    contact_rows=[]
    response_rows=[]
    for r in features.itertuples(index=False):
        if not r.subscription_active_at_prediction: continue
        offer = "OFF-2026-000002" if r.risk_score >= .65 and r.plan in ("plus","pro") else "OFF-2026-000001" if r.risk_score >= .45 else None
        if not offer: continue
        offer_row = offers[offers.offer_id == offer].iloc[0]
        discount_cost = min(float(r.monthly_price)*float(offer_row.discount_rate), float(offer_row.max_cost))
        contribution_margin = float(r.monthly_price) * .55
        eligible = discount_cost <= float(offer_row.max_cost) and (contribution_margin-discount_cost) >= float(r.monthly_price)*float(offer_row.min_margin_rate)
        if not eligible: continue
        group = rng.choice(["treatment","control"])
        sent = bool(group == "treatment" and rng.random() >= .03)
        contact_rows.append({"campaign_contact_id":f"CONTACT-{r.customer_id}-2026","customer_id":r.customer_id,"subscription_id":r.subscription_id,"offer_id":offer,"prediction_date":r.prediction_date,"assigned_group":group,"offer_sent":sent,"offer_cost":round(discount_cost if sent else 0,2),"eligibility_status":"eligible","eligibility_reason":"risk_threshold_and_margin_passed","assignment_seed":config.seed})
        if group == "treatment":
            if not sent:
                response_status="delivery_failed"
            else:
                response_status=str(rng.choice(["accepted","declined","no_response"],p=[.25,.15,.60]))
            response_rows.append({"offer_response_event_id":f"RESPONSE-{r.customer_id}-2026","campaign_contact_id":f"CONTACT-{r.customer_id}-2026","customer_id":r.customer_id,"offer_id":offer,"response_date":(months[pred_idx+1]+pd.offsets.MonthEnd(0)).date().isoformat(),"response_status":response_status,"simulation_rule":"treatment_delivery_and_response_simulation"})
    contacts = pd.DataFrame(contact_rows, columns=["campaign_contact_id","customer_id","subscription_id","offer_id","prediction_date","assigned_group","offer_sent","offer_cost","eligibility_status","eligibility_reason","assignment_seed"])
    offer_response_events=pd.DataFrame(response_rows,columns=["offer_response_event_id","campaign_contact_id","customer_id","offer_id","response_date","response_status","simulation_rule"])
    contact_map = {r.customer_id:r for r in contacts.itertuples(index=False)}
    response_map = {r.customer_id:r.response_status for r in offer_response_events.itertuples(index=False)}
    churn_rows, retention_rows = [], []
    for i, cid in enumerate(customer_ids):
        # Ground truth churn at first simulated churn month; churn outcome is not derived from the prediction score.
        true_churn_date = months[churn_month[i]].date().isoformat() if churn_month[i] >= 0 else None
        churn_rows.append({"churn_outcome_id":f"CHURN-{cid}-{months[-1].year}","customer_id":cid,"subscription_id":sub_ids[i],"prediction_date":prediction_date,"churn_date":true_churn_date,"churned_within_horizon":bool(churn_month[i] == pred_idx+1),"churn_type":churn_type[i],"label_source":"subscription_lifecycle_simulation"})
        c = contact_map.get(cid)
        if c:
            natural_churn = churn_month[i] == pred_idx+1
            # Treatment can reduce churn probability in this synthetic experiment; controls retain natural outcome.
            retained = not natural_churn
            if c.assigned_group == "treatment" and c.offer_sent and response_map.get(cid)=="accepted" and natural_churn and rng.random() < .35: retained = True
            retention_rows.append({"retention_outcome_id":f"RET-{c.campaign_contact_id}","campaign_contact_id":c.campaign_contact_id,"customer_id":cid,"outcome_date":(months[pred_idx+1] + pd.offsets.MonthEnd(0)).date().isoformat(),"retained":bool(retained),"attributed_offer_id":c.offer_id if c.offer_sent else None,"outcome_source":"simulated_behavioral_churn_with_treatment_effect"})
    churn_outcomes = pd.DataFrame(churn_rows)
    retention_outcomes = pd.DataFrame(retention_rows, columns=["retention_outcome_id","campaign_contact_id","customer_id","outcome_date","retained","attributed_offer_id","outcome_source"])
    data = {"customers":customers,"subscriptions":subscriptions,"usage_snapshots":usage,"billing_events":billing,"support_cases":support,"plan_change_events":plan_change_events,"offers":offers,"eligibility_rules":rules,"campaign_contacts":contacts,"offer_response_events":offer_response_events,"churn_outcomes":churn_outcomes,"retention_outcomes":retention_outcomes,"features":features,"temporal_features":temporal_features,"temporal_outcomes":temporal_outcomes}
    if inject_anomalies:
        data["anomaly_ground_truth"] = inject_known_anomalies(data, config.seed)
    else:
        data["anomaly_ground_truth"] = pd.DataFrame(columns=["anomaly_id","issue_type","entity","record_id","expected_detection"])
    return data

def inject_known_anomalies(data: Dict[str,pd.DataFrame], seed: int) -> pd.DataFrame:
    """Append explicitly labelled anomalies; baseline records are preserved."""
    truth=[]
    r=data["churn_outcomes"].iloc[0].copy(); r["churn_outcome_id"]="ANOM-CHURN-PREDATE"; r["churn_date"]="2024-01-01"; r["prediction_date"]="2025-01-31"; r["churned_within_horizon"]=True; r["issue_type"]="churn_label_precedes_prediction_date"
    data["churn_outcomes"] = pd.concat([data["churn_outcomes"],pd.DataFrame([r])],ignore_index=True)
    truth.append({"anomaly_id":"ANOM-001","issue_type":"churn_label_precedes_prediction_date","entity":"churn_outcomes","record_id":"ANOM-CHURN-PREDATE","expected_detection":"temporal_integrity_failure"})
    contacts=data["campaign_contacts"].copy()
    if contacts.empty:
        f=data["features"].iloc[0]
        base={"campaign_contact_id":"ANOM-BASE-CONTACT","customer_id":f.customer_id,"subscription_id":f.subscription_id,"offer_id":"OFF-2026-000001","prediction_date":f.prediction_date,"assigned_group":"treatment","offer_sent":True,"offer_cost":29.9,"eligibility_status":"eligible","eligibility_reason":"synthetic anomaly seed record","assignment_seed":seed}
        contacts=pd.DataFrame([base])
        data["campaign_contacts"]=contacts.copy()
        data["retention_outcomes"]=pd.DataFrame([{"retention_outcome_id":"RET-ANOM-BASE","campaign_contact_id":base["campaign_contact_id"],"customer_id":base["customer_id"],"outcome_date":base["prediction_date"],"retained":True,"attributed_offer_id":"OFF-2026-000001","outcome_source":"synthetic_anomaly_seed"}])
    base_contact=contacts.iloc[0].copy()
    leak=base_contact.copy(); leak["campaign_contact_id"]="ANOM-CONTACT-LEAKAGE"; leak["assigned_group"]="control" if leak["assigned_group"]=="treatment" else "treatment"; leak["issue_type"]="treatment_control_leakage"
    ineligible=base_contact.copy(); ineligible["campaign_contact_id"]="ANOM-INELIGIBLE-OFFER"; ineligible["eligibility_status"]="ineligible"; ineligible["eligibility_reason"]="subscription_inactive"; ineligible["offer_sent"]=True; ineligible["issue_type"]="offer_sent_to_ineligible_customer"
    data["campaign_contacts"]=pd.concat([data["campaign_contacts"],pd.DataFrame([leak,ineligible])],ignore_index=True)
    truth.extend([
      {"anomaly_id":"ANOM-002","issue_type":"treatment_control_leakage","entity":"campaign_contacts","record_id":"ANOM-CONTACT-LEAKAGE","expected_detection":"experiment_integrity_failure"},
      {"anomaly_id":"ANOM-004","issue_type":"offer_sent_to_ineligible_customer","entity":"campaign_contacts","record_id":"ANOM-INELIGIBLE-OFFER","expected_detection":"eligibility_violation"}])
    base_out=data["retention_outcomes"].copy()
    if base_out.empty:
        base_out=pd.DataFrame([{"retention_outcome_id":"RET-ANOM-BASE","campaign_contact_id":base_contact["campaign_contact_id"],"customer_id":base_contact["customer_id"],"outcome_date":base_contact["prediction_date"],"retained":True,"attributed_offer_id":"OFF-2026-000001","outcome_source":"synthetic_anomaly_seed"}])
    target_customer=base_out.iloc[0]["customer_id"]
    idx=base_out.index[base_out.customer_id==target_customer][0]
    base_out.loc[idx,"attributed_offer_id"]="OFF-2026-000001"
    o=base_out.loc[idx].copy(); o["retention_outcome_id"]="ANOM-RET-MULTI-OFFER"; o["attributed_offer_id"]="OFF-2026-000002"; o["issue_type"]="multiple_offer_attribution"
    data["retention_outcomes"]=pd.concat([base_out,pd.DataFrame([o])],ignore_index=True)
    truth.append({"anomaly_id":"ANOM-003","issue_type":"multiple_offer_attribution","entity":"retention_outcomes","record_id":"ANOM-RET-MULTI-OFFER","expected_detection":"duplicate_attribution_failure"})
    return pd.DataFrame(truth,columns=["anomaly_id","issue_type","entity","record_id","expected_detection"])
