---
type: llm
focus: trace
weight: 1
---

The response explicitly mentions audio dulling after more than 4 joins AND recommends either >=12 steps for dialogue segments or locking the audio track (noise_mask=0 / external track), and keeps the chain at <=4 segments with each segment within the reference's 124-192 frame guidance (never above 328 frames).
