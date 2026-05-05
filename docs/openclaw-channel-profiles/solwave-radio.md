# OpenClaw Channel Profile: Solwave Radio

Use this profile only after channel selection returns `Solwave Radio`, or when the human explicitly says to upload to `Solwave Radio`.

## Routing Contract

- This profile is for Latin/Spanish-language music: Latin pop, Spanish pop, urbano latino, reggaeton pop, bachata pop, salsa pop, cumbia pop, tropical dance-pop, verano latino, and similar vocal releases.
- Treat `Solwave Radio` as the Spanish/Latin counterpart to `Tokyo Daydream Radio`.
- Do not route English pop to this channel. Use `sundaze` for English/American pop and `Tokyo Daydream Radio` for Japanese pop.
- Music defaults to vocal songs with original Spanish lyrics unless the human explicitly asks for instrumental/BGM/no vocals.

## Visual Identity

- No fixed recurring visual signature yet.
- Let the playlist concept decide the cover, thumbnail, and loop-video scene.
- Keep the visual language animated, illustrated, anime, or stylized. Avoid photorealistic/live-action looks.
- The visuals should feel warm, rhythmic, sunlit, night-city, beach, dance, or tropical when the concept supports it, but do not force the same scene every time.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and Dreamina/Seedance first frame.
- The cover must include only a large lower-left `Solwave Radio` channel brand label.
- Make `Solwave Radio` clearly readable on mobile playback. Target roughly 18-24% of image width, or 5-6% of image height for text cap height.
- Do not add title text, genre text, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable Latin/Spanish click text matched to the playlist concept, for example `LATIN POP`, `REGGAETON`, `VERANO LATINO`, `SPANISH POP`, `FIESTA LATINA`, or `NOCHE LATINA`.
- Add `SOLWAVE RADIO` as the brand line. Keep it visually consistent with the large lower-left cover channel label.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Loop Video

- Use Dreamina/Seedance only for the moving clip.
- Use Dreamina/Seedance `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `8 seconds`.
- Do not put `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina prompt. Set those in the UI controls.
- Animate the cover/first-frame according to the playlist concept. There is no fixed walking/person/scene requirement.
- Keep the `Solwave Radio` brand label readable and unchanged for the full clip.
- The final moment should stay close to the opening composition, crop, lighting, palette, and subject placement. The app handles smooth repetition with crossfade.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Solwave Radio".
Create one continuous animated music visualizer shot for a Latin/Spanish pop release.
Preserve the opening composition, lighting, palette, subject placement, and illustrated/stylized visual language.
Animate natural motion that fits the specific playlist concept and Latin pop mood.
Preserve the large, readable lower-left "Solwave Radio" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
The motion must progress naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should remain close to the opening composition, camera distance, lighting, palette, and subject placement without becoming frozen.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Main upload metadata should be Spanish. Use `--default-language es` when OpenClaw approves metadata manually.
- Provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, and Simplified Chinese metadata.
- The top-level `--title` / `--description-file` and `--es-title` / `--es-description-file` should match.
- Playlist titles must start with `[playlist]` and should include the Latin/Spanish pop mood/use case, such as fiesta, verano, playa, noche, drive, baile, caminar, workout, or romance.
- Every track should have original Spanish lyrics and a distinct hook concept unless the human explicitly requested instrumental/no-vocal.
