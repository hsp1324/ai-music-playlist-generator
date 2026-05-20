# OpenClaw Visual Asset Skills

Use this when OpenClaw creates cover images, YouTube thumbnails, or short loop videos for this repo.

The visual rules are channel-specific. Do not apply one channel's visual signature to every release. The source of truth for production work is now [openclaw-channel-profiles](openclaw-channel-profiles/README.md). OpenClaw should run `scripts/openclaw-release channel-profile` first, then read the returned `profile_doc`.

## Shared Asset Contract

- Create static cover and thumbnail images with OpenAI GPT Image models, not Dreamina.
- Prefer `gpt-image-2` when available; otherwise use the best available GPT Image model in the current environment.
- Use Gemini first for the moving loop video, then fall back to Dreamina/Seedance when Gemini is unavailable or on cooldown. Gemini can be used through the human's quota for up to 3 successful video generations per 24 hour quota window.
- Always create a final clean 16:9 cover first.
- Create the YouTube thumbnail from that final cover as an image-to-image edit/reference derivative, not as a fresh unrelated scene.
- Keep cover, thumbnail, and loop video visually continuous: same subject count, subject placement, silhouettes, clothing colors, props, background landmarks, lighting, palette, and camera angle.
- The thumbnail is the click image and should contain short readable text plus channel branding.
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini. It must include only a large, readable lower-left selected-channel-name brand label. Match the visual scale of the channel-brand line used on the YouTube thumbnail. Target roughly 18-24% of the image width, or about 5-6% of image height for text cap height. On a 2048x1152 cover, `Soft Hour Radio` should be roughly 360-500 px wide with clearly readable letter height.
- Do not use the text thumbnail as the video-generation first-frame reference.
- The cover/first-frame channel brand label is mandatory for every channel. Do not add title text, genre text, duration text, lyrics, subtitles, UI, logos, or unrelated words.
- The Dreamina/Seedance/Gemini loop video must preserve the exact lower-left channel label for the full clip. Reject/regenerate if it disappears, flickers, moves, morphs, changes spelling, changes style drastically, or becomes unreadable.
- If Gemini/Veo adds its own provider logo or watermark, usually in the bottom-right corner, accept it as an unavoidable provider artifact. Do not regenerate a loop video only because that Gemini/Veo logo or watermark is present. The "no logos" rule means OpenClaw must not ask for, create, or add in-scene logos, brand marks, UI, or unrelated text.
- The thumbnail should use larger click text plus a channel-brand line whose size/style matches the cover channel label.
- The thumbnail channel-brand line should be plain, integrated typography. Do not put the channel name inside a rounded pill, capsule, button, sticker, badge, label tag, or floating plaque unless the human explicitly asks for that graphic treatment.
- Keep every cover and thumbnail text block comfortably inside safe margins, with about 5% image-width horizontal padding and 5% image-height vertical padding on 16:9 assets. Reject/regenerate assets where text is clipped, crowded against image edges, cramped inside a shape, visually detached from the layout, or overlapping the main subject.
- Do not include spectrum bars, waveform graphics, equalizers, or other audio-reactive overlays in generated assets. The app adds an audio-reactive visualizer during final video render, chooses colors from the cover/loop-video palette, and positions it away from channel text when possible.
- Available app-rendered visualizer presets are `bars`, `mirror-bars`, and `none`. Do not blindly use the default. Choose only a clean, natural-moving spectrum: `bars` / `mirror-bars` for clean pop, EDM, and dance energy, or `none` when the overlay would distract. Do not use removed busy/fast presets: small dots/particles, thin waveform, multiwave, radial, pulse, or the spectrum style used on `창세기 창조의 빛`; legacy values fall back to `bars`. Cinematic Pulse must use `bars` unless the human explicitly asks otherwise. `The Old Verse` and `The New Verse` must use `none` with no app spectrum.
- Human visual requests override the channel default. If the human asks for a specific scene, subject, action, camera angle, animal, object, or character type, apply that concept consistently to the cover, thumbnail, and loop video.
- All generated visuals should look animated, anime, illustrated, or stylized unless a channel profile says otherwise. Cinematic Pulse is the explicit exception: use original photorealistic cinematic film-still / movie-poster realism for its cover and thumbnail base, and normally render from that high-resolution still cover instead of a provider loop video. Do not use documentary footage, real war footage, celebrity likenesses, protected IP, or copied real media.
- Try Gemini before Dreamina/Seedance for each loop video unless Gemini is in its 24 hour cooldown window. The cooldown starts when the 3rd successful Gemini video generation is made, not at midnight.
- Count only successful Gemini generations where Gemini actually creates a video result. Copyright/policy/moderation blocks that stop generation before a video is made do not count against the 3-video quota. A generated but visually rejected video still counts because the quota was spent.
- If Gemini says the daily video limit is reached or the 3rd successful Gemini video was made less than 24 hours ago, switch to Dreamina/Seedance for that release. If Dreamina/Seedance cannot create the clip, defer the release until Gemini cooldown clears instead of rendering/publishing with a missing loop video.
- If Dreamina/Seedance/Gemini blocks a loop-video generation for inappropriate content, copyright, moderation, or policy reasons, OpenClaw should rewrite the prompt and retry safely. Each failure must be reported to Slack before retrying with `scripts/openclaw-release slack-notify --text "영상 만들기 실패해서 프롬프트를 수정해 다시 만듭니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`.
- Do not use a locally generated motion loop, app still-image animation, pan/zoom video, or other workaround as the final loop video when Dreamina/Seedance fails. Use Gemini if quota is available; otherwise defer that release and continue with the next eligible release.
- Retry prompts must become more original and generic: remove named artists, studios, franchises, copyrighted characters, brands, celebrity names, exact song/video titles, `in the style of` wording, real-person likenesses, sexualized wording, minors, weapons, gore, and other moderation-risk terms. Preserve only the broad mood, channel label, first-frame continuity, and motion intent.
- Do not spend more than 3 successful Gemini video generations in one 24 hour quota window. If Gemini copyright/policy retries fail 10 times without creating a video, stop Gemini attempts for that release and move on to Dreamina/Seedance.
- If Dreamina/Seedance fails after Gemini fallback was already unavailable due quota, post `scripts/openclaw-release slack-notify --text "Gemini 3개 영상 쿼터가 끝났고 Dreamina/Seedance도 실패해서 이 릴리즈의 loop video를 보류합니다. 24시간 쿨다운 후 Gemini로 먼저 다시 만들겠습니다. RELEASE_TITLE"` and resume this deferred release first when Gemini can create videos again.
- If all 10 total video-generation attempts fail while Gemini quota is available, try Gemini again with a safer prompt before giving up. If all providers still fail, send `scripts/openclaw-release slack-notify --text "영상 생성이 10회 실패해서 중단했습니다. RELEASE_TITLE: ERROR_SUMMARY"` and stop before render/publish unless the human explicitly approves a still-image fallback. If that fallback is approved, pass `--allow-still-image-video`; otherwise the app rejects video render without an uploaded loop video.

