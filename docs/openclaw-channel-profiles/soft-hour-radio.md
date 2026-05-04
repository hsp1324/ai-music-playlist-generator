# OpenClaw Channel Profile: Soft Hour Radio

Use this profile only after channel selection returns `Soft Hour Radio`, or when the human explicitly says to upload to `Soft Hour Radio`.

## Routing Contract

- Explicit channel request wins. If the human says `Soft Hour Radio에 올려줘`, this profile is mandatory even if the music mentions Japan, J-pop, city-pop, or anime influence.
- Default content is background/cafe/sleep/study/work/chill/BGM. These releases are usually instrumental/no-vocal unless the human asks for vocals.

## Visual Identity

- Mood: calm, useful, warm, focused, restful, long-listening friendly.
- Let the specific release concept decide the subject. Do not force a fixed recurring mascot, character count, scene list, or camera composition.
- Prefer restrained, uncluttered compositions that can sit behind long listening sessions without becoming visually noisy.
- Human presence is optional and should serve the release concept rather than act as a channel signature.
- Style must be animated, anime, illustrated, or stylized. Avoid photorealistic/live-action looks.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and Dreamina/Seedance first frame.
- The cover must include only a large lower-left `Soft Hour Radio` channel brand label.
- Make `Soft Hour Radio` clearly readable on mobile playback. Match the visual scale of the `SOFT HOUR RADIO` brand line used on the YouTube thumbnail.
- Size target: roughly 18-24% of image width, or 5-6% of image height for text cap height. On a 2048x1152 cover, `Soft Hour Radio` should be roughly 360-500 px wide with clearly readable letter height.
- Keep the channel name calm and tasteful, but it should feel like visible channel branding, not hidden text.
- Do not add title text, genre text, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable use-case/mood text, for example `CAFE PIANO`, `FOCUS MUSIC`, `STUDY BGM`, `DEEP SLEEP`, `RAINY NIGHT`, or `CALM READING`.
- Add `SOFT HOUR RADIO` as the brand line. Keep this brand line visually consistent with the large lower-left cover channel label.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, or clocks unless the human explicitly asks.

## Loop Video

- Use Dreamina/Seedance only for the moving clip.
- Use Dreamina/Seedance `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `8 seconds`.
- Do not put `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina prompt. Set those in the UI controls.
- The loop video should use calm but clearly visible motion derived from the cover itself. Avoid hard-coded scene/motion templates unless the human requested a specific visual.
- Keep the camera locked. Do not ask for zoom, push-in, pull-back, dolly, camera breathing, camera drift, camera follow, or parallax camera movement unless the human explicitly requests camera movement.
- Animate several environmental layers already present or naturally implied by the first frame, such as leaf clusters swaying, grass moving in a breeze, curtain movement, water or rain reflections, warm light shimmer, drifting dust motes, smoke, steam, fireflies, or soft air movement.
- Write prompts with positive motion language: `calm but clearly visible natural motion across several environmental layers`.
- The final moment should keep the same crop, framing, camera distance, lighting, palette, and subject placement. The app handles smooth repetition with crossfade, so do not force the model to zoom out or return the camera to the opening frame.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Soft Hour Radio".
Create one continuous calm animated music visualizer shot for a Soft Hour Radio background-music release.
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

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Titles should include listening use cases such as study, work, sleep, reading, rest, cafe, focus, or relaxation.
- Korean copy must not use `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`; use `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡`.
