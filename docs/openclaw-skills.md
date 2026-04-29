# OpenClaw Skills For AI Music Releases

Use this document as the instruction source when asking OpenClaw to create or run release-production skills for this repo.

OpenClaw must run commands on the Oracle VM from:

```bash
cd /opt/ai-music-playlist-generator
```

Use the local API or the helper script. Do not use the public `https://ai-music...sslip.io` URL because it is protected by Google login.

```bash
export AIMP_LOCAL_API_BASE=http://127.0.0.1:8000/api
```

## Shared Rules

- Never approve, reject, render, publish, or upload to YouTube unless the human explicitly asks.
- OpenClaw creates audio candidates and uploads them to the app review queue.
- If cover art is ready with the audio, upload the cover in the same command with `--cover`.
- Human review happens in Slack or the web UI.
- Single Release means one final song, but it may contain up to two review candidates from Suno.
- Playlist Release normally means automatic private publishing. If the human asks for a playlist production run, upload generated tracks as already approved, render everything, generate/approve metadata, and upload privately to YouTube.
- Always return the final JSON result and mention `release.id` plus uploaded `track.id` values.
- If a command fails, stop and report the exact error. Do not retry blindly more than once.
- For YouTube title/description/tag writing, use [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).
- For playlist publishing, always use the connected YouTube channel `Soft Hour Radio`.
- YouTube visibility must stay private. The app uses `AIMP_YOUTUBE_PRIVACY_STATUS=private`; do not make a public upload from OpenClaw.
- Do not leave trailing `A` / `B` labels in uploaded playlist track titles. Clean names before upload, and make duplicate base titles unique with natural suffixes.

## Skill 1: Single Release Candidate Set

Use this skill when the user asks for one standalone song/single.

### Goal

Generate one Single Release candidate set. Suno normally returns two candidate songs for one prompt. Upload both candidates into the same Single Release so the human can listen and choose one or approve both. If both are approved, the app combines them into one single-style release audio and proceeds like a two-track mini playlist while metadata still treats it as one song. If both are bad, the human rejects both; the app archives that release automatically and it can be restored later.

### OpenClaw Skill Prompt

```text
You are creating one Single Release for the AI Music app.

Work in /opt/ai-music-playlist-generator on the Oracle VM.
Use the local app API only through scripts/openclaw-release.

Goal:
- Generate one standalone song/single.
- If Suno returns two candidates, upload both candidates to one new Single Release.
- If only one usable candidate exists, upload one candidate to one new Single Release.
- If candidate cover images exist, upload them with the audio candidates.
- Clean awkward trailing A/B labels from uploaded candidate titles. If titles become duplicated, make them naturally unique.
- When the human approves one candidate, its uploaded cover is automatically registered as the release cover. If the human approves both candidates, the two audio files are combined into one release audio.
- The human still reviews/approves the cover before video rendering.
- Do not approve, reject, render, publish, or upload to YouTube.
- Return release.id, release.title, and all uploaded track ids.

After audio generation, run one of these:

For two Suno candidates:
scripts/openclaw-release upload-single-candidates \
  --release-title "RELEASE_TITLE" \
  --audio ABSOLUTE_AUDIO_PATH_A \
  --audio ABSOLUTE_AUDIO_PATH_B \
  --cover ABSOLUTE_COVER_PATH_A \
  --cover ABSOLUTE_COVER_PATH_B \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags"

For one candidate:
scripts/openclaw-release upload-single-candidates \
  --release-title "RELEASE_TITLE" \
  --audio ABSOLUTE_AUDIO_PATH \
  --cover ABSOLUTE_COVER_PATH \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags"

If no cover image is ready, omit every `--cover` argument. If one shared cover should be used for both candidates, provide one `--cover`; if each candidate has a different cover, provide one `--cover` per `--audio` in the same order.

Report the command output JSON. The human will approve one candidate, approve both candidates, or reject both in Slack or the web UI.
```

### Required Output

OpenClaw should finish with a concise report:

```text
Single release candidates uploaded.
release.id: ...
release.title: ...
tracks:
- ...
- ...
Next: human should approve one candidate, approve both candidates to combine them, or reject both.
```

### Safety Checks

- Do not create two separate Single Releases for the two Suno outputs. Both candidates must be in one release.
- Do not upload more than two candidates to a Single Release.
- Do not upload cover images separately after this command if they were already uploaded with the candidate audio.
- A Single Release can contain at most two approved tracks. If it already has two selected/approved tracks, create a new Single Release instead of uploading more candidates to it.
- If both candidates are rejected later, the app archives the release automatically. Do not manually delete it.

## Skill 2: Automatic Private Playlist Publisher

Use this skill when the user asks for a playlist, mix, compilation, or approximately one-hour release and expects OpenClaw to finish the private YouTube upload.

### Goal

