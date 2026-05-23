# OpenClaw Channel Profile: Storylight OST

Use this profile only after channel selection returns `Storylight OST`.

## Routing Contract

- Explicit channel request wins.
- Storylight OST is for no-vocal playful Japanese-style game/anime OST and BGM: arcade games, fantasy games, cute RPG towns, anime side stories, mascot chases, item shops, mini-games, and light adventure scenes.
- Do not use this profile for practical cafe/study BGM, epic trailer/battle music, EDM/house, vocal J-pop, or popular-song remakes/covers.

## Visual Identity

- Mood: playful, bright, mischievous, cute, game-like, Japanese OST, light adventure.
- Style must be animated, anime, illustrated, game-background, pixel-art-inspired, cel-shaded, colorful poster-art, or stylized fantasy-game. Avoid photorealistic/live-action looks.
- The specific release concept decides the setting. Do not force a fixed mascot, fixed character count, or repeated composition.
- Visuals should make the listener feel they entered a fun Japanese game/anime scene.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
- Do not put `Storylight OST`, the channel name, a channel logo, or a brand line on the cover/first-frame.
- If text is useful, use only a short integrated game/anime BGM phrase such as `GAME OST`, `ANIME BGM`, `ARCADE BGM`, `CUTE GAME BGM`, `HAPPY GAME MUSIC`, or `COZY GAME MUSIC`.
- Do not add title sentences, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.
- Keep the scene coherent with the playlist concept: arcade cabinets, item shop, fantasy RPG plaza, magical menu, mini-game field, school-game hallway, festival street, puzzle room, toy-like dungeon, quest map, or other playful game/anime location.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable click text, for example `GAME OST`, `ANIME BGM`, `ARCADE BGM`, `CUTE RPG`, `KAWAII GAME`, `PLAYFUL OST`, or `FANTASY GAME`.
- Do not add `STORYLIGHT OST`, the channel name, or a channel logo.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Loop Video

- Use Dreamina/Seedance or Gemini only for the moving clip.
- Storylight OST must have an uploaded provider-generated loop MP4 before final render. Do not use `--allow-still-image-video`, `--video-render-source-mode still_image`, or a cover-only final render for this channel unless the human explicitly names this exact release and asks for a still-image exception.
- For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `7 seconds`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `7 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
- The loop video should animate the selected cover concept with visible playful game/anime motion: cabinet light pulses, pixel sparkle, floating item icons, UI-like magical glows, bouncing props, lantern shimmer, shop lights, flag movement, toy-like particles, confetti, leaves, water shimmer, or soft character/mascot idle motion when appropriate.
- If the first frame has a short game/anime BGM phrase, keep it stable and readable. Do not invent a channel name.
- Keep the final moment close to the opening crop, framing, camera distance, lighting, palette, and subject placement so the app can repeat it smoothly.
- If the visual concept involves a stage, path, map, or mini-game, gentle environmental motion is allowed. Do not force people walking unless the concept specifically calls for characters.
- Do not use protected IP, real studio names, franchise names, exact game titles, character names, or `in the style of` wording.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame.
Create one uninterrupted playful Japanese game/anime BGM visual take for a no-vocal instrumental release.
Preserve the opening composition, lighting, palette, illustrated/stylized visual language, and the specific arcade, fantasy-game, anime-side-story, or cute RPG scene from the first frame.
If the first frame already contains a short game/anime BGM phrase, keep it stable and readable. Do not invent a channel name.
Animate visible playful environmental motion naturally present in the scene: cabinet light pulses, pixel sparkle, floating item icons, magical UI-like glow, bouncing props, lantern shimmer, shop lights, flags, toy-like particles, confetti, leaves, water shimmer, or soft idle motion when appropriate.
The final moment should preserve the same crop, framing, camera distance, lighting, palette, and subject placement; only ambient details may differ.
No protected characters, studio references, new text, subtitles, logos, UI, photorealism, or live action.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds like a game menu label or less clickable, rewrite it while keeping the playful game/anime-BGM identity and listener benefit truthful.
- Default metadata language can be English unless the human asks otherwise.
- Titles should sell the listening benefit first: happy mood, mood boost, cute background music, work focus, reading, gaming, relaxing, light focus, cozy focus, or cheerful background listening.
- Include broad game/anime-BGM keywords such as `Cute Game BGM`, `Happy Game Music`, `Cozy Fantasy Game BGM`, `Anime Game BGM`, or `Feel-Good Arcade BGM`.
- Make titles broad and public-facing first. Use exact visual scene details as atmosphere in the description unless they are already a strong public search hook.
- Do not lead titles with narrow in-game mechanic, prop, or location wording such as `Bonus Stage Music`, `Item Shop BGM`, `Quest Board`, `Inventory Screen`, `Potion Counter`, or `Save Point`. Those details can appear in the description or tracklist.
- Strong title shapes: `[playlist] Feel-Good Arcade BGM | Happy Game Music for Gaming, Work and Mood Boost`; `[playlist] Cozy Fantasy Game BGM | Happy Music for Reading, Work and Gaming`; `[playlist] Cute Game BGM for Work | Cozy Happy Music for Focus and Relaxing`.
- Avoid claiming a specific existing game, anime, film, studio, or composer.
