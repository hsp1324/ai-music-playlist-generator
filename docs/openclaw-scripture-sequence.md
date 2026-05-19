# OpenClaw Scripture Sequence

Use this document for scripture music that is uploaded to `The Old Verse`.

`The Old Verse` is now the combined Bible music channel. It contains both Old Testament and New Testament releases. `The New Verse` YouTube channel is now reserved for Buddhist scripture-inspired music and must not receive Bible/New Testament uploads.

The web app is the source of truth for scripture sequence state. OpenClaw must not use a local ledger or local app-catalog comparison to decide whether a passage is valid. OpenClaw asks the deployed web app for the next passage, uses exactly what the app returns, and reports completion/failure back to the app.

## Source Of Truth

The deployed VM app stores the runtime ledger in:

```text
storage/openclaw-scripture-sequence.json
```

OpenClaw should inspect it only through the app API helper:

```bash
scripts/openclaw-release openclaw-scripture-status
```

Do not run `scripts/openclaw-scripture-sequence status/start/complete` during normal automation. That legacy local helper is for manual emergency inspection only and can diverge from the deployed VM if OpenClaw runs on another machine.

## Required Workflow

Before creating Suno audio for scripture music:

1. Create the app release first with `--youtube-channel-title "The Old Verse"`.
2. Decide the scripture branch:
   - Old Testament branch: reserve with `--channel-title "The Old Verse"`.
   - New Testament branch: reserve with `--channel-title "New Testament"`. The YouTube upload channel is still `The Old Verse`.
3. Reserve the next passage from the web app:

```bash
scripts/openclaw-release openclaw-scripture-reserve \
  --channel-title "The Old Verse" \
  --release-id "$RELEASE_ID" \
  --title "$RELEASE_TITLE"
```

For a New Testament release, use:

```bash
scripts/openclaw-release openclaw-scripture-reserve \
  --channel-title "New Testament" \
  --release-id "$RELEASE_ID" \
  --title "$RELEASE_TITLE"
```

Use `entry.passage_range` from the JSON response as the selected passage. Also keep `entry.next_start_after_completion` for reporting/debugging. Do not invent a different passage and do not compare the app response against a local ledger.

When publishing either branch, always publish to `The Old Verse`:

```bash
scripts/openclaw-release publish-release \
  --release-id "$RELEASE_ID" \
  --youtube-channel-title "The Old Verse"
```

After the release is successfully uploaded or scheduled on YouTube, mark the same branch you reserved as complete:

```bash
scripts/openclaw-release openclaw-scripture-complete \
  --channel-title "The Old Verse" \
  --passage-range "$PASSAGE_RANGE" \
  --release-id "$RELEASE_ID" \
  --youtube-video-id "$YOUTUBE_VIDEO_ID" \
  --title "$YOUTUBE_TITLE" \
  --status scheduled
```

If generation fails before a YouTube upload is created:

```bash
scripts/openclaw-release openclaw-scripture-fail \
  --channel-title "$SCRIPTURE_BRANCH_CHANNEL_TITLE" \
  --passage-range "$PASSAGE_RANGE" \
  --release-id "$RELEASE_ID" \
  --title "$RELEASE_TITLE" \
  --reason "Gemini/Dreamina could not create the loop video"
```

## Canonical Branches

- Old Testament branch: app key/title `The Old Verse`, sequence starts with `Genesis 1:1-5`, then continues from `Genesis 1:6`.
- New Testament branch: app key/title `New Testament`, sequence starts with `Matthew 1:1-17`, then continues from `Matthew 1:18`. The legacy `The New Verse` alias may still resolve for old automation clients, but new OpenClaw runs should use `New Testament`.

The app owns the configured passage blocks. If the app says the next block is missing, stop and report that the web app needs the next scripture block configured. Do not jump to famous passages, Psalms, John, Romans, Revelation, or any other out-of-order book unless the human explicitly asks and the app is updated accordingly.

## YouTube Channel, Playlists, And Schedule

- Both Old Testament and New Testament scripture releases upload to `The Old Verse`.
- The app creates/uses English YouTube playlists on `The Old Verse`:
  - `Old Testament Songs`
  - `New Testament Songs`
- After upload, each scripture video is also added to one style playlist when the release lane is clear, for example `Scripture Jazz Songs`, `Scripture R&B Songs`, `Gospel Worship Songs`, `Acoustic Scripture Songs`, `Piano Worship Songs`, `Cinematic Worship Songs`, or `Modern Worship Pop Songs`.
- A video can belong to two playlists: one testament playlist plus one style playlist.
- Scheduled public upload times in `AIMP_YOUTUBE_SCHEDULE_TIMEZONE`:
  - Old Testament branch: 07:00
  - New Testament branch: 16:00
- Because both branches share one YouTube channel, the app treats these as separate daily slots. One Old Testament and one New Testament release can be scheduled on the same calendar day.

## Duplicate Rules

- The web app rejects a passage already marked `in_progress`, `scheduled`, or `published` for another release.
- Retrying the same reserve command with the same `release_id` is idempotent.
- Title wording can change after metadata cleanup. OpenClaw must not block only because a previous title differs from the current app/YouTube title.
- If a release was manually deleted from YouTube, keep the app ledger entry and report the situation rather than silently reusing the passage.

## Title And Metadata

The main title and every localized title must include the passage range that the app reserved, because viewers should know exactly which Bible section inspired the music. The title must also say whether the release is Old Testament or New Testament.

Good title shapes:

- `[playlist] Genesis 1:6-13 Creation Songs | Old Testament Music for Worship`
- `[playlist] Matthew 1:18-25 Emmanuel Worship | New Testament Music for Prayer`

The description must also include:

- `Passage: Genesis 1:6-13` or `Passage: Matthew 1:18-25`.
- A short original explanation of the passage mood and message.
- A natural style sentence, such as `This release is arranged as modern worship pop with warm piano, acoustic guitar, and congregational choruses.`
- No long copied Bible text from modern copyrighted translations.

## Planning Output

When the next-release planner selects either scripture channel, the plan must include:

- `scripture_source`: `web_app`
- `scripture_branch`: `old_testament` or `new_testament`
- `scripture_channel`: the internal sequence key, `The Old Verse` for Old Testament or `New Testament` for New Testament
- `youtube_channel_title`: `The Old Verse`
- `selected_passage_range`
- `scripture_next_start_after_completion`
- `why_this_passage_is_next`
- `release_level_music_lane`

If those fields are missing, the plan is incomplete.
