# OpenClaw Channel Profile: Signal Room Radio

Use this profile only after channel selection returns `Signal Room Radio`, or while the connected channel still appears as legacy `AI썰전`.

## Routing Contract

- This profile is for no-vocal analytical/story BGM: AI debate prep, research music, script notes, fact-checking, data review, briefing room focus, mystery documentary BGM, story analysis, whiteboard thinking, and deep analytical work.
- Music defaults to instrumental/no-vocal.
- Do not route normal calm study/cafe/sleep BGM here; use `Soft Hour Radio`.
- Do not route J-pop/K-pop/English pop/Latin pop vocal releases here.
- Do not route manual remake/cover work here; `AnimeMix` remains manual-only.
- Do not turn this into narrated debate/story videos until the app has a separate narration pipeline. Current automation is one-hour instrumental playlists.

## Channel Name

Recommended public channel name:

```text
Signal Room Radio
```

If `/youtube/status` still lists the connected channel as `AI썰전`, treat it as this same channel. Use `Signal Room Radio` in cover labels, thumbnail branding, metadata planning, and Slack reports. `Signal Desk Radio` and `Midnight Cue Radio` are legacy draft names only.

## Visual Identity

- The channel should look like a future research desk, AI debate studio, calm newsroom, editorial room, signal room, mystery-documentary archive, or midnight workbench.
- Use illustrated, graphic, anime/stylized, or cinematic concept-art visuals. Avoid photorealistic/live-action looks.
- Good motifs: research desk, multiple monitors, blue desk light, hologram roundtable, whiteboard, citations, reference stacks, waveform/signal lines, archive UI, editorial notes, glass panels, dashboard glow, data rain, keyboard light, quiet studio microphones, timeline boards, abstract clues, map light, source folders, or documentary planning walls.
- Keep visuals clean, smart, and focused. They may feel mysterious or documentary-like, but should not look like horror, scandal, or exploitative true crime.
- Avoid gore, real crime photos, real victim imagery, celebrity likenesses, weapons, political logos, copyrighted characters, franchise logos, and fake UI that looks like a real platform.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and Dreamina/Seedance first frame.
- The cover must include only a large lower-left `Signal Room Radio` channel brand label.
- Make `Signal Room Radio` clearly readable on mobile playback. Target roughly 18-24% of image width, or 5-6% of image height for text cap height.
- Do not add title text, genre text, duration text, subtitles, UI labels, logos, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable tech/story/focus click text matched to the playlist concept, for example `AI DEBATE`, `RESEARCH`, `SCRIPT NOTES`, `FACT CHECK`, `DEEP WORK`, `DATA REVIEW`, `NEWSROOM`, `MYSTERY`, `DOCUMENTARY`, `STORY NOTES`, or `SIGNAL ROOM`.
- Add `SIGNAL ROOM RADIO` as the brand line. Keep it visually consistent with the large lower-left cover channel label.
- Keep the desk/studio/research subject visually important; text must fit around it and not cover the key workspace.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Loop Video

- Use Dreamina/Seedance only for the moving clip.
- Use Dreamina/Seedance `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `10 seconds`.
- Do not put `10 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina prompt. Set those in the UI controls.
- Animate the cover/first-frame according to the research/newsroom/mystery-documentary concept.
- Preserve the `Signal Room Radio` brand label readable and unchanged for the full clip.
- The final moment should stay close to the opening composition, crop, lighting, palette, and subject placement. The app handles smooth repetition with crossfade.
- Use visible but restrained motion: monitor glow, soft waveform movement, cursor-like light movement, slow hologram sweep, data rain, glass reflection drift, dust in desk light, subtle paper movement, keyboard glow, tiny signal-line pulses, or gentle studio light shimmer.
- Avoid zoom-heavy motion, camera-photo realism, glitch overload, flashing alarms, dramatic crime-board movement, or any motion that distracts from long listening.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Signal Room Radio".
Create one continuous animated music visualizer shot for a future signal-room, tech-newsroom, research, or mystery-documentary background-music release.
Preserve the opening composition, lighting, palette, subject placement, desk/studio props, and illustrated/stylized visual language.
Animate restrained but clearly visible analytical/story-work motion that fits the specific debate-prep, research, data-review, mystery, documentary, or briefing-room concept.
Preserve the large, readable lower-left "Signal Room Radio" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
The motion must progress naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should remain close to the opening composition, camera distance, lighting, palette, and subject placement without becoming frozen.
Stable composition, no hard cuts, no gore, no crime-scene imagery, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Main upload metadata should be English for broader search unless the human explicitly wants Korean default metadata. Use `--default-language en` when OpenClaw approves metadata manually.
- Provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese metadata.
- The top-level `--title` / `--description-file` and `--en-title` / `--en-description-file` should match when default language is English.
- Playlist titles must start with `[playlist]` and should feel like useful focus/work playlists, not raw workspace names.
- Use title shapes with a work/story situation plus music identity, for example `[playlist] AI Debate Prep BGM | Research, Script Notes and Deep Focus Music` or `[playlist] Mystery Documentary BGM | Archive Room, Quiet Clues and Deep Focus`.
- In localized descriptions, preserve timestamps exactly. Translate surrounding prose, recommended-use lines, hashtags, and track titles naturally for that language unless the human asks to keep English track titles.
