
# Grader critique — iteration 1 (graded from outputs only; transcripts not opened)

## Scores
| case | with_skill | without_skill |
|---|---|---|
| diagnoses-hallucinated-prop | 4/4 | 1/4 |
| picks-acceleration-stack-4090 | 4/4 | 2/4 |
| writes-ref2va-prompt-no-negation | 5/5 | 1/5 |

## Critique of the assertions

**Trivially / weakly discriminating**
- 4090 A3 ("draft tier and final tier with concrete resolution, steps and seed strategy") passed for the baseline too; any competent ComfyUI answer produces two tables. It does not check the values (e.g. 8 steps for the 8-step LoRA, same seed carried from draft to final, 17k+5 frame count), so a wrong-but-concrete tier passes.
- 4090 A4 ("sources are HF or GitHub, none ModelScope/网盘/RunningHub") is a negative check that an answer naming zero concrete files also satisfies; the baseline passed while saying "仓库名/文件名需要你在 HF 搜索核实". Better: require the exact repo+filename for the LoRA and at least one more named HF file.
- ref2va A3 (no negations, positives for patients/music) passed for the baseline even though its prompt is Chinese free-text with no `non_diegetic_music` field; the parenthetical "(empty corridor lock, non_diegetic_music: N/A)" reads as an example, not a requirement. Either make `non_diegetic_music: N/A` a hard requirement or fold the field check into A1. It also does not say whether the skill's whitelisted idioms ("no other garment is substituted", "never transfer facial traits from <Picture 4>") count — the with_skill prompt contains four such phrases and still passed the linter; the assertion should name the whitelist explicitly.
- diagnoses A1 (item invented because no prop reference) is common knowledge; both runs passed. Fine as a floor, but it carries no skill signal.

