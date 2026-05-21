# OpenClaw Channel Profile: sundaze

Use this profile only after channel selection returns `sundaze`, or when the human explicitly says to upload to `sundaze`.

## Routing Contract

- This profile is for English-language pop, American pop, US/UK pop, western pop, mainstream vocal pop, dance-pop, synth-pop, pop-rock, and similar English pop releases.
- Treat `sundaze` as the US/English-pop counterpart to `Tokyo Daydream Radio`.
- Do not route J-pop/Japanese pop to this channel. Use `Tokyo Daydream Radio` for Japanese pop and `Solwave Radio` for Latin/Spanish pop.
- Music defaults to vocal songs with original English lyrics unless the human explicitly asks for instrumental/BGM/no vocals.

## Visual Identity

- No fixed recurring visual signature yet.
- Let the playlist concept decide the cover, thumbnail, and loop-video scene.
- Keep the visual language animated, illustrated, anime, or stylized. Avoid photorealistic/live-action looks.
- The visuals should feel modern, bright, pop-friendly, and easy to understand at thumbnail size.
- If the concept naturally involves nightlife, summer, beach, dance, romance, fashion, confidence, or a similar pop hook, it is acceptable to feature clearly adult women with tasteful, mildly sexy styling or light revealing fashion for stronger thumbnail appeal.
- Do not force people into every visual. Only use this when it fits the title and music concept.
- Keep it non-explicit: no nudity, no underwear-focus, no fetish framing, no minors or teen-looking characters, and no sexual acts. The subject should read as confident/pop-stylish rather than pornographic.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
- Do not put `sundaze`, the channel name, a channel logo, or a brand line on the cover/first-frame.
- If text is useful, use only a short integrated pop-lane or use-case phrase such as `POP R&B`, `DANCE POP`, `SYNTH POP`, `FEEL GOOD POP`, `SUMMER POP`, or `NIGHT DRIVE`.
- Do not add title sentences, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable pop click text matched to the playlist concept, for example `POP HITS`, `SUMMER POP`, `NIGHT DRIVE`, `DANCE POP`, `FEEL GOOD POP`, or `HEARTBREAK POP`.
- Do not add `SUNDAZE`, the channel name, or a channel logo.
- Keep all thumbnail text inside safe margins with breathing room. Reject/regenerate if text is clipped, cramped inside a shape, too close to the edge, pasted over the art, or separated from the scene.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Loop Video

- Use Dreamina/Seedance or Gemini only for the moving clip.
- For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `7 seconds`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `7 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
- Animate the cover/first-frame according to the playlist concept. There is no fixed walking/person/scene requirement.
- If the first frame has a short pop/style phrase, keep it stable and readable. Do not invent a channel name.
- The final moment should stay close to the opening composition, crop, lighting, palette, and subject placement. The app handles smooth repetition with a 1.5 second crossfade.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame.
Create one uninterrupted animated English pop visual take.
Preserve the opening composition, lighting, palette, subject placement, and illustrated/stylized visual language.
Animate natural motion that fits the specific playlist concept and pop mood.
If the first frame already contains a short pop/style phrase, keep it stable and readable. Do not invent a channel name.
The final moment should remain close to the opening composition, camera distance, lighting, palette, and subject placement without becoming frozen.
No new text, subtitles, logos, UI, photorealism, or live action.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds awkward, weak, or less clickable, rewrite it while keeping the English-pop identity and real listening use case truthful.
- Main upload metadata should be English. Use `--default-language en` when OpenClaw approves metadata manually.
- Provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Turkish, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese metadata.
- The top-level `--title` / `--description-file` and `--en-title` / `--en-description-file` should match.
- Localized YouTube titles may be natural adaptations in each language instead of exact English copies. If a literal translation is awkward or less clickable, rewrite the localized title while keeping the English-pop identity and actual listening use case truthful.
- In every localized description, keep timestamped tracklist song titles in English exactly as the English description. Translate only the surrounding description prose, recommended use-case line, and hashtag line.
- Playlist titles must start with `[playlist]` and should feel like curated editorial playlists, not raw workspace names. Do not write short generic titles such as `Golden Hour Drive Pop`, `English Pop`, or `American Pop` by themselves.
- Use an `Essential`-style title shape with the selected genre lane near the front: a vivid situation or emotion + Pop R&B / pop hip-hop / dance-pop / synth-pop / pop-rock / soul-pop / acoustic-pop identity + a listening use case. The title should make the click promise obvious before the viewer opens the video.
- Keep the whole release in one lane such as Pop R&B, pop hip-hop, dance-pop, synth-pop, pop-rock, soul-pop, neo-soul pop, acoustic pop, or ballad-pop, and name that lane in the title/description when accurate.
- Make the title broad and public-facing first. The cover/video scene can be specific, but do not let a narrow scene name become the main hook unless it is the strongest searchable phrase.
- Match listening use cases to the actual energy. For energetic rooftop, club, dance-pop, bass-heavy, or workout-feeling releases, prefer getting ready, workout, running, party warmup, driving, nightlife, and confidence. Avoid `focus`, `study`, or `quiet work` unless the rendered audio is genuinely calm enough for those uses.
- Strong examples:
  `[playlist] Sunset Highway Pop-Rock Drive | Windows Down Road Trip Music`
  `[playlist] Feel-Good Pop R&B Essentials | Summer Drive, Walk and Good Days`
  `[playlist] Late Night English Pop Mix | City Lights, Heartbreak and Drive Music`
  `[playlist] Golden Hour Soul-Pop Drive | Warm Vocals, Open Roads and Good Days`
- Every track should have original English lyrics and a distinct hook concept unless the human explicitly requested instrumental/no-vocal.
- Lyrics are judged by song quality first: melody fit, vocal tone, hook, emotional arc, and replay value. They do not need to mention the title/use case.
