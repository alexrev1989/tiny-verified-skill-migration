# Tiny: Verified Skill Migration

**Alexander Revyakin**

> Facts stay external; skills migrate inward.

[Paper PDF](paper/tiny_verified_skill_migration_Alexander_Revyakin.pdf) · [Project page](https://alexrev1989.github.io/tiny-verified-skill-migration/) · [Reproduction artifacts](experiments/) · [Formal results](experiments/formal_test/RESULT.json) · [Latest release](https://github.com/alexrev1989/tiny-verified-skill-migration/releases/latest) · **DOI:** pending Zenodo deposit · **arXiv:** pending submission

## What is Tiny?

Tiny investigates a neuro-symbolic learning pattern in which authoritative factual knowledge remains external and inspectable, while procedural capabilities can migrate from verified LLM fallback experience into compact local models.

The lifecycle is deliberately conservative:

```text
UNKNOWN
   ↓
FALLBACK TO LLM
   ↓
INDEPENDENT OUTCOME VERIFICATION
   ↓
STORE VERIFIED TRACE
   ↓
TRAIN COMPACT SKILL
   ↓
RETEST UNDER FROZEN COMPETENCE GATE
   ↓
PROMOTE
   ↓
FUTURE LLM FALLBACK RATE ↓
```

> **Facts stay external; skills migrate inward.**

The large model is a proposer rather than a factual authority. A fallback outcome enters the learning buffer only after independent verification. Learned components handle procedural decisions; deterministic knowledge-graph access remains the authoritative route to factual values.

## Formal evaluation

**Dataset:** LC-QuAD 2.0 official TEST.

**This is not a full LC-QuAD 2.0 QA benchmark result.** It is a preregistered structural subset of **1,074 questions**, containing every row that matched frozen structural criteria.

| Metric | Baseline | Learned |
|---|---:|---:|
| Real Qwen calls | 1,214 | 1,007 |
| Calls / question | 1.130 | 0.938 |
| Entity hybrid accuracy | 72.53% | 74.02% |
| Property PID accuracy | 66.57% | 68.99% |
| Exact (entity, property) accuracy | 63.59% | 65.64% |
| Zero-call coverage | 25.98% | 34.64% |
| Zero-call precision | 93.91% | 96.51% |

The learned system saved **207 real Qwen calls**. Calls per question decreased from **1.130 to 0.938**, a relative reduction of approximately **17.1%**. The paired bootstrap 95% confidence interval for the absolute reduction in calls per question is **[0.153, 0.233]**.

The accuracy point estimate is positive, but the paired confidence interval includes zero and McNemar p = 0.107. We therefore do **not** claim a statistically significant accuracy improvement.

> Verified Skill Migration substantially reduces real LLM fallback usage and expands a high-precision autonomous region, without evidence that the frozen accuracy non-inferiority requirement is violated.

## Skill migration results

| Skill | Result |
|---|---|
| Entity linking | PASS |
| Property mapping | PASS |
| Relation directionality | FAIL / not promoted |
| Answer-type prediction | FAIL / not promoted |

The negative results are retained intentionally. Tiny does not assume that every skill can be transferred from an LLM; candidates must pass frozen viability and competence criteria before promotion.

## Scope and relation to prior work

Tiny is related to work on cascades, routing, learning from escalations, verified teacher learning, and procedural skill memory, including Cache & Distil, RouteLLM, RouteNLP, MERA, OVCSD, and Anything2Skill. It does not claim to originate those individual ideas.

> Tiny studies the combined design point of external factual authority, outcome verification before learning, modular procedural skill migration, frozen competence gates, and measured displacement of future strong-model calls in a neuro-symbolic QA pipeline.

## Reproducibility

The formal result is frozen. The repository includes the executed test-script snapshot, paired baseline and learned traces, statistical analysis, the formal result, and the original publication-package manifest.

- [Formal test result](experiments/formal_test/RESULT.json)
- [Statistical analysis](experiments/formal_test/STATISTICAL_ANALYSIS.json)
- [Baseline traces](experiments/formal_test/BASELINE_END_TO_END_TRACES.jsonl)
- [Learned traces](experiments/formal_test/LEARNED_END_TO_END_TRACES.jsonl)
- [Executed script snapshot](experiments/formal_test/SCRIPT_SNAPSHOT.py)
- [Source-package SHA-256 manifest](experiments/provenance/MANIFEST_SHA256.json)

Do not rerun or tune against the LC-QuAD 2.0 TEST split. The included artifacts document the completed frozen evaluation; they are not an invitation to select new thresholds, prompts, checkpoints, or models on the test result.

## Paper and submission packages

- `paper/` contains the signed author PDF, LaTeX source, bibliography, and compiled bibliography.
- `submission/arxiv/` contains the minimal arXiv source package and upload instructions.
- `submission/ICLR_anonymous/` preserves the anonymous manuscript package. Before an ICLR submission, it must be ported to the official ICLR 2027 style and rechecked against the current page-limit and double-blind requirements.
- `submission/notes/` preserves final readiness, metadata, literature-verification, and conference-requirement notes.

## Citation

Citation metadata is provided in [`CITATION.cff`](CITATION.cff). A Zenodo DOI and arXiv identifier will be added only after those services issue real identifiers.

## Licensing

Original code and project infrastructure are licensed under [Apache-2.0](LICENSE). The article is licensed separately under [CC BY 4.0](paper/LICENSE.md). See [`LICENSES.md`](LICENSES.md) for scope and third-party exclusions; this repository does not relicense LC-QuAD 2.0, Wikidata, Qwen models, or other third-party datasets, models, and publications.

## Publication status

Version `1.0.0` is prepared for publication at [github.com/alexrev1989/tiny-verified-skill-migration](https://github.com/alexrev1989/tiny-verified-skill-migration). GitHub Pages and the GitHub Release will be activated with the first public release. A Zenodo DOI and arXiv record remain pending until those services issue real identifiers.
