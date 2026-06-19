# OpenClaw Channel Profiles

OpenClaw should decide the channel first, then read exactly one channel profile before making cover, thumbnail, or loop-video assets.

For next-release concept planning, use [openclaw-channel-concepts](../openclaw-channel-concepts/README.md). Channel profiles are for visual and metadata execution, not for deciding the next fresh playlist idea.

Recommended command:

```bash
scripts/openclaw-release channel-profile \
  --release-title "RELEASE_TITLE" \
  --description "RELEASE_CONCEPT" \
  --prompt "PROMPT_OR_STYLE" \
  --tags "comma,separated,tags"
```

If the human explicitly names a channel, include it:

```bash
scripts/openclaw-release channel-profile \
  --release-title "RELEASE_TITLE" \
  --description "RELEASE_CONCEPT" \
  --youtube-channel-title "Soft Hour Radio"
```

The command returns `youtube_channel_title`, `concept_doc`, and `profile_doc`. Read `concept_doc` for the next playlist concept and `profile_doc` for visual execution. Do not mix visual signatures from another channel.

## Global Visual Rules

- Do not put the YouTube channel name, channel logo, or channel-brand line on covers, thumbnails, first-frame images, or loop videos.
- If text is useful, use a short natural style, genre, use-case, or passage phrase instead. Examples: `J-POP`, `LOFI`, `TECH HOUSE`, `CINEMATIC ORCHESTRA`, `GAME OST`, `Genesis 1:1-5`, `Matthew 1:18-25`, `팔정도 명상팝`, `자비 트립합`.
- Text must be integrated into the artwork with safe margins and a transparent background. Letters should sit directly on the image; use only typography choices such as font weight, color, subtle shadow, thin outline, or local contrast for readability. Do not use hard black boxes, semi-transparent black panels, white or colored rectangles, gradient scrims, detached badges, pills, capsules, stickers, UI tags, logos, or watermark-like marks behind text. Reject/regenerate thumbnails when the text is placed inside any filled background shape.
- The thumbnail should usually be created from the final cover as a reference/edit derivative. Keep the same scene and add only the short click text needed for YouTube.
- The loop video should start from the cover/first-frame image, not from a busy text thumbnail, unless the profile explicitly says the first-frame and thumbnail are the same.
- For Dreamina/Seedance, use `Seedance Mini 2.0`, first-frame/start-frame only, no Omni Reference, no last-frame/end-frame reference, `16:9`, `720p`, and exactly `10 seconds` in the provider UI, not in the prompt. The mode offers `5 seconds` or `10 seconds`; always choose `10 seconds`. Do not upload both first and last frames, because Dreamina switches that setup back to `Seedance 2.0 Fast`. HaruHaru, sundaze, Solwave Radio, and Club Bloom do not use provider clips by default; render them from the still cover image. 불송 is a standing still-image channel and should not use provider clips in normal automation. If the duration selector is hidden when the screen opens, gently drag/scroll the settings/control row to the right until it is visible, then set `10 seconds` before Generate.
- For Gemini, do not ask for a duration. Upload the generated MP4 as-is after inspection.
- Do not use `playlist`, `music visual`, `visualizer shot`, `seamless loop`, `repeat`, `cyclic`, or conceptual scripture framework words in video prompts when they can be replaced with visible scene details.
- Use positive fixed-shot language: `single fixed camera shot`, `locked-off camera`, `one uninterrupted calm environmental take`, `same composition from first to last frame`.
- Keep negative prompt lists short. Overloaded `do not` wording can cause provider models to focus on the forbidden action and create hard cuts, resets, or layout changes.
- If Gemini/Veo adds its own provider logo or watermark, usually in the bottom-right corner, accept it as an unavoidable provider artifact. Do not regenerate only because that provider logo is present.
- If Gemini blocks generation for copyright, protected IP, policy, moderation, or similar issues, retry safely up to 10 blocked attempts. Remove protected names and risky terms rather than retrying the same prompt.

## Quick Asset Summary

### Soft Hour Radio

- Calm high-resolution photorealistic solo-piano BGM visuals for study, work, sleep, reading, cafe, or quiet focus.
- Preserve the established quiet background feeling, but make it feel like a real premium cafe, study desk, rain window, greenhouse, reading room, cottage, workshop, or sleep room.
- Use a locked-off tripod/static camera with no camera movement at all. Add only subtle environmental motion such as rain on glass, mug steam, lamp/candle flicker, curtain edges, dust, smoke, reflections, firelight, or leaves. Prefer `none` or very restrained spectrum for very quiet releases.
- If text is useful, use piano/use-case phrases such as `SOLO PIANO`, `CAFE PIANO`, `FOCUS PIANO`, `STUDY PIANO`, `SLEEP PIANO`, or `RAINY PIANO`.

### Tokyo Daydream Radio

- Mainstream J-pop/Japanese pop visual identity.
- Default signature: exactly three people walking toward the viewer in a front-view composition.
- In loop video, the people walk forward while the camera moves backward at the same speed so subject size stays stable.
- If text is useful, use short J-pop/style phrases such as `J-POP`, `CITY POP`, `ANIME POP`, `J-POP DRIVE`, or `SUMMER J-POP`.

