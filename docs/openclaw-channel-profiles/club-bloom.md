# OpenClaw Channel Profile: Club Bloom

Use this profile only after channel selection returns `Club Bloom`, or when the human explicitly says to upload to `Club Bloom`.

## Routing Contract

- Explicit channel request wins.
- Club Bloom is for no-vocal EDM, house, techno, trance, festival, workout, night-drive, gaming, club, and party-energy releases.
- Club Bloom should not publish vocal dance-pop. If a vocal club-pop concept is requested, route it to the appropriate vocal channel instead.
- Do not use this profile for mainstream pop playlists, Latin pop, K-pop, J-pop, cozy BGM, fantasy OST, or cinematic trailer music.

## Visual Identity

- Mood: energetic, neon, glossy, rhythmic, nightlife, movement, dance.
- Style must be animated, anime, illustrated, stylized, or graphic poster-art. Avoid photorealistic/live-action looks.
- Let the playlist concept decide the exact venue and subject, but default Club Bloom visuals should look like an active DJ/performance moment in a desirable dance-music location, not generic abstract neon.
- Strong default locations: beach club or sunset seaside deck, rooftop skyline DJ set, packed nightclub booth, concert/festival main stage, warehouse rave, pool-party deck, open-air desert/mountain stage, yacht/harbor party, neon city terrace, or cyber club venue. Rotate these locations across releases.
- Prefer a visible adult DJ, DJ booth, mixer/decks, crowd, stage lighting, or performance action unless the human explicitly asks for a non-DJ visual. A stylish adult DJ or dancer can be a strong subject when the concept fits, but this is a direction, not a fixed template. Bold adult club glamour, revealing club fashion, confident poses, and sexy nightlife energy are allowed when they match the release. Vary subject identity, pose, camera angle, venue, lighting, outfit color, crowd size, and action so Club Bloom does not keep generating the same woman-at-DJ-booth image.
- Club Bloom visuals must be more click-stopping than calm BGM channels. Avoid timid, soft, polite, empty, or wallpaper-like covers and thumbnails. If the image would not grab attention in a mobile YouTube feed, reject it and regenerate before upload.
- Use high-contrast crops, dramatic stage lighting, saturated neon, glossy skin/fabric highlights, expressive movement, strong silhouettes, crowd heat, DJ/performance action, rooftop skyline drama, beach-club sunset color, nightclub laser haze, concert/festival-scale lighting, or open-air party atmosphere when they fit the lane.
- Visuals should feel clean and premium, not cluttered with random neon objects.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
- Do not put `Club Bloom`, the channel name, a channel logo, or a brand line on the cover/first-frame.
- If text is useful, use only a short integrated EDM/club style phrase such as `TECH HOUSE`, `BASS HOUSE`, `TRANCE MIX`, `EDM MIX`, `DEEP HOUSE`, `MELODIC TECHNO`, `FESTIVAL EDM`, or `CLUB MIX`.
- Do not add title sentences, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.
- Match the scene to the selected club style lane. The image should feel like a real DJ/performance context through venue, booth/decks, lighting, performers, movement, crowd energy, fashion, or nightlife atmosphere, while still staying original and varied.
- Do not accept a cover that reads as generic ambient neon, quiet lounge art, abstract wallpaper, empty venue, random glowing background, or a low-energy image. Unless the human asked otherwise, reject covers that do not clearly show DJ/performance context or a premium dance venue. The cover should already feel energetic enough to justify a strong thumbnail.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable click text that matches the selected style lane, for example `DEEP HOUSE`, `TECH HOUSE`, `MELODIC TECHNO`, `TRANCE MIX`, `BASS HOUSE`, `FESTIVAL EDM`, `WORKOUT EDM`, `UK GARAGE`, `LIQUID DNB`, `TROPICAL HOUSE`, `AFRO HOUSE`, `SYNTHWAVE DRIVE`, or `CLUB MIX`.
- Do not add `CLUB BLOOM`, the channel name, or a channel logo.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.
- The thumbnail should be bolder than the cover: larger subject/action, stronger contrast, clearer facial/body silhouette when a person is present, and text that feels like a club mix hook rather than a neutral label.

