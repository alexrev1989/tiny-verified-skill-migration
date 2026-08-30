# Tiny Verified Skill Migration — Paper & Reproduction Artifacts v1.0

Version 1.0.0 is the initial public research release of **Tiny: Verified Skill Migration for Reducing LLM Fallbacks in Neuro-Symbolic Question Answering** by Alexander Revyakin.

## Included

- Final author paper and LaTeX source
- Formal LC-QuAD 2.0 structural TEST result
- Paired baseline and learned end-to-end traces
- Statistical analysis
- Executed TinyLearner v1.56.2 test-script snapshot
- Anonymous ICLR manuscript package
- Clean arXiv source package
- SHA-256 provenance manifest

## Formal result

The evaluation covers a preregistered 1,074-question structural subset of the LC-QuAD 2.0 official TEST split. It is **not** a full LC-QuAD 2.0 QA benchmark result.

- **207 real Qwen calls saved**
- Calls per question: **1.130 → 0.938**
- Relative reduction in calls per question: **approximately 17.1%**
- Learned zero-call coverage: **34.64%**
- Learned zero-call precision: **96.51%**
- Exact pair accuracy: **63.59% → 65.64%**

The accuracy point estimate is positive, but its paired confidence interval includes zero and McNemar p = 0.107. This release does not claim a statistically significant accuracy improvement.

## Suggested release assets

1. `tiny_verified_skill_migration_Alexander_Revyakin.pdf`
2. `Tiny_Verified_Skill_Migration_FINAL_Alexander_Revyakin.zip`

Zenodo DOI and arXiv metadata will be added only after the corresponding services issue real identifiers.
