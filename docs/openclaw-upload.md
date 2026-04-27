# OpenClaw Upload Workflow

Use this when OpenClaw has generated an audio file and needs to hand it to the AI Music web app.

Run these commands on the Oracle VM from the repo root:

```bash
cd /opt/ai-music-playlist-generator
```

Do not use the public `https://ai-music...sslip.io` URL from OpenClaw. Public traffic is protected by Google login. Use the local API through the helper script instead.

## Upload A New Single

Use this for one generated song that should become its own single release.

```bash
scripts/openclaw-release upload-audio \
  --new-single \
  --audio /absolute/path/to/song.mp3 \
  --title "Song Title" \
  --prompt "Short generation prompt or notes" \
  --tags "ai music, single"
```

The command returns JSON with:

- `release.id`
- `release.title`
- `track.id`
- next action

After this, the track appears in the web/Slack review queue. A human should approve it before render.

## Upload To Existing Release

First list release ids:

```bash
scripts/openclaw-release list-releases
```

Then upload audio to a chosen release:

```bash
scripts/openclaw-release upload-audio \
  --release-id RELEASE_ID \
  --audio /absolute/path/to/song.mp3 \
  --title "Song Title" \
  --prompt "Short generation prompt or notes" \
  --tags "playlist candidate"
```

Use existing playlist releases for multiple songs. Use a single release only for one approved song.

## Upload Cover Image

Only do this after the release has rendered audio. The web UI should show `Rendered Mix` first.

```bash
scripts/openclaw-release upload-cover \
  --release-id RELEASE_ID \
  --cover /absolute/path/to/cover.png
```

Supported cover formats:

- `jpg`
- `jpeg`
- `png`
- `webp`

Preferred cover size is 16:9, for example `1280x720` or `1920x1080`.

After upload, the release moves to `cover_review`. A human should approve the cover in the web UI, then render video.

## Suggested OpenClaw Instruction

Give OpenClaw this instruction when it finishes a song:

```text
When the final audio file is ready, upload it to the local AI Music app from /opt/ai-music-playlist-generator.
For a one-song release, run:

scripts/openclaw-release upload-audio --new-single --audio ABSOLUTE_AUDIO_PATH --title "TITLE" --prompt "PROMPT" --tags "TAGS"

Return the JSON result, especially release.id and track.id.
Do not approve, render, or publish unless explicitly asked.
If a 16:9 cover image is also ready and the release already has rendered audio, run:

scripts/openclaw-release upload-cover --release-id RELEASE_ID --cover ABSOLUTE_COVER_PATH
```

## Safety Rules

- Do not call `Approve Publish` automatically.
- Do not upload to YouTube automatically.
- Prefer creating a new single only when exactly one final song is ready.
- If multiple songs are ready for one release, use `list-releases` and upload them to an existing playlist release.
