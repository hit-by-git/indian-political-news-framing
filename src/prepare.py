"""Rebuild frozen manifests from reviewed sources, retaining the entire GDELT screening ledger."""
import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data/sources"


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def main():
    raw = ROOT / "data/raw/gdelt_india_political_1500.csv"
    with raw.open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))
    by_url = defaultdict(list)
    for row in records:
        by_url[row["SOURCEURL"]].append(row)
    reviewed = read_lines(SOURCES / "verified_excerpts.jsonl")
    attempted = json.loads((SOURCES / "retrieval_status.json").read_text())
    rng = random.Random(20261125)
    ids = sorted(row["event_id"] for row in reviewed)
    if len(set(ids)) != len(ids) or len(set(x["source_url"] for x in reviewed)) != len(ids):
        raise ValueError("Duplicate story or source in selection")
    calibration = set(rng.sample(ids, 10))
    passages = set()
    selected = {}
    dataset = []
    for item in sorted(reviewed, key=lambda x: x["event_id"]):
        url = item["source_url"]
        matches = [r for r in by_url[url] if r["GLOBALEVENTID"] == item["event_id"]]
        passage = item["passage"].strip()
        if not matches or url not in attempted or not 10 <= len(passage.split()) <= 25 or passage.casefold() in passages:
            raise ValueError(f"Invalid source linkage, length, or duplicate for {url}")
        if any(tag in passage for tag in ("【", "<script", "Click here", "Subscribe now")):
            raise ValueError(f"Page markup in {url}")
        passages.add(passage.casefold())
        selected[url] = item["event_id"]
        dataset.append(dict(story_id="gdelt-" + item["event_id"], source_url=url,
                            gdelt_ids=[r["GLOBALEVENTID"] for r in by_url[url]],
                            publisher_domain=urlparse(url).hostname, passage=passage,
                            passage_sha256=digest(passage), split="calibration" if item["event_id"] in calibration else "evaluation"))
    with (SOURCES / "stories.jsonl").open("w", encoding="utf-8") as out:
        for story in dataset:
            print(json.dumps(story, ensure_ascii=False), file=out)
    with (SOURCES / "screening.csv").open("w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["gdelt_id", "url", "disposition"])
        for row in records:
            url = row["SOURCEURL"]
            disposition = attempted.get(url, "outside_publisher_and_topic_shortlist")
            if url in selected:
                disposition = "selected" if row["GLOBALEVENTID"] == selected[url] else "duplicate_url_of_selection"
            writer.writerow([row["GLOBALEVENTID"], url, disposition])
    write_json(SOURCES / "dataset_summary.json", dict(raw_rows=len(records), distinct_urls=len(by_url),
               shortlisted_urls=len(attempted), opened_urls=sum(v.startswith("opened") for v in attempted.values()),
               selected=len(dataset), evaluation=len(dataset)-len(calibration), calibration=len(calibration),
               publisher_domains=len({x["publisher_domain"] for x in dataset}),
               words_min=min(len(x["passage"].split()) for x in dataset),
               words_max=max(len(x["passage"].split()) for x in dataset),
               manifest_sha256=hashlib.sha256((SOURCES / "stories.jsonl").read_bytes()).hexdigest()))


if __name__ == "__main__":
    main()
