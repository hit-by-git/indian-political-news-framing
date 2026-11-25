"""Generate, judge and export annotation sheets; restart safely after notebook interruption."""
import argparse
import csv
import hashlib
import json
import random
from importlib.metadata import version
from pathlib import Path
from prepare import ROOT, SOURCES, digest, read_lines, write_json
from inference import Fixture, Llama
from rubric import validate, BRIEF_PROMPT, JUDGE_PROMPT, primary

SHEET = ["item_id", "passage", "brief", "status", "factuality", "frames_json"]


def protected_csv(path, rows):
    if path.exists():  # retain completed human work
        return
    temp = path.with_suffix(".tmp")
    with temp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SHEET)
        w.writeheader()
        w.writerows(rows)
    temp.replace(path)


def run(mode, model, revision, name):
    if Path(name).name != name or name in ("", ".", ".."):
        raise ValueError("Use a simple run name")
    path = ROOT / "outputs" / mode / name
    path.mkdir(parents=True, exist_ok=True)
    stories = read_lines(SOURCES / "stories.jsonl")
    data_hash = hashlib.sha256((SOURCES / "stories.jsonl").read_bytes()).hexdigest()
    if data_hash != json.loads((SOURCES / "dataset_summary.json").read_text())["manifest_sha256"]:
        raise ValueError("Dataset differs from the frozen manifest")
    settings = dict(mode=mode, model=model if mode == "llama" else "deterministic-fixture", revision=revision,
        dataset=data_hash, brief_prompt=BRIEF_PROMPT, judge_prompt=JUDGE_PROMPT,
        code={f: digest((ROOT/"src"/f).read_text()) for f in ("inference.py","rubric.py","run.py")},
        decoding="greedy", max_new_tokens={"brief":110,"judge":400})
    if mode == "llama":
        import torch
        from huggingface_hub import HfApi
        if torch.cuda.device_count() < 2:
            raise RuntimeError("Select GPU T4 x2 in Kaggle. This FP16 run requires two visible CUDA GPUs.")
        if not Path(model).is_dir():
            revision = HfApi().model_info(model, revision=revision).sha
        elif not revision:
            raise ValueError("For mounted weights supply --revision with the checkpoint version")
        settings.update(revision=revision, gpus=[torch.cuda.get_device_name(i) for i in (0,1)], dtype="float16", quantization=None, device_map="balanced",
                        packages={k:version(k) for k in ("torch","transformers","accelerate")})
    manifest = path / "run.json"
    if manifest.exists() and json.loads(manifest.read_text()) != settings:
        raise ValueError("Run configuration changed. Choose a fresh run name.")
    write_json(manifest, settings)
    model_runner = None
    records = []
    for index, s in enumerate(stories):
        folder = path / "records" / s["story_id"]
        response, judged = folder/"brief.json", folder/"judge.json"
        if not (response.exists() and judged.exists()) and model_runner is None:
            model_runner = Fixture() if mode == "dummy" else Llama(model, revision)
            if mode == "llama":
                write_json(path/"device_map.json", model_runner.device_map)
        if not response.exists():
            brief, capped = model_runner.brief(s["passage"], index)
            write_json(response, dict(story_id=s["story_id"], brief=brief, at_token_limit=capped))
        record = json.loads(response.read_text())
        brief = record["brief"]
        if not judged.exists():
            raw, limited = model_runner.judge(s["passage"], brief, index)
            try:
                if not brief or limited:
                    raise ValueError("Empty brief or judge output reached limit")
                a = validate(json.loads(raw), s["passage"], brief)
                error = None
            except (ValueError, TypeError) as exc:
                a, error = None, str(exc)
            write_json(judged, dict(raw=raw, annotation=a, validation_error=error, at_token_limit=limited))
        j = json.loads(judged.read_text())
        records.append(dict(**s, brief=brief, brief_at_token_limit=record["at_token_limit"],
            item_id=digest(name+"|"+s["story_id"])[:16], judge=j["annotation"], judge_error=j["validation_error"]))
    write_json(path/"records.json", records)
    packets = ROOT/"data/annotations"/mode/name
    packets.mkdir(parents=True, exist_ok=True)
    for split in ("calibration","evaluation"):
        rows = [dict(item_id=r["item_id"], passage=r["passage"], brief=r["brief"], status="", factuality="", frames_json="") for r in records if r["split"]==split]
        for n, role in enumerate(("reviewer_a","reviewer_b","adjudicated")):
            shuffled=rows.copy()
            random.Random(121+n).shuffle(shuffled)
            protected_csv(packets/f"{split}_{role}.csv", shuffled)
    summary = {}
    for split in ("calibration","evaluation"):
        rows=[r for r in records if r["split"]==split]
        labels=[primary(r["judge"]) for r in rows]
        summary[split]=dict(n=len(rows), automatic_new_unfavorable=labels.count(True), automatic_scorable=len(rows)-labels.count(None),
                            judge_invalid=sum(r["judge_error"] is not None for r in rows),
                            brief_at_token_limit=sum(r["brief_at_token_limit"] for r in rows))
    write_json(path/"automatic_summary.json", summary)
    print(path, json.dumps(summary))


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=["dummy","llama"], required=True)
    p.add_argument("--name",default="pilot")
    p.add_argument("--model",default="meta-llama/Llama-3.1-8B-Instruct")
    p.add_argument("--revision",default=None)
    args=p.parse_args()
    run(args.mode,args.model,args.revision,args.name)
