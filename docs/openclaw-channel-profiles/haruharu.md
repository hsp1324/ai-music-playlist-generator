# OpenClaw Channel Profile: HaruHaru

Use this profile only after channel selection returns `HaruHaru`, or when the human explicitly says to upload to `HaruHaru`.

## Routing Contract

- This profile is for Korean-language K-pop vocal releases: K-pop, Korean dance-pop, idol-pop inspired music, Korean synth-pop, Korean pop-rock, Korean R&B pop, and similar Korean vocal pop.
- Music defaults to original Korean vocal songs with lyrics.
- Do not route J-pop/Japanese pop here; use `Tokyo Daydream Radio`.
- Do not route English/American pop here; use `sundaze`.
- Do not route Latin/Spanish pop here; use `Solwave Radio`.
- Do not route instrumental/BGM/no-vocal releases here unless the human explicitly asks for a Korean-pop-flavored instrumental.
- Do not use existing popular-song remake/cover concepts here; those are manual-only and not part of HaruHaru automation.

## Visual Identity

- No fixed recurring visual signature yet.
- Let the playlist concept decide the cover, thumbnail, and loop-video scene.
- Keep the visual language illustrated, anime, stylized, graphic, or painterly. Avoid photorealistic/live-action looks.
- The visuals should feel Korean pop-friendly: expressive fashion, clean composition, strong color mood, and easy thumbnail readability.
- Seoul/Korea setting cues are useful when relevant, but do not repeat the same skyline, street, or idol-practice-room scene every time.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and Dreamina/Seedance first frame.
- The cover must include only a large lower-left `HaruHaru` channel brand label.
- Make `HaruHaru` clearly readable on mobile playback. Target roughly 18-24% of image width, or 5-6% of image height for text cap height.
- Do not add title text, genre text, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, clothing colors, and camera angle from the cover.
- Add short readable K-pop click text matched to the playlist concept, for example `K-POP`, `SEOUL POP`, `DANCE POP`, `HEARTBREAK`, `SUMMER KPOP`, `RAINY KPOP`, or `K-POP DRIVE`.
- Add `HARUHARU` as the brand line. Keep it visually consistent with the large lower-left cover channel label.
- Keep the main subject visually important; text must fit around the subject and must not push the subject into an awkward crop.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Loop Video

- Use Dreamina/Seedance only for the moving clip.
- Use Dreamina/Seedance `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `8 seconds`.
- Do not put `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina prompt. Set those in the UI controls.
- Animate the cover/first-frame according to the playlist concept. There is no fixed walking/person/scene requirement.
- Keep the `HaruHaru` brand label readable and unchanged for the full clip.
- The final moment should stay close to the opening composition, crop, lighting, palette, and subject placement. The app handles smooth repetition with crossfade.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "HaruHaru".
Create one continuous animated music visualizer shot for an original Korean K-pop vocal release.
Preserve the opening composition, lighting, palette, subject placement, fashion details, and illustrated/stylized visual language.
Animate natural motion that fits the specific playlist concept and K-pop mood.
Preserve the large, readable lower-left "HaruHaru" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
The motion must progress naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should remain close to the opening composition, camera distance, lighting, palette, and subject placement without becoming frozen.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Main upload metadata should be Korean. Use `--default-language ko` when OpenClaw approves metadata manually.
- Provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese metadata.
- The top-level `--title` / `--description-file` and `--ko-title` / `--ko-description-file` should match.
- Playlist titles must start with `[playlist]` and should feel like curated editorial K-pop playlists, not raw workspace names.
- Use a title shape with a broad mainstream K-pop listening promise first, then a clear use case or emotion. Good example: `[playlist] 신나는 K-POP 믹스 | 운동, 러닝, 외출 준비, 파티 웜업`.
- Do not use the visual scene as the main title hook unless it is broadly searchable. A rooftop, rainy street, practice room, cafe, or bus stop can guide cover/video mood, but the title should usually focus on K-pop energy, workout, running, getting ready, party warmup, night drive, heartbreak, confidence, or feel-good listening.
- Every track should have original Korean lyrics and a distinct hook concept unless the human explicitly requested instrumental/no-vocal.
- Lyrics are judged by song quality first: melody fit, beat, vocal tone, hook, emotional arc, and replay value. They do not need to mention the title/use case.
- In localized descriptions, preserve timestamps exactly. Translate surrounding prose, recommended-use lines, hashtags, and track titles naturally for that language unless the human asks to keep Korean track titles.
