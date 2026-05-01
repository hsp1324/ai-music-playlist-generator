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
- When uploading audio, include lyrics or song-content notes with `--lyrics` or `--lyrics-file` whenever available. Empty lyrics are acceptable for instrumentals or unknown lyrics, but do not discard lyrics when Suno/OpenClaw has them.
- Always return the final JSON result and mention `release.id` plus uploaded `track.id` values.
- If a command fails, stop and report the exact error. Do not retry blindly more than once.
- For YouTube title/description/tag writing, use [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).
- For playlist publishing, choose the YouTube channel by release concept:
- Default background/cafe/sleep/study/chill playlists go to `Soft Hour Radio`.
- Japan-related releases go to `Tokyo Daydream Radio`. Treat these as Japan-related when the title, prompt, tags, or concept includes Japan, Tokyo, Shibuya, Shinjuku, Japanese lofi, city pop, J-pop, anime, vaporwave, 일본, 도쿄, 시티팝, 애니, 제이팝, 日本, 東京, 渋谷, 新宿, アニメ, or シティポップ.
- Do not use `MusicSun` unless the human explicitly requests it.
- `scripts/openclaw-release auto-publish-playlist` can infer the channel when `--youtube-channel-title` is omitted, but OpenClaw should pass `--youtube-channel-title "Tokyo Daydream Radio"` when the Japan routing intent is clear.
- YouTube visibility must stay private. The app uses `AIMP_YOUTUBE_PRIVACY_STATUS=private`; do not make a public upload from OpenClaw.
- Do not leave trailing `A` / `B`, `1` / `2`, `Morning` / `Evening`, or similar pair labels in uploaded playlist track titles.
- Treat every playlist track as its own song title. If Suno returns two outputs from one prompt, rename both as independent editorial titles, not as variants of the same title.
- Full playlist publishing needs two 16:9 images:
- `cover`: clean video visual shown during playback. It should look good for the full video duration and should have no or minimal text.
- `thumbnail`: YouTube click thumbnail. It should include short readable text such as `CAFE PIANO`, `DEEP SLEEP`, `FOCUS MUSIC`, `TOKYO NIGHT`, `CITY POP`, `1 HOUR`, plus a small brand mark for the selected channel.
- If Dreamina/Seedance can create a visual motion clip, OpenClaw should generate exactly one 8 second MP4 and pass it with `--loop-video`. The app will repeat it smoothly during final video render. OpenClaw should not render a one-hour video itself.
- Keep these assets separate: `--thumbnail` is the click image with text, `--cover` is the clean fallback visual, and `--loop-video` is the 8 second moving visual used inside the rendered video. Do not use the text thumbnail as the video visual.
- The 8 second loop video must visually match the thumbnail. Use the final thumbnail image as the first frame, image-to-video reference, or starting-scene reference in Dreamina/Seedance, then animate from that scene. This keeps the clicked thumbnail and the video's opening shot consistent.
- For browser-based Dreamina generation, OpenClaw should use `https://dreamina.capcut.com/ai-tool/home/`. Create/download the 8 second MP4 there, save it locally, then pass the downloaded file path as `--loop-video`.

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
- If candidate lyrics exist, upload them with the audio candidates using `--lyrics` or `--lyrics-file`. If a candidate is instrumental, leave lyrics empty.
- Clean awkward trailing A/B or 1/2 labels from uploaded candidate titles. If titles become duplicated, make them naturally unique without using pair labels.
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
  --lyrics-file ABSOLUTE_LYRICS_PATH_A \
  --lyrics-file ABSOLUTE_LYRICS_PATH_B \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags"

For one candidate:
scripts/openclaw-release upload-single-candidates \
  --release-title "RELEASE_TITLE" \
  --audio ABSOLUTE_AUDIO_PATH \
  --cover ABSOLUTE_COVER_PATH \
  --lyrics-file ABSOLUTE_LYRICS_PATH \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags"