Create one Playlist Release, generate enough tracks, upload them as approved tracks, render audio/video, generate and approve metadata, and upload the result privately to YouTube on `Soft Hour Radio`.

The human does not review every playlist track before rendering. The human reviews the final private YouTube upload later and only intervenes if something sounds wrong.

### Important Duration Rule

Playlist uploads are auto-approved, so `workspace.actual_duration_seconds` becomes the source of truth after upload.

Generate enough material before publishing:

- Target at least `3600` seconds for a one-hour playlist.
- A practical buffer of `3900` seconds is acceptable.
- Do not publish under target unless the human explicitly says a shorter playlist is acceptable.

### OpenClaw Skill Prompt

```text
You are creating and privately publishing a one-hour Playlist Release for the AI Music app.

Work in /opt/ai-music-playlist-generator on the Oracle VM.
Use scripts/openclaw-release only.

Goal:
- Generate songs in batches until the usable duration is at least 3600 seconds, preferably around 3900 seconds.
- If Suno returns two outputs from one request, use both outputs as separate playlist tracks when both are usable.
- Before upload, remove awkward trailing A/B labels from track titles.
- If removing A/B creates duplicate titles, rename the displayed titles naturally so they are unique.
- Upload all usable tracks to one Playlist Release.
- Upload tracks as auto-approved, not pending human review.
- If using `scripts/openclaw-release upload-audio` for individual playlist tracks, do not pass `--pending-review`; playlist uploads auto-approve by default.
- If a final 16:9 cover image exists, pass it with --cover.
- If no final cover exists, let the app generate a local draft cover.
- Render playlist audio.
- Approve the cover.
- Render video.
- Generate and approve YouTube metadata.
- Publish privately to YouTube channel Soft Hour Radio.
- Return the command output JSON, including release.id, uploaded track ids, YouTube video id, and output paths.
```

### Slack Command Example

If the human gives this instruction through Slack, interpret it as approval to run the full private playlist automation:

```text
카페 피아노 1시간 플레이리스트 만들어서 Soft Hour Radio에 private으로 업로드까지 해줘.
Suno가 두 곡씩 주면 둘 다 playlist 트랙으로 쓰고, 트랙별 A/B 표시는 제목에서 빼줘.
마지막 private 업로드가 끝나면 YouTube video id만 알려줘.
```

### Run The Full Automation

After all generated audio files are ready, run one command:

```bash
scripts/openclaw-release auto-publish-playlist \
  --release-title "PLAYLIST_TITLE" \
  --description "Short mood/use-case description for metadata generation." \
  --audio ABSOLUTE_AUDIO_PATH_01 \
  --audio ABSOLUTE_AUDIO_PATH_02 \
  --audio ABSOLUTE_AUDIO_PATH_03 \
  --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags" \
  --youtube-channel-title "Soft Hour Radio"
```

If no final cover image exists, omit `--cover`; the app will create a local draft cover automatically.

If the run is continuing an existing release, use `--release-id RELEASE_ID` instead of creating a new title.

Only use `--force-under-target` if the human explicitly accepted a shorter playlist.

### Required Output

OpenClaw should finish with:

```text
Private playlist upload completed.
release.id: ...
release.title: ...
uploaded tracks:
- ...
- ...
youtube_video_id: ...
youtube_channel: Soft Hour Radio
privacy: private
Next: human should listen to the private YouTube upload and change visibility to Public only if it is good.
```

### Safety Checks

- Keep all generated tracks for the same playlist in one Playlist Release.
- Do not create a Single Release for playlist candidates.
- Do not use the `MusicSun` channel for playlist publishing unless the human explicitly overrides the channel.
- Do not upload public. The final upload must be private.
- Do not publish if YouTube channel `Soft Hour Radio` is not connected.
- Do not keep A/B in uploaded track titles.
- Do not create a Slack review message for every playlist track during automatic playlist publishing.
- If the automation times out while waiting for render/upload, report the exact stage and current release state. Do not start a duplicate publish blindly.

## Quick Selection Guide

Use `Single Release Candidate Set` when:

- The user asks for one song, one single, one YouTube single, or one standalone track.
- Suno returns two alternatives for the same prompt.
- The human needs to choose A or B.

Use `Automatic Private Playlist Publisher` when:

- The user asks for a playlist, mix, compilation, batch, or one-hour release.
- The goal is many tracks.
- The human expects OpenClaw to upload privately to YouTube and review only the final result.

Use `OpenClaw YouTube Metadata Skill` when:

- The release already has rendered video.
- The human asks OpenClaw to write YouTube title, description, and tags.
- The human wants OpenClaw to approve metadata but not publish.
- The human can alternatively use the web `Generate Metadata` / `Regenerate Metadata Draft` button, which may call the VM's local Codex CLI when enabled.
- OpenClaw must first run `scripts/openclaw-release metadata-context --release-id RELEASE_ID` and use `display_timestamp_lines` when available.
- Follow [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).
