# Pilot validation

The deterministic run processed 50 frozen source records. The 10 calibration records stayed separate from the 40 evaluation records. Each story received one brief and one judge record. The two separate reviewer packets and adjudication packet carried the same opaque IDs, passages and briefs.

| Software check | Expected | Observed |
|---|---:|---:|
| Evaluation records | 40 | 40 |
| New unfavorable flags on evaluation fixtures | 6 | 6 |
| Deliberate malformed judge responses on evaluation fixtures | 6 | 6 |
| Scorable automated evaluation responses after refusals and invalid outputs | 28 | 28 |
| Changed consolidated outputs after resume | 0 | 0 |

A faithful repetition, new negative interpretation, new favorable interpretation, strengthened frame, factual addition, refusal and invalid judgment exercised seven paths. Evidence validation rejected an invented quotation. The synthetic reviewer sheets exercised adjudication, scoring, confidence intervals and denominator handling. They were built from the fixture contract and cannot estimate human agreement in practice. Inspect the saved check file and records under `outputs/dummy/fixture_v1/`.

The test exercised storage and scoring on CPU. GPU model loading, quantized generation, actual Llama judge behavior and independent human annotation still require the study run.
