# OpenClaw Channel Profile: Custom Channel

Use this when the selected connected YouTube channel does not yet have a dedicated profile file.

## Visual Identity

- Let the playlist concept and channel title decide the cover, thumbnail, and loop-video direction.
- Do not reuse another channel's fixed signature unless the human explicitly asks.
- The cover/first-frame must be 16:9 and illustrated, anime, stylized, painterly, graphic, or otherwise non-photorealistic unless the channel identity clearly requires another style.
- The only text on the cover/first-frame is the selected channel name as a large, readable lower-left brand label.
- The channel label should be readable on mobile. Target roughly 18-24% of image width, or about 5-6% of image height for text cap height.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image reference/edit derivative.
- Preserve the same subject, scene, camera angle, palette, and main composition so the thumbnail and rendered video feel connected.
- Add one large click-friendly phrase that fits the selected channel and release concept.
- Add the selected channel name as the brand line, visually consistent with the cover's lower-left channel label.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Loop Video

- Use the uploaded cover/first-frame image as the exact starting frame.
- Generate a 10 second 16:9 720p loop video unless the human explicitly requested another length.
- Animate only visual elements that already fit the first frame and playlist concept.
- Preserve the lower-left channel label for the full clip. Regenerate if it disappears, flickers, moves, morphs, changes spelling, changes style drastically, or becomes unreadable.
- The final frame should return close to the opening composition so the app's 2 second crossfade loop feels natural.
- Do not add subtitles, lyrics, title text, duration text, logos, UI, or unrelated words.

## Metadata

- Follow `docs/openclaw-youtube-metadata.md`.
- If the channel has no dedicated language rule, include every supported localization unless the human says otherwise.
- Choose the default language from the channel identity. If unclear, use English for global pop-style channels and Korean for Korean-run background/BGM channels.
- Make titles broad and public-facing first. Use exact visual-scene details as atmosphere unless they are clearly the strongest searchable hook for that custom channel.
- For vocal channels, lyrics are judged by song quality first: melody fit, beat/rhythm, vocal tone, hook, emotional arc, and replay value. They do not need to mention the title/use case.