## Tokyo Daydream Radio Visual Skill

Use this for `Tokyo Daydream Radio`, mainstream J-pop/Japanese pop, Tokyo/Japan pop, city-pop, dance-pop, synth-pop, pop-rock, anime-pop, or similar Japan-themed vocal pop releases.

Default visual signature:

- Exactly three people walking toward the viewer in a front-view composition.
- The camera/viewer sees the people from the front, preferably medium-wide or full-body rather than close-up faces.
- The three people stay centered and visually important.
- For loop videos, the people walk forward while the camera moves backward at the same speed. Do not allow zoom-in, push-in, pull-back, lens breathing, or subject scale growth. The three-person silhouette should remain roughly the same size and centered throughout the clip.
- Let the side/background environment create most of the loopable movement through parallax, light, rain, reflections, signs, trees, water, or distant background activity.
- Text must fit around the centered three-person silhouette, usually in lower-left or lower negative space. Do not push the people sideways.
- Background can adapt to the release: Tokyo street, forest path, beach, rainy city, night park, station road, fantasy forest, seaside walk, etc.

Thumbnail text:

- Use large `J-POP`.
- Use smaller `TOKYO DAYDREAM RADIO` directly beneath it.
- Keep the same full-bleed two-line treatment for Tokyo/city, forest/nature, and beach variants.
- Do not add `1 HOUR`, `60 MIN`, `1時間`, clocks, timers, or duration badges.

