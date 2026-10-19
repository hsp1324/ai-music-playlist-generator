# OpenClaw Scripture Sequence

Use this document for scripture music that is uploaded to `BibliaCanto`.

`BibliaCanto` is now the combined Bible music channel. It contains both Old Testament and New Testament releases. `불송` YouTube channel is now reserved for Buddhist scripture-inspired music and must not receive Bible/New Testament uploads.

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

1. Create the app release first with `--youtube-channel-title "BibliaCanto"`.
2. Decide the scripture branch:
   - Old Testament branch: reserve with `--channel-title "BibliaCanto"`.
   - New Testament branch: reserve with `--channel-title "New Testament"`. The YouTube upload channel is still `BibliaCanto`.
3. Reserve the next passage from the web app:

```bash
scripts/openclaw-release openclaw-scripture-reserve \
  --channel-title "BibliaCanto" \
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

When publishing either branch, always publish to `BibliaCanto`:

```bash
scripts/openclaw-release publish-release \
  --release-id "$RELEASE_ID" \
  --youtube-channel-title "BibliaCanto"
```

After the release is successfully uploaded or scheduled on YouTube, mark the same branch you reserved as complete:

```bash
scripts/openclaw-release openclaw-scripture-complete \
  --channel-title "BibliaCanto" \
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

- Old Testament branch: app key/title `BibliaCanto`, sequence starts with `Genesis 1:1-5`, then continues from `Genesis 1:6`.
- New Testament branch: app key/title `New Testament`, sequence starts with `Matthew 1:1-17`, then continues from `Matthew 1:18`. The legacy `불송` alias may still resolve for old automation clients, but new OpenClaw runs should use `New Testament`.

The app owns the configured passage blocks. If the app says the next block is missing (`next_block_missing` / HTTP 409), do not invent, skip, or reserve a later Matthew (or other Bible) passage. Do not start Suno, image, or video work for that BibliaCanto release. First diagnose the app sequence/configuration and, when the omission is deterministic, add only the immediate contiguous next block, run the focused sequence tests, deploy through the established app deployment path when available, re-check the deployed API, and resume the same release. If that repair cannot be completed and verified in this pass, archive the unstarted/asset-free workspace with `scripts/openclaw-release archive-release --release-id "$RELEASE_ID" --reason "next_block_missing: $CAUSE"`, exclude `BibliaCanto` from the rest of the current automation pass, and continue with the next eligible connected non-`BibliaCanto` channel. Preserve (do not archive) any workspace that already has real audio, cover, video, or a reserved passage; record its blocker and do not create a duplicate. This is a channel-specific deferral, not a reason to stop the whole OpenClaw run or leave the app lock blocked. Do not jump to famous passages, Psalms, John, Romans, Revelation, or any other out-of-order book unless the human explicitly asks and the app is updated accordingly.

## YouTube Channel, Playlists, And Schedule

- Both Old Testament and New Testament scripture releases upload to `BibliaCanto`.
- The app creates/uses English YouTube playlists on `BibliaCanto`:
  - `Old Testament Songs`
  - `New Testament Songs`
- After upload, each scripture video is also added to one style playlist when the release lane is clear, for example `Scripture Hip-Hop Songs`, `Scripture R&B Songs`, `Bible K-Pop Songs`, `Scripture Trap Songs`, `Bible Neo-Soul Songs`, `Bible Afropop Songs`, or `Scripture Synth-Pop Songs`.
- Do not use gospel/worship/church style playlists for new BibliaCanto releases. New Testament uploads must also be in `New Testament Songs`, and Old Testament uploads must also be in `Old Testament Songs`.
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

- `[playlist] Genesis 1:6-13 Creation Hip-Hop | Old Testament Rap & R&B Songs`
- `[playlist] Matthew 1:18-25 Emmanuel K-Pop R&B | New Testament Scripture Songs`

The description must also include:

- `Passage: Genesis 1:6-13` or `Passage: Matthew 1:18-25`.
- A short original explanation of the passage mood and message.
- A natural style sentence, such as `This release turns Matthew 1:18-25 into modern scripture R&B with sung hooks, tight drums, and K-pop-inspired pop energy.`
- No long copied Bible text from modern copyrighted translations.

## Planning Output

When the next-release planner selects either scripture channel, the plan must include:

- `scripture_source`: `web_app`
- `scripture_branch`: `old_testament` or `new_testament`
- `scripture_channel`: the internal sequence key, `BibliaCanto` for Old Testament or `New Testament` for New Testament
- `youtube_channel_title`: `BibliaCanto`
- `selected_passage_range`
- `scripture_next_start_after_completion`
- `why_this_passage_is_next`
- `release_level_music_lane`

If those fields are missing, the plan is incomplete.
