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
- Let the playlist concept decide the scene and subject. No fixed recurring mascot or required person count.
- Prefer imagery that immediately reads as a club/dance-music channel, not generic abstract neon. Stylish adult DJs, dancers, performers, club crowds, rooftop parties, festival stages, dance floors, and nightlife silhouettes are all valid directions when they match the selected style lane.
- A female DJ or dancer can be a strong subject when the concept fits, but this is a direction, not a template. Bold adult club glamour, revealing club fashion, confident dance poses, and sexy nightlife energy are allowed when they match the release. Vary the subject, pose, camera angle, venue, lighting, outfit color, and scene across releases so Club Bloom does not keep generating the same woman-at-DJ-booth image.
- Club Bloom visuals must be more click-stopping than calm BGM channels. Avoid timid, soft, polite, empty, or wallpaper-like covers and thumbnails. If the image would not grab attention in a mobile YouTube feed, reject it and regenerate before upload.
- Use high-contrast crops, dramatic stage lighting, saturated neon, glossy skin/fabric highlights, expressive movement, strong silhouettes, crowd heat, DJ/performance action, rooftop/night-drive velocity, or festival-scale lighting when they fit the lane.
- Visuals should feel clean and premium, not cluttered with random neon objects.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
- The cover must include only a large lower-left `Club Bloom` channel brand label.
- Make `Club Bloom` clearly readable on mobile playback. Target roughly 18-24% of image width, or 5-6% of image height for text cap height.
- Do not add title text, genre text, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.
- Match the scene to the selected club style lane. The image should feel like a real dance/club context through venue, lighting, performers, movement, crowd energy, fashion, or nightlife atmosphere, while still staying original and varied.
- Do not accept a cover that reads as generic ambient neon, quiet lounge art, abstract wallpaper, or a low-energy background image. The cover should already feel energetic enough to justify a strong thumbnail.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable click text that matches the selected style lane, for example `DEEP HOUSE`, `TECH HOUSE`, `MELODIC TECHNO`, `TRANCE MIX`, `BASS HOUSE`, `FESTIVAL EDM`, `WORKOUT EDM`, `UK GARAGE`, `LIQUID DNB`, `TROPICAL HOUSE`, `AFRO HOUSE`, `SYNTHWAVE DRIVE`, or `CLUB MIX`.
- Add `CLUB BLOOM` as the brand line. Keep this brand line visually consistent with the lower-left cover channel label.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.
- The thumbnail should be bolder than the cover: larger subject/action, stronger contrast, clearer facial/body silhouette when a person is present, and text that feels like a club mix hook rather than a neutral label.

## Loop Video

- Use Dreamina/Seedance or Gemini only for the moving clip.
- For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `6 seconds`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `6 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
- Animate the selected cover concept with visible rhythmic motion: light sweeps, neon reflections, LED pulses, laser haze, city light motion, stage particles, equalizer-like environmental lighting, road light streaks, or dance-floor glow.
- Preserve the large, readable lower-left `Club Bloom` text exactly for the full clip.
- The final moment should stay close to the opening composition so the app can repeat it smoothly.
- Do not add subtitles, lyrics, title text, duration text, UI, logos, full nudity, sexual acts, unsafe minors, protected brands, or real club footage.
- The loop video must visibly move. Reject weak clips where only tiny background particles move, the scene feels static, or the club energy drops below the still cover.

## Visual Rework Note

- The human flagged the currently uploaded Club Bloom release on 2026-05-15 as visually too mild. When video-generation capacity is available, keep the music/audio and remake only the visual assets: final cover, text YouTube thumbnail, and short loop video. Try Gemini first, then use Dreamina/Seedance if Gemini is on cooldown, unavailable, or blocked after retries. Then upload/replace those assets, approve the cover, queue a fresh video render, and publish/update from the new render.
- Do not regenerate the songs for this rework unless the human explicitly asks.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Club Bloom".
Create one continuous animated neon dance music visualizer shot for a Club Bloom no-vocal club release in the selected style lane.
Preserve the opening composition, lighting, palette, illustrated/stylized visual language, and the specific nightlife/dance scene from the first frame.
Preserve the large, readable lower-left "Club Bloom" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
Animate visible rhythmic environmental motion naturally present in the scene: light sweeps, neon reflections, LED pulses, laser haze, stage particles, city lights, road light streaks, dance-floor glow, or atmospheric color pulses when appropriate.
The motion must progress naturally for the full clip. Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should preserve the same crop, framing, camera distance, lighting, palette, and subject placement; only light and atmospheric details may differ.
Stable composition, no hard cuts, no photorealism, no live action, no full nudity, no sexual acts, no unsafe minors, no protected brands, no other text, no subtitles, no logos, no UI.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Default metadata language can be English unless the human asks otherwise.
- Titles should include the selected club style lane plus clear dance-listening situations such as night drive, workout, party warmup, gaming, club, running, festival, or rooftop.
- Make titles broad and public-facing first. Use the exact visual scene as atmosphere unless it is the strongest searchable hook.
- Metadata should describe the release as no-vocal/instrumental club music. Do not imply vocals, singers, lyrics, or pop songs.
- Avoid AI/process/tool hashtags and avoid overstating `hits` if the music is original.