Dreamina/Seedance prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Tokyo Daydream Radio".
Create one continuous forward-moving animated music visualizer shot.
Keep the Tokyo Daydream Radio signature: exactly three people walking toward the viewer in a front-view composition.
The viewer should see the people from the front, preferably medium-wide or full-body rather than close-up faces.
The people walk forward naturally while the camera moves backward at the same speed, keeping the same distance from them.
Do not repeat any segment. Do not ping-pong or restart motion.
Preserve the opening composition, lighting, palette, and anime/illustrated style.
Preserve the large, readable lower-left "Tokyo Daydream Radio" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
Adapt the background and atmosphere to the release concept.
Add gentle environmental motion, side-background parallax, reflections, rain shimmer, particles, or soft light motion around the walking subjects.
Keep the camera at the same distance from the three people while moving backward; no zoom in, no push-in, no pull-back, no camera breathing, no changing lens scale. The three people must stay roughly the same size in frame.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI, no extra people or characters.
```

## Soft Hour Radio Visual Skill

Use this for `Soft Hour Radio`, default background music, cafe, piano, sleep, study, work, chill, relaxing, ambient, lofi, and similar non-Japan BGM releases.

Default visual direction:

- Prefer calm, restrained visuals matched to the music use case, with clearly visible natural motion throughout the clip.
- Let the specific release concept decide the subject. Do not force a fixed recurring mascot, character count, scene list, or camera composition.
- Human presence is optional and should serve the release concept.
- Keep the composition uncluttered, warm, readable, and suitable for long background listening.

Thumbnail text:

- Use 2-4 large use-case or mood words such as `DEEP SLEEP`, `CAFE PIANO`, `FOCUS MUSIC`, `RAINY NIGHT`, `STUDY BGM`, or `CALM READING`.
- Add smaller `SOFT HOUR RADIO` as the channel brand line.
- Do not add duration badges unless the human explicitly asks.

Dreamina/Seedance prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Soft Hour Radio".
Create one continuous calm animated music visualizer shot for a background-music release.
Preserve the opening composition, lighting, palette, and illustrated/stylized visual language.
Preserve the large, readable lower-left "Soft Hour Radio" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
Animate calm but clearly visible natural motion across several environmental layers already present or naturally implied by the first frame and release mood: leaves, grass, curtains, water/rain reflections, warm light shimmer, drifting particles, smoke, steam, fireflies, or soft air movement when appropriate.
Keep continuous visible motion throughout the full clip while preserving the calm long-listening mood.
Keep the camera locked in the same crop and framing for the full clip. No zoom, no push-in, no pull-back, no dolly, no camera breathing, no camera drift, no camera follow, no parallax camera movement.
The motion must progress naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should preserve the same crop, framing, camera distance, lighting, palette, and subject placement; only ambient details may differ.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI.
```

## sundaze Visual Skill

Use this for `sundaze`, English-language pop, American pop, US/UK pop, western pop, mainstream vocal pop, dance-pop, synth-pop, pop-rock, and similar English pop releases.

- No fixed recurring visual signature yet.
- Let the playlist concept decide the cover, thumbnail, and loop-video scene.
- The cover must contain only the large lower-left `sundaze` brand label.
- The thumbnail should use short English pop click text such as `POP HITS`, `SUMMER POP`, `NIGHT DRIVE`, `DANCE POP`, `FEEL GOOD POP`, or `HEARTBREAK POP`, plus `SUNDAZE`.
- Keep `SUNDAZE` as plain text directly tied to the thumbnail headline layout. Do not use a rounded yellow pill, capsule, button, sticker, or detached badge for the channel name.
- The loop video should animate the selected cover concept, not borrow Tokyo Daydream or Soft Hour signatures.

## Solwave Radio Visual Skill

Use this for `Solwave Radio`, Latin/Spanish-language pop, Latin pop, Spanish pop, urbano latino, reggaeton pop, bachata pop, salsa pop, cumbia pop, tropical dance-pop, and similar Spanish vocal releases.

- No fixed recurring visual signature yet.
- Let the playlist concept decide the cover, thumbnail, and loop-video scene.
- The cover must contain only the large lower-left `Solwave Radio` brand label.
- The thumbnail should use short Latin/Spanish click text such as `LATIN POP`, `REGGAETON`, `VERANO LATINO`, `SPANISH POP`, `FIESTA LATINA`, or `NOCHE LATINA`, plus `SOLWAVE RADIO`.
- The loop video should animate the selected cover concept, not borrow Tokyo Daydream or Soft Hour signatures.

## HaruHaru Visual Skill

Use this for `HaruHaru`, K-pop, Korean pop, Korean dance-pop, Korean synth-pop, Korean R&B pop, idol-pop inspired music, and similar Korean vocal releases.

