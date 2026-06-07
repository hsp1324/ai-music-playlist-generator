# OpenClaw Channel Profile: Tokyo Daydream Radio

Use this profile only after channel selection returns `Tokyo Daydream Radio`, or when the human explicitly says to upload to `Tokyo Daydream Radio`.

## Routing Contract

- This profile is for mainstream J-pop/Japanese pop and Japan-themed vocal pop releases: J-pop, city-pop, dance-pop, synth-pop, pop-rock, emotional pop ballads, summer pop, night-drive pop, anime-pop, Japanese rap, Japanese hip-hop, Japanese R&B, Japanese neo-soul, and similar releases.
- Anime/OST-like music is allowed as one lane inside the channel, but this is not an anime OST-only channel.
- If the human explicitly names a different channel such as `Soft Hour Radio`, do not use this profile unless the human also explicitly asks for Tokyo Daydream visuals.
- Keep `Tokyo Daydream Radio` visually distinct from Soft Hour Radio.
- New Tokyo Daydream playlist planning should alternate visual systems across releases when practical: one animated/anime moving-video release, then one photorealistic friend-taken still-image release, then repeat. Use recent Tokyo releases to keep this roughly every other upload; do not force the alternation if a human explicitly requests a specific visual style or if an unfinished workspace already has assets in the other style.

## Visual Identity

- Music identity: popular J-pop first. Keep the sound accessible, hook-driven, vocal, and playlist-friendly. Do not make every release feel like anime OST.
- Tokyo Daydream now has two allowed visual systems:
  - `animated_moving_video`: for mainstream J-pop, city-pop, dance-pop, synth-pop, pop-rock, anime-pop, arcade/game-center pop, fantasy/anime-feeling J-pop, and other releases that should feel like Japanese animation. This lane uses an animated/anime/illustrated cover plus a short Gemini/Dreamina/Seedance loop video.
  - `photorealistic_still_image`: for Japanese rap, Japanese hip-hop, Japanese R&B, Japanese neo-soul, trap-soul, boom-bap, Tokyo/Shibuya street R&B, and other hipper Japan vocal lanes. This lane uses a photorealistic friend-taken smartphone/Instagram still image only, with app-managed lower-left lyrics and lower-right spectrum during final render.
- For the animated moving-video lane, the legacy signature remains: exactly three people walking toward the viewer in a front-view composition. The camera/viewer sees the people from the front, preferably a medium-wide or full-body view rather than a close-up face shot. The three people stay centered and visually important.
- For the photorealistic still-image lane, do not force the three-person walking signature. Use natural candid Japanese street/lifestyle photography: stylish clearly adult Japanese friends, solo woman/man, couple, or small group in Shibuya, Shimokitazawa, Koenji, Harajuku, Daikanyama, a record shop, small live bar, club-side alley, rooftop, late-night convenience-store street, train station exit, or Tokyo streetwear scene. Prefer a friend-taken phone-photo feeling, slight focus shake or motion softness, natural side/three-quarter angles, medium framing, visible environment, and hip streetwear. Avoid glossy idol portraits, studio fashion campaigns, celebrity likenesses, minors, school uniforms, and over-retouched AI-beauty close-ups.
- In the animated lane, any visual text must fit around the centered three-person silhouette. Do not push people sideways. In the photorealistic still-image lane, any visual text must fit around the candid subject and leave lower-left/lower-right space for app-managed lyrics and spectrum.
- Background adapts to the release: Tokyo street, forest path, beach, rainy city, night park, station road, fantasy forest, seaside walk, neon alley, or similar Japan-themed scene.
- Animated lane style must be animated, anime, illustrated, or stylized. Avoid photorealistic/live-action looks in that lane.
- Photorealistic still-image lane must be realistic photography, not anime, illustration, 3D render, painterly art, or graphic design.

## Cover

