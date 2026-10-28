import argparse
from .generator import GeneratorConfig
from .pipeline import run_pipeline

def main():
    p=argparse.ArgumentParser(description="Generate synthetic churn and retention data")
    p.add_argument("--customers",type=int,default=20000)
    p.add_argument("--months",type=int,default=18)
    p.add_argument("--seed",type=int,default=20261022)
    p.add_argument("--output",default="data/generated")
    p.add_argument("--no-anomalies",action="store_true")
    args=p.parse_args()
    _,issues,summary=run_pipeline(GeneratorConfig(customers=args.customers,months=args.months,seed=args.seed),args.output,inject_anomalies=not args.no_anomalies)
    print(f"Generated {summary['total_rows']:,} rows across {len(summary['tables'])} tables")
    print(f"Validation findings: {summary['errors']} errors, {summary['warnings']} warnings")
    print(f"Output: {args.output}")
if __name__=="__main__": main()
