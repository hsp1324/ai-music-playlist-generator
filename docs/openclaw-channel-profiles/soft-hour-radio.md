# OpenClaw Channel Profile: Soft Hour Radio

## Publishing schedule — effective 2026-10-19

Every channel publishes at most one video each Wednesday at 07:00 Asia/Seoul (Tuesday 22:00 UTC). This overrides all older daily, dual-slot, and branch-specific times below. Upload/render/metadata preparation may continue on other days; public publication must use the server-calculated weekly slot.
Cinematic Pulse shares ONE weekly channel slot: orchestra on 2026-10-21, cute_game on 2026-10-28, orchestra on 2026-11-04, alternating every week thereafter. Each lane therefore publishes every 14 days, always at 07:00. Set the exact lane; do not schedule two videos on the same Wednesday. Do not manually reintroduce daily timestamps. Follow `docs/openclaw-weekly-publishing.md`.

## Prospective policy update — 2026-10-02

Read [audience-first image copy](../openclaw-thumbnail-copy-policy.md) and [Suno v6 generation/reuse](../openclaw-suno-v6-policy.md) before new work. Preserve existing songs, images, releases, jobs, and approved briefs; continue them unchanged. For new releases, bare genre labels are not primary image hooks; new songs use verified standard v6, reuse is v6-only except human-Good legacy tracks at the tail, and global shuffle must not defeat that order. Existing text-free defaults and routing exclusions remain in force.

New copy direction for this channel: `A Quiet Place to Focus` or `Piano for a Slow Morning`. These are examples, not fixed slogans; keep the actual music promise and channel language truthful.
Use this profile only after channel selection returns `Soft Hour Radio`, or when the human explicitly says to upload to `Soft Hour Radio`.

## Global image rule — effective 2026-10-20

For every new release, use one approved cover image file for playback and the YouTube thumbnail. Do not create or edit a separate thumbnail, including any crop, reframe, grade, or thumbnail-only lettering. Any permitted words must be part of the single cover image. Compose the image to read well at full size and at thumbnail size. Keep existing releases and published assets unchanged. Follow the natural-image quality standards in [the shared visual asset policy](../openclaw-visual-assets.md); this rule overrides older instructions below if they conflict.

## Routing Contract

- Explicit channel request wins. If the human says `Soft Hour Radio에 올려줘`, this profile is mandatory even if the music mentions Japan, J-pop, city-pop, or anime influence.
- Default content is background/cafe/sleep/study/work/chill/BGM. These releases are usually instrumental/no-vocal unless the human asks for vocals.
- Soft Hour has two equal rotation lanes: `classic_piano` keeps the current calm real-world piano package, and `anime_game_ost` uses original Japanese-animation/game-OST-style piano music with matching bright illustrated game/anime artwork. Before creating a release, run `scripts/openclaw-release soft-hour-lane` and pass its `next_lane` to `create-release --soft-hour-lane`. Do not choose both lanes inside one release.
- Alternate the lanes release by release. This is the 50:50 rule: one normal current-style release, then one Japanese anime/game OST-style release, then repeat. If history is missing, start with `anime_game_ost`; if a human explicitly selects a lane, that instruction wins.
- Music remains piano-first. For each normal new Soft Hour playlist, generate about three new piano tracks as the fresh lead block, then fill the remaining duration with approved same-lane or closely compatible Soft Hour piano tracks. Generate more than three new tracks only when one is unusable or the human explicitly asks for more new music. Music, cover, thumbnail, metadata, and video must all use the selected lane.

## Visual Identity