- No fixed recurring visual signature yet.
- Let the playlist concept decide the cover, thumbnail, and loop-video scene.
- The cover must contain only the large lower-left `HaruHaru` brand label.
- The thumbnail should use short K-pop click text such as `K-POP`, `SEOUL POP`, `DANCE POP`, `HEARTBREAK`, `SUMMER KPOP`, `RAINY KPOP`, or `K-POP DRIVE`, plus `HARUHARU`.
- The loop video should animate the selected cover concept, not borrow Tokyo Daydream, Soft Hour, HaruHaru, Storylight, Cinematic Pulse, Club Bloom, sundaze, or Solwave signatures.
- For photorealistic HaruHaru clips with an adult woman as the main subject, keep the subject the same size, crop, and approximate placement for the full clip. If she moves, the camera tracks with her at the same speed/distance; use background parallax, wind, clothing, light, water, vehicle, or city motion for movement. Reject zoom-in, push-in, pull-back, lens breathing, camera drift toward/away from her, or subject scale changes because they make the loop feel awkward.

## Storylight OST Visual Skill

Use this for `Storylight OST`, playful no-vocal Japanese-style game/anime OST, arcade-game BGM, fantasy-game BGM, cute RPG music, item-shop music, mini-game music, or light adventure instrumental releases.

- No fixed recurring visual signature yet.
- Let the playlist concept decide the arcade, fantasy-game, anime-side-story, item-shop, mini-game, cute RPG, object, palette, and loop-video motion.
- The cover must contain only the large lower-left `Storylight OST` brand label.
- The thumbnail should use short game/anime click text such as `GAME OST`, `ANIME BGM`, `ARCADE BGM`, `CUTE RPG`, `KAWAII GAME`, `PLAYFUL OST`, or `FANTASY GAME`, plus `STORYLIGHT OST`.
- The loop video should animate the selected cover concept with visible playful game/anime environmental motion, not borrow Soft Hour calm-use-case visuals or Tokyo walking signatures.
- Do not use protected IP, real studio names, franchise names, exact game titles, copyrighted characters, celebrity likenesses, or `in the style of` wording.

## Cinematic Pulse Visual Skill

Use this for `Cinematic Pulse`, no-vocal large-scale cinematic orchestra, movie OST, film score, trailer music, orchestral battle music, dark fantasy confrontation, heroic music, emotional film score, mystery tension, sci-fi action, or grand cinematic instrumental releases.

- No fixed recurring visual signature yet.
- Let the playlist concept decide the cinematic orchestra, movie-OST, trailer, battle, emotional film-score, mystery-tension, or sci-fi scene, object, palette, and loop-video motion.
- Use photorealistic cinematic film-still / premium movie-poster realism for the cover and thumbnail base. Avoid anime, cartoon, flat illustration, painterly fantasy art, game UI art, documentary footage, real war footage, celebrity likenesses, protected IP, and exact franchise references.
- The cover must contain only the large lower-left `Cinematic Pulse` brand label and should be high resolution, preferably 2560x1440 (`2k`) or at least 1920x1080.
- The thumbnail should use short cinematic click text such as `MOVIE OST`, `CINEMATIC ORCHESTRA`, `EPIC BATTLE`, `DARK FANTASY`, `HEROIC MUSIC`, `SCI-FI ACTION`, `TRAILER MUSIC`, or `FILM SCORE`, plus `CINEMATIC PULSE`.
- Avoid juvenile game-menu wording such as `BOSS BGM`, `FINAL BOSS`, `보스`, or `보스전` unless the human explicitly asks for that packaging. Cinematic Pulse should read as grand film-score / cinematic orchestra first.
- Do not generate or upload a Gemini/Dreamina/Seedance loop video for normal Cinematic Pulse releases. Render from the high-resolution still cover instead so provider video generation does not reduce the visual to 720p.
- Queue final render with `--allow-still-image-video --video-render-source-mode still_image --video-render-resolution 2k --video-spectrum-overlay-style bars`. Keep the spectrum as a clean restrained bar visualizer; do not use radial, pulse, multiwave, dots/particles, or busy waveform styles for Cinematic Pulse unless the human explicitly asks.
- Do not use gore, real war footage, political symbols, protected IP, franchise names, copyrighted characters, or celebrity likenesses.

## Club Bloom Visual Skill

Use this for `Club Bloom`, no-vocal EDM, house, techno, trance, festival EDM, workout EDM, night drive EDM, gaming dance, club, or party-energy releases.

