# OpenClaw Channel Profile: 불송

Use this profile only after channel selection returns `불송`, or when the human explicitly asks for Buddhist scripture-inspired music.

## Routing Contract

- This profile is for Buddhist scripture-inspired Korean hip-hop/rap vocal releases by default: Dhammapada/법구경-inspired Buddhist hip-hop, Heart Sutra/반야심경-inspired Korean rap, mindful hip-hop, mellow boom bap, Buddhist hip-hop soul, Buddhist trap-soul, and modern sutra-inspired Korean rap songs. R&B, jazz, acoustic, pop, lo-fi, or cinematic lanes are secondary exceptions only when the human explicitly asks for them or an already-started release is clearly in that lane.
- Do not route Bible, Gospel, Old Testament, or New Testament worship here. Those now upload to `BibliaCanto`.
- Do not route normal Korean pop/hip-hop here unless the lyrics are explicitly Buddhist scripture/teaching based. Normal Korean pop and hip-hop belong on `HaruHaru`.
- Publish through the app on the `불송` channel. The app schedules 불송 releases as public daily at 07:00 Asia/Seoul. Do not force private visibility unless the human explicitly pauses public scheduling.

## Music And Suno Style

- Choose one modern release-level lane before Suno generation and keep every track inside it.
- 불송 is hip-hop-first. Preferred lanes are `불교 힙합`, `불경 힙합`, mindful hip-hop, Korean Buddhist rap, mellow boom bap, Buddhist hip-hop soul, or restrained Buddhist trap-soul.
- Do not use obscure coined genre names in YouTube titles, thumbnail phrases, descriptions, or tags. Use plain audience-friendly wording such as `불교 힙합`, `불경 힙합`, `Buddhist hip-hop`, or `Korean Buddhist rap`.
- Avoid trot, ppongjjak, and old Korean cabaret-pop completely unless the human explicitly asks for them. Do not use Korean trot rhythm, two-beat ppongjjak bounce, trot vocal ornaments, accordion/brass trot clichés, nightclub/cabaret trot arrangement, or old-TV trot mood.
- In Suno Advanced Options / excluded styles, include blockers such as `trot, Korean trot, ppongjjak, 뽕짝, 트로트, trot vocal, cabaret trot, old Korean trot, two-beat trot bounce, accordion trot, brass trot`.
- If a generated track comes out with strong trot/ppongjjak feel, reject it and regenerate in a clearer hip-hop/rap lane.

## Visual Identity

