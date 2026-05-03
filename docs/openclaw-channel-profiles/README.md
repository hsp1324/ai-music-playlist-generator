# OpenClaw Channel Profiles

OpenClaw should decide the channel first, then read exactly one channel profile before making cover, thumbnail, or loop-video assets.

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

The command returns `youtube_channel_title` and `profile_doc`. Read that `profile_doc` and do not mix visual signatures from another channel.

Global branding rule for every channel:

- Every final cover/first-frame image must include the selected channel name as a medium-sized, readable lower-left watermark. Do not make channel names tiny. Target roughly 7-9% of the image width and keep enough contrast or subtle backing shadow/glow for mobile playback and video compression.
- The cover/first-frame should contain only that channel name. Do not add title text, genre text, duration text, lyrics, UI, logos, or unrelated words to the cover/first-frame.
- The Dreamina/Seedance loop video must preserve the exact lower-left channel name for the full clip. Reject/regenerate clips where the channel name disappears, flickers, moves, morphs, changes spelling, changes style drastically, or becomes unreadable.
- The YouTube thumbnail still needs large click text above or near a channel-brand line. Keep the channel-brand line size/style consistent with the cover watermark when possible.

## Quick Asset Summary

Use this as the fast checklist after channel selection. The full profile file remains the source of truth.

### Soft Hour Radio

Cover / first frame:

- 16:9 illustrated/anime/stylized image for long background listening.
- Subject, scene, color, and camera are decided by the specific release concept.
- No fixed mascot, fixed character count, or repeated channel composition.
- Only text allowed is the medium-sized lower-left `Soft Hour Radio` watermark.

Loop video:

- Animate the cover/first-frame with subtle, calm motion derived from the release concept.
- Keep the composition stable and long-listening friendly.
- Preserve the lower-left `Soft Hour Radio` watermark exactly for the whole clip.
- Do not add subtitles, lyrics, title text, duration text, logos, UI, or unrelated words.

YouTube thumbnail:

- Start from the final cover as an image-to-image/reference edit.
- Keep the same subject, placement, lighting, palette, props, and camera angle.
- Add large readable use-case or mood text such as `CAFE PIANO`, `FOCUS MUSIC`, `STUDY BGM`, `DEEP SLEEP`, `RAINY NIGHT`, or `CALM READING`.
- Add `SOFT HOUR RADIO` brand line, visually consistent with the larger cover watermark.
- Do not add duration badges like `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

### Tokyo Daydream Radio

Cover / first frame:

- 16:9 illustrated/anime/stylized image for mainstream J-pop/Japanese pop, Tokyo/Japan pop, city-pop, dance-pop, synth-pop, pop-rock, anime-pop, or similar releases.
- Anime/OST-like music is included, but the channel is broader mainstream J-pop/pop and should not feel anime OST-only.
- Default signature is exactly three people seen from behind, walking forward away from the viewer.
- Keep the three people centered and visually important unless the human explicitly requested a different visual concept.
- Only text allowed is the medium-sized lower-left `Tokyo Daydream Radio` watermark.

Loop video:

- Animate the cover/first-frame as one continuous forward-moving shot.
- Keep the three people walking away from the camera with subtle camera-follow and environmental motion.
- Preserve the medium-sized lower-left `Tokyo Daydream Radio` watermark exactly for the whole clip; do not shrink it.
- Do not add subtitles, lyrics, title text, duration text, logos, UI, or unrelated words.

YouTube thumbnail:

- Start from the final cover as an image-to-image/reference edit.
- Preserve the same three people, positions, clothing colors, silhouettes, lighting, palette, background landmarks, and camera angle.
- Use large `J-POP`.
- Use `TOKYO DAYDREAM RADIO` directly beneath it, visually consistent with the larger cover watermark.
- Keep the centered people important; text must fit around them and must not push them sideways.
- Do not add duration badges like `1 HOUR`, `60 MIN`, `1時間`, clocks, or timers.

Profiles:

- [Soft Hour Radio](soft-hour-radio.md)
- [Tokyo Daydream Radio](tokyo-daydream-radio.md)
