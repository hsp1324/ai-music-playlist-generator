# OpenClaw Channel Profile: Midnight Cue Radio

Use this profile only after channel selection returns `Midnight Cue Radio`, or while the connected channel still appears as legacy `AI썰전`.

## Routing Contract

- This profile is for cinematic mystery/storytelling BGM: mystery documentary music, investigation BGM, dark ambient, noir background music, urban legend atmosphere, thriller writing music, and late-night story music.
- Music defaults to instrumental/no-vocal.
- Do not route normal calm study/cafe/sleep BGM here; use `Soft Hour Radio`.
- Do not route J-pop/K-pop/English pop/Latin pop vocal releases here.
- Do not route manual remake/cover work here; `AnimeMix` remains manual-only.
- Until a dedicated narration pipeline exists, do not create narrated debate/story videos for this channel. Use one-hour instrumental playlists.

## Channel Name

Recommended public channel name:

```text
Midnight Cue Radio
```

If `/youtube/status` still lists the connected channel as `AI썰전`, treat it as this same channel. Use `Midnight Cue Radio` in cover labels, thumbnail branding, metadata planning, and Slack reports.

## Visual Identity

- No fixed recurring mascot or character count.
- Let the playlist concept decide the scene, but keep the channel consistently cinematic, nocturnal, mysterious, and story-driven.
- Use illustrated, graphic, painterly, anime/stylized, or cinematic concept-art visuals. Avoid photorealistic/live-action looks.
- Good motifs: archive shelves, evidence board, detective desk, cassette recorder, rain on glass, map pins, CCTV glow, observatory, old documents, foggy road, empty station, ruins, locked door, red thread, flashlight beam, or noir city lights.
- Avoid gore, real crime photos, real victim imagery, celebrity likenesses, weapons aimed at people, minors in danger, copyrighted characters, franchise logos, or explicit violent scenes.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and Dreamina/Seedance first frame.
- The cover must include only a large lower-left `Midnight Cue Radio` channel brand label.
- Make `Midnight Cue Radio` clearly readable on mobile playback. Target roughly 18-24% of image width, or 5-6% of image height for text cap height.
- Do not add title text, genre text, duration text, subtitles, UI, logos, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable mystery/story click text matched to the playlist concept, for example `MYSTERY`, `DARK CASE`, `NOIR`, `INVESTIGATION`, `URBAN LEGEND`, `DOCUMENTARY`, `COLD CASE`, or `NIGHT FILES`.
- Add `MIDNIGHT CUE RADIO` as the brand line. Keep it visually consistent with the large lower-left cover channel label.
- Keep the main mystery object/scene visually important; text must fit around it and not cover the key clue/object.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Loop Video

- Use Dreamina/Seedance only for the moving clip.
- Use Dreamina/Seedance `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `10 seconds`.
- Do not put `10 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina prompt. Set those in the UI controls.
- Animate the cover/first-frame according to the mystery/story concept.
- Preserve the `Midnight Cue Radio` brand label readable and unchanged for the full clip.
- The final moment should stay close to the opening composition, crop, lighting, palette, and subject placement. The app handles smooth repetition with crossfade.
- Use visible but restrained motion: rain streaks, flickering desk lamp, slow dust, moving tape reels, monitor scanlines, drifting fog, map light shimmer, file pages barely moving, distant city reflections, or subtle shadow movement.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Midnight Cue Radio".
Create one continuous animated music visualizer shot for a cinematic mystery/storytelling background-music release.
Preserve the opening composition, lighting, palette, subject placement, mystery props, and illustrated/stylized visual language.
Animate restrained but clearly visible atmospheric motion that fits the specific mystery/documentary concept.
Preserve the large, readable lower-left "Midnight Cue Radio" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
The motion must progress naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should remain close to the opening composition, camera distance, lighting, palette, and subject placement without becoming frozen.
Stable composition, no hard cuts, no gore, no real crime photos, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Main upload metadata should be English for broader search. Use `--default-language en` when OpenClaw approves metadata manually.
- Provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese metadata.
- The top-level `--title` / `--description-file` and `--en-title` / `--en-description-file` should match.
- Playlist titles must start with `[playlist]` and should feel like curated cinematic/storytelling playlists, not raw workspace names.
- Use a title shape with a story use case plus music identity, for example `[playlist] Midnight Mystery Documentary BGM | Dark Cases, Archives and Investigation Music`.
- In localized descriptions, preserve timestamps exactly. Translate surrounding prose, recommended-use lines, hashtags, and track titles naturally for that language unless the human asks to keep English track titles.
