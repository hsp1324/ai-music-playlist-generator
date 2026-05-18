# OpenClaw Scripture Sequence Ledger

Use this document for `The Old Verse` and `The New Verse`. These channels must remember which Bible passage has already been turned into music, then continue from the next canonical passage without repeats.

## State File

The persistent ledger is:

```text
storage/openclaw-scripture-sequence.json
```

This file is intentionally runtime state and is ignored by git. Do not delete it. If OpenClaw runs in a separate checkout, keep the ledger in that persistent OpenClaw checkout, or set `AIMP_SCRIPTURE_SEQUENCE_PATH` to a durable shared path.

Initialize or inspect it:

```bash
scripts/openclaw-scripture-sequence status --init
```

## Required Workflow

Before creating any Suno audio, cover, thumbnail, loop video, metadata, or YouTube upload for `The Old Verse` or `The New Verse`:

1. Run `scripts/openclaw-release list-releases`.
2. Run `scripts/openclaw-scripture-sequence status --init`.
3. Compare the app catalog and the ledger.
4. Choose the next passage range after the ledger's `last_completed` / `next_start`.
5. Confirm that the same passage range is not already `in_progress`, `scheduled`, or `published`.
6. Mark the chosen passage as `in_progress` before opening Suno.

Example:

```bash
scripts/openclaw-scripture-sequence start \
  --channel "The Old Verse" \
  --passage "Genesis 1:1-5" \
  --release-id "$RELEASE_ID" \
  --title "[playlist] Genesis 1:1-5 Creation Songs | Old Testament Music for Worship"
```

After the release is successfully uploaded or scheduled on YouTube, update the same ledger entry:

```bash
scripts/openclaw-scripture-sequence complete \
  --channel "The Old Verse" \
  --passage "Genesis 1:1-5" \
  --release-id "$RELEASE_ID" \
  --youtube-video-id "$YOUTUBE_VIDEO_ID" \
  --title "[playlist] Genesis 1:1-5 Creation Songs | Old Testament Music for Worship" \
  --next-start "Genesis 1:6" \
  --status scheduled
```

If generation fails before a YouTube upload is created, mark the passage failed so the same passage can be retried later:

```bash
scripts/openclaw-scripture-sequence fail \
  --channel "The New Verse" \
  --passage "Matthew 1:1-17" \
  --release-id "$RELEASE_ID" \
  --reason "Dreamina blocked the first-frame image"
```

## Canonical Starts

- `The Old Verse`: if there is no prior history, start with `Genesis 1:1-5`.
- `The New Verse`: if there is no prior history, start with `Matthew 1:1-17`.

After that, continue in canonical order. Do not jump to famous passages, Psalms, John, Romans, Revelation, or any other out-of-order book unless the human explicitly asks.

## Duplicate Rules

- Never repeat a passage already marked `in_progress`, `scheduled`, or `published`.
- If `list-releases` and the ledger disagree, stop and report the mismatch instead of guessing.
- Title wording may change after metadata cleanup. If the passage range, release id, and YouTube video id match the app catalog, do not block only because the ledger title text differs from the current app/YouTube title. Continue from `next_start`; update the ledger title later if needed.
- A `failed` passage may be retried, but only if no YouTube video was published or scheduled for that passage.
- If a release was manually deleted from YouTube, keep the ledger entry and add a note rather than silently reusing the passage.

## Title And Metadata

The main title and every localized title for `The Old Verse` / `The New Verse` must include the passage range that was adapted, because viewers should know exactly which Bible section inspired the music.

Good title shapes:

- `[playlist] Genesis 1:1-5 Creation Songs | Old Testament Music for Worship`
- `[playlist] Matthew 1:1-17 Gospel Songs | New Testament Worship Music for Prayer`

The description must also include:

- `Passage: Genesis 1:1-5` or `Passage: Matthew 1:1-17`.
- A short original explanation of the passage mood and message.
- No long copied Bible text from modern copyrighted translations.

## Planning Output

When the next-release planner selects either scripture channel, the plan must include:

- `scripture_ledger_path`
- `scripture_last_completed`
- `scripture_next_start`
- `selected_passage_range`
- `why_this_passage_is_next`

If those fields are missing, the plan is incomplete.
