# OpenClaw Channel Profile: 불송

Use this profile only after channel selection returns `불송`, or when the human explicitly asks for Buddhist scripture-inspired music.

## Routing Contract

- This profile is for Buddhist scripture-inspired vocal releases: Dhammapada/법구경-inspired songs, Heart Sutra/반야심경-inspired songs, Buddhist jazz, Buddhist hip-hop, Buddhist R&B/soul, dharma songs, mindfulness songs, compassion songs, and modern sutra-inspired music.
- Do not route Bible, Gospel, Old Testament, or New Testament worship here. Those now upload to `BibliaCanto`.
- Do not route normal Korean pop/hip-hop here unless the lyrics are explicitly Buddhist scripture/teaching based. Normal Korean pop and hip-hop belong on `HaruHaru`.
- Publish through the app on the `불송` channel. The app schedules 불송 releases as public daily at 07:00 Asia/Seoul. Do not force private visibility unless the human explicitly pauses public scheduling.

## Visual Identity

- Mood: calm, modern, reflective, respectful, spacious, inward, quietly cinematic.
- Use a photorealistic or premium cinematic-real background by default: temple path, lanterns, lotus pond, incense smoke, moonlit water, mountains, rain on stone, candlelight, meditation room, forest path, prayer beads, window light, or abstract mindful city-night scenes. It should feel like a tasteful real music visual, not clipart.
- Cute, gentle animation/anime variants are allowed occasionally when the selected concept clearly fits them. Use them only with a matching soft music lane such as cute acoustic dharma pop, gentle city-pop, warm lo-fi, soft R&B, or bright healing songs. Do not pair cute animation with solemn cinematic meditation, heavy hip-hop, or serious sutra themes unless the human explicitly asks.
- Avoid goofy parody, cheap mystic clipart, and disrespectful religious imagery.
- Prefer symbolic Buddhist imagery: lotus, lantern, temple path, incense smoke, moonlit water, mountains, rain on stone, candlelight, meditation room, forest path, empty sandals, prayer beads, window light, or abstract mindful city-night scenes.
- Avoid face-focused photorealistic Buddha depictions. Symbolic objects and atmosphere are safer.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual, YouTube thumbnail base, and first-frame reference for Gemini/Dreamina/Seedance.
- Do not add the `불송` channel label, the channel name, a channel logo, title sentences, sutra paragraphs, lyrics, subtitles, UI, duration text, watermark-like marks, or unrelated words to the cover/first-frame.
- The cover/first-frame may include one short Korean passage/theme + music-style phrase that naturally fits the artwork, such as `팔정도 명상팝`, `자비 트립합`, `무상 불교 재즈`, `반야심경 R&B`, or `법구경 힙합`.
- That phrase is the visual hook. Keep it short, readable, integrated into the image, and free of hard black rectangles, detached labels, stickers, badges, pills, or UI-like tags.

## YouTube Thumbnail

- Use the same final cover/first-frame composition as the YouTube thumbnail.
- Do not create a separate channel-branded thumbnail. Do not add `불송`, channel labels, headline blocks, black text boxes, hard rectangles, stickers, badges, pills, capsules, or detached label shapes.
- The thumbnail should keep the same short Korean passage/theme + style phrase as the first-frame when present. It can be the exact same image as the cover.
- When using `scripts/openclaw-release auto-publish-playlist` or `auto-publish-single`, pass the same image as both `--cover` and `--thumbnail`, or use `--allow-cover-as-thumbnail` when the same image is intended.

## Loop Video

- Use Gemini, Dreamina, or Seedance only for the moving clip.
- For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `7 seconds`. If the duration control is hidden on entry, gently drag/scroll the settings/control row to the right until the duration option is visible before Generate. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection.
- Do not put `7 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Set those only through provider controls when available.
- Animate calm environmental motion: lantern flicker, incense smoke, rain ripple, moonlight on water, drifting petals, soft wind, candle glow, dust in light, or slow reflections.
- Preserve the opening composition and any short Korean passage/style phrase already present. Do not add, preserve, or invent any `불송` label or channel name in the loop video.
- Queue final render with `--video-spectrum-overlay-style calm-bars`. The app enforces a very low-motion, low-opacity bar spectrum for 불송. Do not use radial/multiwave/pulse visualizers, waveform overlays, dots, particles, or busy equalizer graphics.
- The final moment should stay close to the opening composition so the app can repeat it smoothly with the 1.5 second crossfade.
- Do not add subtitles, scripture text, title text, duration text, UI, logos, disrespectful religious imagery, or photorealistic Buddha face reenactment.
- Inspect Gemini/Dreamina/Seedance clips for mid-clip scene changes. Reject/regenerate if the layout cuts to a different scene, resets the frame, changes the text, or behaves like a montage.
- Do not use conceptual terms such as `playlist`, `music visual`, `visualizer shot`, `Four Noble Truths`, `사성제`, `Eightfold Path`, or `팔정도` in the video-generation prompt when a visual description is enough. Put the Buddhist source/theme in metadata, not the video prompt, unless it is visible text already designed into the first frame.
- Prefer positive fixed-shot wording: `single fixed camera shot`, `locked-off camera`, `one uninterrupted calm environmental take`, `same composition from first to last frame`. Keep negative lists short.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame.
It is a clean Buddhist/dharma music artwork with a short Korean passage/theme + music-style phrase integrated into the image.
Create one uninterrupted calm environmental take from a locked-off camera.
Keep the same composition, crop, camera distance, lighting, palette, subject placement, and typography from first frame to final frame.
Animate calm environmental motion naturally present in the scene: lantern flicker, incense smoke, rain ripple, moonlight on water, drifting petals, soft wind, candle glow, dust in light, or slow reflections.
Keep the existing short Korean phrase stable and readable if present. Do not invent any channel name.
No new text, subtitles, lyrics, UI, added logos, disrespectful religious imagery, photorealistic Buddha face, or protected characters.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Default metadata language should be Korean unless the human asks otherwise.
- Include the selected Buddhist source/theme and release-level music lane in the title and first description paragraph.
- If using a scripture source, name it carefully, such as Dhammapada-inspired, Heart Sutra-inspired, Diamond Sutra-inspired, Lotus Sutra-inspired, or Buddhist wisdom-inspired. Do not claim exact chapter/verse coverage unless verified.
- The description must state that lyrics are original paraphrases inspired by Buddhist teaching, not direct scripture recitation.
- Keep each release in one coherent style family and name it naturally: Buddhist jazz, dharma R&B, mindful hip-hop, Buddhist neo-soul, acoustic dharma songs, cinematic meditation pop, warm lo-fi, or gentle city-pop.
- If choosing a cute/gentle animation visual direction, choose a compatible music lane and make that lane clear in the title/description. The visual style and music style must feel like one package.
- Provide localized metadata for all configured languages, but keep Korean as the default top-level title/description.
- Uploads should be app-scheduled public daily at 07:00 Asia/Seoul unless the human explicitly pauses 불송 public scheduling.
