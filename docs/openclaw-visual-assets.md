# OpenClaw Visual Asset Skills

Use this when OpenClaw creates cover images, YouTube thumbnails, or Dreamina/Seedance loop videos for this repo.

The visual rules are channel-specific. Do not apply one channel's visual signature to every release. The source of truth for production work is now [openclaw-channel-profiles](openclaw-channel-profiles/README.md). OpenClaw should run `scripts/openclaw-release channel-profile` first, then read the returned `profile_doc`.

## Shared Asset Contract

- Create static cover and thumbnail images with OpenAI GPT Image models, not Dreamina.
- Prefer `gpt-image-2` when available; otherwise use the best available GPT Image model in the current environment.
- Use Dreamina/Seedance only for the moving loop video.
- Always create a final clean 16:9 cover first.
- Create the YouTube thumbnail from that final cover as an image-to-image edit/reference derivative, not as a fresh unrelated scene.
- Keep cover, thumbnail, and loop video visually continuous: same subject count, subject placement, silhouettes, clothing colors, props, background landmarks, lighting, palette, and camera angle.
- The thumbnail is the click image and should contain short readable text plus channel branding.
- The cover is the playback visual and Dreamina/Seedance first-frame reference. It must include only a large, readable lower-left selected-channel-name brand label. Match the visual scale of the channel-brand line used on the YouTube thumbnail. Target roughly 18-24% of the image width, or about 5-6% of image height for text cap height. On a 2048x1152 cover, `Soft Hour Radio` should be roughly 360-500 px wide with clearly readable letter height.
- Do not use the text thumbnail as the Dreamina first-frame reference.
- The cover/first-frame channel brand label is mandatory for every channel. Do not add title text, genre text, duration text, lyrics, subtitles, UI, logos, or unrelated words.
- The Dreamina/Seedance loop video must preserve the exact lower-left channel label for the full clip. Reject/regenerate if it disappears, flickers, moves, morphs, changes spelling, changes style drastically, or becomes unreadable.
- The thumbnail should use larger click text plus a channel-brand line whose size/style matches the cover channel label.
- Human visual requests override the channel default. If the human asks for a specific scene, subject, action, camera angle, animal, object, or character type, apply that concept consistently to the cover, thumbnail, and loop video.
- All generated visuals should look animated, anime, illustrated, or stylized. Do not use photorealistic, live-action, documentary, camera-photo, or realistic human footage unless the human explicitly asks and the YouTube synthetic-media policy is handled.
- If Dreamina/Seedance blocks a loop-video generation for inappropriate content, copyright, moderation, or policy reasons, OpenClaw should rewrite the prompt and retry up to 10 total attempts. Each failure must be reported to Slack before retrying with `scripts/openclaw-release slack-notify --text "영상 만들기 실패해서 프롬프트를 수정해 다시 만듭니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`.
- Dreamina retry prompts must become more original and generic: remove named artists, studios, franchises, copyrighted characters, brands, celebrity names, exact song/video titles, `in the style of` wording, real-person likenesses, sexualized wording, minors, weapons, gore, and other moderation-risk terms. Preserve only the broad mood, channel label, first-frame continuity, and motion intent.
- If all 10 Dreamina attempts fail, send `scripts/openclaw-release slack-notify --text "영상 생성이 10회 실패해서 중단했습니다. RELEASE_TITLE: ERROR_SUMMARY"` and stop before render/publish unless the human explicitly approves a still-image fallback. If that fallback is approved, pass `--allow-still-image-video`; otherwise the app rejects video render without an uploaded 8 second loop video.

## Tokyo Daydream Radio Visual Skill

Use this for `Tokyo Daydream Radio`, mainstream J-pop/Japanese pop, Tokyo/Japan pop, city-pop, dance-pop, synth-pop, pop-rock, anime-pop, or similar Japan-themed vocal pop releases.

Default visual signature:

- Exactly three people seen from behind, walking forward away from the viewer into the scene.
- The camera/viewer sees backs and backs of heads, not front-facing faces.
- The three people stay centered and visually important.
- Text must fit around the centered three-person silhouette, usually in lower-left or lower negative space. Do not push the people sideways.
- Background can adapt to the release: Tokyo street, forest path, beach, rainy city, night park, station road, fantasy forest, seaside walk, etc.

Thumbnail text:

- Use large `J-POP`.
- Use smaller `TOKYO DAYDREAM RADIO` directly beneath it.
- Keep the same full-bleed two-line treatment for Tokyo/city, forest/nature, and beach variants.
- Do not add `1 HOUR`, `60 MIN`, `1時間`, clocks, timers, or duration badges.