- Mood: calm, useful, warm, focused, restful, long-listening friendly.
- Let the specific release concept decide the subject. Do not force a fixed recurring mascot, character count, scene list, or camera composition.
- Prefer restrained, uncluttered compositions that can sit behind long listening sessions without becoming visually noisy.
- Human presence is optional and should serve the release concept rather than act as a channel signature.
- In `classic_piano`, use high-resolution photorealistic / premium real-world BGM imagery. Avoid anime, cartoon, illustrated, painterly, vector, or obviously stylized looks in this lane.
- In `anime_game_ost`, use polished original Japanese-animation/game-key-art styling: luminous 2D animation, refined cel shading, soft painted backgrounds, clean line work, bright daylight or warm magical light, and an inviting fantasy/adventure atmosphere. The result may be calm, gently hopeful, or lively; it does not need to be fast or hyperactive. Do not copy protected characters, costumes, locations, logos, UI, franchise compositions, or named-game artwork.
- Preserve the established Soft Hour long-listening feeling in both lanes. `classic_piano` can use a quiet cafe, study, work, reading, sleep, rain-window, greenhouse, library, cottage, workshop, or warm desk. `anime_game_ost` can use an original sunlit fantasy town, lakeside path, sky island, flower meadow, observatory, cozy item shop, railway platform, forest clearing, or peaceful journey scene, while staying uncluttered and piano-listening friendly.
- Current local performance shows that interchangeable quiet-room piano thumbnails are not getting enough clicks. Every new Soft Hour visual package must make the piano/use-case promise readable in one glance. `classic_piano` should include a concrete piano or listening cue such as visible keys, sheet music, headphones, a bench, laptop/desk, book, rainy window, bedside sleep cue, or cafe context. `anime_game_ost` may use a visible piano/music cue or a large integrated OST-piano phrase when a literal piano would weaken the fantasy scene. Vary scene and crop across releases.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Gemini when a moving clip is needed.
- Match the selected lane. `classic_piano` must be photorealistic, high-resolution, clean, and calm. `anime_game_ost` must be a bright, premium original anime/game-OST illustration with a readable focal scene, strong depth, and clean small-thumbnail composition.
- Do not put `Soft Hour Radio`, the channel name, a channel logo, or a brand line on the cover/first-frame.
- New image copy follows [the audience-first policy](../openclaw-thumbnail-copy-policy.md): `A Quiet Place to Focus` or `Piano for a Slow Morning`. Prefer one natural listener promise over a standalone genre label; text-free remains valid. Keep letters integrated directly on the artwork with no filled background.
- Do not add title sentences, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.

## YouTube Thumbnail

- Use the exact approved cover image file as the thumbnail; do not create or edit a separate thumbnail image.
- Preserve the same photorealistic scene, subject placement, lighting, palette, props, and camera angle from the cover.
- New image copy follows [the audience-first policy](../openclaw-thumbnail-copy-policy.md): `A Quiet Place to Focus` or `Piano for a Slow Morning`. Prefer one natural listener promise over a standalone genre label; text-free remains valid. Keep letters integrated directly on the artwork with no filled background.
- Make the text large enough to read on a phone thumbnail and pair it with a visual cue that proves the promise. Do not let the thumbnail be only a beautiful room plus small decorative words.
- Keep thumbnail text directly on the image with a transparent background. Use font weight, color, subtle shadow, thin outline, or local contrast for readability; do not use black boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, stickers, badges, pills, capsules, or any filled label shape behind text.
- Do not add `SOFT HOUR RADIO`, the channel name, or a channel logo.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, or clocks unless the human explicitly asks.

## Loop Video

