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
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
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

- Use Dreamina/Seedance or Gemini only for the moving clip.
- For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `6 seconds`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `6 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
- The loop video should keep the three people walking forward away from the camera with subtle camera-follow motion and environmental motion. The camera may follow at the same distance, but it must not push in, zoom in, pull back, or make the three people grow larger in frame.
- Keep the three-person silhouette at roughly the same screen size and centered placement throughout the clip. Reject/regenerate if the people noticeably scale up, the frame feels like a dolly-in, or the camera zooms into the subjects.
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
Keep the camera at the same distance from the three people while following them; no zoom in, no push-in, no pull-back, no camera breathing, no changing lens scale. The three people must stay roughly the same size in frame.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI, no extra people or characters.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds awkward, weak, or less clickable, rewrite it while keeping the J-pop identity, mood, and real listening use case truthful.
- Provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese metadata.
- Use Korean as the default API metadata unless the human changes this app convention.
- Titles must be broad mainstream J-pop discovery copy first. Use specific city/visual scenes as supporting atmosphere unless they are clearly the strongest public keyword.
- Do not over-emphasize the language in titles. Prefer `J-POP`, the actual Japan scene, mainstream pop substyle, mood, and listening use cases.
- Do not put `Tokyo` / `도쿄` in every title. Use it only for Tokyo-specific concepts such as Shibuya, Shinjuku, Tokyo commute, Tokyo skyline, or a clearly Tokyo-coded city scene. For generic J-pop, beach, forest, festival, school, karaoke, Osaka, Kyoto, Yokohama, or other Japan lifestyle concepts, omit Tokyo from the title.
- Do not default every Tokyo title to `walk` / `산책`. Use walking only for street, commute, crosswalk, beach, forest, or similar movement concepts. For arcade, game-center, karaoke, friend-hangout, rooftop, party, or night-out concepts, prefer arcade, gaming, friends, night out, driving, getting ready, weekend energy, or party warmup.
- Avoid making every title sound like anime OST. Use anime/OST wording only when that is the actual concept.
- Localized timestamp rows:
- Korean/default description: Japanese title plus Korean translation in parentheses.
- Japanese description: Japanese title only.
- English description: English translated title only.
- Spanish description: Spanish translated title only.