If no cover image is ready, omit every `--cover` argument. If one shared cover should be used for both candidates, provide one `--cover`; if each candidate has a different cover, provide one `--cover` per `--audio` in the same order. If lyrics are not available, omit `--lyrics`/`--lyrics-file`; the app stores an empty lyrics field.

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

Create one Playlist Release, generate enough tracks, upload them as approved tracks, render audio/video, generate and approve metadata, and upload the result privately to YouTube on the correct channel.

Use `Soft Hour Radio` for normal background/cafe/sleep/study/chill releases. Use `Tokyo Daydream Radio` for Japan, Tokyo, city pop, J-pop, anime, Japanese lofi, or similar Japan-themed releases.

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
- Before upload, replace awkward trailing A/B, 1/2, or pair-style labels with independent song titles.
- Preserve each track's lyrics or content notes during upload. Pass one `--lyrics` or `--lyrics-file` per `--audio` when available, because good playlist tracks may later be republished as standalone singles and OpenClaw needs this context for thumbnail/loop-video generation.
- If Suno gives two outputs from the same prompt, do not name them like `Title A`, `Title B`, `Title 1`, `Title 2`, `Title - Morning`, or `Title - Evening`.
- Give each output a standalone title that fits the mood, for example `Saffron Motion` and `Open Road Cadence` instead of `Highway Saffron A` and `Highway Saffron B`.
- Upload all usable tracks to one Playlist Release.
- Upload tracks as auto-approved, not pending human review.
- If using `scripts/openclaw-release upload-audio` for individual playlist tracks, do not pass `--pending-review`; playlist uploads auto-approve by default.
- A final 16:9 cover image is required before YouTube upload.
- A separate YouTube thumbnail image with readable text is required before YouTube upload.
- Generate or obtain the final cover image before running the full publish command, then pass it with `--cover`.
- Generate or obtain a separate text thumbnail before running the full publish command, then pass it with `--thumbnail`.
- Optionally generate an 8 second Dreamina/Seedance 2.0 motion clip before running the full publish command, then pass it with `--loop-video`.
- The thumbnail, cover, and loop video are three different assets. The thumbnail must contain readable click text; the cover should stay clean, and the loop video should not add extra text, subtitles, lyrics, logos, or UI elements beyond the thumbnail reference used for its first frame.
- Use the approved/final thumbnail as the visual starting reference for Dreamina/Seedance image-to-video generation. The first shot of the 8 second loop video should look like the thumbnail, but the loop video itself should not add extra text, subtitles, lyrics, logos, or UI elements beyond what is already baked into the thumbnail reference.
- For loop clips, prompt Dreamina/Seedance for `exactly 8 seconds`, `seamless loop`, `slow camera motion`, `start and end frames match`, `no extra text overlays`, `no subtitles`, and `no hard cuts`.
- If using browser automation instead of an API, open `https://dreamina.capcut.com/ai-tool/home/`, create the video with Dreamina/Seedance, download the MP4, confirm the local file exists, and use that absolute path for `--loop-video`.
- If Dreamina login, CAPTCHA, payment, or human approval blocks browser automation, stop and report the exact blocked step instead of skipping the loop video.
- Do not let the app's local draft cover stand in for final cover art.
- Render playlist audio.
- Approve the cover.
- Render video.
- Generate and approve YouTube metadata.
- Publish privately to the selected YouTube channel. Use `Tokyo Daydream Radio` for Japan-related releases; otherwise use `Soft Hour Radio`.
- Return the command output JSON, including release.id, uploaded track ids, YouTube video id, and output paths.
```

### Slack Command Example

If the human gives this instruction through Slack, interpret it as approval to run the full private playlist automation:

```text
카페 피아노 1시간 플레이리스트 만들어서 Soft Hour Radio에 private으로 업로드까지 해줘.
Suno가 두 곡씩 주면 둘 다 playlist 트랙으로 쓰고, 트랙별 A/B 표시는 제목에서 빼줘.
마지막 private 업로드가 끝나면 YouTube video id만 알려줘.
```

Japan routing example:

```text
도쿄 시티팝 1시간 플레이리스트 만들어서 Tokyo Daydream Radio에 private으로 업로드까지 해줘.
Suno가 두 곡씩 주면 둘 다 playlist 트랙으로 쓰고, 트랙별 A/B 표시는 제목에서 빼줘.
썸네일에는 TOKYO NIGHT나 CITY POP처럼 짧게 읽히는 텍스트를 넣어줘.
```

### Run The Full Automation

After all generated audio files are ready, run one command:

```bash
scripts/openclaw-release auto-publish-playlist \
  --release-title "PLAYLIST_TITLE" \
  --description "Short mood/use-case description for metadata generation." \
  --audio ABSOLUTE_AUDIO_PATH_01 \
  --title "INDEPENDENT_TRACK_TITLE_01" \
  --lyrics-file ABSOLUTE_LYRICS_PATH_01 \
  --audio ABSOLUTE_AUDIO_PATH_02 \
  --title "INDEPENDENT_TRACK_TITLE_02" \
  --lyrics-file ABSOLUTE_LYRICS_PATH_02 \
  --audio ABSOLUTE_AUDIO_PATH_03 \
  --title "INDEPENDENT_TRACK_TITLE_03" \
  --lyrics-file ABSOLUTE_LYRICS_PATH_03 \
  --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH \
  --thumbnail ABSOLUTE_YOUTUBE_THUMBNAIL_IMAGE_PATH \
  --loop-video ABSOLUTE_DREAMINA_SEEDANCE_LOOP_MP4 \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags" \
  --youtube-channel-title "SELECTED_CHANNEL_TITLE"
