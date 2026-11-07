
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
