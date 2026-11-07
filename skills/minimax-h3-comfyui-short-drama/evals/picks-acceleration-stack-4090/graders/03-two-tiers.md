---
type: llm
focus: trace
weight: 1
---

The response gives a draft tier and a final tier with concrete resolution, step count and seed strategy for each, keeps CFG at 1.0 in both (the open weights are CFG-distilled), and uses MiniMaxH3SigmaShift (not ModelSamplingSD3 or another model's shift node) for the shift setting.
