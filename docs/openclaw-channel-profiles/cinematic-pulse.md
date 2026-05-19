# OpenClaw Channel Profile: Cinematic Pulse

Use this profile only after channel selection returns `Cinematic Pulse`, or when the human explicitly says to upload to `Cinematic Pulse`.

## Routing Contract

- Explicit channel request wins.
- Cinematic Pulse is for no-vocal large-scale cinematic orchestra and film-score music: movie OST, trailer music, emotional film score, orchestral battle, dark fantasy confrontation, sci-fi journey, heroic, mystery tension, and orchestral scene music.
- Do not use this profile for cozy fantasy, cafe/study BGM, EDM/house, or vocal pop.

## Visual Identity

- Mood: cinematic, dramatic, large-scale, orchestral, emotional, tense, heroic, mysterious, or high-stakes.
- Style should be photorealistic cinematic film-still / high-end movie-poster realism, not anime, cartoon, flat illustration, or game UI art.
- The cover, thumbnail base, and loop video should feel like a dramatic movie frame or premium trailer shot with realistic lighting, depth of field, cinematic lensing, atmosphere, and believable materials.
- Do not use documentary-looking real war footage, news footage, real political imagery, celebrity likenesses, protected film/game characters, or exact franchise references. Photorealistic means original cinematic realism, not copied real media.
- Composition should read quickly on mobile: one strong focal scene, bold lighting, clear silhouettes, and high contrast.
- Visuals can be intense, but avoid gore, real-world political symbols, real war footage, and protected IP.
- App-rendered spectrum must use `bars` for Cinematic Pulse. Do not use `radial`, `multiwave`, small dots/particles, or busy waveform presets for this channel unless the human explicitly asks. Keep the bar spectrum clean, restrained, and non-cluttered.

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

## Render Visual

- Do not create or upload a Gemini/Dreamina/Seedance loop video for normal Cinematic Pulse releases. Those providers usually reduce the moving clip to 720p, which weakens the channel's premium film-score look.
- Instead, create a very high quality 16:9 photorealistic cover/first-frame image, preferably 2560x1440 (`2k`) or at minimum 1920x1080. Use that still image as the final video source.
- Queue final render with:

```bash
scripts/openclaw-release render-video \
  --release-id RELEASE_ID \
  --allow-still-image-video \
  --video-render-source-mode still_image \
  --video-render-resolution 2k \
  --video-spectrum-overlay-style bars
```

- The app/render worker will render from the high-resolution image and add only the clean bar spectrum overlay. Do not bake spectrum graphics into the image itself.
- If a human explicitly asks for a moving Cinematic Pulse clip, follow the request, but default automation should prefer the high-resolution still-image render.

Still-image prompt shape:

```text
Create a 16:9 original photorealistic cinematic film-still / premium movie-poster image for a Cinematic Pulse instrumental film-score release.
Use realistic lighting, cinematic lensing, depth of field, atmosphere, believable materials, strong silhouettes, and one clear focal scene.
Make it high resolution, preferably 2560x1440 or at least 1920x1080.
Include only the large, readable lower-left channel brand label "Cinematic Pulse". Do not add title text, genre text, subtitles, logos, UI, or any other words.
No anime, no cartoon, no illustration, no game UI art, no gore, no real war footage, no protected characters, no franchise references, no celebrity likenesses.
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