### sundaze

- English/American pop playlist counterpart to Tokyo Daydream Radio.
- Covers mainstream English pop plus pop-adjacent playlist lanes such as Pop R&B, dance-pop, synth-pop, pop-rock, country pop, Americana pop, indie/bedroom/alt-pop, singer-songwriter/folk-pop, soft rock, pop-punk, Y2K/recession pop, disco/funk pop, Afrobeats, Afropop, and Amapiano-pop.
- Default visual package is photorealistic English/American lifestyle still images, not provider loop video.
- Prefer casual friend-taken smartphone/Instagram snapshots: clearly adult road-trip, rooftop, beach boardwalk, cafe terrace, country road, Americana diner, indie room, festival lawn, neon night drive, or downtown walk moments with natural side/three-quarter angles, medium or farther framing, slight phone-photo imperfection, and enough environment to feel real.
- If text is useful, use one natural integrated English-pop lane phrase, preferably upper-left: `POP R&B`, `DANCE POP`, `SYNTH POP`, `COUNTRY POP`, `AMERICANA POP`, `INDIE POP`, `POP ROCK`, `AFRO POP`, `AMAPIANO POP`, `FEEL GOOD POP`, `SUMMER POP`, or `NIGHT DRIVE`.
- Queue final render as still image with app lyrics lower-left and app spectrum lower-right. Do not create or upload a Gemini/Dreamina/Seedance loop video unless the human explicitly asks for motion.

### Solwave Radio

- Latin/Spanish vocal pop.
- Default visual package is photorealistic Latin/Spanish lifestyle still images, not provider loop video.
- Prefer casual friend-taken smartphone/Instagram snapshots: clearly adult night-out, travel, cafe terrace, beach road, plaza dance, rooftop, open-air bar, or city-street moments with natural side/three-quarter/phone-glance angles, medium or farther framing, slight phone-photo imperfection, and enough environment to feel real.
- Avoid professional photographer shoots, studio portraits, glossy fashion campaigns, tight straight-on AI-beauty close-ups, minors, celebrity lookalikes, and over-retouched model faces.
- If text is useful, use one natural integrated Latin/Spanish lane phrase, preferably upper-left: `POP LATINO`, `REGGAETON SUAVE`, `BACHATA POP`, `LATIN R&B`, `VERANO LATINO`, or `NOCHE LATINA`.
- Queue final render as still image with app lyrics lower-left and app spectrum lower-right. Do not create or upload a Gemini/Dreamina/Seedance loop video unless the human explicitly asks for motion.

### HaruHaru

- Korean K-pop/Korean pop vocal channel.
- Korean/default titles should be click-led: `[playlist] 짧은 감정/상황 훅 | 상황에 듣기 좋은 장르 노래모음`, such as `나랑 데이트 할래? | 데이트하기 전 기분 좋아지는 K-POP 힙합 노래모음`. The hook must be tasteful, truthful, and matched by the thumbnail mood.
- Default visual package is now photorealistic Korean lifestyle still images, not animated/anime rotation and not provider loop video.
- Use attractive clearly adult women, handsome stylish adult men, or tasteful adult couple/friend scenes in natural Instagram-style daily-life settings such as Hongdae, Itaewon, Seoul cafe streets, seaside roads, beaches, coastal overlooks, flower gardens, Han River sunset, rooftops, boutiques, or rainy city streets.
- Prefer friend-taken adult day-trip/cafe/seaside snapshots over studio or fashion-campaign portraits. Faces may be visible, but avoid tight straight-on AI-beauty close-ups. Prefer side profile, three-quarter view, candid looking-away, laughing/smiling travel moments, or medium/farther framing where the place and mood also matter.
- A fresh 청순 idol-inspired adult woman can work for bright K-pop concepts, but keep her fictional, natural, and varied; no real idol/member lookalikes, no minors, no school uniforms, no doll-like symmetry, and no over-retouched skin.
- Do not add channel names, logos, style text, title text, badges, or stickers to the cover/thumbnail by default.
- Queue final render as still image with app spectrum lower-right and app lyric overlay lower-left. Do not create or upload a Gemini/Dreamina/Seedance loop video unless the human explicitly asks for motion.

### Storylight OST

- Playful no-vocal Japanese game/anime OST, happy amusement park BGM, and feel-good background music.
- Use game/anime/theme-park environmental motion such as cabinet lights, carousel bulbs, ferris-wheel glow, magical glows, flags, lantern shimmer, toy-like particles, confetti, or water shimmer.
- If text is useful, use broad clickable benefit/style phrases such as `GAME OST`, `ANIME BGM`, `ARCADE BGM`, `CUTE GAME BGM`, `HAPPY GAME MUSIC`, `COZY GAME MUSIC`, `THEME PARK BGM`, or `HAPPY PARK`.

### Cinematic Pulse

