"""Analyze independently completed evaluation sheets against the adjudicated human labels."""
import argparse
import csv
import json
import math
from collections import Counter
from prepare import ROOT, write_json
from rubric import validate, primary


def ratio(x, n):
    return x/n if n else None


def wilson(x, n):
    if not n:
        return None
    z = 1.95996398454
    p = x/n
    center = (p + z*z/(2*n))/(1+z*z/n)
    radius = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/(1+z*z/n)
    return [max(0, center-radius), min(1, center+radius)]


def comparison(reference, predicted):
    pairs=[(a,b) for a,b in zip(reference,predicted) if a is not None and b is not None]
    n=len(pairs)
    tp=sum(a and b for a,b in pairs)
    tn=sum(not a and not b for a,b in pairs)
    fp=sum(not a and b for a,b in pairs)
    fn=n-tp-tn-fp
    agree=ratio(tp+tn,n)
    expected=ratio((tp+fn)*(tp+fp)+(tn+fp)*(tn+fn), n*n)
    kappa=(agree-expected)/(1-expected) if expected is not None and expected < 1 else None
    return dict(n=n,tp=tp,tn=tn,fp=fp,fn=fn,agreement=agree,kappa=kappa,precision=ratio(tp,tp+fp),recall=ratio(tp,tp+fn))


def read_sheet(path, data):
    with path.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=len(data) or {r["item_id"] for r in rows}!=set(data):
        raise ValueError(f"Unexpected, duplicate or missing IDs in {path.name}")
    annotations={}
    for row in rows:
        i=row["item_id"]
        if any(row[k]!=data[i][k] for k in ("passage","brief")):
            raise ValueError(f"Source or brief changed for {i}")
        if not row["status"]:
            raise ValueError(f"Incomplete review in {path.name} for {i}")
        a=dict(status=row["status"],factuality=row["factuality"],frames=json.loads(row["frames_json"]))
        annotations[i]=validate(a,row["passage"],row["brief"])
    return [annotations[i] for i in data]


def analyze(mode, name):
    if not name or name in (".","..") or "/" in name:
        raise ValueError("Invalid run name")
    path=ROOT/"outputs"/mode/name
    data={r["item_id"]:r for r in json.loads((path/"records.json").read_text()) if r["split"]=="evaluation"}
    directory=ROOT/"data/annotations"/mode/name
    a,b,gold=[read_sheet(directory/f"evaluation_{role}.csv",data) for role in ("reviewer_a","reviewer_b","adjudicated")]
    labels=list(map(primary,gold))
    n=len(data)
    unresolved=labels.count(None)
    positive=labels.count(True)
    categories=Counter()
    for annotation in gold:
        for pair in {(f["direction"],f["relation"]) for f in annotation["frames"]}:
            categories["/".join(pair)]+=1
    metrics=dict(mode=mode,evaluation_n=n,human_scorable=n-unresolved,new_unfavorable=positive,
        rate=ratio(positive,n-unresolved),wilson95=wilson(positive,n-unresolved),
        sensitivity_bounds=[positive/n,(positive+unresolved)/n],briefs_by_framing=dict(categories),
        statuses=dict(Counter(x["status"] for x in gold)),factuality=dict(Counter(x["factuality"] for x in gold)),
        human_agreement=comparison(list(map(primary,a)),list(map(primary,b))),
        llama_or_fixture_vs_human=comparison(labels,[primary(r["judge"]) for r in data.values()]))
    write_json(path/"human_summary.json", metrics)
    print(json.dumps(metrics,indent=2))
    return metrics


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",required=True,choices=["dummy","llama"])
    p.add_argument("--name",default="pilot")
    a=p.parse_args()
    analyze(a.mode,a.name)
