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
- Text must be integrated into the artwork with safe margins. Do not use hard black boxes, detached badges, pills, capsules, stickers, UI tags, logos, or watermark-like marks.
- The thumbnail should usually be created from the final cover as a reference/edit derivative. Keep the same scene and add only the short click text needed for YouTube.
- The loop video should start from the cover/first-frame image, not from a busy text thumbnail, unless the profile explicitly says the first-frame and thumbnail are the same.
- For Dreamina/Seedance, set duration in the provider UI, not in the prompt. Default clips are `7 seconds`; `불송` clips are `6 seconds`; HaruHaru photorealistic clips use 1080p. If the duration selector is hidden when the screen opens, gently drag/scroll the settings/control row to the right until it is visible, then set the required duration before Generate.
- For Gemini, do not ask for a duration. Upload the generated MP4 as-is after inspection.
- Do not use `playlist`, `music visual`, `visualizer shot`, `seamless loop`, `repeat`, `cyclic`, or conceptual scripture framework words in video prompts when they can be replaced with visible scene details.
- Use positive fixed-shot language: `single fixed camera shot`, `locked-off camera`, `one uninterrupted calm environmental take`, `same composition from first to last frame`.
- Keep negative prompt lists short. Overloaded `do not` wording can cause provider models to focus on the forbidden action and create hard cuts, resets, or layout changes.
- If Gemini/Veo adds its own provider logo or watermark, usually in the bottom-right corner, accept it as an unavoidable provider artifact. Do not regenerate only because that provider logo is present.
- If Gemini blocks generation for copyright, protected IP, policy, moderation, or similar issues, retry safely up to 10 blocked attempts. Remove protected names and risky terms rather than retrying the same prompt.

## Quick Asset Summary

### Soft Hour Radio

- Calm illustrated/stylized BGM visuals for study, work, sleep, reading, cafe, lofi, or quiet focus.
- Use locked camera and calm environmental motion. Prefer `none` or very restrained spectrum for very quiet releases.
- If text is useful, use use-case/style phrases such as `LOFI`, `CAFE PIANO`, `FOCUS MUSIC`, `STUDY BGM`, `DEEP SLEEP`, or `RAINY NIGHT`.

### Tokyo Daydream Radio

- Mainstream J-pop/Japanese pop visual identity.
- Default signature: exactly three people walking toward the viewer in a front-view composition.
- In loop video, the people walk forward while the camera moves backward at the same speed so subject size stays stable.
- If text is useful, use short J-pop/style phrases such as `J-POP`, `CITY POP`, `ANIME POP`, `J-POP DRIVE`, or `SUMMER J-POP`.

### sundaze

- English/US-pop counterpart to Tokyo Daydream Radio.
- Let the concept decide the scene; do not force a recurring visual.
- If text is useful, name the pop lane or use case: `POP R&B`, `DANCE POP`, `SYNTH POP`, `FEEL GOOD POP`, `SUMMER POP`, or `NIGHT DRIVE`.

### Solwave Radio

- Latin/Spanish vocal pop.
- Use warm, rhythmic, beach, night-city, dance, or tropical visuals when the concept supports it.
- If text is useful, use natural Latin/Spanish lane text: `POP LATINO`, `REGGAETON SUAVE`, `BACHATA POP`, `LATIN R&B`, `VERANO LATINO`, or `NOCHE LATINA`.

### HaruHaru

- Korean K-pop/Korean pop vocal channel.
- Keep a 2:1 photorealistic-to-animated visual ratio when recent history allows.
- Photorealistic visuals can feature a clearly adult woman in tasteful fashion/lifestyle scenes with face hidden or obscured. Keep it non-explicit and avoid minors, school-uniform cues, celebrity likenesses, or fetish framing.
- In photorealistic loop videos, keep the subject the same size and crop for the full clip. The camera tracks at the same speed/distance if she moves; background parallax and environment provide motion.
- If text is useful, use short lane text such as `K-POP`, `K-R&B`, `K-POP HIPHOP`, `DANCE POP`, `SYNTH POP`, or `POP ROCK`.

### Storylight OST

- Playful no-vocal Japanese game/anime OST and BGM.
- Use game/anime environmental motion such as cabinet lights, magical glows, flags, lantern shimmer, toy-like particles, or water shimmer.
- If text is useful, use broad clickable benefit/style phrases such as `GAME OST`, `ANIME BGM`, `ARCADE BGM`, `CUTE GAME BGM`, `HAPPY GAME MUSIC`, or `COZY GAME MUSIC`.

### Cinematic Pulse

- No-vocal cinematic orchestra, movie OST, film score, trailer, heroic, sci-fi, dark fantasy, mystery, or emotional cinematic music.
- Use photorealistic cinematic first-frame / premium movie-poster realism and create a restrained provider loop video.
- Queue renders with `--video-render-source-mode loop_video --video-render-resolution 720p --video-spectrum-overlay-style bars` unless a human explicitly approves a still-image fallback.
- Include a tasteful lower-left cinematic style phrase on the cover/first-frame and use that image as the loop-video starting frame. Use `MOVIE OST`, `CINEMATIC ORCHESTRA`, `FILM SCORE`, `TRAILER MUSIC`, `DARK FANTASY`, or `HEROIC MUSIC`, not the channel name.

### Club Bloom

- No-vocal EDM, house, techno, trance, club, festival, workout, night-drive, or party-energy releases.
- Prefer active DJ/performance visuals in desirable dance locations: beach-club deck, rooftop skyline DJ set, nightclub booth, concert/festival stage, warehouse rave, pool party, yacht/harbor party, neon city terrace, or cyber club.
- If text is useful, name the club lane near the front: `TECH HOUSE`, `BASS HOUSE`, `TRANCE MIX`, `EDM MIX`, `DEEP HOUSE`, `MELODIC TECHNO`, `FESTIVAL EDM`, or `CLUB MIX`.

### BibliaCanto

- Combined Bible music channel for Old Testament and New Testament releases.
- Do not put `Old Verse`, `New Verse`, `The Old Verse`, `The New Verse`, or the channel name on visuals.
- If text is useful, use the exact passage range and/or music lane: `Genesis 1:1-5`, `Matthew 1:18-25`, `Old Testament Jazz`, `Gospel R&B`, or `Scripture Worship`.
- Queue final render with `--video-spectrum-overlay-style none`.

### 불송

- Buddhist scripture-inspired vocal music.
- Cover, thumbnail, first-frame, and loop-video first frame should be one clean visual package with a short Korean passage/theme + style phrase when useful, such as `팔정도 명상팝`, `자비 트립합`, or `무상 불교 재즈`. Never use `불송` as visual text.
- Use photorealistic/premium Buddhist visuals by default. Cute/gentle animation is allowed occasionally when the music lane fits.
- Use Seedance/Dreamina `2.0 Fast`, first-frame only, `16:9`, `720p`, exactly `6 seconds`.
- Queue final render with `--video-spectrum-overlay-style calm-bars`; the app burns lyrics in centered `center-breath-serif` style when lyrics are present.
- Video prompts must avoid conceptual words such as `playlist` or `Four Noble Truths`; describe only the visible scene and motion.

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
- [불송](the-new-verse.md)
- [Custom Channel](custom-channel.md)

The automation rotation can include newly connected YouTube channels before dedicated profile docs exist. In that case, `scripts/openclaw-release channel-profile` returns `custom-channel.md`; use it instead of copying another channel's visual signature.