```

Do not omit `--cover` or `--thumbnail` for a full private publish run. If either asset is not ready, stop after audio upload/render and report the missing asset. The app's local draft cover is only a placeholder for manual review, not acceptable for automatic YouTube upload.

`--loop-video` is optional but preferred when the human wants moving visuals. If it is omitted, the app renders a still-image visual from `--cover`. If it is provided, the app trims/pads the source to 8 seconds, creates a smooth crossfade ping-pong loop, and repeats it to match the full audio duration. The loop transition should dissolve/fade between motion directions instead of hard-cutting.

If the release is Japan-related, set `--youtube-channel-title "Tokyo Daydream Radio"`. Otherwise set `--youtube-channel-title "Soft Hour Radio"` or omit the flag and let the helper infer the default.

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
youtube_channel: SELECTED_CHANNEL_TITLE
privacy: private
Next: human should listen to the private YouTube upload and change visibility to Public only if it is good.
```

### Safety Checks

- Keep all generated tracks for the same playlist in one Playlist Release.
- Do not create a Single Release for playlist candidates.
- Do not use the `MusicSun` channel for playlist publishing unless the human explicitly overrides the channel.
- Do not upload public. The final upload must be private.
- Do not publish if the selected YouTube channel is not connected. Current intended routing is `Soft Hour Radio` for general releases and `Tokyo Daydream Radio` for Japan-related releases.
- Do not publish if final cover art was not uploaded. `auto-publish-playlist` requires `--cover` unless a final uploaded cover already exists on the release.
- Do not publish if final YouTube thumbnail art was not uploaded. `auto-publish-playlist` requires `--thumbnail` unless a final uploaded thumbnail already exists on the release.
- Do not use `--allow-generated-draft-cover` unless the human explicitly says a placeholder cover is acceptable for this upload.
- Do not use `--allow-cover-as-thumbnail` unless the human explicitly says one image is acceptable for both the video visual and YouTube thumbnail.
- Do not create a long one-hour MP4 in OpenClaw. Upload only the 8 second loop clip with `--loop-video`; the app handles the long render.
- Do not add new text, subtitles, lyric overlays, logos, or UI elements inside the loop video. Text should come only from the thumbnail reference used as the opening frame.
- Do not keep A/B, 1/2, or artificial pair suffixes in uploaded track titles.
- Do not use titles that read like numbered alternatives. Playlist tracks should look like a real album/playlist tracklist.
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
