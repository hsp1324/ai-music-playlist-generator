# OpenClaw Channel Profile: Cinematic Pulse

Use this profile only after channel selection returns `Cinematic Pulse`, or when the human explicitly says to upload to `Cinematic Pulse`.

## Routing Contract

- Explicit channel request wins.
- Cinematic Pulse is for no-vocal cinematic orchestra and game/film-score music: movie OST, trailer music, emotional film score, orchestral battle, dark fantasy confrontation, sci-fi journey, heroic, mystery tension, lyrical game orchestra, and orchestral scene music.
- Cinematic Pulse also receives former Storylight-style no-vocal game/anime/theme-park BGM because `Storylight OST` is manual-only. Treat that as a separate former-Storylight lane with truthful cute game/anime/arcade/theme-park packaging.
- Never cross-package lanes. If the audio is playful, cute, whimsical, cozy, arcade, anime side-story, item-shop, fantasy town, theme-park, or amusement-park BGM, do not use dark fantasy, cinematic battle, final battle, epic orchestra, or ominous movie-poster titles/thumbnail phrases. Retitle and re-visualize it as cute game/anime/theme-park BGM instead.
- If the title, thumbnail, or cover says `DARK FANTASY`, `CINEMATIC ORCHESTRA`, `EPIC BATTLE`, `TRAILER MUSIC`, or a similar serious film-score hook, every lead-block track must actually be cinematic/orchestral/film-score/game-orchestra enough to support that promise. Do not hide cute/playful fallback tracks at the front of a dark fantasy release.
- Do not use this profile for cozy fantasy, cafe/study BGM, EDM/house, or vocal pop.

## Visual Identity

- Mood: cinematic, dramatic, orchestral, emotional, tense, heroic, mysterious, high-stakes, gentle, bittersweet, lyrical, or graceful depending on the release.
- Cinematic Pulse has two approved visual lanes:
  - **Film-real lane:** photorealistic cinematic film-still / high-end movie-poster realism.
  - **Premium game-animation lane:** original high-end sci-fi/fantasy action-RPG key art with a beautiful adult heroine, elegant armor or futuristic fashion, dramatic game-cinematic lighting, and polished anime-real/game-animation rendering. This can evoke a modern console action RPG mood, but must not copy Stellar Blade, its characters, outfits, logos, UI, or exact composition.
- The cover, thumbnail base, and loop video should feel like a dramatic movie frame, premium trailer shot, or high-end game key visual with cinematic lighting, depth of field, atmosphere, and believable materials.
- Do not use documentary-looking real war footage, news footage, real political imagery, celebrity likenesses, protected film/game characters, or exact franchise references. Photorealistic means original cinematic realism, not copied real media.
- Composition should read quickly on mobile: one strong focal scene, bold lighting, clear silhouettes, and high contrast.
- Visuals can be intense, but avoid gore, real-world political symbols, real war footage, and protected IP.
- App-rendered spectrum must use `bars` for Cinematic Pulse. Do not use `radial`, `multiwave`, `pulse`, small dots/particles, or busy waveform presets for this channel. Keep the bar spectrum clean, restrained, and non-cluttered.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Gemini when a moving clip is needed.
- Do not put `Cinematic Pulse`, the channel name, a channel logo, or a brand line on the cover/first-frame image.
- Cinematic Pulse cover/first-frame art should usually include one short integrated cinematic style phrase in the upper-left area so the video does not feel empty and will not collide with lower-left lyric overlays on vocal channels. Use phrases such as `MOVIE OST`, `CINEMATIC ORCHESTRA`, `FILM SCORE`, `TRAILER MUSIC`, `DARK FANTASY`, or `HEROIC MUSIC`.
- For former Storylight-style releases, use truthful phrases such as `GAME OST`, `ANIME BGM`, `CUTE GAME BGM`, `FANTASY GAME OST`, `ARCADE BGM`, or `THEME PARK BGM` instead of dark fantasy / battle / movie-orchestra phrases.
- Keep that style phrase tasteful and movie-poster-like: integrated typography, subtle shadow, thin outline, or local contrast is fine, but the text background must be transparent. Do not use detached black boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, badges, plaques, stickers, channel labels, or long title sentences.
- Do not add title sentences, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.
- Match the scene to the playlist concept: movie-poster landscape, final battle, dark fantasy confrontation, sci-fi journey, heroic sunrise, dark castle, robot conflict, storm, mystery hallway, emotional farewell, vast ocean, mountain horizon, premium game heroine scene, gentle fantasy city, moonlit sci-fi garden, quiet post-battle memory, or trailer/key-art scene.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Use the same upper-left style phrase family as the cover/first-frame, with thumbnail readability adjustments only if needed. Examples: `MOVIE OST`, `CINEMATIC ORCHESTRA`, `EPIC BATTLE`, `DARK FANTASY`, `HEROIC MUSIC`, `SCI-FI ACTION`, `TRAILER MUSIC`, or `FILM SCORE`. Keep the text directly on the image with no filled background shape.
- The thumbnail phrase must match the actual track list. If reused or newly uploaded tracks are cute/playful anime-game BGM, use the former-Storylight phrase family and visual mood; do not leave a dark fantasy thumbnail on cute audio.
- Avoid juvenile game-menu wording such as `BOSS BGM`, `FINAL BOSS`, `보스`, or `보스전` unless the human explicitly asks for game-combat packaging. Game-related Cinematic Pulse packaging should read as premium game orchestra / anime action-RPG OST / cinematic game score, not a menu label.
- Do not add `CINEMATIC PULSE`, the channel name, or a channel logo.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Render Visual