**Important outcomes with no assertion**
- 4090: nothing checks that CFG stays at 1.0 (the baseline recommended "cfg 4~6" for a no-LoRA final tier, a real error against CFG-distilled weights) or that the shift node is MiniMaxH3SigmaShift (baseline used ModelSamplingSD3 shift ~5). Nothing checks the `length` frame grid (243 for 10 s) or that the pruned-int8 + nvfp4 TE pair is kept rather than swapped for an unverified fp8 file.
- 4090: no assertion checks that the answer tells the user to A/B one variable at a time / run a no-acceleration baseline, which the skill treats as a core practice and the with_skill answer delivered.
- ref2va: no assertion checks `length`/frame alignment (243 = 10.125 s) or that timecodes are strictly increasing with each shot >= 1.2 s; no assertion checks that line breaks are avoided inside detailed_description (baseline prompt has 10 line breaks, each read as a cut). Running `lint_prompt.py` as a hard assertion would cover all of these mechanically and is far more discriminating than A1/A3.
- ref2va: no assertion checks that the prompt only describes things present in the references (with_skill invented a green exit sign and a nurses' station; baseline added a 病历 prop with no image). A "no unreferenced props / anchors" check would catch both.
- diagnoses: no assertion checks that the fix names the prop's reference slot in wiring order (character -> scene -> prop) or that the prop image should be a clean white-background single item without UI frames — both are where real-world runs fail.

**Verifiability**
- Several with_skill numeric claims (693 s first step with Sage+LowVRAM, 134 s draft, 9% sharpness loss, 3090 "合并快 25%") trace to the skill's own references but cannot be verified from outputs; no assertion depends on them, which is right.

## Per-case comparison

**diagnoses-hallucinated-prop**
- with_skill delivers the complete fix: catalog the prop library with `catalog.py build --kind prop`, bind one item, write `the exact item shown in <Picture 4>` + `fully_preserved`, rewrite both negations positively, and overlay the rarity frame in post. All tooling claims verified against the scripts.
- without_skill gets the headline (prop needs a reference image) and sensibly adds a back-view/blocking fix for the jetpack, but keeps negations ("no self-illumination", "nothing on his back"), uses generic "reference image 4" syntax, suggests dropping the scene reference for slot budget (H3 has 9), and never mentions post-production overlay.
- Net: skill adds the CFG-distilled mechanism, the exact H3 prompt grammar, and the post-production split; baseline would send the user back to another round of hallucinated props.

**picks-acceleration-stack-4090**
- with_skill nails the root cause (544p 4-step v0.1 LoRA at 768p) with the exact HF file, keeps 12/3, gives the Sage-via-KJNodes wiring, the LowVRAM incompatibility, bypass-not-delete, two tiers, and a one-variable-at-a-time test plan.
- without_skill misdiagnoses smearing as BlockSparse, never notices the LoRA mismatch, proposes CFG 4-6 and ModelSamplingSD3 shift 5, suggests deleting nodes and swapping the nvfp4 TE for an unverified fp8 file; its generic Windows/VRAM advice is sound but secondary.
- with_skill is over-long (latent upscale pipeline, ecosystem blacklist) for the question; trimming would not cost any assertion.

**writes-ref2va-prompt-no-negation**
- with_skill prompt passes `lint_prompt.py` (0 errors, 0 warnings, 3 shots, 10.125 s), uses the six fields, `<d>[Chinese]` with (S1)/(S2), correct `ref_image_N` = `<Picture N>` wiring, one speaker per shot with the listener's mouth closed, and `non_diegetic_music: N/A`.
- without_skill prompt fails lint (5 errors): Chinese free text, curly quotes, no [Shot N], no field labels, pictures never referenced; it also invents API-style node params (`duration`, `aspect_ratio`, `prompt_optimizer`, a `scene` port) that the ComfyUI node lacks.
- Baseline still got the dramatic structure and positive phrasing right, which is why A3 passed; that is the clearest sign A3 is under-specified.

## Round 2 — splits-60s-script-into-segments, decides-continuation-for-long-shot (graded from outputs only)

| case | with_skill | without_skill |
|---|---|---|
| splits-60s-script-into-segments | 6/6 | 1/6 |
| decides-continuation-for-long-shot | 4/5 | 1/5 |

### Assertion weaknesses

**splits-60s-script-into-segments**
- A5 (dialogue budget) passed for the baseline because the script only has 39 Chinese characters over 60 s; any split satisfies (duration−2)×4.5. The assertion only discriminates on "states the budget rule", and "中文正常语速约 3–4 字/秒" was enough. A harder check: the per-shot budget (每镜 ≤ 18 字, 4 s ≤ 12 字), or a script with one 30+ char line that must be split across shots.
- A1 fixes "5–7 segments" but the skill's own rule is 60 s ÷ 12 s ≈ 5 ± 20% → 4–6; a 4-segment plan at 15 s each would be skill-compliant yet fail. Conversely the 4–15 s per-segment bound is loose: a 15 s dialogue segment is the thing the skill warns against. Consider "no segment > 12 s unless it carries a long walk/monologue".
- A6 is the only mechanically verifiable assertion and it carried all the signal this round. Nothing checks `lint_prompt.py` on the built prompts, the `<Picture N>` wiring order (character → scene → prop), or that voice refs go only to speaking characters — which is exactly where the with_skill run found a real builder bug (build_prompts.py attaches `<Audio N>` for every character).
- No assertion checks fidelity to the script's lines. The baseline rewrote 「上面的人是你爸」 as 「上面的人……是你爸。」 and added terminal periods; the skill says lines are never LLM-rewritten and are checked character by character. A "dialogue text equals the script verbatim" check is cheap and discriminating.
- No assertion checks the 17k+5 frame grid (8/10/12 s → 192/243/294 frames) or that prompt timecodes stay under the effective duration; the with_skill answer got this right and the baseline's "6s/10s 档位 ... 裁掉多余帧" shows it is where baselines go wrong.

**decides-continuation-for-long-shot**
- A1 asks the response to "first check whether the monologue can be broken with a reaction or insert shot", but the user prompt says 「中间不切镜」 explicitly. The with_skill answer named the hard-cut default and dismissed it in one clause without offering an insert shot, which I failed strictly. Either the assertion should accept "names hard-cut default and explains why it is overridden", or the prompt should drop the no-cut constraint so pushing back is clearly the right behaviour. As written it mostly measures willingness to contradict the user.
- A5 is an or-list ("warns about >4 joins / recommends ≥12 steps or a locked audio track, and ≤4 segments"). The baseline passed by recommending a generic external audio track and 2 segments while never mentioning dulling, 12 steps, or the H3 `noise_mask=0` mechanism. Split it: (a) 12 steps or Hard AV / noise_mask=0 for dialogue chains, (b) >4 joins dulling warning. 25 s → 2 segments makes the ≤4 clause trivially true for every answer.
- A2 and A3 are strong and did the discriminating work (baseline 0/2). A4 is also good but could add "does not instruct the user to write negated camera text (`no camera movement, no cut`)" — the baseline's prompt pattern does exactly that.
- No assertion checks frame-grid arithmetic for the chain (311+311−22 = 600 = 25.000 s), which the with_skill run got right and the baseline hand-waved ("多数视频 VAE 要求 4n+1 帧"). No assertion checks the explanation of *why* tail-frame→I2VA is bad for a monologue (loses the `<Audio 1>` timbre slot) — the clearest H3-specific signal in the with_skill answer.
- Nothing checks adherence to the skill's own segment-length guidance for Motion-Context (124–192 frames per segment); the with_skill answer used 311-frame segments. Whether that is a deviation worth penalising is a skill-author call, but it is invisible to the current assertions.

### Per-case comparison

**splits-60s-script-into-segments**
- with_skill produced the full pipeline artefact set: validated `episode.json` (grader re-ran `validate_episode.py` → OK, 6 segments, 60 s), six built prompts that pass lint, media wiring tables, placeholder asset specs, `cues.srt`, and a 10-point rationale that cites the skill rules (one speaker per shot, listener mouth closed, prop bound with its own image, end_state → continuity, hard cuts).
- with_skill also surfaced a real skill defect: `build_prompts.py` attaches a voice reference to every character in a segment, contradicting SKILL step 2; the executor post-processed outside the skill into `prompts_final/`. This should be fixed in the builder (only attach `<Audio N>` for characters with dialogue in the segment).
- without_skill made 10 × 6 s segments, one per beat/line, with no sub-shots, no end_state/continuity, no prop reference, API-style node fields (negative prompt, duration tiers), and silently edited a line of dialogue. Its reasoning ("超过 10 秒后半段容易漂脸") is the generic video-model heuristic the skill exists to override.
- Baseline's only pass (A5) is a property of the input script, not of the answer.
- Minor with_skill slips: counted 「所以……我们……」 as 6 chars (4), and the builder-emitted retention text still carries whitelisted negations ("Do not reuse the reference's background", "never transfer facial traits").

**decides-continuation-for-long-shot**
- with_skill named the right node and exact params (Motion-Context 0.7.1, 22/18, Trim match_tail, Save/Load Latent, LoadLatent never to the decoder), the PrefixStream 39-frame alternative, the Multishot/0.37 and Spectrum warnings, the WhaleTrans seam sentence, 2.4 s no-new-action, 12-step dialogue rule, >4-join dulling, and a complete six-field second-segment prompt. All frame arithmetic verified.
- with_skill's one miss is the A1 "offer an insert shot first" step; it acknowledged the hard-cut default and moved on because the user forbade cuts. It also went beyond the ask (first-frame still + AddGuide, 1280×704, full QC/stitch section), making a long answer longer.
- without_skill is a reasonable generic latent-continuation recipe (cut on a breath, identical sampler settings, pass latents not mp4, Color Match, small test first) and is honest about not knowing parameter names, but it mischaracterises Multishot and WhaleTrans, prefers PrefixStream on a guess, writes negated camera text into the prompt, and guesses a 4n+1 frame rule.
- Baseline's single pass (A5) comes from the or-list wording; its "locked audio track" depends on an a2v mode it cannot confirm and falls back to TTS re-dub + external lip-sync, i.e. not an H3 solution.
