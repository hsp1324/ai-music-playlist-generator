# OpenClaw Channel Profile: Custom Channel

Use this when the selected connected YouTube channel does not yet have a dedicated profile file.

## Visual Identity

- Let the playlist concept and channel title decide the cover, thumbnail, and loop-video direction.
- Do not reuse another channel's fixed signature unless the human explicitly asks.
- The cover/first-frame must be 16:9 and illustrated, anime, stylized, painterly, graphic, or otherwise non-photorealistic unless the channel identity clearly requires another style.
- Do not put the selected channel name, a channel logo, or a channel-brand line on the cover/first-frame.
- If text is useful, use only a short integrated style, genre, use-case, or theme phrase that fits the release.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image reference/edit derivative.
- Preserve the same subject, scene, camera angle, palette, and main composition so the thumbnail and rendered video feel connected.
- Add one large click-friendly phrase that fits the selected channel and release concept.
- Keep thumbnail text directly on the image with a transparent background. Use font weight, color, subtle shadow, thin outline, or local contrast for readability; do not use black boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, stickers, badges, pills, capsules, or any filled label shape behind text.
- Do not add the selected channel name or a channel logo.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Loop Video

- Use the uploaded cover/first-frame image as the exact starting frame.
- Generate a short loop video. Use Gemini first as-is; for Dreamina/Seedance use `1.0 Fast`, first-frame/start-frame only, no last-frame reference, `16:9`, `720p`, and exactly `10 seconds` unless the human explicitly requests another setup.
- Animate only visual elements that already fit the first frame and playlist concept.
- If the first frame has a short style/theme phrase, keep it stable and readable. Do not invent a channel name.
- The final frame should return close to the opening composition so the app's loop crossfade feels natural. The app uses 2.0 seconds for Gemini-tagged loop videos and 1.5 seconds for the default provider path.
- Do not add subtitles, lyrics, title text, duration text, logos, UI, or unrelated words.

## Metadata

- Follow `docs/openclaw-youtube-metadata.md`.
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds awkward, weak, or less clickable, rewrite it while keeping the inferred channel identity, genre/lane, and real listening use case truthful.
- If the channel has no dedicated language rule, include every supported localization unless the human says otherwise.
- Choose the default language from the channel identity. If unclear, use English for global pop-style channels and Korean for Korean-run background/BGM channels.
- Make titles broad and public-facing first. Use exact visual-scene details as atmosphere unless they are clearly the strongest searchable hook for that custom channel.
- For vocal channels, lyrics are judged by song quality first: melody fit, beat/rhythm, vocal tone, hook, emotional arc, and replay value. They do not need to mention the title/use case.
