# Tools

Scripts that operate on the catalog data. None of these are part of the build itself — they're audit and verification utilities.

## `verify.py`

Tier 1 mechanical scanner. Checks JSON validity, schema completeness, field-length sanity, confidence-flag distribution, AI-tone markers, primary-sources format, and repeated phrasing across entries.

It does **not** verify facts. Hallucination detection requires either a cross-model second pass (Tier 3) or human verification against authoritative sources (Tier 4).

### Run it

```
python3 tools/verify.py jsonl/batch_*.jsonl
```

Or against a sample:

```
python3 tools/verify.py jsonl/batch_01.jsonl jsonl/batch_22.jsonl jsonl/batch_44.jsonl
```

Output is a printed report. No external dependencies; pure standard library.

### Baseline (50-entry sample, May 2026)

- Parse errors: 0
- Schema completeness issues: 0
- AI-tone hits: minimal (~6% of entries contain any flagged marker)
- Confidence flag distribution: `originators_confidence` 100% high, others 96% high — flagged as suspiciously uniform; calibration audit pending in pass III
- Extended summary length: 0/50 within methodology range of 500–800 chars (median 1018; bloated rather than wrong)

Re-run after pass III edits to confirm the bloat is reduced and confidence distribution looks more credible.
