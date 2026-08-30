# Final submission metadata

Title: Tiny: Verified Skill Migration for Reducing LLM Fallbacks in Neuro-Symbolic Question Answering

Author: Alexander Revyakin

Suggested arXiv primary category: cs.AI
Possible cross-lists: cs.CL, cs.LG

Abstract:
Large language model (LLM) cascades reduce inference cost by routing easy requests to smaller models, and distillation can further improve those models over time. We study a stricter neuro-symbolic variant: declarative facts remain external and replaceable, while only procedural skills migrate into learned parameters. We call this process verified skill migration (VSM). A compact local model attempts a procedural subtask, a frozen competence gate escalates uncertain cases to an LLM, and the LLM outcome becomes a training trace only after independent verification using withheld ground truth or deterministic knowledge-graph evidence. We instantiate VSM for Wikidata QA with entity linking and property mapping as migratable skills and a pinned local Wikidata snapshot as factual authority. Two skills successfully migrate, while two preregistered candidates—relation directionality and answer-type prediction—fail teacher-viability criteria and are not trained. In a fresh integrated development evaluation, the learned system saves 53 real Qwen2.5-3B calls over 351 questions and raises exact ({entity,{property) accuracy from 34.47% to 44.16%. On a preregistered structural subset of the previously unopened official LC-QuAD 2.0 test split (1,074 questions), VSM reduces real teacher calls from 1,214 to 1,007, or 1.130 to 0.938 calls/question. The paired bootstrap 95% CI for the call reduction is [0.153,0.233] calls/question. Zero-call coverage rises from 25.98% to 34.64% while zero-call precision reaches 96.51% (Wilson 95% CI [94.11,97.95]). Exact pair accuracy has a positive point estimate, 63.59% to 65.64%, but its paired 95% bootstrap CI for the difference ([-0.28,4.47] percentage points) includes zero. These results support VSM as a conservative mechanism for reducing dependence on a large model without making learned weights the authoritative store of factual knowledge.

ICLR 2027: use the anonymous manuscript and official 2027 style files.