## Loop Video

- Use Dreamina/Seedance or Gemini only for the moving clip.
- For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `7 seconds`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `7 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
- Animate the selected cover concept with visible rhythmic motion tied to the DJ/performance location: DJ hand movement, mixer/deck LEDs, crowd movement, light sweeps, neon reflections, LED pulses, laser haze, stage lighting, ocean/sunset reflections for beach clubs, skyline light motion for rooftops, concert strobes, or dance-floor glow.
- If the first frame has a short EDM/club style phrase, keep it stable and readable. Do not invent a channel name.
- The final moment should stay close to the opening composition so the app can repeat it smoothly.
- Do not add subtitles, lyrics, title text, duration text, UI, logos, full nudity, sexual acts, unsafe minors, protected brands, or real club footage.
- The loop video must visibly move. Reject weak clips where only tiny background particles move, the scene feels static, there is no DJ/performance or premium venue read, or the club energy drops below the still cover.

## Visual Rework Note

- The human flagged the currently uploaded Club Bloom release on 2026-05-15 as visually too mild. When video-generation capacity is available, keep the music/audio and remake only the visual assets: final cover, text YouTube thumbnail, and short loop video. Try Gemini first, then use Dreamina/Seedance if Gemini is on cooldown, unavailable, or blocked after retries. Then upload/replace those assets, approve the cover, queue a fresh video render, and publish/update from the new render.
- Do not regenerate the songs for this rework unless the human explicitly asks.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame.
Create one uninterrupted animated neon dance music take for a no-vocal club release in the selected style lane.
Preserve the opening composition, lighting, palette, illustrated/stylized visual language, and the specific nightlife/dance scene from the first frame.
If the first frame already contains a short EDM/club style phrase, keep it stable and readable. Do not invent a channel name.
The scene should read as an active DJ/performance moment in a premium dance venue such as a beach club, rooftop skyline, packed nightclub, concert/festival stage, warehouse rave, pool-party deck, open-air desert/mountain stage, yacht/harbor party, neon city terrace, or cyber club.
Animate visible rhythmic environmental motion naturally present in the scene: DJ hands, mixer/deck lights, crowd movement, light sweeps, neon reflections, LED pulses, laser haze, concert strobes, ocean or skyline reflections, dance-floor glow, or atmospheric color pulses when appropriate.
The final moment should preserve the same crop, framing, camera distance, lighting, palette, and subject placement; only light and atmospheric details may differ.
No full nudity, sexual acts, unsafe minors, protected brands, new text, subtitles, logos, UI, photorealism, or live action.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation becomes an awkward keyword tail, rewrite it while keeping the selected EDM/house/techno/trance lane and one or two real listening situations truthful.
- Default metadata language can be English unless the human asks otherwise.
- Titles must put the selected club style lane or genre fusion near the front, immediately after `[playlist]`. Prefer direct YouTube mix wording such as `Progressive Trance x EDM Mix`, `Tech House Workout Mix`, `Hype Trap x EDM Mix`, `Melodic Techno Night Drive`, `Bass House Workout Mix`, `Bass Boosted EDM & Electro House Mix`, or `Festival EDM Mix`.
- After the separator, add one or two clear dance-listening situations using natural YouTube phrasing, such as `Heavy EDM for Gaming & Night Drive`, `Running Beats and Club Bass`, `Night Drive & Gaming Club Music`, or `Big Room Drops for Party Warmup`. Avoid awkward three-part use-case lists such as `for Night Roads, Gaming Focus and Club Drive`, and never use keyword tails like `Gaming Night & Workout Energy`.
- Make titles broad and public-facing first. Use the exact visual scene as atmosphere unless it is the strongest searchable hook.
- Metadata should describe the release as no-vocal/instrumental club music. Do not imply vocals, singers, lyrics, or pop songs.
- Avoid AI/process/tool hashtags and avoid overstating `hits` if the music is original.
