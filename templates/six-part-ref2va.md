```
subject_definitions: <Subject 1> is {NAME_A}, the person in <Picture 1> and <Picture 2>, {IDENTITY_PHRASE_A}. <Subject 2> is {NAME_B}, the person in <Picture 3>, {IDENTITY_PHRASE_B}. <Subject 3> is {SCENE_NAME} in <Picture 4>: {SCENE_DESCRIPTION}. <Audio 1> is the voice-timbre reference for <Subject 1> (S1).

summary: [reference generation + audio reference] {ONE_SENTENCE_PLOT}. {N} shots, {DURATION} seconds, 9:16.

retention_analysis: <Subject 1> (appears in [Shot 1], [Shot 3]): fully_preserved - face, hair, build and outfit are retained from <Picture 1>; <Picture 2> controls outfit and silhouette only. <Subject 2> (appears in [Shot 2], [Shot 3]): fully_preserved - face, beard and coat are retained. <Subject 3>: partially_preserved - layout, lighting and set dressing are retained; never transfer facial traits from <Picture 4>. <Audio 1>: reference - timbre only; do not carry its original words into the video. Do not reuse any reference's background.

detailed_description: {STYLE}. The setting is <Subject 3>. {CONTINUITY_FROM_PREVIOUS_SEGMENT} [Shot 1] {FRAMING}: <Subject 1> {ACTION}. {CAMERA}. <Subject 1>, {VOICE_PHRASE_A} (S1), says {DELIVERY}: <d>[Chinese] {LINE_1}</d> [Shot 2] At 00:05.000, the shot cuts to {FRAMING_2}: <Subject 2> steps in from frame right, {ACTION_2}; <Subject 1> listens with her mouth closed. {CAMERA_2}. <Subject 2>, {VOICE_PHRASE_B} (S2), says: <d>[Chinese] {LINE_2}</d> [Shot 3] At 00:10.000, an over-the-shoulder shot from behind <Subject 2>, who stands at frame right, a head taller; <Subject 1> faces the camera from frame left. {ACTION_3}. The segment ends with {END_STATE}. No other people, no signage text, no subtitles.

overall_soundscape: {…}

non_diegetic_music: N/A
```

content 顺序必须与 `<Picture N>` 编号一致：`[text, img(ref) ×4, audio(ref)]`。参考总数 ≤ 12，前 5 张图免费。
