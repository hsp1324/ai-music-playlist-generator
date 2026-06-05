# OpenClaw Channel Profile: Club Bloom

Use this profile only after channel selection returns `Club Bloom`, or when the human explicitly says to upload to `Club Bloom`.

## Routing Contract

- Explicit channel request wins.
- Club Bloom is for no-vocal EDM, house, techno, trance, festival, workout, night-drive, gaming, club, and party-energy releases.
- Club Bloom should not publish vocal dance-pop. If a vocal club-pop concept is requested, route it to the appropriate vocal channel instead.
- Do not use this profile for mainstream pop playlists, Latin pop, K-pop, J-pop, cozy BGM, fantasy OST, or cinematic trailer music.

## Visual Identity

- Mood: energetic, neon, glossy, rhythmic, nightlife, dance, premium party.
- Style must be photorealistic still-image nightlife photography by default, not animated/anime/illustrated/poster art and not provider loop video.
- Let the playlist concept decide the exact venue, but default Club Bloom visuals should look like a hot adult nightlife moment in a place where club music naturally plays: nightclub, premium bar, lounge, rooftop club, beach club, pool party, festival VIP area, DJ booth, dance floor, neon city terrace, or yacht/harbor party.
- Prefer attractive clearly adult women partying, dancing, posing with friends, or playing/standing near a DJ booth in revealing YouTube-safe club fashion. A visible adult female DJ/BJ or club-streamer performance moment is good, but not required; a premium club/bar/lounge scene with hot adult women enjoying the music is also valid. Vary subject identity, pose, camera angle, venue, lighting, outfit color, crowd size, and action so Club Bloom does not keep generating the same woman-at-DJ-booth image.
- Revealing outfits are allowed and preferred for this channel when they stay YouTube-safe: crop tops, metallic mini dresses, sheer outer layers over opaque clothing, bikini-style festival tops, bodycon silhouettes, high boots, club gloves, dramatic makeup, and dramatic stage lighting. Do not use full nudity, visible genitals, exposed nipples, sexual acts, minors, school-uniform/teen-coded styling, fetish framing, celebrity likenesses, protected brands, or porn-style composition.
- Club Bloom visuals must be more click-stopping than calm BGM channels. Avoid timid, soft, polite, empty, or wallpaper-like covers and thumbnails. If the image would not grab attention in a mobile YouTube feed, reject it and regenerate before upload.
- Use high-contrast crops, dramatic stage lighting, saturated neon, glossy skin/fabric highlights, expressive movement, strong silhouettes, crowd heat, DJ/performance action, rooftop skyline drama, beach-club sunset color, nightclub laser haze, concert/festival-scale lighting, or open-air party atmosphere when they fit the lane.
- Visuals should feel clean and premium, not cluttered with random neon objects.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and still-image render source. Club Bloom does not create or upload a Dreamina/Seedance/Gemini loop video in normal automation.
- Do not put `Club Bloom`, the channel name, a channel logo, or a brand line on the cover/first-frame.
- If text is useful, use only a short integrated EDM/club style phrase such as `TECH HOUSE`, `BASS HOUSE`, `TRANCE MIX`, `EDM MIX`, `DEEP HOUSE`, `MELODIC TECHNO`, `FESTIVAL EDM`, or `CLUB MIX`.
- Do not add title sentences, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.
- Match the scene to the selected club style lane. The image should feel like a real club/bar/lounge/festival place where this music would play, through venue, lights, crowd energy, DJ/decks when useful, adult women in revealing club outfits, cocktails or party details, and premium nightlife atmosphere, while still staying original and varied.
- Do not accept a cover that reads as generic ambient neon, quiet lounge art, abstract wallpaper, empty venue, random glowing background, or low-energy image. Unless the human asked otherwise, reject covers that do not clearly show attractive adult nightlife subjects in a premium club, bar, lounge, festival, pool-party, rooftop, or DJ setting. The cover should already feel energetic and sexy enough to justify a strong thumbnail.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable click text that matches the selected style lane, for example `DEEP HOUSE`, `TECH HOUSE`, `MELODIC TECHNO`, `TRANCE MIX`, `BASS HOUSE`, `FESTIVAL EDM`, `WORKOUT EDM`, `UK GARAGE`, `LIQUID DNB`, `TROPICAL HOUSE`, `AFRO HOUSE`, `SYNTHWAVE DRIVE`, or `CLUB MIX`.
- Keep thumbnail text directly on the image with a transparent background. Use font weight, color, subtle shadow, thin outline, or local contrast for readability; do not use black boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, stickers, badges, pills, capsules, or any filled label shape behind text.
- Do not add `CLUB BLOOM`, the channel name, or a channel logo.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.
- The thumbnail should be bolder than the cover: stronger contrast, clearer adult female nightlife subjects, more click-stopping club glamour, and text that feels like a club mix hook rather than a neutral label. Keep it photorealistic and YouTube-safe.

## Render Visual

- Do not create or upload a Gemini, Dreamina, or Seedance loop video for normal Club Bloom releases.
- Upload the final cover and separate YouTube thumbnail, approve the cover, then queue final render as a still image:
  `scripts/openclaw-release render-video --release-id RELEASE_ID --allow-still-image-video --video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars`
- Do not pass `--loop-video`, `--loop-video-provider`, or browser-generated provider clips unless the human explicitly asks for motion on a specific release.
- Do not add subtitles, lyrics, title text, duration text, UI, logos, full nudity, exposed nipples, visible genitals, sexual acts, unsafe minors, protected brands, or real club footage to the generated images.
- Keep spectrum graphics out of the static images; the app adds lower-right `bars` spectrum during final render.

## Visual Rework Note

- The human flagged the currently uploaded Club Bloom release on 2026-05-15 as visually too mild. Keep the music/audio and remake only the visual assets: final cover and text YouTube thumbnail. Use the still-image render path above, approve the cover, queue a fresh video render, and publish/update from the new render.
- Do not regenerate the songs for this rework unless the human explicitly asks.

Still-image prompt shape:

```text
Create a photorealistic 16:9 premium nightlife still image for a no-vocal club release in the selected style lane.
The scene should look like a place where club music naturally plays: a hot nightclub, premium bar, lounge, rooftop club, beach club, pool party, festival VIP area, DJ booth, dance floor, neon city terrace, or yacht/harbor party.
Show attractive clearly adult women in revealing but YouTube-safe club outfits, enjoying the party, dancing, posing with friends, or standing near DJ/decks when the concept fits.
Use glossy neon lighting, premium nightlife atmosphere, crowd energy, cocktails or party details when useful, and a strong mobile-thumbnail composition.
If using text, keep only a short integrated EDM/club lane phrase directly on the image with transparent background. Do not invent a channel name.
No full nudity, exposed nipples, visible genitals, sexual acts, minors, teen-coded styling, school uniforms, fetish framing, celebrity likenesses, protected brands, logos, UI, spectrum bars, lyrics, or porn-style composition.
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
