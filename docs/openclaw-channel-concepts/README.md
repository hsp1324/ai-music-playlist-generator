# OpenClaw Channel Concept Planners

Use these documents after the next-release planner selects a channel, or when the human explicitly names a channel. They are for deciding the next playlist concept, not for final cover/video rendering details.

The channel profile docs in `docs/openclaw-channel-profiles/` control visual identity, cover, thumbnail, loop video, and channel-specific metadata details. These concept planner docs control what kind of playlist to make next and how to avoid repetition.

## Required Workflow

1. Run `scripts/openclaw-release list-releases`.
2. Treat that output as the app's known YouTube upload catalog. It includes release titles, channel titles, YouTube ids, durations, and recent update times.
3. Filter recent releases by the selected `youtube_channel_title`.
4. Inspect at least the latest 5 releases on the selected channel when available, plus the latest 15-20 releases globally for cross-channel repetition.
5. Extract recent setting, use case, subgenre, lyric premise, thumbnail phrase, visual scene, and title pattern.
6. Read exactly one channel concept planner from this directory.
7. Choose one fresh concept that fits that channel and does not repeat recent releases.
8. Then read the matching channel profile and continue with `docs/openclaw-skills.md` Skill 3.

If the app catalog looks incomplete or the human says there are YouTube videos outside this app, report that limitation before claiming a concept is non-duplicated.

## Global Planning Rules

- Every channel title should be broad, searchable, and useful to normal viewers. A specific cover/video scene can guide atmosphere, but the release title should usually lead with genre identity plus a listening reason or emotion.
- For vocal channels, the YouTube title/use case is packaging only. Lyrics should be written as strong standalone songs first; they do not need to mention or explain the title, visual scene, thumbnail text, or playlist use case.
- Do not sacrifice lyric quality to force SEO terms into the song. The melody, beat, vocal delivery, hook, and emotional arc are the source of truth for lyrics.

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
- [Custom Channel](custom-channel.md)

The rotation roster is not limited to this file. For automation, OpenClaw must read `/youtube/status` and include every connected channel in `channels` unless the docs explicitly mark that channel inactive/excluded. Newly connected channels are active by default. If a connected channel has no dedicated planner yet, use `custom-channel.md` and infer the channel direction from its name, local app history, and the human's recent instructions.
If `/youtube/status` shows `AI썰전`, treat it as the legacy upload destination for `Storylight OST` until the human manually renames/reconnects the YouTube channel. Do not continue the retired AI썰전/Signal Room/Signal Desk/Midnight Cue concept direction.
`AnimeMix` is connected but manual-only for popular-song remake/cover work and must not be selected by automatic next-release rotation unless the human explicitly asks.
