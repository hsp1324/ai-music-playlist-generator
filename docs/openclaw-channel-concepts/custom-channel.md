# OpenClaw Channel Concept Planner: Custom Channel

Use this when `scripts/openclaw-release channel-profile` returns `custom-channel`, or when `/youtube/status` shows a connected YouTube channel that does not yet have a dedicated concept planner.

## Goal

Infer the channel identity from the connected channel title, the human request, and the channel's existing uploads. Then choose a fresh one-hour playlist concept that fits that inferred identity without copying recent releases.

## Required Checks

1. Run `scripts/openclaw-release list-releases`.
2. Run `curl -sS "$AIMP_LOCAL_API_BASE/youtube/status"` and use the returned `channels` list as the active rotation roster.
3. Filter recent releases by the selected `youtube_channel_title`.
4. Inspect at least the latest 5 releases on that channel when available.
5. Inspect the latest 15-20 releases globally for repeated title, setting, visual scene, thumbnail text, genre, use case, and lyric premise.
6. If the selected channel has no local history, infer conservatively from the channel name and ask for a clear channel direction in the Slack report if the identity is ambiguous.

## Concept Rules

- Keep the channel identity stable. Do not borrow the fixed visual signature or genre rules from Tokyo Daydream Radio, Soft Hour Radio, HaruHaru, sundaze, or Solwave Radio unless the channel title or human instruction clearly matches that identity.
- Use one clear genre or listening lane per playlist.
- Choose a specific setting, use case, emotional direction, and thumbnail phrase.
- Avoid generic titles like `Pop Mix`, `New Playlist`, `BGM`, or `Music for You` unless the human explicitly wants that.
- If the channel appears to be language-specific, write lyrics and metadata in that language by default.
- If the channel appears to be instrumental/background-specific, avoid vocals unless the human explicitly requests them.

## Output

Return the standard next-release plan:

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

Then continue with `docs/openclaw-skills.md` Skill 3.
