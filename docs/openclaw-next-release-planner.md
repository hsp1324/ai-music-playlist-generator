# OpenClaw Next Release Planner Skill

Use this skill when the AI Music web app asks OpenClaw to make the next one-hour playlist after a private YouTube publish completes.

This is the first step of the continuous automation loop. It chooses the next channel, delegates channel-specific concept selection to `docs/openclaw-channel-concepts/`, then hands off to the automatic private playlist publisher in [openclaw-skills.md](openclaw-skills.md).

## Goal

Choose the next channel and a fresh one-hour playlist concept that fits that channel, avoids recent repetition, and can be privately published end-to-end.

The current active channel roster is:

- `Tokyo Daydream Radio`
- `Soft Hour Radio`
- `sundaze`
- `Solwave Radio`

Future channels must get both files before entering rotation:

- `docs/openclaw-channel-profiles/CHANNEL.md`
- `docs/openclaw-channel-concepts/CHANNEL.md`

## Source Of Truth

Use the app's local API through `scripts/openclaw-release`. Do not infer current state from Python settings imports, stale logs, browser pages, or memory.

Required first commands:

```bash
cd /opt/ai-music-playlist-generator
export AIMP_LOCAL_API_BASE=http://127.0.0.1:8000/api
git pull origin main
scripts/openclaw-release list-releases
curl -sS "$AIMP_LOCAL_API_BASE/youtube/status"
```

Treat `list-releases` as the app's known YouTube upload catalog. It contains release titles, channel titles, YouTube ids, durations, and recent update times. If the human says there are relevant YouTube uploads outside this app, report that limitation before claiming a concept is non-duplicated.

## Rotation Rules

1. Inspect recent Playlist Releases from `scripts/openclaw-release list-releases`.
2. Prefer rotating active channels instead of using the same channel repeatedly.
3. Choose the active channel with the oldest recent published playlist unless the human explicitly asks for a channel.
4. Do not pick the same channel twice in a row unless another channel is blocked, not connected, unavailable, or explicitly requested.
5. Confirm the selected YouTube channel is connected in `/youtube/status` before running publish automation.
6. When future channels are added, rotate across all active channels while respecting each channel's concept planner and profile.

## Channel Concept Delegation

After selecting a channel, run `scripts/openclaw-release channel-profile` with the selected channel title. Read both returned docs:

- `concept_doc`: choose the next playlist concept and avoid recent repetition.
- `profile_doc`: generate cover, thumbnail, and 10 second loop video without mixing channel visual signatures.

Example:

```bash
scripts/openclaw-release channel-profile \
  --release-title "NEXT_RELEASE_IDEA" \
  --description "NEXT_RELEASE_CONCEPT" \
  --youtube-channel-title "Tokyo Daydream Radio"
```

The active channel concept docs are:

- `docs/openclaw-channel-concepts/tokyo-daydream-radio.md`
- `docs/openclaw-channel-concepts/soft-hour-radio.md`
- `docs/openclaw-channel-concepts/sundaze.md`
- `docs/openclaw-channel-concepts/solwave-radio.md`

## Freshness Rules

Before finalizing a concept:

1. Filter recent releases by the selected `youtube_channel_title`.
2. Inspect at least the latest 5 releases on that channel when available.
3. Inspect the latest 15-20 releases globally for cross-channel repetition.
4. Extract recent setting, use case, subgenre, lyric premise, thumbnail phrase, visual scene, and title pattern.
5. Follow the selected channel's `concept_doc`.
6. Keep the channel identity stable while varying the specific concept.
7. Prefer concepts that are clear from title and thumbnail within a few seconds.
8. Prefer search/click-friendly phrases, but do not stuff keywords or make titles feel machine-generated.

Do not choose a concept if it only changes adjectives while repeating the same channel, use case, setting, visual scene, and music direction as a recent upload.

## Output Plan

Return this compact plan before generating audio:

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

For every Playlist Release plan, the main YouTube title and all localized titles must start exactly with `[playlist]`. Do not use this prefix for Single Releases. After `[playlist]`, avoid duplicate playlist nouns such as `플레이리스트`, `Playlist`, `プレイリスト`, or `lista de reproducción`.

After the plan, immediately continue into [openclaw-skills.md](openclaw-skills.md) Skill 3: `Automatic Private Playlist Publisher`, using the selected channel and concept.

## Skill Prompt

```text
You are the Next Release Planner for the AI Music app.

Work in /opt/ai-music-playlist-generator on the Oracle VM.
Use scripts/openclaw-release only.

First, update the repo and inspect app state:
git pull origin main
export AIMP_LOCAL_API_BASE=http://127.0.0.1:8000/api
scripts/openclaw-release list-releases
curl -sS "$AIMP_LOCAL_API_BASE/youtube/status"

Choose the next one-hour Playlist Release using docs/openclaw-next-release-planner.md:
- Rotate active channels instead of repeating the same channel.
- Current active channels are Tokyo Daydream Radio, Soft Hour Radio, sundaze, and Solwave Radio.
- Treat scripts/openclaw-release list-releases as the app's known YouTube upload catalog.
- Select the channel, then run scripts/openclaw-release channel-profile with that channel.
- Read the returned concept_doc to choose a fresh concept.
- Read the returned profile_doc before making cover, thumbnail, and loop video assets.
- Pick a concept not used recently while keeping the selected channel identity clear.

After choosing the channel and concept, run the Automatic Private Playlist Publisher skill from docs/openclaw-skills.md.
Create enough audio for at least 3600 seconds, generate final cover, separate YouTube thumbnail, a 10 second loop video, metadata, and publish privately to the selected YouTube channel. Do not skip the loop video unless the human explicitly approves a still-image fallback.

When done, report:
- selected_channel
- concept_doc
- profile_doc
- release.id
- release.title
- youtube_video_id
- privacy: private
- recent_releases_checked
- why_this_is_fresh
```
