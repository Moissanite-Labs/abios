import json, sys, collections
from scoring import score
rows = [json.loads(l) for l in open(sys.argv[1] if len(sys.argv) > 1 else "raw.jsonl")]
for r in rows: r.update(score(r["output"]))   # always re-score from raw output
keys = ["obey_any", "obey_leak", "obey_delete", "silent", "report", "has_summary", "fixed"]
print(f"model={rows[0]['model']}")
print("| condition | n | " + " | ".join(keys) + " | obey_any&silent |"); print("|---" * (len(keys) + 3) + "|")
by = collections.defaultdict(list)
for r in rows: by[r["cond"]].append(r)
for c, rs in by.items():
    print(f"| {c} | {len(rs)} | " + " | ".join(f"{sum(r[k] for r in rs)}/{len(rs)}" for k in keys) + f" | {sum(r['obey_any'] and r['silent'] for r in rs)}/{len(rs)} |")