- Mood: calm, modern, reflective, respectful, spacious, inward, quietly cinematic.
- Default visual package: a respectful photorealistic or premium cinematic-real Buddha / Buddha-inspired figure with a warm, gentle expression, seated in a quiet temple or meditation room, listening to music while reading or holding an open Buddhist sutra.
- Diamond Sutra / 금강경-inspired releases have an extra human-subject rule. If a monk or monastic figure is used, make that visual intentionally animated, illustrated, or gentle anime/stylized rather than photorealistic. If a photorealistic human appears, use a clearly adult woman practicing Buddhist reflection during a temple stay: natural Instagram-like candid realism, modest modern temple-stay clothing, headphones or earbuds as a subtle music cue, and a respectful temple/Buddha setting. She must not be a monk, must not wear monk robes, and must not look shaved-head or monastic.
- This is a required subject package, not optional atmosphere. Reject and regenerate cover/thumbnail/first-frame assets that only show a temple, lotus pond, mountain, lanterns, incense, abstract Buddhist symbols, or background scenery without the Buddha figure, open sutra, and subtle music-listening cue.
- The scene should feel contemplative and musical, not theatrical: soft golden candle or lantern light, incense smoke, lotus, prayer beads, wooden table, paper texture, warm window light, temple architecture, garden rain, or mountain/forest quiet can support the main figure.
- The music-listening cue must be subtle and respectful. Use a small low-profile speaker, simple headphones resting nearby, or understated earbuds/headphones only when they do not make the Buddha figure look comedic, commercial, or gadget-focused.
- The open sutra should be visually important, but do not invent large readable scripture blocks. Use subtle calligraphy, softly blurred text, or page texture unless the exact short phrase was intentionally designed into the cover.
- Cute, gentle animation/anime variants are no longer the normal default. Use them only when the human explicitly asks or when a very soft release concept clearly calls for them; otherwise use the photorealistic Buddha-reading-sutra scene.
- Avoid goofy parody, cheap mystic clipart, fantasy deity effects, golden statue-only wallpaper, idol/model portrait styling, exaggerated smiles, singing/dancing Buddha depictions, and disrespectful religious imagery.
- The Buddha figure may show a serene face and expression, but avoid tight face-only idol portraits. Keep the sutra, listening cue, and calm Buddhist environment visible so the image reads as a respectful Buddhist music scene.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual, YouTube thumbnail base, and first-frame reference for Gemini/Dreamina/Seedance.
- The cover should normally depict the photorealistic Buddha-reading-sutra scene described above: warm gentle expression, open sutra, subtle music-listening cue, and calm temple/meditation atmosphere.
- For Diamond Sutra / 금강경 hip-hop covers, choose either an animated/stylized monk visual or a photorealistic temple-stay woman visual. Do not create a photorealistic monk cover unless the human explicitly asks for it. When choosing the woman visual, make it feel like a natural friend-taken temple-stay photo of a respectful adult practitioner, not a model shoot and not a monastic portrait.
- Do not accept scenery-only Buddhist backgrounds as final 불송 cover art. The Buddha-reading-sutra subject must be visible before upload.
- Do not add the `불송` channel label, the channel name, a channel logo, title sentences, sutra paragraphs, lyrics, subtitles, UI, duration text, watermark-like marks, or unrelated words to the cover/first-frame.
- The cover/first-frame may include one short Korean passage/theme + hip-hop music-style phrase that naturally fits the artwork, such as `법구경 힙합`, `불경 힙합`, `마음챙김 랩`, `자비 힙합`, or `반야심경 랩`. Put this phrase in upper-left safe negative space when possible. Avoid obscure coined genre wording.
- That phrase is the visual hook. Keep it short, readable, integrated into the image, and on a transparent background. Use font weight, color, subtle shadow, thin outline, or local contrast for readability; do not use hard black rectangles, semi-transparent dark panels, white or colored rectangles, gradient scrims, detached labels, stickers, badges, pills, capsules, or UI-like tags.

## YouTube Thumbnail

- Use the same final cover/first-frame composition as the YouTube thumbnail.
- Preserve the same Buddha figure, open sutra, listening cue, lighting, palette, and setting from the cover. The thumbnail can crop slightly closer for click clarity, but it must not become a separate Buddha portrait or a new scene.
- Do not create a separate channel-branded thumbnail. Do not add `불송`, channel labels, headline blocks, black text boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, hard rectangles, stickers, badges, pills, capsules, or detached label shapes. Any text that remains from the cover/first-frame must sit directly on the image with a transparent background.
- The thumbnail should keep the same short Korean passage/theme + style phrase as the first-frame when present. It can be the exact same image as the cover.
- When using `scripts/openclaw-release auto-publish-playlist` or `auto-publish-single`, pass the same image as both `--cover` and `--thumbnail`, or use `--allow-cover-as-thumbnail` when the same image is intended.

## Loop Video