- Use Gemini only for the moving clip. Do not use Dreamina, Seedance, or CapCut for Soft Hour moving visuals.
- For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection. If Gemini is unavailable, on cooldown, blocked after safe retries, or cannot create a usable MP4 within the wait window, use the approved still-image fallback instead of switching providers.
- Do not put `10 seconds`, `5 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts.
- The moving clip must preserve the selected cover lane exactly. Keep photorealistic materials in `classic_piano`; keep the same illustrated/cel-animated visual language in `anime_game_ost`. Avoid hard-coded scene/motion templates unless the human requested one.
- If the first-frame cover contains short piano/use-case text, the provider video must keep that text as plain letters directly on the scene with a transparent background. Do not add, preserve, or animate in any black box, semi-transparent dark panel, rectangle, gradient scrim, sticker, badge, pill, capsule, or filled label shape behind the text. Reject/regenerate if the moving clip wraps clean first-frame text in a new box.
- The camera must be completely static: locked-off tripod, fixed frame, no pan, tilt, zoom, push-in, pull-back, dolly, handheld shake, camera breathing, camera drift, camera follow, parallax camera move, or any other camera movement.
- Use only subtle environmental motion already present or naturally implied by the first frame. `classic_piano` can use rain on glass, mug steam, lamp flicker, curtains, dust, firelight, reflections, or leaves. `anime_game_ost` can use hair or cloth settling, petals, grass, clouds, water sparkle, magical motes, distant windmills, or warm light shimmer. Do not move the camera to create motion.
- Write prompts with positive motion language: `calm but clearly visible natural motion across several environmental layers`.
- The final moment should keep the same crop, framing, camera distance, lighting, palette, and subject placement. The app handles smooth repetition with provider-aware crossfade timing, so do not force the model to zoom out or return the camera to the opening frame.
- If Gemini rejects generation for inappropriate content, copyright, moderation, or policy reasons, follow the shared retry rule in `docs/openclaw-visual-assets.md`: send Slack before every retry, remove protected IP or risky terms from the prompt, and use the approved still-image fallback when safe Gemini retries are exhausted.
- Use `--video-spectrum-overlay-style bars` for final renders, matching HaruHaru and every other channel. Do not use the retired thin waveform style from `아침 온실 피아노 BGM`.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame.
Create one uninterrupted calm environmental take for a background-music release from a locked-off tripod camera.
Preserve the opening composition, lighting, palette, and exact selected visual lane: high-resolution photorealism for classic piano, or premium original Japanese-animation/game-key-art illustration for anime/game OST piano.
If the first frame already contains a short use-case/style phrase, keep it stable and readable. Do not invent a channel name.
Keep that phrase as transparent-background typography directly on the scene; do not create or preserve any black box, translucent dark panel, gradient scrim, sticker, badge, pill, capsule, or filled label shape behind the letters.
Animate only calm natural motion already present or naturally implied by the first frame and release mood: rain on glass, steam from a cup, candle or lamp flicker, curtain edge movement, drifting dust, smoke, firelight, soft reflections, or gentle leaf movement when appropriate.
Keep the same crop, framing, camera distance, lighting, palette, and subject placement from first frame to final frame.
No camera movement, no pan, no tilt, no zoom, no dolly, no handheld shake, no parallax camera move, no new text, no text background boxes or panels, subtitles, logos, UI, protected characters, franchise references, or style switching.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds awkward, weak, or less clickable, rewrite it while keeping the BGM use case and calm channel identity truthful.
- Titles should include piano plus a truthful listening use case. For `anime_game_ost`, they should also clearly say original anime/game OST-style or fantasy-game piano without implying an official soundtrack or named franchise.
- Titles should read like a natural clickable sentence, not a keyword pile. `classic_piano` shapes include `조용히 집중하고 싶을 때 듣는 피아노 BGM | 공부와 작업을 위한 솔로 피아노`. `anime_game_ost` shapes include `모험이 시작될 것 같은 피아노 OST | 잔잔하게 듣는 애니·게임 감성 BGM` or `햇살 가득한 판타지 마을의 피아노 | 공부와 휴식을 위한 게임 OST풍 BGM`.
- Do not use lofi / lo-fi, guitar-led, jazz-trio, Rhodes, synth-pad, or unrelated mixed-instrument wording in Soft Hour metadata. A restrained `anime_game_ost` support color does not need to dominate the title; keep the public promise piano-first.
- Keep titles and descriptions audience-friendly and searchable. If the visual is a niche scene, do not make that niche the main title unless the human asks. For example, use `조용히 집중하고 싶을 때 듣는 피아노 BGM | 공부와 작업을 위한 솔로 피아노` instead of making `도자기 공방` the primary hook.
- The description can mention the visual atmosphere lightly, but the first paragraph should explain how the music is useful: study, work, reading, writing, calm handwork, rest, sleep, cafe, or focus.
- Korean copy must not use `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`; use `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡`.
