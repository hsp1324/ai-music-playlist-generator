# OpenClaw Upload Workflow

Use this when OpenClaw has generated an audio file and needs to hand it to the AI Music web app.

For higher-level OpenClaw skill instructions, including "make one single", "build a one-hour playlist", and "write YouTube metadata", see [openclaw-skills.md](openclaw-skills.md).
For the metadata-specific command and prompt, see [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).

Run these commands on the Oracle VM from the repo root:

```bash
cd /opt/ai-music-playlist-generator
```

Do not use the public `https://ai-music...sslip.io` URL from OpenClaw. Public traffic is protected by Google login. Use the local API through the helper script instead.

## Upload A New Single Candidate Set

Use this when Suno/OpenClaw produced one or two candidates for the same single release. Suno usually returns two songs; upload both to the same new Single Release so a human can choose one or approve both.

```bash
scripts/openclaw-release upload-single-candidates \
  --release-title "Song Title" \
  --audio /absolute/path/to/song-a.mp3 \
  --audio /absolute/path/to/song-b.mp3 \
  --cover /absolute/path/to/cover-a.png \
  --cover /absolute/path/to/cover-b.png \
  --lyrics-file /absolute/path/to/song-a-lyrics.txt \
  --lyrics-file /absolute/path/to/song-b-lyrics.txt \
  --prompt "Short generation prompt or notes" \
  --tags "ai music, single"
```

The command returns JSON with:

- `release.id`
- `release.title`
- `tracks[].id`
- next action

After this, both candidates appear in the web/Slack review queue. A human can approve one candidate, or approve both candidates to combine them into one single-style release audio. If both candidates are rejected, the Single Release is automatically archived instead of deleted. It can be restored from the web UI archive.

Cover behavior:

- `--cover` is optional.
- Use one `--cover` to share the same cover across all uploaded candidates.
- Use one `--cover` per `--audio` to upload candidate-specific covers.
- When a Single Release candidate is approved, its uploaded cover is automatically registered as the release cover. If both candidates are approved, the first available uploaded cover is used as the release cover. The human only needs to review/approve the cover before rendering video.

Lyrics/content behavior:

- `--lyrics` or `--lyrics-file` is optional, but OpenClaw should provide it whenever Suno generated lyrics or meaningful song content.
- If the track is instrumental or lyrics are unknown, omit the flag or pass an empty value.
- Lyrics are stored with the track so future thumbnail, Dreamina loop-video, metadata, or standalone single publishing work has song-content context.

## Upload One New Single Candidate

Use this for one generated song that should become its own single release candidate.

```bash
scripts/openclaw-release upload-audio \
  --new-single \
  --audio /absolute/path/to/song.mp3 \
  --cover /absolute/path/to/cover.png \
  --title "Song Title" \
  --lyrics-file /absolute/path/to/song-lyrics.txt \
  --prompt "Short generation prompt or notes" \
  --tags "ai music, single"
```

The command returns JSON with:

- `release.id`
- `release.title`
- `track.id`
- next action

After this, the track appears in the web/Slack review queue. A human should approve it before render.
If `--cover` is provided and this is a Single Release, approving the track automatically registers that image as the release cover.

## Upload One Playlist Track

When `scripts/openclaw-release upload-audio` targets an existing Playlist Release, the helper now uploads the track and immediately approves it into the playlist. It also skips the per-track Slack review message so a one-hour playlist does not spam Slack.

Playlist track titles should look like final tracklist titles, not Suno alternatives. Do not upload names like `Title A`, `Title B`, `Title 1`, `Title 2`, `Title - Morning`, or `Title - Evening`. Give every playlist item a standalone title that fits the mood.

```bash
scripts/openclaw-release upload-audio \
  --release-id RELEASE_ID \
  --audio /absolute/path/to/playlist-track.mp3 \
  --title "Track Title" \
  --lyrics-file /absolute/path/to/playlist-track-lyrics.txt \
  --prompt "Short generation prompt or notes" \
  --tags "ai music, playlist"
```

