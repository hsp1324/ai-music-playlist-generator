# OpenClaw Channel Profile: Custom Channel

## Publishing schedule — effective 2026-10-19

Every channel publishes at most one video each Wednesday at 07:00 Asia/Seoul (Tuesday 22:00 UTC). This overrides all older daily, dual-slot, and branch-specific times below. Upload/render/metadata preparation may continue on other days; public publication must use the server-calculated weekly slot.
Cinematic Pulse shares ONE weekly channel slot: orchestra on 2026-10-21, cute_game on 2026-10-28, orchestra on 2026-11-04, alternating every week thereafter. Each lane therefore publishes every 14 days, always at 07:00. Set the exact lane; do not schedule two videos on the same Wednesday. Do not manually reintroduce daily timestamps. Follow `docs/openclaw-weekly-publishing.md`.

## Prospective policy update — 2026-10-02

Read [audience-first image copy](../openclaw-thumbnail-copy-policy.md) and [Suno v6 generation/reuse](../openclaw-suno-v6-policy.md) before new work. Preserve existing songs, images, releases, jobs, and approved briefs; continue them unchanged. For new releases, bare genre labels are not primary image hooks; new songs use verified standard v6, reuse is v6-only except human-Good legacy tracks at the tail, and global shuffle must not defeat that order. Existing text-free defaults and routing exclusions remain in force.

New copy direction for this channel: one audience-native feeling or listening-situation hook, or a strong text-free image. These are examples, not fixed slogans; keep the actual music promise and channel language truthful.
Use this when the selected connected YouTube channel does not yet have a dedicated profile file.

## Global image rule — effective 2026-10-20

For every new release, use one approved cover image file for playback and the YouTube thumbnail. Do not create or edit a separate thumbnail, including any crop, reframe, grade, or thumbnail-only lettering. Any permitted words must be part of the single cover image. Compose the image to read well at full size and at thumbnail size. Keep existing releases and published assets unchanged. Follow the natural-image quality standards in [the shared visual asset policy](../openclaw-visual-assets.md); this rule overrides older instructions below if they conflict.

## Visual Identity

- Let the playlist concept and channel title decide the cover, thumbnail, and loop-video direction.
- Do not reuse another channel's fixed signature unless the human explicitly asks.
- The cover/first-frame must be 16:9 and illustrated, anime, stylized, painterly, graphic, or otherwise non-photorealistic unless the channel identity clearly requires another style.
- Do not put the selected channel name, a channel logo, or a channel-brand line on the cover/first-frame.
- New image copy follows [the audience-first policy](../openclaw-thumbnail-copy-policy.md): one audience-native feeling or listening-situation hook, or a strong text-free image. Prefer one natural listener promise over a standalone genre label; text-free remains valid. Keep letters integrated directly on the artwork with no filled background.

## YouTube Thumbnail

- Use the exact approved cover image file as the thumbnail; do not create or edit a separate thumbnail image.
- Preserve the same subject, scene, camera angle, palette, and main composition so the thumbnail and rendered video feel connected.
- New image copy follows [the audience-first policy](../openclaw-thumbnail-copy-policy.md): one audience-native feeling or listening-situation hook, or a strong text-free image. Prefer one natural listener promise over a standalone genre label; text-free remains valid. Keep letters integrated directly on the artwork with no filled background.
- Keep thumbnail text directly on the image with a transparent background. Use font weight, color, subtle shadow, thin outline, or local contrast for readability; do not use black boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, stickers, badges, pills, capsules, or any filled label shape behind text.
- Do not add the selected channel name or a channel logo.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Loop Video

- Use the uploaded cover/first-frame image as the exact starting frame.
- Generate a short loop video with Gemini first when the custom channel needs motion. If Gemini quota is exhausted, unavailable, or on cooldown, use Dreamina **Seedance Mini** from the same first frame; do not use another Dreamina model or CapCut. Every provider output must pass the fixed camera-angle/crop/focus check in `docs/openclaw-visual-assets.md`; otherwise use the approved still-image fallback immediately.
- Animate only visual elements that already fit the first frame and playlist concept.
- If the first frame has a short style/theme phrase, keep it stable and readable. Do not invent a channel name.
- The final frame should return close to the opening composition so the app's loop crossfade feels natural. The app uses 2.0 seconds for Gemini-tagged loop videos and 1.5 seconds for the default provider path.
- Do not add subtitles, lyrics, title text, duration text, logos, UI, or unrelated words.

## Metadata

- Follow `docs/openclaw-youtube-metadata.md`.
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds awkward, weak, or less clickable, rewrite it while keeping the inferred channel identity, genre/lane, and real listening use case truthful.
- If the channel has no dedicated language rule, include every supported localization unless the human says otherwise.
- Choose the default language from the channel identity. If unclear, use English for global pop-style channels and Korean for Korean-run background/BGM channels.
- Make titles broad and public-facing first. Use exact visual-scene details as atmosphere unless they are clearly the strongest searchable hook for that custom channel.
- For vocal channels, lyrics are judged by song quality first: melody fit, beat/rhythm, vocal tone, hook, emotional arc, and replay value. They do not need to mention the title/use case.