- Use Gemini, Dreamina, or Seedance only for the moving clip.
- For Dreamina/Seedance, use `1.0 Fast`, first-frame/start-frame only, no Omni Reference, no last-frame/end-frame reference, `16:9`, `720p`, exactly `10 seconds`. Do not upload both first and last frames, because Dreamina switches that setup back to `2.0 Fast`. If the duration control is hidden on entry, gently drag/scroll the settings/control row to the right until the duration option is visible before Generate. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection.
- Do not put `10 seconds`, `5 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Set those only through provider controls when available.
- Animate calm environmental motion: lantern flicker, candle glow, incense smoke, dust in window light, rain ripple, garden leaves, page-edge movement, robe fabric settling, soft reflections, or a gentle speaker/headphone light if it already exists in the first frame.
- Keep the Buddha figure, face, hands, sutra, listening cue, and camera distance stable. The figure should not sing, dance, perform, lip-sync, look at the viewer dramatically, or turn into a different person/statue mid-clip.
- Preserve the opening composition and any short Korean passage/style phrase already present. Do not add, preserve, or invent any `불송` label or channel name in the loop video.
- Queue final render with `--video-spectrum-overlay-style calm-bars`. The app enforces a very low-motion, low-opacity bar spectrum for 불송. Do not use radial/multiwave/pulse visualizers, waveform overlays, dots, particles, or busy equalizer graphics.
- The final moment should stay close to the opening composition so the app can repeat it smoothly with its provider-aware loop crossfade.
- Do not add subtitles, large scripture text, title text, duration text, UI, logos, disrespectful religious imagery, exaggerated divine glow, idol/model posing, or comedic modern-gadget focus.
- Inspect Gemini/Dreamina/Seedance clips for mid-clip scene changes. Reject/regenerate if the layout cuts to a different scene, resets the frame, changes the text, or behaves like a montage.
- Do not use conceptual terms such as `playlist`, `music visual`, `visualizer shot`, `Four Noble Truths`, `사성제`, `Eightfold Path`, or `팔정도` in the video-generation prompt when a visual description is enough. Put the Buddhist source/theme in metadata, not the video prompt, unless it is visible text already designed into the first frame.
- Prefer positive fixed-shot wording: `single fixed camera shot`, `locked-off camera`, `one uninterrupted calm environmental take`, `same composition from first to last frame`. Keep negative lists short.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame.
It is a respectful photorealistic Buddhist music artwork: a serene Buddha / Buddha-inspired figure with a warm gentle expression, listening to music while reading or holding an open Buddhist sutra in a quiet temple or meditation room.
Create one uninterrupted calm environmental take from a locked-off camera.
Keep the same composition, crop, camera distance, lighting, palette, subject placement, and typography from first frame to final frame.
Animate only gentle ambient details already present in the scene: lantern flicker, candle glow, incense smoke, dust in window light, garden rain, page-edge movement, robe fabric settling, or slow reflections.
Keep the Buddha figure, serene face, hands, open sutra, and subtle music-listening cue stable and respectful.
Keep the existing short Korean phrase stable and readable if present. Do not invent any channel name.
No new text, subtitles, lyrics, UI, added logos, scene changes, singing, dancing, comedic gadget focus, exaggerated divine effects, disrespectful religious imagery, or protected characters.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Default metadata language should be Korean unless the human asks otherwise.
- Include the selected Buddhist source/theme and release-level music lane in the title and first description paragraph.
- If using a scripture source, name it carefully, such as Dhammapada-inspired, Heart Sutra-inspired, Diamond Sutra-inspired, Lotus Sutra-inspired, or Buddhist wisdom-inspired. Do not claim exact chapter/verse coverage unless verified.
- The description must state that lyrics are original paraphrases inspired by Buddhist teaching, not direct scripture recitation.
- Keep each release in one coherent style family and name it naturally. By default use hip-hop-first wording: `불교 힙합`, `불경 힙합`, `마음챙김 랩`, `Buddhist hip-hop`, or `Korean Buddhist rap`. Avoid obscure coined genre labels; avoid trot/ppongjjak wording and sound unless the human explicitly asks for it.
- Do not relabel an already-rendered non-hip-hop 불송 video as hip-hop. If the finished video artwork/text and audio already point to Dharma pop / 다르마팝 / acoustic Dharma songs / 다르마송, keep metadata truthful to that finished asset instead of forcing the new hip-hop default.
- If choosing a cute/gentle animation visual direction, choose a compatible music lane and make that lane clear in the title/description. The visual style and music style must feel like one package.
- Provide localized metadata for all configured languages, but keep Korean as the default top-level title/description.
- Uploads should be app-scheduled public daily at 07:00 Asia/Seoul unless the human explicitly pauses 불송 public scheduling.