The JSON result should include:

- `auto_approved: true`
- `track.status: approved`

Only use `--pending-review` if the human explicitly asks to review playlist tracks one by one.

If OpenClaw uploads many playlist files in one automation run, prefer `auto-publish-playlist` with one `--title` per `--audio` so the final YouTube tracklist already has natural titles.
Also pass one `--lyrics` or `--lyrics-file` per `--audio` when lyrics are available. For instrumental tracks, empty lyrics are acceptable.

For full automatic playlist publishing, two final 16:9 images are required.

- `--cover /absolute/path/to/video-cover.png`: clean playback visual used inside the rendered video. Use little or no text because viewers will see it for the full video.
- `--thumbnail /absolute/path/to/youtube-thumbnail.png`: YouTube click thumbnail. Include short readable text and a small brand mark for the selected channel.

Do not rely on the app's generated draft cover for YouTube upload. Do not reuse the cover as the thumbnail unless the human explicitly approves one image for both roles. The thumbnail is for clicks and should have text; the cover is the clean still-image fallback for video rendering and should not have text.

Static image creation rules:

- Do not use Dreamina for static cover or YouTube thumbnail images.
- Use OpenAI GPT Image models for static image generation. Prefer `gpt-image-2` when available; otherwise use the currently available GPT Image model in the running OpenAI/Image tool environment. Do not assume OpenAI API usage is free; use the available image tool or configured API credentials.
- If `gpt-image-2` is unavailable in the actual tool/API environment, fall back to the best available GPT Image model instead of using Dreamina for static images.
- Produce 16:9 images, preferably `1280x720` or `1920x1080`.
- Create the text thumbnail first, then use that final thumbnail image as the first-frame reference for Dreamina/Seedance video generation.

Optional moving visual:

- `--loop-video /absolute/path/to/dreamina-loop.mp4`: exactly 8 second Dreamina/Seedance visual clip. The app repeats it during video render.
- OpenClaw should generate/download only the short clip. Do not export a one-hour MP4 from OpenClaw.
- The app uses smooth 2 second forward crossfade looping by default. It trims/pads the source to 8 seconds, then fades the end of each forward pass into the beginning of the next forward pass so the join feels like a dissolve instead of a sudden jump.
- Use `--hard-loop-video` only if the clip is already a perfect seamless loop and direct repeat is preferred.
- If the human expects a moving final video, `--loop-video` must be a separate MP4 asset. Do not use the thumbnail image or text cover as the moving video visual.

Dreamina website workflow for OpenClaw:

- Use `https://dreamina.capcut.com/ai-tool/home/` for browser-based Dreamina/Seedance generation.
- Use Dreamina/Seedance `2.0 Fast`.
- Do not use Omni Reference.
- Use the first/last-frame workflow if the UI asks which mode to use, but provide only the first-frame image.
- Start from the final YouTube thumbnail image. Use it as the first frame or starting scene so the video's opening shot matches the clicked thumbnail.
- Leave the last-frame input empty. Do not upload a last-frame reference; it makes the generated motion too static.
- Set ratio to `16:9` when selectable.
- Set quality to `720p` when selectable.
- Generate exactly one `8 second` MP4.
- Download the generated MP4 to the VM or OpenClaw workspace.
- Confirm the file exists locally before passing it to `--loop-video`.
- If login, CAPTCHA, subscription limits, or manual approval blocks generation/download, stop and report the blocked step. Do not continue without `--loop-video` unless the human explicitly accepts a still-image video.

Dreamina/Seedance loop prompt guidance:

