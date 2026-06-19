# OpenClaw Channel Profile: Soft Hour Radio

Use this profile only after channel selection returns `Soft Hour Radio`, or when the human explicitly says to upload to `Soft Hour Radio`.

## Routing Contract

- Explicit channel request wins. If the human says `Soft Hour Radio에 올려줘`, this profile is mandatory even if the music mentions Japan, J-pop, city-pop, or anime influence.
- Default content is background/cafe/sleep/study/work/chill/BGM. These releases are usually instrumental/no-vocal unless the human asks for vocals.
- Music identity is piano-first by default. New Soft Hour audio should be solo piano / felt piano / quiet piano; existing similar Soft Hour tracks may temporarily fill the back half when there are not enough piano tracks to approach one hour. Visuals and titles should support the piano-listening promise for the fresh lead block.

## Visual Identity

- Mood: calm, useful, warm, focused, restful, long-listening friendly.
- Let the specific release concept decide the subject. Do not force a fixed recurring mascot, character count, scene list, or camera composition.
- Prefer restrained, uncluttered compositions that can sit behind long listening sessions without becoming visually noisy.
- Human presence is optional and should serve the release concept rather than act as a channel signature.
- Style must now be high-resolution photorealistic / premium real-world BGM imagery by default. Avoid anime, cartoon, illustrated, painterly, vector, or obviously stylized looks unless the human explicitly asks for them.
- Preserve the established Soft Hour background feeling: quiet cafe, study, work, reading, sleep, rain-window, greenhouse, library, cottage, workshop, warm desk, or other calm long-listening spaces. Make the scene feel real and high quality, not stock-photo glossy or fashion-shoot staged.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
- Make the cover photorealistic, high-resolution, clean, and calm. It should look like a real quiet BGM environment with soft natural light, believable materials, and restrained composition.
- Do not put `Soft Hour Radio`, the channel name, a channel logo, or a brand line on the cover/first-frame.
- If text is useful, use only a short integrated use-case or style phrase that still signals piano, such as `SOLO PIANO`, `CAFE PIANO`, `PIANO BGM`, `STUDY PIANO`, `SLEEP PIANO`, `RAINY PIANO`, or `READING PIANO`.
- Do not add title sentences, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same photorealistic scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable use-case/mood text that names piano, for example `CAFE PIANO`, `SOLO PIANO`, `PIANO BGM`, `STUDY PIANO`, `SLEEP PIANO`, `RAINY PIANO`, or `READING PIANO`.
- Keep thumbnail text directly on the image with a transparent background. Use font weight, color, subtle shadow, thin outline, or local contrast for readability; do not use black boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, stickers, badges, pills, capsules, or any filled label shape behind text.
- Do not add `SOFT HOUR RADIO`, the channel name, or a channel logo.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, or clocks unless the human explicitly asks.

## Loop Video

- Use Dreamina/Seedance or Gemini only for the moving clip.
- For Dreamina/Seedance, use `Seedance Mini 2.0`, first-frame/start-frame only, no Omni Reference, no last-frame/end-frame reference, `16:9`, `720p`, exactly `10 seconds`. Do not upload both first and last frames, because Dreamina switches that setup back to `Seedance 2.0 Fast`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `10 seconds`, `5 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
- The loop video should preserve the same photorealistic high-quality background feeling as the cover. Avoid hard-coded scene/motion templates unless the human requested a specific visual.
- If the first-frame cover contains short piano/use-case text, the provider video must keep that text as plain letters directly on the scene with a transparent background. Do not add, preserve, or animate in any black box, semi-transparent dark panel, rectangle, gradient scrim, sticker, badge, pill, capsule, or filled label shape behind the text. Reject/regenerate if the moving clip wraps clean first-frame text in a new box.
- The camera must be completely static: locked-off tripod, fixed frame, no pan, tilt, zoom, push-in, pull-back, dolly, handheld shake, camera breathing, camera drift, camera follow, parallax camera move, or any other camera movement.
- Use only subtle environmental motion already present or naturally implied by the first frame, such as rain on glass, steam from a mug, candle or lamp flicker, curtain edge movement, drifting dust motes, smoke, firelight, soft reflections, or gentle leaf movement. Do not move the camera to create motion.
- Write prompts with positive motion language: `calm but clearly visible natural motion across several environmental layers`.
- The final moment should keep the same crop, framing, camera distance, lighting, palette, and subject placement. The app handles smooth repetition with provider-aware crossfade timing, so do not force the model to zoom out or return the camera to the opening frame.
- If Dreamina rejects generation for inappropriate content, copyright, moderation, or policy reasons, follow the shared 10-attempt retry rule in `README.md` and `docs/openclaw-visual-assets.md`: send Slack before every retry, remove protected IP or risky terms from the prompt, and stop before render/publish after 10 failures.
- For very calm piano, greenhouse, cafe, reading, sleep, or quiet focus releases, prefer `--video-spectrum-overlay-style none` so the final video stays visually restful. Do not use the retired thin waveform style from `아침 온실 피아노 BGM`; it looked too busy for this channel.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame.
Create one uninterrupted calm environmental take for a background-music release from a locked-off tripod camera.
Preserve the opening composition, lighting, palette, and high-resolution photorealistic visual language.
If the first frame already contains a short use-case/style phrase, keep it stable and readable. Do not invent a channel name.
Keep that phrase as transparent-background typography directly on the scene; do not create or preserve any black box, translucent dark panel, gradient scrim, sticker, badge, pill, capsule, or filled label shape behind the letters.
Animate only calm natural motion already present or naturally implied by the first frame and release mood: rain on glass, steam from a cup, candle or lamp flicker, curtain edge movement, drifting dust, smoke, firelight, soft reflections, or gentle leaf movement when appropriate.
Keep the same crop, framing, camera distance, lighting, palette, and subject placement from first frame to final frame.
No camera movement, no pan, no tilt, no zoom, no dolly, no handheld shake, no parallax camera move, no new text, no text background boxes or panels, subtitles, logos, UI, anime, illustration, or cartoon styling.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds awkward, weak, or less clickable, rewrite it while keeping the BGM use case and calm channel identity truthful.
- Titles should include both piano and a real listening use case such as study, work, sleep, reading, rest, cafe, focus, or relaxation.
- Titles should read like a natural clickable sentence, not a keyword pile. Good Korean shapes: `조용히 집중하고 싶을 때 듣는 피아노 BGM | 공부와 작업을 위한 솔로 피아노`, `잠들기 전 틀어놓는 잔잔한 피아노 | 깊은 밤 휴식과 수면 BGM`, or `비 오는 밤 책 읽을 때 좋은 피아노 연주곡 | 독서와 휴식 BGM`.
- Do not use lofi / lo-fi, guitar, jazz trio, Rhodes, strings, synth pads, or mixed-instrument wording in Soft Hour metadata unless the human explicitly changes the channel direction later.
- Keep titles and descriptions audience-friendly and searchable. If the visual is a niche scene, do not make that niche the main title unless the human asks. For example, use `조용히 집중하고 싶을 때 듣는 피아노 BGM | 공부와 작업을 위한 솔로 피아노` instead of making `도자기 공방` the primary hook.
- The description can mention the visual atmosphere lightly, but the first paragraph should explain how the music is useful: study, work, reading, writing, calm handwork, rest, sleep, cafe, or focus.
- Korean copy must not use `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`; use `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡`.
