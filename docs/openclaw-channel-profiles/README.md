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

Global branding rule for every channel:

- Every final cover/first-frame image must include the selected channel name as a large, readable lower-left brand label. It should match the visual scale of the channel-brand line used on the YouTube thumbnail. Target roughly 18-24% of the image width, or about 5-6% of image height for text cap height. On a 2048x1152 cover, `Soft Hour Radio` should be roughly 360-500 px wide with clearly readable letter height.
- The cover/first-frame should contain only that channel name. Do not add title text, genre text, duration text, lyrics, UI, logos, or unrelated words to the cover/first-frame.
- The Dreamina/Seedance loop video must preserve the exact lower-left channel name for the full clip. Reject/regenerate clips where the channel name disappears, flickers, moves, morphs, changes spelling, changes style drastically, or becomes unreadable.
- For normal OpenClaw work, Dreamina/Seedance duration must be set to `10 seconds` before the Generate click. Do not create a `5 seconds` draft/test clip first; the helper rejects short loop clips unless `--allow-short-loop-video` is used after explicit human approval.
- The YouTube thumbnail still needs large click text above or near a channel-brand line. Keep the channel-brand line size/style consistent with the large cover channel label.
- Metadata titles should be broad and public-facing across all channels. Use the visual scene to guide cover/video mood, but do not let a niche scene name become the main title unless it is truly the most searchable hook.
- If Dreamina/Seedance blocks generation for inappropriate content, copyright, moderation, or policy reasons, retry up to 10 total attempts with a safer rewritten prompt. Send Slack before every retry with `scripts/openclaw-release slack-notify --text "영상 만들기 실패해서 프롬프트를 수정해 다시 만듭니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`. If 10 attempts fail, send a final Slack failure message and stop before render/publish unless the human explicitly approves a still-image fallback.

## Quick Asset Summary

Use this as the fast checklist after channel selection. The full profile file remains the source of truth.

### Soft Hour Radio

Cover / first frame:

- 16:9 illustrated/anime/stylized image for long background listening.
- Subject, scene, color, and camera are decided by the specific release concept.
- No fixed mascot, fixed character count, or repeated channel composition.
- Only text allowed is the large lower-left `Soft Hour Radio` brand label.

Loop video:

- Animate the cover/first-frame with calm but clearly visible natural motion derived from the release concept.
- Keep the composition stable and long-listening friendly.
- Preserve the large lower-left `Soft Hour Radio` brand label exactly for the whole clip.
- Use several environmental motion layers when the first frame supports them so Soft Hour clips have continuous visible motion without becoming visually noisy.
- Do not add subtitles, lyrics, title text, duration text, logos, UI, or unrelated words.

YouTube thumbnail:

- Start from the final cover as an image-to-image/reference edit.
- Keep the same subject, placement, lighting, palette, props, and camera angle.
- Add large readable use-case or mood text such as `CAFE PIANO`, `FOCUS MUSIC`, `STUDY BGM`, `DEEP SLEEP`, `RAINY NIGHT`, or `CALM READING`.
- Add `SOFT HOUR RADIO` brand line, visually consistent with the large cover channel label.
- Do not add duration badges like `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

### Tokyo Daydream Radio

Cover / first frame:

- 16:9 illustrated/anime/stylized image for mainstream J-pop/Japanese pop, Tokyo/Japan pop, city-pop, dance-pop, synth-pop, pop-rock, anime-pop, or similar releases.
- Anime/OST-like music is included, but the channel is broader mainstream J-pop/pop and should not feel anime OST-only.
- Default signature is exactly three people seen from behind, walking forward away from the viewer.
- Keep the three people centered and visually important unless the human explicitly requested a different visual concept.
- Only text allowed is the large lower-left `Tokyo Daydream Radio` brand label.

Loop video:

- Animate the cover/first-frame as one continuous forward-moving shot.
- Keep the three people walking away from the camera with subtle camera-follow and environmental motion.
- Preserve the large lower-left `Tokyo Daydream Radio` brand label exactly for the whole clip; do not shrink it.
- Do not add subtitles, lyrics, title text, duration text, logos, UI, or unrelated words.

YouTube thumbnail:

- Start from the final cover as an image-to-image/reference edit.
- Preserve the same three people, positions, clothing colors, silhouettes, lighting, palette, background landmarks, and camera angle.
- Use large `J-POP`.
- Use `TOKYO DAYDREAM RADIO` directly beneath it, visually consistent with the large cover channel label.
- Keep the centered people important; text must fit around them and must not push them sideways.
- Do not add duration badges like `1 HOUR`, `60 MIN`, `1時間`, clocks, or timers.

### sundaze

Cover / first frame:

- 16:9 illustrated/anime/stylized image for English-language pop, American pop, US/UK pop, western pop, dance-pop, synth-pop, pop-rock, or similar releases.
- This is the English/US-pop counterpart to Tokyo Daydream Radio.
- No fixed recurring visual signature yet. The playlist concept decides the scene, subject, color, and camera.
- Only text allowed is the large lower-left `sundaze` brand label.

Loop video:

- Animate the cover/first-frame according to the specific playlist concept.
- Preserve the large lower-left `sundaze` brand label exactly for the whole clip.
- Do not add subtitles, lyrics, title text, duration text, logos, UI, or unrelated words.

YouTube thumbnail:

- Start from the final cover as an image-to-image/reference edit.
- Preserve the same subject, placement, lighting, palette, props, and camera angle.
- Add large readable English pop text such as `POP HITS`, `SUMMER POP`, `NIGHT DRIVE`, `DANCE POP`, `FEEL GOOD POP`, or `HEARTBREAK POP`.
- Add `SUNDAZE` brand line, visually consistent with the large cover channel label.

### Solwave Radio

Cover / first frame:

- 16:9 illustrated/anime/stylized image for Latin/Spanish-language music: Latin pop, Spanish pop, urbano latino, reggaeton pop, bachata pop, salsa pop, cumbia pop, tropical dance-pop, or similar releases.
- This is the Spanish/Latin counterpart to Tokyo Daydream Radio.
- No fixed recurring visual signature yet. The playlist concept decides the scene, subject, color, and camera.
- Only text allowed is the large lower-left `Solwave Radio` brand label.

Loop video:

- Animate the cover/first-frame according to the specific playlist concept and Latin pop mood.
- Preserve the large lower-left `Solwave Radio` brand label exactly for the whole clip.
- Do not add subtitles, lyrics, title text, duration text, logos, UI, or unrelated words.

YouTube thumbnail:

- Start from the final cover as an image-to-image/reference edit.
- Preserve the same subject, placement, lighting, palette, props, and camera angle.
- Add large readable Latin/Spanish text such as `LATIN POP`, `REGGAETON`, `VERANO LATINO`, `SPANISH POP`, `FIESTA LATINA`, or `NOCHE LATINA`.
- Add `SOLWAVE RADIO` brand line, visually consistent with the large cover channel label.

### HaruHaru

Cover / first frame:

- 16:9 illustrated/anime/stylized image for original Korean K-pop vocal releases.
- No fixed recurring visual signature yet. The playlist concept decides the scene, subject, color, and camera.
- Only text allowed is the large lower-left `HaruHaru` brand label.

Loop video:

- Animate the cover/first-frame according to the specific K-pop playlist concept.
- Preserve the large lower-left `HaruHaru` brand label exactly for the whole clip.
- Do not add subtitles, lyrics, title text, duration text, logos, UI, or unrelated words.

YouTube thumbnail:

- Start from the final cover as an image-to-image/reference edit.
- Preserve the same subject, placement, lighting, palette, props, and camera angle.
- Add large readable K-pop text such as `K-POP`, `SEOUL POP`, `DANCE POP`, `HEARTBREAK`, `SUMMER KPOP`, or `RAINY KPOP`.
- Add `HARUHARU` brand line, visually consistent with the large cover channel label.

### Storylight OST

Cover / first frame:

- 16:9 illustrated/anime/stylized/storybook image for fantasy, fairy-tale, cozy RPG, game-OST, magical village, forest path, castle road, story BGM, or calm adventure instrumental releases.
- No fixed recurring visual signature yet. The playlist concept decides the fantasy/story scene, object, palette, and camera.
- Only text allowed is the large lower-left `Storylight OST` brand label.
- If the connected YouTube channel still appears as `AI썰전`, use it only as the upload destination; the intended public brand label is `Storylight OST`.

Loop video:

- Animate the cover/first-frame with visible storybook environmental motion such as lantern glow, fireflies, drifting magic dust, leaves, candle flame, window glow, snow, water shimmer, clouds, or star shimmer.
- Preserve the large lower-left `Storylight OST` brand label exactly for the whole clip.
- Do not add subtitles, title text, duration text, logos, UI, protected characters, studio references, or unrelated words.

YouTube thumbnail:

- Start from the final cover as an image-to-image/reference edit.
- Preserve the same subject, placement, lighting, palette, props, and camera angle.
- Add large readable fantasy/story text such as `FANTASY OST`, `COZY RPG`, `MAGIC VILLAGE`, `STORY BGM`, `FAIRY TALE MUSIC`, or `GAME TOWN BGM`.
- Add `STORYLIGHT OST` brand line, visually consistent with the large cover channel label.

### Cinematic Pulse

Cover / first frame:

- 16:9 illustrated/anime/stylized/poster-art image for cinematic, trailer, battle, final boss, heroic, sci-fi action, dark fantasy, game-combat, or epic orchestral instrumental releases.
- Strong focal scene, bold lighting, readable silhouettes, and high contrast.
- Only text allowed is the large lower-left `Cinematic Pulse` brand label.

Loop video:

- Animate the cover/first-frame with controlled cinematic motion such as storm clouds, sparks, embers, dust, banners, energy pulses, engine glow, portal light, rain, or atmospheric light movement.
- Preserve the large lower-left `Cinematic Pulse` brand label exactly for the whole clip.
- Do not add gore, real war footage, protected characters, franchise references, subtitles, title text, logos, UI, or unrelated words.

YouTube thumbnail:

- Start from the final cover as an image-to-image/reference edit.
- Preserve the same subject, placement, lighting, palette, props, and camera angle.
- Add large readable cinematic text such as `EPIC BATTLE`, `FINAL BOSS`, `DARK FANTASY`, `HEROIC MUSIC`, `SCI-FI ACTION`, `TRAILER MUSIC`, or `BATTLE OST`.
- Add `CINEMATIC PULSE` brand line, visually consistent with the large cover channel label.

### Club Bloom

Cover / first frame:

- 16:9 illustrated/anime/stylized neon image for EDM, house, dance, festival, workout, night-drive, gaming, club, or party-energy releases.
- No fixed recurring visual signature yet. The playlist concept decides the scene, subject, color, and camera.
- Only text allowed is the large lower-left `Club Bloom` brand label.

Loop video:

- Animate the cover/first-frame with visible rhythmic motion such as light sweeps, neon reflections, LED pulses, laser haze, stage particles, city lights, road light streaks, dance-floor glow, or atmospheric color pulses.
- Preserve the large lower-left `Club Bloom` brand label exactly for the whole clip.
- Do not add subtitles, lyrics, title text, duration text, UI, logos, explicit nudity, unsafe minors, protected brands, or unrelated words.

YouTube thumbnail:

- Start from the final cover as an image-to-image/reference edit.
- Preserve the same subject, placement, lighting, palette, props, and camera angle.
- Add large readable dance text such as `EDM MIX`, `HOUSE MUSIC`, `NIGHT DRIVE`, `WORKOUT EDM`, `CLUB HITS`, `FESTIVAL EDM`, or `DANCE MIX`.
- Add `CLUB BLOOM` brand line, visually consistent with the large cover channel label.

### The Old Verse

Cover / first frame:

- 16:9 illustrated/anime/stylized biblical image for Old Testament scripture-inspired music.
- Follow the selected Old Testament passage in sequence from Genesis onward.
- Only text allowed is the large lower-left `The Old Verse` brand label.

Loop video:

- Animate the cover/first-frame with reverent symbolic motion such as light over water, stars, oil-lamp glow, scroll dust, desert wind, cloud/fire glow, rain, water shimmer, or temple light.
- Preserve the large lower-left `The Old Verse` brand label exactly for the whole clip.
- Do not add verse text, subtitles, lyrics, title text, duration text, logos, UI, or long scripture quotes.

YouTube thumbnail:

- Start from the final cover as an image-to-image/reference edit.
- Preserve the same passage scene, lighting, palette, props, and camera angle.
- Add large readable Bible text such as `GENESIS SONGS`, `OLD TESTAMENT`, `BIBLE MUSIC`, `PSALMS MUSIC`, `SCRIPTURE SONGS`, or `EXODUS MUSIC`.
- Add `THE OLD VERSE` brand line, visually consistent with the large cover channel label.

### The New Verse

Cover / first frame:

- 16:9 illustrated/anime/stylized Gospel/worship image for New Testament scripture-inspired music.
- Follow the selected New Testament passage in sequence from Matthew onward.
- Only text allowed is the large lower-left `The New Verse` brand label.

Loop video:

- Animate the cover/first-frame with warm worshipful motion such as sunrise light, candle glow, dust in light, gentle wind, sea shimmer, doorway light, fabric movement, lamp flame, or cloud movement.
- Preserve the large lower-left `The New Verse` brand label exactly for the whole clip.
- Do not add verse text, subtitles, lyrics, title text, duration text, logos, UI, or long scripture quotes.

YouTube thumbnail:

- Start from the final cover as an image-to-image/reference edit.
- Preserve the same passage scene, lighting, palette, props, and camera angle.
- Add large readable worship text such as `GOSPEL SONGS`, `NEW TESTAMENT`, `JESUS MUSIC`, `GRACE MUSIC`, `SCRIPTURE SONGS`, or `WORSHIP POP`.
- Add `THE NEW VERSE` brand line, visually consistent with the large cover channel label.

Profiles:

- [Soft Hour Radio](soft-hour-radio.md)
- [Tokyo Daydream Radio](tokyo-daydream-radio.md)
- [sundaze](sundaze.md)
- [Solwave Radio](solwave-radio.md)
- [HaruHaru](haruharu.md)
- [Storylight OST](storylight-ost.md)
- [Cinematic Pulse](cinematic-pulse.md)
- [Club Bloom](club-bloom.md)
- [The Old Verse](the-old-verse.md)
- [The New Verse](the-new-verse.md)
- [Custom Channel](custom-channel.md)

The automation rotation can include newly connected YouTube channels before dedicated profile docs exist. In that case, `scripts/openclaw-release channel-profile` returns `custom-channel.md`; use it instead of copying another channel's visual signature.
If `/youtube/status` shows `AI썰전`, treat it as the legacy/old title for `Club Bloom` until YouTube status refreshes to the renamed channel. Do not continue the retired AI썰전/Signal Room/Signal Desk/Midnight Cue research/debate concept direction.
`AnimeMix` is connected but manual-only for popular-song remake/cover work and must not be selected by automatic next-release rotation unless the human explicitly asks.