- Ask for a seamless ambient visual loop.
- Ask for exactly 8 seconds. Do not request 5, 10, or 15 seconds.
- Ask Dreamina/Seedance to preserve the thumbnail's composition, lighting, palette, and main subject in the first shot.
- Use slow camera movement, stable composition, no hard cuts, no extra text overlays, no subtitles, no logos, and no people unless specifically requested.
- Do not include `start and end frames match` or equivalent wording. The app handles smooth repeat with forward crossfade rendering, and forcing the last frame to match can make the clip too static.
- Prefer atmospheric scenes that match the channel mood: cafe window, moonlit room, soft rain, abstract light, slow landscape, piano/candle detail.
- If the model outputs audio, ignore it; the app uses the rendered playlist audio.

Thumbnail text rules for OpenClaw:

- Use 2-4 large words that describe the use case or mood, for example `CAFE PIANO`, `DEEP SLEEP`, `FOCUS MUSIC`, `RUNNING BEATS`.
- Prefer the approved full-bleed style: strong image background, no card or panel, large bottom-left genre/mood text, and a smaller channel-brand line directly below.
- For Japan-related releases routed to `Tokyo Daydream Radio`, use the channel name as the brand line. The approved J-pop pattern is large `J-POP` with `TOKYO DAYDREAM RADIO` beneath it.
- Add support text or a duration badge only when it improves readability without cluttering the full-bleed layout.
- Keep text large enough to read on a phone.
- Avoid long titles, dense paragraphs, fake UI, and obviously AI-looking distorted text.

Localized YouTube metadata rules for OpenClaw:

- The app can upload YouTube localized metadata for `ko`, `ja`, and `en`.
- For `Tokyo Daydream Radio`, Japan, Tokyo, city-pop, J-pop, anime, or Japanese lofi releases, always write all three language versions.
- Use Korean as the default upload metadata. Pass Korean through `--title` and `--description-file`, and also pass `--ko-title` and `--ko-description-file`.
- Pass Japanese through `--ja-title` and `--ja-description-file`. This should be natural Japanese copy, not a literal Korean line-by-line translation.
- Pass English through `--en-title` and `--en-description-file`. This should be natural English YouTube copy for international listeners.
- Keep all localized titles under 100 characters. Keep timestamps identical across languages; translate only the displayed title text and surrounding description.

Example localized metadata approval:

```bash
scripts/openclaw-release approve-metadata \
  --release-id RELEASE_ID \
  --title "기분 좋아지는 일본어 J-pop 1시간 | 산책, 드라이브, 작업할 때 듣는 플레이리스트" \
  --description-file /tmp/metadata-ko.txt \
  --tags "Jpop,JapanesePop,TokyoDaydreamRadio,Playlist,DriveMusic,WorkMusic" \
  --ko-title "기분 좋아지는 일본어 J-pop 1시간 | 산책, 드라이브, 작업할 때 듣는 플레이리스트" \
  --ko-description-file /tmp/metadata-ko.txt \
  --ja-title "気分が上がる日本語J-POP 1時間 | 散歩・ドライブ・作業用プレイリスト" \
  --ja-description-file /tmp/metadata-ja.txt \
  --en-title "Feel-Good Japanese J-Pop 1 Hour | Walk, Drive, Work Playlist" \
  --en-description-file /tmp/metadata-en.txt
```

## YouTube Channel Routing

For automatic playlist publishing, `scripts/openclaw-release auto-publish-playlist` chooses the YouTube channel from the release concept when `--youtube-channel-title` is omitted.

- Use `Soft Hour Radio` for default background/cafe/sleep/study/chill playlists.
- Use `Tokyo Daydream Radio` for Japan, Tokyo, Shibuya, Shinjuku, Japanese lofi, city pop, J-pop, anime, vaporwave, 일본, 도쿄, 시티팝, 애니, 제이팝, 日本, 東京, 渋谷, 新宿, アニメ, or シティポップ concepts.
- Pass `--youtube-channel-title "Tokyo Daydream Radio"` explicitly when the human asks for Japanese/Tokyo/city-pop/anime music.
- Do not use `MusicSun` unless the human explicitly requests it.

## Web Review Surface

