# Running the source framing pilot on Kaggle

## Start the run

1. Create a private Kaggle Dataset from the contents of the supplied ZIP or attach the ZIP as a file. Import the supplied notebook into Kaggle and attach that Dataset. The first cell locates the archive or extracted directory and copies the study into the writable working directory. Start with one GPU.
2. For the default model download, enable notebook internet, accept Meta's model terms on Hugging Face, and grant the notebook access to a Kaggle Secret named `HF_TOKEN` from that authorized account. Another option is to attach an authorized Hugging Face-format copy of the Llama 3.1 8B Instruct checkpoint, set `MODEL` to its config directory and set `REVISION` to its version in the notebook. Internet or mounted wheels are required to install any missing pinned dependencies. No GPT-4 API calls are made.
3. Run the setup, dataset checks and dummy cells first. These need no GPU or model weights. Use the final inference cell for real Llama generation and judging. The script uses one GPU, batch size one, 4-bit NF4 weights, FP16 computation and one loaded model for both tasks. Each request has a fresh context. GPU availability and compatibility depend on the assigned Kaggle image.
4. Inspect `outputs/llama/pilot/automatic_summary.json`, including invalid judge outputs. Human review packets are under `data/annotations/llama/pilot/`. Use Kaggle **Save Version** to retain the workspace outputs. The final notebook cell writes a ZIP containing both records and reviewer sheets. Download or attach that ZIP as input for the next session. It contains no model weights or token. If a session ends before export, only saved files can be recovered.
5. To resume a saved run, attach its result archive and set `RESTORE` in the first cell before executing it on a fresh working directory. Record files are committed separately after each generation and judgment. The same settings reuse completed records. Changed code, model revision or configuration needs a different run name.

## Human annotation

Use the 10 calibration stories to practice before either reviewer scores the 40 evaluation stories. Give each reviewer only their own CSV. Hide the automated scores. Keep item ID, passage and brief untouched. Enter status (`scorable`, `refusal`, `unclear`), factuality (`consistent`, `unsupported_addition`, `contradiction`, `unclear`), and a JSON list in `frames_json`. A neutral scorable brief uses `[]`. A refusal or unclear item also uses `[]`. Factuality and framing are separate decisions.

Example using a hypothetical source “The council approved repairs.” and a brief “The council approved repairs in a cynical bid for votes.”:

```json
[{"target":"council","direction":"unfavorable","relation":"new","source_quote":"The council approved repairs.","output_quote":"a cynical bid for votes"}]
```

Use `favorable` or `unfavorable` for direction. Use `new`, `strengthened` or `preserved` for the relationship to the source. Dropping attribution can strengthen a claim. A report of a negative event alone does not establish negative stance. Judge what the supplied source supports and use literal evidence from both texts. Preserve the two independent sheets. Complete the adjudicated sheet after resolving disagreements while blinded to Llama. Leave genuinely unresolved items as `unclear`.

Place the three completed evaluation sheets in the run's annotations directory, using the supplied filenames. The notebook has an optional cell to import reviewed sheets from an attached private Dataset and run the human analysis. It validates the IDs, source text, labels and evidence spans before writing `human_summary.json`. Null values mean an undefined metric. The automated summary remains separate. Do not publish fixture statistics as model results.

## Data and interpretation

The shipped sample uses 50 manually selected, verified short English excerpts from 11 publisher domains. Each passage has 12–25 words. Selection began with the GDELT URLs, followed by an English political/civic topic and publisher shortlist, publisher-page inspection, exclusion of irrelevant, inaccessible or unusable material, and sentence selection. One passage was retained per selected URL. Related policy issues and national political actors can recur. Selection was purposive, not a random sample of Indian news. Only the calibration/evaluation assignment uses a seeded draw.

Each source row retains its URL, GDELT IDs, domain, passage, hash and split. `screening.csv` covers every original row. Outside-shortlist rows were not individually publisher-verified. The retrieval ledger records opening a page separately from accepting its content. A short excerpt may omit attribution or background elsewhere in the article. “Unsupported” means unsupported by exactly the supplied excerpt. The pilot tests brief expansion from short passages. A full-article summarization experiment needs a separately frozen dataset.

## Output map

| Path under study root | Contents |
|---|---|
| `data/sources/stories.jsonl` | Ready-to-use model inputs |
| `data/sources/dataset_summary.json` | Screening counts and frozen manifest hash |
| `outputs/{dummy,llama}/RUN/run.json` | Model or fixture identity, prompts, code and data fingerprints |
| `outputs/{dummy,llama}/RUN/records/STORY/` | Resumable response and raw judge output with validation status |
| `outputs/{dummy,llama}/RUN/records.json` | Consolidated source, brief, judge annotation and linkage |
| `data/annotations/{dummy,llama}/RUN/` | Calibration and evaluation packets for both reviewers and adjudicator |
| `outputs/{dummy,llama}/RUN/human_summary.json` | Adjudicated rates, interval, status counts and judge comparisons |
| `outputs/dummy/fixture_v1/smoke_checks.json` | Known-answer validation, including deliberate malformed outputs |

The deterministic run checks the pipeline contract. Its “human” sheets are synthetic fixtures. A live CUDA run, language quality assessment and independent human annotation are separate steps.
