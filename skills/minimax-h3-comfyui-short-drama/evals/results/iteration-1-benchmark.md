# Skill Benchmark: minimax-h3-comfyui-short-drama

**Model**: <model-name>
**Date**: 2026-11-07T20:33:38Z
**Evals**: decides-continuation-for-long-shot, diagnoses-hallucinated-prop, picks-acceleration-stack-4090, splits-60s-script-into-segments, writes-ref2va-prompt-no-negation (1 run each per configuration)

## Summary

| Metric | With Skill | Without Skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 96% ± 9% | 26% ± 14% | +0.70 |
| Time | 309.8s ± 235.4s | 133.1s ± 47.6s | +176.6s |
| Tokens | 127098 ± 28866 | 77448 ± 3144 | +49650 |
## Iteration 2 (after script fixes) — splits-60s-script-into-segments, with_skill only

Re-run with the fixed builder (voice refs only for speakers, stable Subject numbering, style propagation). Raw `build_prompts.py` output used without post-processing: 6 segments (10/8/10/12/12/10 s), one speaker per shot, ≤2 speakers per segment, every segment with end_state, the photo modelled as two prop states, no `<Audio N>` in the three no-dialogue segments and exactly two in the two-speaker segment; `validate_episode.py` OK and `lint_prompt.py` PASS (0 errors / 0 warnings) on all six prompts. Remaining known limitation: `cues.srt` timings are an even spread and must be re-timed with whisper before burn-in.
