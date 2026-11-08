# Iteration 3 — regression on the final skill (with_skill only)

Run after the consistency audit, the reference restructure and all long-tail/fresh-repo merges, to check nothing regressed. Graders are the tightened ones from iteration 1.

| Case | Passed | Notes |
|------|--------|-------|
| writes-ref2va-prompt-no-negation | 7/7 | lint 0 errors / 0 warnings; no invented scene anchors; states `length` 243 = 10.125 s; Autogrow API key note |
| picks-acceleration-stack-4090 | 4/4 | half the length of iteration 1; benchmarks labelled 单机实测 with 口径; Ref2V shift 12/3; Sage never with LowVRAM |
| diagnoses-hallucinated-prop | 4/4 | demonstrated catalog → validate → lint on a mock library |

**Total 15/15.** The acceleration run hit an API rate limit only after writing its complete answer, so its timing was not captured.

## Defects found by this round and fixed
- `catalog.py` generic-item detection only matched Chinese wording; now also catches English (`red precious item`, `golden loot`, …).
- `build_prompts.py` emitted two negations of its own (`Do not reuse the reference's background.`, `…are not carried into the video.`); both rewritten as positive sentences.
- `lint_prompt.py` now also scans `subject_definitions` / `retention_analysis` for negations and whitelists the official `never transfer facial traits` idiom.
