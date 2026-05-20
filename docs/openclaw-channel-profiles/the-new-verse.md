# OpenClaw Channel Profile: 불송

Use this profile only after channel selection returns `불송`, or when the human explicitly asks for Buddhist scripture-inspired music.

## Routing Contract

- This profile is for Buddhist scripture-inspired vocal releases: Dhammapada/법구경-inspired songs, Heart Sutra/반야심경-inspired songs, Buddhist jazz, Buddhist hip-hop, Buddhist R&B/soul, dharma songs, mindfulness songs, compassion songs, and modern sutra-inspired music.
- Do not route Bible, Gospel, Old Testament, or New Testament worship here. Those now upload to `BibliaCanto`.
- Do not route normal Korean pop/hip-hop here unless the lyrics are explicitly Buddhist scripture/teaching based. Normal Korean pop and hip-hop belong on `HaruHaru`.
- Until the human reviews tomorrow, uploads to this channel should remain private, not scheduled public.

## Visual Identity

- Mood: calm, modern, reflective, respectful, spacious, inward, quietly cinematic.
- Style may be illustrated, anime/stylized, painterly, cinematic 2D, or modern editorial. Avoid goofy parody, cheap mystic clipart, and disrespectful religious imagery.
- Prefer symbolic Buddhist imagery: lotus, lantern, temple path, incense smoke, moonlit water, mountains, rain on stone, candlelight, meditation room, forest path, empty sandals, prayer beads, window light, or abstract mindful city-night scenes.
- Avoid face-focused photorealistic Buddha depictions. Symbolic objects and atmosphere are safer.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Gemini/Dreamina/Seedance.
- The cover must include only a large lower-left `불송` channel brand label until the human renames the channel.
- Make the channel label clearly readable on mobile playback. Target roughly 18-24% of image width, or 5-6% of image height for text cap height.
- Keep the channel label as integrated typography. Do not place it on a solid black rectangle, opaque dark box, plaque, banner, pill, capsule, sticker, or detached background shape. If readability needs help, use subtle shadow, thin outline, or gentle local contrast that still feels natural in the art.
- Do not add title text, sutra paragraphs, lyrics, subtitles, UI, logos, duration text, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, and camera angle from the cover.
- Add short readable click text tied to the selected Buddhist teaching and music lane.
- Good thumbnail wording can include `BUDDHIST JAZZ`, `DHARMA R&B`, `MINDFUL HIP-HOP`, `SUTRA SONGS`, `불경 노래`, `법구경 힙합`, `반야심경 R&B`, or a natural Korean hook.
- Add `불송` as the brand line.
- Keep all thumbnail text inside safe margins. Do not add duration badges unless the human explicitly asks.
- Do not use a black text box or hard rectangular background behind the channel name.

## Loop Video

- Use Gemini, Dreamina, or Seedance only for the moving clip.
- For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `6 seconds`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection.
- Do not put `6 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Set those only through provider controls when available.
- Animate calm environmental motion: lantern flicker, incense smoke, rain ripple, moonlight on water, drifting petals, soft wind, candle glow, dust in light, or slow reflections.
- Preserve the large lower-left `불송` text exactly for the full clip.
- Queue final render with `--video-spectrum-overlay-style none`. 불송 must not use app-rendered spectrum bars, radial/multiwave/pulse visualizers, waveform overlays, dots, particles, or equalizer graphics.
- The final moment should stay close to the opening composition so the app can repeat it smoothly.
- Do not add subtitles, scripture text, title text, duration text, UI, logos, disrespectful religious imagery, or photorealistic Buddha face reenactment.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "불송".
Create one continuous animated Buddhist scripture-inspired music visualizer shot.
Preserve the opening composition, lighting, palette, respectful modern visual language, and the selected Buddhist/dharma atmosphere from the first frame.
Preserve the large, readable lower-left "불송" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
The channel label must be integrated into the artwork; no solid black rectangle, opaque dark box, plaque, banner, pill, capsule, sticker, or detached text background behind it.
Animate calm environmental motion naturally present in the scene: lantern flicker, incense smoke, rain ripple, moonlight on water, drifting petals, soft wind, candle glow, dust in light, or slow reflections.
The motion must progress naturally for the full clip. Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should preserve the same crop, framing, camera distance, lighting, palette, and subject placement; only ambient details may differ.
Stable composition, no hard cuts, no disrespectful religious imagery, no photorealistic Buddha face, no protected characters, no other text, no subtitles, no logos, no UI.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Default metadata language should be Korean unless the human asks otherwise.
- Include the selected Buddhist source/theme and release-level music lane in the title and first description paragraph.
- If using a scripture source, name it carefully, such as Dhammapada-inspired, Heart Sutra-inspired, Diamond Sutra-inspired, Lotus Sutra-inspired, or Buddhist wisdom-inspired. Do not claim exact chapter/verse coverage unless verified.
- The description must state that lyrics are original paraphrases inspired by Buddhist teaching, not direct scripture recitation.
- Keep each release in one coherent style family and name it naturally: Buddhist jazz, dharma R&B, mindful hip-hop, Buddhist neo-soul, acoustic dharma songs, or cinematic meditation pop.
- Provide localized metadata for all configured languages, but keep Korean as the default top-level title/description.
- Uploads should remain private for now; the human will decide public scheduling later.
