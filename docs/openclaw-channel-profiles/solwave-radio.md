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
- If the concept naturally involves beach, summer, dance, nightlife, romance, fiesta, fashion, confidence, or a similar Latin-pop hook, it is acceptable to feature clearly adult women with tasteful, mildly sexy styling or light revealing fashion for stronger thumbnail appeal.
- Do not force people into every visual. Only use this when it fits the title and music concept.
- Keep it non-explicit: no nudity, no underwear-focus, no fetish framing, no minors or teen-looking characters, and no sexual acts. The subject should read as confident/pop-stylish rather than pornographic.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
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

- Use Dreamina/Seedance or Gemini only for the moving clip.
- For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `7 seconds`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `7 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
- Animate the cover/first-frame according to the playlist concept. There is no fixed walking/person/scene requirement.
- Keep the `Solwave Radio` brand label readable and unchanged for the full clip.
- The final moment should stay close to the opening composition, crop, lighting, palette, and subject placement. The app handles smooth repetition with a 1.5 second crossfade.

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
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds awkward, weak, or less clickable, rewrite it while keeping the Latin/Spanish-pop identity and real listening use case truthful.
- Main upload metadata should be Spanish. Use `--default-language es` when OpenClaw approves metadata manually.
- Provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese metadata.
- The top-level `--title` / `--description-file` and `--es-title` / `--es-description-file` should match.
- Playlist titles must start with `[playlist]` and should feel like curated editorial playlists, not raw workspace names. Do not write short generic titles such as `Ruta Dorada Pop`, `Latin Pop`, `Spanish Pop`, or `Pop para manejar` by themselves.
- Use an `Essential`-style title shape with the selected genre lane near the front: a vivid situation or emotion + Pop Latino / reggaeton pop / urbano latino / bachata pop / salsa pop / cumbia pop / Latin R&B / Latin soul identity + a listening use case. The title should make the click promise obvious before the viewer opens the video.
- Keep the whole release in one lane such as Pop Latino, reggaeton pop, urbano latino, bachata pop, salsa pop, cumbia pop, Latin R&B, Spanish R&B, or Latin soul, and name that lane in the title/description when accurate.
- Make the title broad and public-facing first. The cover/video scene can be specific, but do not let a narrow scene name become the main hook unless it is the strongest searchable phrase.
- Good Solwave title ingredients: `Pop Latino`, `Spanish Pop`, `Reggaeton Suave`, `Urbano Latino`, `Bachata Pop`, `Salsa Pop`, `Cumbia Pop`, `Latin R&B`, `Latin Soul`, `Verano Latino`, `Noche Latina`, `Ruta al Atardecer`, `Carretera`, `Playa`, `Fiesta`, `Baila`, `Drive`, `Caminar`, `Workout`, `Romance`, `Buenas Vibras`.
- Strong examples:
  `[playlist] Pop Latino para Ruta al Atardecer | Carretera, Verano y Buenas Vibras`
  `[playlist] Spanish Pop Essentials para Manejar | Sol, Ventanas Abajo y Road Trip`
  `[playlist] Reggaeton Suave de Noche | Latin Pop para Playa, Drive y Fiesta`
  `[playlist] Latin R&B de Noche | Romance, Drive y Buenas Vibras`
- Avoid repeating `lista de reproducción` after `[playlist]`; use `mix`, `music`, `música`, `radio`, or the use case instead.
- Every track should have original Spanish lyrics and a distinct hook concept unless the human explicitly requested instrumental/no-vocal.
- Lyrics are judged by song quality first: melody fit, rhythm, vocal tone, hook, emotional arc, and replay value. They do not need to mention the title/use case.