Dreamina/Seedance prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Tokyo Daydream Radio".
Create one continuous forward-moving animated music visualizer shot.
Keep the Tokyo Daydream Radio signature: exactly three people seen from behind, walking away from the camera into the scene.
The viewer should see backs and backs of heads, not front-facing faces.
The motion must progress forward naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
Preserve the opening composition, lighting, palette, and anime/illustrated style.
Preserve the large, readable lower-left "Tokyo Daydream Radio" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
Adapt the background and atmosphere to the release concept.
Add subtle camera-follow movement from behind, gentle environmental motion, reflections, rain shimmer, particles, or soft light motion.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI, no extra people or characters.
```

## Soft Hour Radio Visual Skill

Use this for `Soft Hour Radio`, default background music, cafe, piano, sleep, study, work, chill, relaxing, ambient, lofi, and similar non-Japan BGM releases.

Default visual direction:

- Prefer calm, restrained visuals matched to the music use case, with clearly visible natural motion throughout the clip.
- Let the specific release concept decide the subject. Do not force a fixed recurring mascot, character count, scene list, or camera composition.
- Human presence is optional and should serve the release concept.
- Keep the composition uncluttered, warm, readable, and suitable for long background listening.

Thumbnail text:

- Use 2-4 large use-case or mood words such as `DEEP SLEEP`, `CAFE PIANO`, `FOCUS MUSIC`, `RAINY NIGHT`, `STUDY BGM`, or `CALM READING`.
- Add smaller `SOFT HOUR RADIO` as the channel brand line.
- Do not add duration badges unless the human explicitly asks.

Dreamina/Seedance prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Soft Hour Radio".
Create one continuous calm animated music visualizer shot for a background-music release.
Preserve the opening composition, lighting, palette, and illustrated/stylized visual language.
Preserve the large, readable lower-left "Soft Hour Radio" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
Animate calm but clearly visible natural motion across several environmental layers already present or naturally implied by the first frame and release mood: leaves, grass, curtains, water/rain reflections, warm light shimmer, drifting particles, smoke, steam, fireflies, or soft air movement when appropriate.
Keep continuous visible motion throughout the full clip while preserving the calm long-listening mood.
Keep the camera locked in the same crop and framing for the full clip. No zoom, no push-in, no pull-back, no dolly, no camera breathing, no camera drift, no camera follow, no parallax camera movement.
The motion must progress naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should preserve the same crop, framing, camera distance, lighting, palette, and subject placement; only ambient details may differ.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI.
```

## sundaze Visual Skill

Use this for `sundaze`, English-language pop, American pop, US/UK pop, western pop, mainstream vocal pop, dance-pop, synth-pop, pop-rock, and similar English pop releases.

- No fixed recurring visual signature yet.
- Let the playlist concept decide the cover, thumbnail, and loop-video scene.
- The cover must contain only the large lower-left `sundaze` brand label.
- The thumbnail should use short English pop click text such as `POP HITS`, `SUMMER POP`, `NIGHT DRIVE`, `DANCE POP`, `FEEL GOOD POP`, or `HEARTBREAK POP`, plus `SUNDAZE`.
- The loop video should animate the selected cover concept, not borrow Tokyo Daydream or Soft Hour signatures.

## Solwave Radio Visual Skill

Use this for `Solwave Radio`, Latin/Spanish-language pop, Latin pop, Spanish pop, urbano latino, reggaeton pop, bachata pop, salsa pop, cumbia pop, tropical dance-pop, and similar Spanish vocal releases.

- No fixed recurring visual signature yet.
- Let the playlist concept decide the cover, thumbnail, and loop-video scene.
- The cover must contain only the large lower-left `Solwave Radio` brand label.
- The thumbnail should use short Latin/Spanish click text such as `LATIN POP`, `REGGAETON`, `VERANO LATINO`, `SPANISH POP`, `FIESTA LATINA`, or `NOCHE LATINA`, plus `SOLWAVE RADIO`.
- The loop video should animate the selected cover concept, not borrow Tokyo Daydream or Soft Hour signatures.

## Other Channels Or Explicit Requests

- If the channel is not one of the documented profiles, derive a visual system from the channel name, release concept, and human request.
- If the human explicitly names the target channel, that channel's visual skill wins over automatic genre routing.
- Keep the shared asset contract.
- Do not borrow another channel's visual signature unless the human explicitly asks for it.