- Create one final 16:9 cover first.
- In the animated moving-video lane, the cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
- In the photorealistic still-image lane, the cover is the final video visual itself; do not make or upload a provider loop video.
- Do not put `Tokyo Daydream Radio`, the channel name, a channel logo, or a brand line on the cover/first-frame.
- If text is useful, use only a short integrated J-pop/style phrase such as `J-POP`, `CITY POP`, `ANIME POP`, `J-POP DRIVE`, `SUMMER J-POP`, `J-RAP`, `TOKYO R&B`, or `J-HIP-HOP`.
- Do not add title sentences, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same subject placement, clothing colors, lighting, palette, background landmarks, and camera angle from the cover. For animated moving-video releases, preserve the same three people. For photorealistic still-image releases, preserve the same candid photo subject and street/lifestyle scene.
- Use large natural click text such as `J-POP`, `CITY POP`, `ANIME POP`, `J-POP DRIVE`, `SUMMER J-POP`, `J-RAP`, `TOKYO R&B`, or `J-HIP-HOP`. Photorealistic hip-hop/R&B thumbnails may also be text-free when the candid image is strong.
- Keep thumbnail text directly on the image with a transparent background. Use font weight, color, subtle shadow, thin outline, or local contrast for readability; do not use black boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, stickers, badges, pills, capsules, or any filled label shape behind text.
- Do not add `TOKYO DAYDREAM RADIO`, the channel name, or a channel logo.
- Keep the same full-bleed two-line treatment for Tokyo/city, forest/nature, and beach versions.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, `1時間`, clocks, or timers.

## Loop Video

- Use Dreamina/Seedance or Gemini only for the animated moving-video lane. Do not create a loop video for the photorealistic still-image lane.
- For photorealistic Japanese hip-hop/R&B/rap releases, queue final render with:

```bash
scripts/openclaw-release render-video --release-id RELEASE_ID --allow-still-image-video --video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars --lyrics-overlay --lyrics-overlay-style editorial-lower-left
```

- For Dreamina/Seedance, use `1.0 Fast`, first-frame/start-frame only, no Omni Reference, no last-frame/end-frame reference, `16:9`, `720p`, exactly `10 seconds`. Do not upload both first and last frames, because Dreamina switches that setup back to `2.0 Fast`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `10 seconds`, `5 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
- The loop video should keep the three people walking toward the camera while the camera dollies backward at the same pace. The people must not grow larger or smaller in frame.
- Keep the three-person silhouette at roughly the same screen size and centered placement throughout the clip. Reject/regenerate if the people noticeably scale up, the frame feels like a dolly-in, or the camera zooms into the subjects.
- Let the side/background environment provide most of the motion: street lights, signs, rain, water, trees, reflections, people far in the background, or parallax should move naturally around the centered subjects.
- The final moment should return close to the opening composition, camera distance, lighting, palette, and subject placement while maintaining natural motion, so the app's loop crossfade does not feel like a jump.
- If Dreamina rejects generation for inappropriate content, copyright, moderation, or policy reasons, follow the shared 10-attempt retry rule in `README.md` and `docs/openclaw-visual-assets.md`: send Slack before every retry, remove protected IP or risky terms from the prompt, and stop before render/publish after 10 failures.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame.
Create one continuous forward-moving J-pop visual shot.
Keep the channel signature: exactly three people walking toward the viewer in a front-view composition.
The viewer should see the people from the front, preferably medium-wide or full-body rather than close-up faces.
The people walk forward naturally while the camera moves backward at the same speed, keeping the same distance from them.
The final moment should return close to the opening composition, camera distance, lighting, palette, and subject placement without becoming frozen.
Preserve the opening composition, lighting, palette, and anime/illustrated style.
If the first frame already contains a short J-pop/style phrase, keep it stable and readable. Do not invent a channel name.
Adapt the background and atmosphere to the release concept.
Add gentle environmental motion, side-background parallax, reflections, rain shimmer, particles, or soft light motion around the walking subjects.
Keep the camera at the same distance from the three people while moving backward; the three people must stay roughly the same size in frame.
No new text, subtitles, logos, UI, photorealism, live action, or extra people.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds awkward, weak, or less clickable, rewrite it while keeping the J-pop identity, mood, and real listening use case truthful.
- Provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Turkish, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese metadata.
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
