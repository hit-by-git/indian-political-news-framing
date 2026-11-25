# Source framing study

Run the Kaggle notebook in `notebooks/source_framing_kaggle.ipynb` with the study attached as a private dataset. The [Kaggle guide](docs/kaggle_guide.md) covers model access, reviewer instructions and output recovery. The [validation report](docs/smoke_test.md) records the dummy run.

The ready model inputs are `data/sources/stories.jsonl`. Regenerate them with `python src/prepare.py`. Run `python src/smoke.py` to test the full fixture workflow. Use `python src/run.py --mode llama --name pilot` for a real GPU run, then `python src/analyze.py --mode llama --name pilot` after human annotation. All commands run from the study root.

## Run from GitHub on Kaggle

Import the notebook from this repository's `notebooks/source_framing_kaggle.ipynb`. With internet enabled, run this in a new first cell of a fresh Kaggle session:

```python
!git clone --depth 1 https://github.com/hit-by-git/indian-political-news-framing.git /kaggle/working/source_framing_study
```

The notebook recognizes this checkout and writes results under its `outputs/` directory. No separate study dataset upload is required.
