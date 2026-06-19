# OpenClaw Channel Concept Planners

Use these documents after the next-release planner selects a channel, or when the human explicitly names a channel. They are for deciding the next playlist concept, not for final cover/video rendering details.

The channel profile docs in `docs/openclaw-channel-profiles/` control visual identity, cover, thumbnail, loop video, and channel-specific metadata details. These concept planner docs control what kind of playlist to make next and how to avoid repetition.

## Required Workflow

1. Run `scripts/openclaw-release list-releases`.
2. Treat that output as the app's known YouTube upload catalog. It includes release titles, channel titles, YouTube ids, durations, and recent update times.
3. Filter recent releases by the selected `youtube_channel_title`.
4. Inspect at least the latest 5 releases on the selected channel when available, plus the latest 15-20 releases globally for cross-channel repetition.
5. Extract recent setting, use case, subgenre, lyric premise, thumbnail phrase, visual scene, and title pattern.
6. Read [../openclaw-channel-genre-taxonomy.md](../openclaw-channel-genre-taxonomy.md) and pick one underused broad YouTube playlist bucket plus one detailed video style lane.
7. Read exactly one channel concept planner from this directory.
8. Choose one fresh concept that fits that channel, stays inside the selected detailed style lane, and does not repeat recent releases.
9. Then read the matching channel profile and continue with `docs/openclaw-skills.md` Skill 3.

If the app catalog looks incomplete or the human says there are YouTube videos outside this app, report that limitation before claiming a concept is non-duplicated.

## Global Planning Rules

- Every channel title should be broad, searchable, and useful to normal viewers. A specific cover/video scene can guide atmosphere, but the release title should usually lead with genre identity plus a listening reason or emotion.
- Each release should be one coherent style lane, not a mixed sampler. The rendered video can use a detailed style such as trap, boom bap, bachata pop, lofi study, or tech house, while YouTube playlist assignment uses the broader bucket from the taxonomy.
- For vocal channels, the YouTube title/use case is packaging only. Lyrics should be written as strong standalone songs first; they do not need to mention or explain the title, visual scene, thumbnail text, or playlist use case.
- Do not sacrifice lyric quality to force SEO terms into the song. The melody, beat, vocal delivery, hook, and emotional arc are the source of truth for lyrics.
- For every Suno generation on every channel, treat the prompt as a credit-bearing full song/cue, not a short sketch. Do not use lower-bound duration wording such as `at least 2 minutes` or `minimum 2 minutes`; instead build enough song/arrangement structure to naturally land near a full 4-minute result. For vocal songs, write longer lyrics with a real first verse, second verse, chorus returns, bridge/breakdown or rap/sung contrast, final lift, and ending when the genre supports it. For instrumental/no-vocal tracks, write longer bracket-only section metatags with intro, developed main sections, variation/breakdown, final theme, and resolved outro. Tracks shorter than 4:00 are still valid uploads when they fit; only tracks under 1:00 are a default blocker, and 1:00-1:59 tracks are accepted and recorded for later analysis.
- `thumbnail_text` is only the short phrase to place on the image. It must never imply a black box, dark panel, sticker, badge, pill, capsule, or any filled background behind the letters; final rendering rules in the channel profile require transparent-background text directly on the artwork.

## Output Contract

Return a compact plan before generating audio:

- `selected_channel`
- `concept_doc`
- `profile_doc`
- `release_title`
- `release_description`
- `music_direction`
- `visual_direction`
- `thumbnail_text`
- `metadata_language_plan`
- `recent_releases_checked`
- `why_this_is_fresh`

## Active Concept Planners

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

The rotation roster is not limited to this file. For automation, OpenClaw must read `/youtube/status` and include every connected channel in `channels` unless the docs explicitly mark that channel inactive/excluded. `MusicSun` is the only current manual-only channel and must not enter automatic rotation unless the human explicitly requests it. Newly connected channels are active by default. If a connected channel has no dedicated planner yet, use `custom-channel.md` and infer the channel direction from its name, local app history, and the human's recent instructions.
Do not continue the retired Signal Room/Signal Desk/Midnight Cue research/debate concept direction unless the human explicitly revives it.