- Create a very high quality 16:9 cover/first-frame image, preferably 2560x1440 (`2k`) or at minimum 1920x1080. Use the film-real lane for movie/film-score concepts and the premium game-animation lane for game-orchestra, anime action-RPG, sci-fi heroine, or graceful fantasy game-score concepts.
- The uploaded first-frame image for the provider loop should be this cover image with the upper-left style phrase already integrated.
- Create a subtle Gemini loop video from that first frame when Gemini is available. The motion should feel like a premium movie shot: restrained atmosphere, light, smoke, rain, clouds, water, flags, or camera ambience, not fast scene changes.
- Do not use Dreamina, Seedance, or CapCut for Cinematic Pulse. Gemini clips are uploaded as generated after inspection. If Gemini is unavailable, on cooldown, blocked after safe retries, or cannot create a usable MP4 within the wait window, use the approved still-image fallback instead of switching providers.
- Queue final render with:

```bash
scripts/openclaw-release render-video \
  --release-id RELEASE_ID \
  --video-render-source-mode loop_video \
  --video-render-resolution 720p \
  --video-spectrum-overlay-style bars
```

- The app/render worker will use the uploaded loop video and add only the clean bar spectrum overlay. Do not bake spectrum graphics into the image or provider video itself.
- Use `--allow-still-image-video --video-render-source-mode still_image` when Gemini cannot produce a usable moving clip, or when the human explicitly approves a static-cover fallback for that release.

First-frame prompt shape:

```text
Create a 16:9 original high-end Cinematic Pulse cover/first-frame image for an instrumental cinematic orchestra / game-score release.
Use either photorealistic cinematic movie-poster realism or premium sci-fi/fantasy action-RPG game-animation key art, whichever best matches the release concept.
For game-orchestra lanes, an original beautiful adult heroine is allowed: elegant, confident, cinematic, YouTube-safe, not sexualized, not a protected character, and not copied from any existing game.
Use cinematic lighting, lensing, depth of field, atmosphere, believable materials, strong silhouettes, and one clear focal scene.
Make it high resolution, preferably 2560x1440 or at least 1920x1080.
Do not add the channel name, channel logo, title sentence, subtitles, UI, or unrelated words. If visual text is useful, use only one short cinematic style phrase such as "FILM SCORE" or "CINEMATIC ORCHESTRA".
No cartoon parody, no flat illustration, no game UI art, no gore, no real war footage, no protected characters, no franchise references, no celebrity likenesses, no exact game costume or logo.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds childish, vague, or less cinematic, rewrite it while keeping the film-score/orchestra lane and real listening use case truthful.
- Default metadata language can be English unless the human asks otherwise.
- Titles should be bold, search-friendly, and immediately understandable to a broad YouTube audience. Include cinematic music, cinematic orchestra, movie OST, film score, trailer music, final battle scene, orchestral battle, emotional film score, mystery tension, fantasy writing, game orchestra, anime action RPG OST, or cinematic game score when accurate.
- Before approving metadata, inspect the first 10 minutes and the full track list titles/styles. If any lead-block track is clearly cute/playful/anime side-story/arcade/item-shop/theme-park BGM, metadata must not promise dark fantasy orchestra, epic battle, final battle, trailer music, or serious film-score content. Either replace those tracks with matching cinematic tracks or repackage the release as former Storylight-style game/anime BGM.
- Make titles broad and public-facing first. Use exact visual scene details as atmosphere unless they are the strongest searchable hook.
- Do not use `Boss BGM`, `Final Boss Music`, `Final Boss Focus Music`, `보스`, `보스전`, or bare `BGM` in public YouTube titles. Avoid wording that sounds like a niche game menu rather than a cinematic music video.
- Use varied cinematic title families across releases: final battle scene, dark fantasy film score, heroic trailer music, emotional film score, sci-fi cinematic music, mystery tension score, grand journey orchestra, orchestral battle music, epic writing music, gentle game orchestra, lyrical fantasy game OST, bittersweet anime action-RPG score, and movie OST focus. These are direction families, not fixed templates to repeat mechanically.
- Reusing a strong channel-fit title shape is better than inventing a weak off-brand one, but do not lock the channel into only a few example titles.
- Avoid naming existing films, games, franchises, composers, studios, or characters.
