import json
import sqlite3

from churn_platform.generator import GeneratorConfig, generate_dataset
from churn_platform.pipeline import export_dataset


def test_exports_include_offer_response_history(tmp_path):
    data=generate_dataset(GeneratorConfig(customers=300,months=8,seed=20261022),inject_anomalies=False)
    manifest=export_dataset(data,tmp_path,seed=20261022)

    assert (tmp_path/"offer_response_events.csv").exists()
    assert (tmp_path/"offer_response_events.jsonl").exists()
    assert manifest["offer_response_events_jsonl"]["rows"]==len(data["offer_response_events"])
    with (tmp_path/"offer_response_events.jsonl").open(encoding="utf-8") as stream:
        assert sum(1 for _ in stream)==len(data["offer_response_events"])

    conn=sqlite3.connect(":memory:")
    conn.executescript((tmp_path/"seed_data.sql").read_text(encoding="utf-8"))
    count=conn.execute("SELECT COUNT(*) FROM OfferResponseEvent").fetchone()[0]
    assert count==len(data["offer_response_events"])
    source_manifest=json.loads((tmp_path/"source_manifest.json").read_text(encoding="utf-8"))
    assert "seed_sql" in source_manifest["files"]
