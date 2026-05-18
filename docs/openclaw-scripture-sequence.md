# OpenClaw Scripture Sequence

Use this document for `The Old Verse` and `The New Verse`.

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

Before creating Suno audio for `The Old Verse` or `The New Verse`:

1. Create the app release first with the selected channel title.
2. Reserve the next passage from the web app:

```bash
scripts/openclaw-release openclaw-scripture-reserve \
  --channel-title "The Old Verse" \
  --release-id "$RELEASE_ID" \
  --title "$RELEASE_TITLE"
```

Use `entry.passage_range` from the JSON response as the selected passage. Also keep `entry.next_start_after_completion` for reporting/debugging. Do not invent a different passage and do not compare the app response against a local ledger.

After the release is successfully uploaded or scheduled on YouTube:

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
  --channel-title "The New Verse" \
  --passage-range "$PASSAGE_RANGE" \
  --release-id "$RELEASE_ID" \
  --title "$RELEASE_TITLE" \
  --reason "Gemini/Dreamina could not create the loop video"
```

## Canonical Starts

- `The Old Verse`: the app sequence starts with `Genesis 1:1-5`, then continues from `Genesis 1:6`.
- `The New Verse`: the app sequence starts with `Matthew 1:1-17`, then continues from `Matthew 1:18`.

The app owns the configured passage blocks. If the app says the next block is missing, stop and report that the web app needs the next scripture block configured. Do not jump to famous passages, Psalms, John, Romans, Revelation, or any other out-of-order book unless the human explicitly asks and the app is updated accordingly.

## Duplicate Rules

- The web app rejects a passage already marked `in_progress`, `scheduled`, or `published` for another release.
- Retrying the same reserve command with the same `release_id` is idempotent.
- Title wording can change after metadata cleanup. OpenClaw must not block only because a previous title differs from the current app/YouTube title.
- If a release was manually deleted from YouTube, keep the app ledger entry and report the situation rather than silently reusing the passage.

## Title And Metadata

The main title and every localized title for `The Old Verse` / `The New Verse` must include the passage range that the app reserved, because viewers should know exactly which Bible section inspired the music.

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
- `scripture_channel`
- `selected_passage_range`
- `scripture_next_start_after_completion`
- `why_this_passage_is_next`

If those fields are missing, the plan is incomplete.