- No-vocal cinematic orchestra, movie OST, film score, trailer, heroic, sci-fi, dark fantasy, mystery, or emotional cinematic music.
- Use photorealistic cinematic first-frame / premium movie-poster realism and create a restrained provider loop video.
- Queue renders with `--video-render-source-mode loop_video --video-render-resolution 720p --video-spectrum-overlay-style bars` unless a human explicitly approves a still-image fallback.
- Include a tasteful upper-left cinematic style phrase on the cover/first-frame and use that image as the loop-video starting frame. Use `MOVIE OST`, `CINEMATIC ORCHESTRA`, `FILM SCORE`, `TRAILER MUSIC`, `DARK FANTASY`, or `HEROIC MUSIC`, not the channel name.

### Club Bloom

- No-vocal EDM, house, techno, trance, club, festival, workout, night-drive, or party-energy releases.
- Default visual package is now HaruHaru-style photorealistic friend-taken smartphone/Instagram still images, not provider loop video.
- Prefer attractive clearly adult women in revealing YouTube-safe club fashion at places where club music naturally plays: nightclub, bar, lounge, rooftop club, beach club, pool party, festival VIP area, DJ booth, dance floor, neon city terrace, or yacht/harbor party. Use natural side or three-quarter phone-photo framing, medium or farther composition, slight motion/focus imperfection, and no glossy campaign or centered AI-model headshot. Keep it YouTube-safe with no nudity, sexual acts, minors, teen-coded styling, fetish framing, celebrity likenesses, protected brands, or porn-style composition.
- Keep thumbnails text-free by default. If text is useful, name the club lane with one short transparent-background phrase such as `TECH HOUSE`, `BASS HOUSE`, `TRANCE MIX`, `EDM MIX`, `DEEP HOUSE`, `MELODIC TECHNO`, `FESTIVAL EDM`, or `CLUB MIX`.
- Queue final render as still image with app spectrum lower-right. Do not create or upload a Gemini/Dreamina/Seedance loop video unless the human explicitly asks for motion.

### BibliaCanto

- Combined Bible music channel for Old Testament and New Testament releases.
- Do not put `Old Verse`, `New Verse`, `The Old Verse`, `The New Verse`, or the channel name on visuals.
- If text is useful, use the exact passage range and/or modern music lane: `Genesis 1:1-5`, `Matthew 1:18-25`, `Old Testament Hip-Hop`, `New Testament R&B`, `Bible K-Pop`, or `Scripture Rap`.
- Queue final render with `--video-spectrum-overlay-style none`.

### 불송

- Buddhist scripture-inspired vocal music.
- Cover, thumbnail, and still-image render source should be one clean contemporary female-led Buddhist music visual package. Use clearly adult temple-stay women, Hongdae/Seoul streetwear women practitioners/listeners, Buddha/statue plus modern woman listener scenes, two adult women for duet songs, or female-coded animated/stylized Buddhist practitioner concepts. Do not use men, male monks, male rappers, male listeners, or male-only couple/duet imagery unless the human explicitly asks for a male subject in the current request.
- New 불송 releases are hip-hop-first by default. A short upper-left Korean passage/theme + hip-hop style phrase may be used when useful, such as `법구경 힙합`, `불경 힙합`, `마음챙김 랩`, `자비 힙합`, or `반야심경 랩`. Never use `불송` as visual text, and avoid obscure coined genre labels.
- For vocal tracks, include a concrete Korean lead-vocal tone or delivery phrase in each Suno style string and vary it across tracks, such as `calm low-register Korean rap`, `warm soulful male vocal`, `airy female hook vocal`, `restrained boom-bap spoken rap`, or `warm male/female duet`.
- Keep the music cue subtle and respectful, such as headphones, earbuds, a small speaker, prayer beads, or a human-held microphone. Avoid stale Buddha-only wallpapers, generic old sutra-desk scenes, singing/dancing Buddha, glossy idol/model studio posing, comedic gadget focus, fantasy deity effects, or background-only temple/lotus/lantern images.
- Queue final render as still image with `--video-render-source-mode still_image --video-spectrum-overlay-style calm-bars`; the app burns lyrics in centered `center-breath-serif` style when lyrics are present.
- 불송 is always an app-rendered still-image video channel in normal automation, not a moving-video channel and not a quota fallback. Do not create, upload, or wait for a Gemini/Dreamina/Seedance loop video unless the human explicitly changes this standing 불송 still-image rule in the current request. Image prompts must avoid conceptual words such as `playlist` or `Four Noble Truths`; describe only the visible scene.

Profiles:

- [Soft Hour Radio](soft-hour-radio.md)
- [Tokyo Daydream Radio](tokyo-daydream-radio.md)
- [sundaze](sundaze.md)
- [Solwave Radio](solwave-radio.md)
- [HaruHaru](haruharu.md)
- [Storylight OST](storylight-ost.md)
- [Cinematic Pulse](cinematic-pulse.md)
- [Club Bloom](club-bloom.md)
- [BibliaCanto](the-old-verse.md)
- [불송](bulsong.md)
- [Custom Channel](custom-channel.md)

The automation rotation can include newly connected YouTube channels before dedicated profile docs exist. In that case, `scripts/openclaw-release channel-profile` returns `custom-channel.md`; use it instead of copying another channel's visual signature.
