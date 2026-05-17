# OpenClaw Channel Profile: Cinematic Pulse

Use this profile only after channel selection returns `Cinematic Pulse`, or when the human explicitly says to upload to `Cinematic Pulse`.

## Routing Contract

- Explicit channel request wins.
- Cinematic Pulse is for no-vocal large-scale cinematic orchestra and film-score music: movie OST, trailer music, emotional film score, orchestral battle, dark fantasy confrontation, sci-fi journey, heroic, mystery tension, and orchestral scene music.
- Do not use this profile for cozy fantasy, cafe/study BGM, EDM/house, or vocal pop.

## Visual Identity

- Mood: cinematic, dramatic, large-scale, orchestral, emotional, tense, heroic, mysterious, or high-stakes.
- Style must be animated, anime, illustrated, poster-art, concept-art, or stylized. Avoid photorealistic/live-action looks.
- Composition should read quickly on mobile: one strong focal scene, bold lighting, clear silhouettes, and high contrast.
- Visuals can be intense, but avoid gore, real-world political symbols, real war footage, and protected IP.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
- The cover must include only a large lower-left `Cinematic Pulse` channel brand label.
- Make `Cinematic Pulse` clearly readable on mobile playback. Target roughly 18-24% of image width, or 5-6% of image height for text cap height.
- Do not add title text, genre text, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.
- Match the scene to the playlist concept: movie-poster landscape, final battle, dark fantasy confrontation, sci-fi journey, heroic sunrise, dark castle, robot conflict, storm, mystery hallway, emotional farewell, vast ocean, mountain horizon, or trailer-poster scene.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable click text, for example `MOVIE OST`, `CINEMATIC ORCHESTRA`, `EPIC BATTLE`, `DARK FANTASY`, `HEROIC MUSIC`, `SCI-FI ACTION`, `TRAILER MUSIC`, or `FILM SCORE`.
- Avoid juvenile game-menu wording such as `BOSS BGM`, `FINAL BOSS`, `보스`, or `보스전` unless the human explicitly asks for game-combat packaging. Cinematic Pulse should read as grand film-score / cinematic orchestra first.
- Add `CINEMATIC PULSE` as the brand line. Keep this brand line visually consistent with the lower-left cover channel label.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Loop Video

- Use Dreamina/Seedance or Gemini only for the moving clip.
- For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `6 seconds`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `6 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
- Animate the selected cover concept with visible cinematic motion: storm clouds, banners, sparks, energy pulses, engine glow, portal light, dust, rain, embers, distant silhouettes, or weapon/armor light when appropriate.
- Preserve the large, readable lower-left `Cinematic Pulse` text exactly for the full clip.
- The final moment should stay close to the opening composition so the app can repeat it smoothly.
- Do not add blood, gore, real war footage, protected characters, franchise references, subtitles, UI, or extra text.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Cinematic Pulse".
Create one continuous animated cinematic music visualizer shot for a Cinematic Pulse instrumental release.
Preserve the opening composition, lighting, palette, illustrated/stylized poster-art visual language, and the specific cinematic scene from the first frame.
Preserve the large, readable lower-left "Cinematic Pulse" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
Animate powerful but controlled cinematic motion already present or naturally implied by the scene: storm clouds, sparks, embers, dust, banners, energy pulses, engine glow, portal light, rain, distant silhouettes, or atmospheric light movement when appropriate.
The motion must progress naturally for the full clip. Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should preserve the same crop, framing, camera distance, lighting, palette, and subject placement; only atmospheric details may differ.
Stable composition, no hard cuts, no photorealism, no live action, no gore, no real war footage, no protected characters, no franchise references, no other text, no subtitles, no logos, no UI.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds childish, vague, or less cinematic, rewrite it while keeping the film-score/orchestra lane and real listening use case truthful.
- Default metadata language can be English unless the human asks otherwise.
- Titles should be bold, search-friendly, and immediately understandable to a broad YouTube audience. Include cinematic music, cinematic orchestra, movie OST, film score, trailer music, final battle scene, orchestral battle, emotional film score, mystery tension, fantasy writing, or epic scene use cases when accurate.
- Make titles broad and public-facing first. Use exact visual scene details as atmosphere unless they are the strongest searchable hook.
- Do not use `Boss BGM`, `Final Boss Music`, `Final Boss Focus Music`, `보스`, `보스전`, or bare `BGM` in public YouTube titles. Avoid wording that sounds like a niche game menu rather than a cinematic music video.
- Use varied cinematic title families across releases: final battle scene, dark fantasy film score, heroic trailer music, emotional film score, sci-fi cinematic music, mystery tension score, grand journey orchestra, orchestral battle music, epic writing music, and movie OST focus. These are direction families, not fixed templates to repeat mechanically.
- Reusing a strong channel-fit title shape is better than inventing a weak off-brand one, but do not lock the channel into only a few example titles.
- Avoid naming existing films, games, franchises, composers, studios, or characters.
