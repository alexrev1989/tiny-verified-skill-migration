# Reproduction artifacts

This directory preserves the frozen evidence for the paper's formal evaluation. The reported experiment used every row in a preregistered 1,074-question structural subset of the LC-QuAD 2.0 official TEST split. It is **not** a full LC-QuAD 2.0 QA benchmark result.

## Contents

- `formal_test/RESULT.json` — frozen integrated result from TinyLearner v1.56.2.
- `formal_test/STATISTICAL_ANALYSIS.json` — paired bootstrap, McNemar, and Wilson-interval results.
- `formal_test/BASELINE_END_TO_END_TRACES.jsonl` — baseline per-question traces.
- `formal_test/LEARNED_END_TO_END_TRACES.jsonl` — learned-system per-question traces.
- `formal_test/SCRIPT_SNAPSHOT.py` — the executed formal-test script snapshot.
- `provenance/MANIFEST_SHA256.json` — unchanged SHA-256 manifest from the final publication archive.

The source-package manifest uses paths and filenames from the original final archive. Files in `formal_test/` were renamed only to provide a clean public repository layout; their bytes were not changed.

## Frozen-evaluation notice

The formal LC-QuAD 2.0 TEST result is complete and frozen. Do not use the test split for new threshold tuning, prompt optimization, model selection, checkpoint selection, or rescue runs.
