"""Run the real pipeline with known outputs, then check labels, resume and human analysis."""
import csv
import json
from analyze import analyze
from prepare import ROOT, write_json
from run import run
from rubric import primary, validate


def check(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    name="fixture_v1"
    run("dummy", "", None, name)
    folder=ROOT/"outputs/dummy"/name
    before=(folder/"records.json").read_bytes()
    run("dummy", "", None, name)
    check(before==(folder/"records.json").read_bytes(), "Resume changed output")
    records=json.loads(before)
    expected=[False, True, False, False, False, None, None]
    for i,r in enumerate(records):
        check(primary(r["judge"])==expected[i%7], "Incorrect primary result")
        check(bool(r["judge_error"])==(i%7==6), "Malformed judge was not isolated")
    try:
        validate({"status":"scorable","factuality":"consistent","frames":[dict(target="official",direction="unfavorable",
                 relation="new",source_quote="missing evidence",output_quote="invalid")]}, "Source", "Brief")
    except ValueError:
        pass
    else:
        raise RuntimeError("Fabricated evidence span accepted")
    packet=ROOT/"data/annotations/dummy"/name
    ids={r["item_id"]:r for r in records}
    for role in ("reviewer_a","reviewer_b","adjudicated"):
        path=packet/f"evaluation_{role}.csv"
        with path.open(newline="") as f:
            reader=csv.DictReader(f)
            fields=reader.fieldnames
            rows=list(reader)
        for row in rows:
            a=ids[row["item_id"]]["judge"] or dict(status="scorable",factuality="consistent",frames=[])
            row.update(status=a["status"], factuality=a["factuality"],frames_json=json.dumps(a["frames"],ensure_ascii=False))
        with path.open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    m=analyze("dummy",name)
    check(m["evaluation_n"]==40 and m["human_agreement"]["agreement"]==1,"Review export or analysis failed")
    positive=sum(i%7==1 and r["split"]=="evaluation" for i,r in enumerate(records))
    check(m["new_unfavorable"]==positive,"Human rate disagrees with fixture specification")
    write_json(folder/"smoke_checks.json",dict(status="pass",records_checked=len(records),evaluation_checked=40,
        known_classes_checked=7,resume_identical=True,invalid_evidence_rejected=True,
        invalid_judge_retained=True,expected_primary_count=positive,actual_primary_count=m["new_unfavorable"],
        human_annotations="simulated solely for software validation",cuda_llama_tested=False))
    print("Smoke checks passed")


if __name__=="__main__":
    main()