After OpenClaw uploads audio, the web UI shows the selected release as a music-library style list:

- Clicking a release card opens a focused `?release=...` page instead of scrolling to a lower dashboard panel.
- `Awaiting Approval` contains uploaded candidates with cover art, duration, player controls, prompt notes, and approve/hold/reject actions.
- `Final Order` contains approved tracks in playlist order. Playlist releases can be reordered by drag/drop before audio rendering.
- Single Releases can end with one approved selected track, or two approved tracks that are combined into one single-style release audio. Playlist Releases may contain many approved tracks.
- The web UI defers automatic polling while any audio player is actively playing, so mobile playback is not interrupted by background refresh.
- Starting one web audio player pauses any other currently playing web audio player.

OpenClaw should only upload candidate files and report the returned JSON. It should not depend on the UI layout, approve tracks, reorder tracks, render audio/video, or publish unless the human explicitly asks.

## Slack Audio Preview Behavior

Slack review alerts are intended to show a playable audio preview directly in Slack:

- Local uploaded files are sent to Slack as audio files.
- Remote Suno/CDN audio URLs are downloaded by the app server and then sent to Slack as audio files.
- If Slack upload fails, the app falls back to a normal review message with an audio link so review is not blocked.

For the most reliable Slack preview, prefer passing a real local audio file path to `scripts/openclaw-release`. If OpenClaw only has a remote Suno URL, the app can still post a Slack-playable preview as long as the URL is publicly fetchable from the VM.

## Remote Audio Playback Rule

Mobile browsers can stop playback when they stream directly from temporary Suno/CDN URLs. To avoid that, the app now caches remote `audio_url`/`audio_path` values into local VM storage at intake time and serves playback from `/media/...`.

Operational rules for OpenClaw:

- Prefer uploading a local audio file path when possible.
- If only a remote Suno/CDN URL is available, submit it as `audio_url` or `audio_path`; the app will download it into local storage before creating the track.
- Do not leave release candidates pointing directly at `cdn1.suno.ai` unless the local cache step fails and the failure is reported to the human.
- Existing remote-only tracks should be backfilled to local storage before serious mobile review.

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
  --cover /absolute/path/to/cover.png \
  --title "Standalone Track Title" \
  --prompt "Short generation prompt or notes" \
  --tags "playlist candidate"
```

Use existing playlist releases for multi-song playlist releases. A Single Release may hold up to two review candidates, but only one can be approved and selected for the final single. Track-level covers are used automatically only for approved Single Release candidates; Playlist Release covers should still be chosen at the release level.

## Upload Cover Image

Only do this after release audio is ready. Playlist releases should show `Rendered Mix`; Single Releases use the approved source audio directly.

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

The web UI also has `Generate Draft Cover`, but that only creates a simple local placeholder PNG. It does not call Codex/OpenAI image generation. If OpenClaw creates better cover art elsewhere, upload that file with `upload-cover` or include it with the audio upload command.

## Suggested OpenClaw Instruction

Give OpenClaw this instruction when it finishes a song:

```text
When the final audio file is ready, upload it to the local AI Music app from /opt/ai-music-playlist-generator.
Before uploading Suno output, decide whether this belongs to a Single Release workspace or a Playlist Release workspace.
For a new single candidate set, create one Single Release by using --release-title with upload-single-candidates.
For an existing release, use --release-id and keep all related Suno outputs in that same workspace.
When Suno returns two candidate songs for one single release, run:

scripts/openclaw-release upload-single-candidates --release-title "TITLE" --audio ABSOLUTE_AUDIO_PATH_A --audio ABSOLUTE_AUDIO_PATH_B --cover ABSOLUTE_COVER_PATH_A --cover ABSOLUTE_COVER_PATH_B --prompt "PROMPT" --tags "TAGS"

Return the JSON result, especially release.id and tracks[].id.
Do not approve, render, or publish unless explicitly asked.
If only one candidate exists, run:

