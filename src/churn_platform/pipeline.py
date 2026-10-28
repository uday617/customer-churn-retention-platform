"""Export, reproduce, and run the end-to-end synthetic workflow."""
from __future__ import annotations
from pathlib import Path
import hashlib, json
import pandas as pd
from .generator import GeneratorConfig, generate_dataset
from .validation import validate_data, validation_summary
from .evaluation import campaign_metrics

def frame_checksum(df: pd.DataFrame) -> str:
    raw=df.to_csv(index=False,na_rep="<NA>",lineterminator="\n").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def export_dataset(data, out_dir, seed=20261022):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    manifest={}
    for name,df in data.items():
        path=out/f"{name}.csv"; df.to_csv(path,index=False)
        manifest[name]={"file":path.name,"rows":int(len(df)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
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
