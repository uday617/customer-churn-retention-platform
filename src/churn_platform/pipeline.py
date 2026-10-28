"""Export, reproduce, and run the end-to-end synthetic workflow."""
from __future__ import annotations
from pathlib import Path
import hashlib, json, sqlite3
import pandas as pd
from .generator import GeneratorConfig, generate_dataset
from .validation import validate_data, validation_summary

def frame_checksum(df: pd.DataFrame) -> str:
    raw=df.to_csv(index=False,na_rep="<NA>",lineterminator="\n").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def export_dataset(data, out_dir, seed=20261022):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    manifest={}
    for name,df in data.items():
        csv_path=out/f"{name}.csv"; df.to_csv(csv_path,index=False)
        jsonl_path=out/f"{name}.jsonl"
        if df.empty:
            # pandas emits a lone newline for an empty JSONL frame; an empty
            # file is the correct zero-record representation.
            jsonl_path.write_text("",encoding="utf-8")
        else:
            df.to_json(jsonl_path,orient="records",lines=True,date_format="iso")
        for path,fmt in ((csv_path,"csv"),(jsonl_path,"jsonl")):
            manifest[f"{name}_{fmt}"]={"file":path.name,"rows":int(len(df)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    # Produce executable SQLite seed SQL using the documented relational schema.
    # The schema tables intentionally omit derived features and anomaly annotations;
    # those remain available in their CSV/JSONL exports and ground_truth file.
    sql_path=out/"seed_data.sql"
    schema_path=Path(__file__).resolve().parents[2]/"schemas"/"schema.sql"
    schema=schema_path.read_text(encoding="utf-8")
    table_map={"customers":"Customer","subscriptions":"Subscription","plan_change_events":"PlanChangeEvent","usage_snapshots":"UsageSnapshot","billing_events":"BillingEvent","support_cases":"SupportCase","offers":"Offer","eligibility_rules":"EligibilityRule","campaign_contacts":"CampaignContact","offer_response_events":"OfferResponseEvent","churn_outcomes":"ChurnOutcome","retention_outcomes":"RetentionOutcome"}
    with sqlite3.connect(":memory:") as conn:
        conn.executescript(schema)
        for source,table in table_map.items():
            if source not in data: continue
            df=data[source]
            # Extra anomaly marker columns are represented in ground_truth.csv,
            # not added to the normalized relational tables.
            columns=[c for c in df.columns if c in {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}]
            if not columns or df.empty: continue
            values=[]
            for row in df[columns].itertuples(index=False,name=None):
                values.append(tuple(None if pd.isna(v) else (int(v) if isinstance(v,(bool,)) else v.item() if hasattr(v,"item") else v) for v in row))
            conn.executemany(f'INSERT INTO "{table}" ({",".join(chr(34)+c+chr(34) for c in columns)}) VALUES ({",".join("?" for _ in columns)})',values)
        inserts=[]
        for line in conn.iterdump():
            if line.startswith("INSERT INTO"):
                inserts.append(line+";")
    sql_path.write_text("-- Synthetic SQLite seed data; schema follows schemas/schema.sql.\n"+schema+"\n"+"\n".join(inserts)+"\n",encoding="utf-8")
    manifest["seed_sql"]={"file":sql_path.name,"rows":sum(len(data[k]) for k in table_map if k in data),"sha256":hashlib.sha256(sql_path.read_bytes()).hexdigest()}
    (out/"source_manifest.json").write_text(json.dumps({"generator":"churn_platform.generator.generate_dataset","seed":int(seed),"synthetic_only":True,"files":manifest},indent=2),encoding="utf-8")
    return manifest

def run_pipeline(config=GeneratorConfig(), out_dir="data/generated", inject_anomalies=True):
    data=generate_dataset(config,inject_anomalies=inject_anomalies)
    issues=validate_data(data)
    # Separate anomaly truth from operational inputs; never use it as a feature.
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    clean={k:v for k,v in data.items() if k!="anomaly_ground_truth"}
    manifest=export_dataset(clean,out,seed=config.seed)
    data["anomaly_ground_truth"].to_csv(out/"ground_truth.csv",index=False)
    issues.to_csv(out/"validation_issues.csv",index=False)
    summary=validation_summary(data,issues)
    summary["checksums"]={k:v["sha256"] for k,v in manifest.items()}
    summary_path=out/"validation_summary.json"
    summary_path.write_text(json.dumps(summary,indent=2,default=str),encoding="utf-8")
    # Include every generated artifact (including ground truth and reports) in the source manifest.
    for filename in ("ground_truth.csv", "validation_issues.csv", "validation_summary.json"):
        path=out/filename
        manifest[filename.removesuffix(".csv").removesuffix(".json")]={"file":filename,"rows":int(sum(1 for _ in path.open(encoding="utf-8"))-1) if filename.endswith(".csv") else 1,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    (out/"source_manifest.json").write_text(json.dumps({"generator":"churn_platform.generator.generate_dataset","seed":int(config.seed),"synthetic_only":True,"files":manifest},indent=2),encoding="utf-8")
    return data,issues,summary
