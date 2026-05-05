# OpenClaw Channel Profile: Tokyo Daydream Radio

Use this profile only after channel selection returns `Tokyo Daydream Radio`, or when the human explicitly says to upload to `Tokyo Daydream Radio`.

## Routing Contract

- This profile is for mainstream J-pop/Japanese pop and Japan-themed vocal pop releases: J-pop, city-pop, dance-pop, synth-pop, pop-rock, emotional pop ballads, summer pop, night-drive pop, anime-pop, and similar releases.
- Anime/OST-like music is allowed as one lane inside the channel, but this is not an anime OST-only channel.
- If the human explicitly names a different channel such as `Soft Hour Radio`, do not use this profile unless the human also explicitly asks for Tokyo Daydream visuals.
- Keep `Tokyo Daydream Radio` visually distinct from Soft Hour Radio.

## Visual Identity

- Music identity: popular J-pop first. Keep the sound accessible, hook-driven, vocal, and playlist-friendly. Do not make every release feel like anime OST.
- Default signature: exactly three people seen from behind, walking forward away from the viewer into the scene.
- The camera/viewer sees backs and backs of heads, not front-facing faces.
- The three people stay centered and visually important.
- Text must fit around the centered three-person silhouette, usually lower-left or lower negative space. Do not push people sideways.
- Background adapts to the release: Tokyo street, forest path, beach, rainy city, night park, station road, fantasy forest, seaside walk, neon alley, or similar Japan-themed scene.
- Style must be animated, anime, illustrated, or stylized. Avoid photorealistic/live-action looks.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and Dreamina/Seedance first frame.
- The cover must include only a large lower-left `Tokyo Daydream Radio` channel brand label.
- Make `Tokyo Daydream Radio` clearly readable on mobile playback. Match the visual scale of the `TOKYO DAYDREAM RADIO` brand line used on the YouTube thumbnail.
- Size target: roughly 18-24% of image width, or 5-6% of image height for text cap height. On a 2048x1152 cover, the channel label should be roughly 360-500 px wide with clearly readable letter height.
- Keep the channel name tasteful and integrated into the scene, but it should feel like visible channel branding, not hidden fine print.
- Do not add title text, genre text, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same three people, subject placement, clothing colors, silhouettes, lighting, palette, background landmarks, and camera angle from the cover.
- Use large `J-POP`.
- Use `TOKYO DAYDREAM RADIO` directly beneath it. Keep this brand line visually consistent with the large lower-left cover channel label.
- Keep the same full-bleed two-line treatment for Tokyo/city, forest/nature, and beach versions.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, `1時間`, clocks, or timers.

## Loop Video

- Use Dreamina/Seedance only for the moving clip.
- Use Dreamina/Seedance `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `8 seconds`.
- Do not put `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina prompt. Set those in the UI controls.
- The loop video should keep the three people walking forward away from the camera with subtle forward camera-follow motion and environmental motion.
- The final moment should return close to the opening composition, camera distance, lighting, palette, and subject placement while maintaining natural motion.
- If Dreamina rejects generation for inappropriate content, copyright, moderation, or policy reasons, follow the shared 10-attempt retry rule in `README.md` and `docs/openclaw-visual-assets.md`: send Slack before every retry, remove protected IP or risky terms from the prompt, and stop before render/publish after 10 failures.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Tokyo Daydream Radio".
Create one continuous forward-moving animated music visualizer shot for Tokyo Daydream Radio.
Keep the Tokyo Daydream Radio signature: exactly three people seen from behind, walking away from the camera into the scene.
The viewer should see backs and backs of heads, not front-facing faces.
The motion must progress forward naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should return close to the opening composition, camera distance, lighting, palette, and subject placement without becoming frozen.
Preserve the opening composition, lighting, palette, and anime/illustrated style.
Preserve the large, readable lower-left "Tokyo Daydream Radio" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
Adapt the background and atmosphere to the release concept.
Add subtle camera-follow movement from behind, gentle environmental motion, reflections, rain shimmer, particles, or soft light motion.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI, no extra people or characters.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, and Simplified Chinese metadata.
- Use Korean as the default API metadata unless the human changes this app convention.
- Do not over-emphasize the language in titles. Prefer `J-POP`, Tokyo/Japan scene, mainstream pop substyle, mood, and listening use cases.
- Avoid making every title sound like anime OST. Use anime/OST wording only when that is the actual concept.
- Localized timestamp rows:
- Korean/default description: Japanese title plus Korean translation in parentheses.
- Japanese description: Japanese title only.
- English description: English translated title only.
- Spanish description: Spanish translated title only.