- No fixed recurring visual signature yet.
- Let the selected club style lane decide the neon/dance/nightlife scene, subject, palette, and loop-video motion. Prefer visuals that clearly read as club, dance floor, DJ/performance, festival, rooftop party, nightlife, or movement energy rather than generic abstract neon.
- A stylish adult female DJ or dancer can be used when it fits the release, including bold club fashion, confident poses, and sexy nightlife energy, but treat it as one possible direction, not a fixed template. Vary subject, pose, camera angle, venue, lighting, wardrobe color, and crowd/solo composition across releases.
- Club Bloom visuals must be click-stopping, not polite. Reject calm, soft, empty, low-contrast, generic abstract neon, quiet lounge, or wallpaper-like images before upload. Use stronger crops, saturated neon, dramatic club lighting, confident adult performance energy, crowd heat, festival scale, night-drive velocity, or rooftop party motion when the lane supports it.
- The cover must contain only the large lower-left `Club Bloom` brand label.
- The thumbnail should use short style-specific dance click text such as `DEEP HOUSE`, `TECH HOUSE`, `MELODIC TECHNO`, `TRANCE MIX`, `BASS HOUSE`, `FESTIVAL EDM`, `WORKOUT EDM`, `UK GARAGE`, `LIQUID DNB`, `TROPICAL HOUSE`, `AFRO HOUSE`, `SYNTHWAVE DRIVE`, or `CLUB MIX`, plus `CLUB BLOOM`.
- The loop video should animate the selected cover concept with rhythmic neon motion: light sweeps, neon reflections, LED pulses, laser haze, stage particles, city lights, road light streaks, dance-floor glow, or atmospheric color pulses.
- Reject weak loop videos where only tiny particles move or the result feels static. The clip should look like an active club visual, not a still cover with minor shimmer.
- Bold adult nightlife subjects are allowed when the concept fits, but do not use full nudity, sexual acts, unsafe minors, fetish framing, protected brands, photorealistic club footage, or UI overlays.

## The Old Verse Visual Skill

Use this for `The Old Verse`, Old Testament songs, New Testament songs, Genesis songs, Matthew/Gospel songs, Psalms music, Bible verse music, scripture-inspired worship, or ancient biblical music releases.

- Follow `docs/openclaw-channel-profiles/the-old-verse.md`.
- The cover must contain only the large lower-left `The Old Verse` brand label.
- The thumbnail should use short passage-aware Bible click text that connects to the selected book, passage, theme, or worship lane, plus `THE OLD VERSE`. Do not rely on a generic `BIBLE MUSIC` / `SCRIPTURE SONGS` headline alone when the passage can make the thumbnail more specific and trustworthy.
- Keep `THE OLD VERSE` as plain typography, not a pill, capsule, badge, sticker, label tag, or floating plaque.
- The loop video should animate the selected Old Testament or New Testament passage scene with reverent symbolic motion and preserve the `The Old Verse` label.
- Do not paste long scripture text onto visuals. Use passage-inspired symbolic imagery.

## The New Verse Visual Skill

Use this for `The New Verse`, Buddhist scripture-inspired songs, Dhammapada/법구경-inspired songs, Heart Sutra/반야심경-inspired songs, Buddhist jazz, Buddhist hip-hop, Buddhist R&B/soul, dharma songs, mindfulness songs, and modern sutra-inspired music.

- Follow `docs/openclaw-channel-profiles/the-new-verse.md`.
- The cover must contain only the large lower-left `The New Verse` brand label.
- The thumbnail should use short Buddhist teaching or lane-aware click text that connects to the selected source/theme, such as `BUDDHIST JAZZ`, `DHARMA R&B`, `MINDFUL HIP-HOP`, `SUTRA SONGS`, `불경 노래`, `법구경 힙합`, or `반야심경 R&B`, plus `THE NEW VERSE` until the channel is renamed.
- Keep `THE NEW VERSE` as plain typography, not a pill, capsule, badge, sticker, label tag, or floating plaque.
- The loop video should animate a respectful Buddhist/dharma atmosphere with calm environmental motion and preserve the `The New Verse` label.
- Do not paste long scripture text onto visuals. Use symbolic Buddhist imagery such as lotus, lanterns, temple paths, incense smoke, moonlit water, mountains, rain on stone, candlelight, or meditation-room light.

## Other Channels Or Explicit Requests

- If the channel is not one of the documented profiles, derive a visual system from the channel name, release concept, and human request.
- If the human explicitly names the target channel, that channel's visual skill wins over automatic genre routing.
- Keep the shared asset contract.
- Do not borrow another channel's visual signature unless the human explicitly asks for it.