scripts/openclaw-release upload-audio --new-single --audio ABSOLUTE_AUDIO_PATH --cover ABSOLUTE_COVER_PATH --title "TITLE" --prompt "PROMPT" --tags "TAGS"

Return the JSON result, especially release.id and track.id.
Do not approve, render, or publish unless explicitly asked.
If a 16:9 cover image is also ready and the release already has rendered audio, run:

scripts/openclaw-release upload-cover --release-id RELEASE_ID --cover ABSOLUTE_COVER_PATH
```

If the human explicitly asks OpenClaw to publish one single all the way to YouTube, use the automatic single publisher instead:

```text
Create an original single release and publish it privately.
Generate or obtain:
- one or two Suno audio candidates
- a final clean 16:9 cover image
- a separate YouTube thumbnail image with readable text
- optionally one exactly 8 second Dreamina/Seedance loop video

Then run:

scripts/openclaw-release auto-publish-single \
  --release-title "SINGLE_TITLE" \
  --description "CONCEPT_FOR_METADATA" \
  --audio ABSOLUTE_AUDIO_PATH_01 \
  --title "INDEPENDENT_TRACK_TITLE_01" \
  --lyrics-file ABSOLUTE_LYRICS_PATH_01 \
  --cover ABSOLUTE_FINAL_CLEAN_COVER_IMAGE_PATH \
  --thumbnail ABSOLUTE_YOUTUBE_TEXT_THUMBNAIL_IMAGE_PATH \
  --loop-video ABSOLUTE_DREAMINA_SEEDANCE_8_SECOND_MP4 \
  --prompt "PROMPT" \
  --tags "TAGS" \
  --youtube-channel-title "Tokyo Daydream Radio"

For non-Japan releases, use "Soft Hour Radio" unless the human says otherwise.
For one audio candidate, pass one --audio/--title/--lyrics-file. For two candidates that should be combined, pass two.
```

## Safety Rules

- Do not call `Approve Publish` automatically unless the human explicitly asks for full private publishing.
- Do not upload to YouTube automatically unless using `auto-publish-single` or `auto-publish-playlist` after explicit human instruction.
- If cover art is ready with the audio, upload it in the same command with `--cover`; otherwise omit `--cover` and let the human add/regenerate cover later.
- If lyrics or meaningful song-content notes are available, upload them in the same command with `--lyrics` or `--lyrics-file`. Use an empty value for instrumentals or unknown lyrics.
- Treat generated draft covers in the web UI as replaceable placeholders, not final art.
- Use OpenAI GPT Image models for static cover and thumbnail images. Do not use Dreamina for static image generation.
- Do not use generated draft covers for full OpenClaw auto-publish runs. OpenClaw must create/upload a real final cover image first.
- Do not publish without a separate YouTube thumbnail image. OpenClaw must create/upload a text thumbnail and pass it as `--thumbnail`.
- If OpenClaw creates a Dreamina/Seedance loop clip, pass the 8 second MP4 as `--loop-video`. The app handles smooth crossfade repeat and long video rendering.
- Keep `--cover`, `--thumbnail`, and `--loop-video` separate. `--thumbnail` should have readable YouTube text; `--cover` and `--loop-video` should be clean visuals without text.
- Use Dreamina/Seedance `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, and exactly `8 seconds` for loop video generation.
- For Playlist Releases, `upload-audio` auto-approves by default. Do not add `--pending-review` unless the human explicitly asks.
- For Playlist Releases, do not use pair/number titles. Replace Suno A/B or 1/2 output labels with independent track names before upload.
- For Suno two-output generations, upload both candidates to one Single Release using `upload-single-candidates`.
- Single Release candidates are still human-reviewed; the human may approve one candidate, approve both candidates to combine them, or reject both.
- If both candidates are rejected, the app will archive the release automatically; do not delete files or database rows manually.
- If three or more songs are ready for one release, use a Playlist Release instead.
