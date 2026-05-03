# OpenClaw Channel Profile: Tokyo Daydream Radio

Use this profile only after channel selection returns `Tokyo Daydream Radio`, or when the human explicitly says to upload to `Tokyo Daydream Radio`.

## Routing Contract

- This profile is for Japan, Tokyo, Shibuya, Shinjuku, J-pop, city-pop, anime-pop, Japanese lofi, vaporwave, and similar Japan-themed releases.
- If the human explicitly names a different channel such as `Soft Hour Radio`, do not use this profile unless the human also explicitly asks for Tokyo Daydream visuals.
- Keep `Tokyo Daydream Radio` visually distinct from Soft Hour Radio.

## Visual Identity

- Default signature: exactly three people seen from behind, walking forward away from the viewer into the scene.
- The camera/viewer sees backs and backs of heads, not front-facing faces.
- The three people stay centered and visually important.
- Text must fit around the centered three-person silhouette, usually lower-left or lower negative space. Do not push people sideways.
- Background adapts to the release: Tokyo street, forest path, beach, rainy city, night park, station road, fantasy forest, seaside walk, neon alley, or similar Japan-themed scene.
- Style must be animated, anime, illustrated, or stylized. Avoid photorealistic/live-action looks.

## Cover

- Create one final clean 16:9 cover first.
- The cover is the playback visual and Dreamina/Seedance first frame.
- Keep it text-free by default.
- If the human explicitly asks for channel text inside the video, the cover may contain only a small lower-left `Tokyo Daydream Radio` label.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same three people, subject placement, clothing colors, silhouettes, lighting, palette, background landmarks, and camera angle from the cover.
- Use large `J-POP`.
- Use smaller `TOKYO DAYDREAM RADIO` directly beneath it.
- Keep the same full-bleed two-line treatment for Tokyo/city, forest/nature, and beach versions.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, `1時間`, clocks, or timers.

## Loop Video

- Use Dreamina/Seedance only for the moving clip.
- Use Dreamina/Seedance `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `8 seconds`.
- Do not put `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina prompt. Set those in the UI controls.
- The loop video should keep the three people walking forward away from the camera with subtle forward camera-follow motion and environmental motion.

Prompt shape:

```text
Use the uploaded clean text-free first-frame image as the exact starting frame.
Create one continuous forward-moving animated music visualizer shot for Tokyo Daydream Radio.
Keep the Tokyo Daydream Radio signature: exactly three people seen from behind, walking away from the camera into the scene.
The viewer should see backs and backs of heads, not front-facing faces.
The motion must progress forward naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
Preserve the opening composition, lighting, palette, and anime/illustrated style.
Adapt the background and atmosphere to the release concept.
Add subtle camera-follow movement from behind, gentle environmental motion, reflections, rain shimmer, particles, or soft light motion.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no text, no subtitles, no logos, no UI, no extra people or characters.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Provide Korean, Japanese, English, and Spanish metadata.
- Use Korean as the default API metadata unless the human changes this app convention.
- Do not over-emphasize the language in titles. Prefer `J-POP`, `Tokyo`, city-pop, mood, and listening use cases.
- Localized timestamp rows:
- Korean/default description: Japanese title plus Korean translation in parentheses.
- Japanese description: Japanese title only.
- English description: English translated title only.
- Spanish description: Spanish translated title only.
