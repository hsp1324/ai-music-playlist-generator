# Project Status

Last updated: 2026-05-01

## Goal

This project is now aimed at a web-first AI music release workflow:

1. Import finished audio tracks manually
2. Route tracks into a chosen workspace
3. Review tracks in the web UI
4. Build either:
   - a playlist workspace
   - a single-track video workspace
5. Approve publish
6. Generate cover art, render video, and upload to YouTube automatically when configured

The original Suno API automation idea is intentionally not the current core path. Manual intake is the primary workflow.

## Current Working Flow

### 1. Manual intake

- Tracks can be added from the web UI
- Quick Upload supports:
  - drag and drop
  - file picker
  - assigning uploads directly into a workspace review queue
- Uploaded files are stored with the original filename when possible
- Duplicate filenames are deduplicated with suffixes like `-2`, `-3`

### 2. Workspace review

- The main UI is workspace-first
- The release list uses `Active` and `Archive` tabs so archived releases no longer fill the homepage
- The top of the active tab shows workspace cards
- Clicking `More` opens the selected workspace detail board
- Failed releases show a delete action that moves them into Archive first
- Archived releases record `archived_at` and `purge_after`; they are permanently deleted after 7 days unless restored
- Each workspace detail board has:
  - `Awaiting Approval`
  - `Approved`

### 3. Track state transitions

- `Awaiting Approval` tracks can be:
  - approved
  - put on hold
  - rejected
- `Approved` tracks can now be:
  - played inline in the app
  - moved back to review with `Hold`
- `Hold` from the approved section sends the track back to the same workspace's `awaiting approval`

### 4. Workspace modes

Two modes exist:

- `playlist`
  - collect approved tracks until target duration
  - then request publish approval
- `single_track_video`
  - one approved track becomes one YouTube single
  - two Suno candidates can be reviewed together, but if both are good they are published as separate Single Releases
  - can auto-publish when ready

### 5. Publish pipeline

Background worker handles long-running jobs:

- playlist audio render
- local draft cover generation
- looped video render
- YouTube upload

Long video render jobs now expose ffmpeg progress through the workspace API:

- percent complete
- rendered media time vs total duration
- ETA when ffmpeg speed is available
- output file size heartbeat

The stall guard is progress-based, not a hard wall-clock timeout. It only fails a render if ffmpeg stops reporting progress and the output file stops growing for `AIMP_FFMPEG_STALL_TIMEOUT_SECONDS`.

For `single_track_video`, the intended publish path is:

1. approve one selected track into the workspace
2. use its uploaded source audio directly
3. generate cover
4. optionally generate a short Dreamina clip
5. loop the clip to match the audio
6. upload to YouTube with generated title/description/tags

## External Integrations

### YouTube

- OAuth-based upload is implemented
- Needs `AIMP_YOUTUBE_CLIENT_SECRETS_PATH`
- Uses a web OAuth callback at `/api/youtube/oauth/callback`, which fits the deployed VM better than a local desktop-browser OAuth flow
- Needs one-time `Connect YouTube` action from the web UI
- Multiple channels under the same Google account are supported by connecting each channel through OAuth
- The web UI stores connected YouTube channels and lets the operator choose the active upload channel before publish/re-upload
- Publish/re-upload shows a `Publish Channel` dropdown directly in the release action area
- Published releases still show the final track list and inline audio players, but review/reorder controls are locked
- YouTube OAuth now requests both upload and readonly scopes so the app can identify the selected channel after OAuth
- YouTube uploads are API-only through the app's YouTube Data API flow (`videos.insert` plus thumbnail/localization calls). OpenClaw must not upload directly in YouTube Studio; Studio is only for human review, visibility changes, and manual cleanup after the private API upload.
- Caption tracks are not uploaded or managed by the app. Vocal releases infer and send `snippet.defaultAudioLanguage` when the title/description/tags clearly identify J-pop/K-pop/pop language; BGM/instrumental/no-vocal releases omit it so YouTube is not told to expect speech.
- Cafe/solo-piano playlist metadata now generates a Korean YouTube title, use-case description, timestamped tracklist, and music hashtags
- Approved metadata can be regenerated from the release action area, which creates a new draft that must be approved before re-upload
- OpenClaw can write and approve YouTube metadata through `scripts/openclaw-release approve-metadata`, passing title, multiline description, and comma-separated tags
- YouTube metadata can now store `ko`, `ja`, `en`, and `es` localized title/description drafts. Tokyo/J-pop releases should provide all four; the publish flow sends Korean as the default metadata and Japanese/English/Spanish as YouTube localizations.
- Playlist Release YouTube titles now start with `[playlist]` for the default title and every localized title across all channels. Redundant playlist words like `플레이리스트` / `Playlist` are removed from the title body. Single Release titles remain unprefixed.
- Playlist/BGM YouTube titles should include listening use cases directly in the title, such as study, work, walk, drive, sleep, reading, or rest, instead of only mood/genre wording.
- Korean YouTube metadata must not use the transliterated words `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`; use `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡` instead.
- OpenClaw can get exact final-order timestamps through `scripts/openclaw-release metadata-context` and should use `display_timestamp_lines` in YouTube descriptions when available, so awkward `A` / `B` suffixes are not shown while timestamps stay fixed
- When `AIMP_CODEX_METADATA_ENABLED=true`, the web `Generate Metadata` / `Regenerate Metadata Draft` actions ask the VM's local Codex CLI to write the YouTube title, description, and tags. The app limits this to one Codex run at a time and falls back to the template generator on CLI failure, timeout, or invalid JSON.
- OpenClaw playlist automation can now run `scripts/openclaw-release auto-publish-playlist` to upload generated playlist tracks as approved, skip Slack per-track review spam, render audio/video, approve generated metadata, and upload privately to the selected connected YouTube channel. OpenClaw can also run `scripts/openclaw-release auto-publish-single` for a human-approved end-to-end private single upload. General BGM releases default to `Soft Hour Radio`; mainstream J-pop/Japanese pop/Tokyo pop releases route to `Tokyo Daydream Radio`.
- OpenClaw auto-publish helpers now refuse to re-upload an already published release unless `--allow-reupload` is explicitly passed, preventing accidental duplicate YouTube uploads.
- OpenClaw should create or select the target app release before opening Suno. Use `scripts/openclaw-release create-release` for fresh Single/Playlist Release work, keep the returned `release.id`, and upload later Suno outputs with `--release-id`.
- `scripts/openclaw-release upload-audio` also auto-approves tracks when the target release is a Playlist Release. Use `--pending-review` only when one-by-one playlist review is explicitly desired.
- OpenClaw should provide standalone playlist track titles, not Suno pair labels. The helper also rewrites trailing A/B, 1/2, and older `Morning` / `Evening` style variants into natural standalone display titles.
- BGM/background/lofi/study/sleep/cafe production defaults to instrumental music. For Soft Hour Radio or other no-vocal Suno work, OpenClaw must follow `docs/suno-v55-instrumental-format.md`: enable Instrumental when available, use bracket-only metatag lines in Suno's lyrics/custom-lyrics field, and upload that exact file with `--lyrics-file`. J-pop/K-pop/pop/Japanese pop/anime-pop production defaults to vocal songs with lyrics. OpenClaw should not generate instrumental/no-vocal pop-family tracks unless explicitly asked, and should upload lyrics for every pop-family track with `--lyrics` or `--lyrics-file`.
- Soft Hour Radio/no-vocal Suno work should also fill Suno Advanced Options excluded styles with vocal-related terms such as vocals, voice, singing, humming, choir, spoken word, narration, rap, ad-libs, scat, vocal chops, and lyrics.
- Playlist automation now keeps individual songs to 4 minutes or shorter by default. `scripts/openclaw-release auto-publish-playlist` rejects tracks over 240 seconds unless OpenClaw passes `--allow-long-track` after explicit human approval.
- OpenClaw helper commands now reject pop-family uploads with empty lyrics before publish unless the concept explicitly says BGM/instrumental/no-vocal. YouTube metadata approval also appends a visible public hashtag line when OpenClaw/Codex provides API tags but forgets description hashtags.
- OpenClaw generation guidance now requires track-level variation inside a release: distinct prompts, titles, lyrics concepts, chorus hooks, and preferably per-track Suno style/settings, while keeping the overall channel/release mood coherent.
- Playlist workspaces no longer auto-queue audio render just because the target duration is reached. The operator or OpenClaw must explicitly start render after all intended tracks have finished uploading.
- Audio/video rendering now snapshots the ordered track ids used for the render. If OpenClaw or the UI adds tracks while audio/video render is running, the stale render is rejected and a fresh render is queued or required before publish, preventing YouTube timelines from outlasting the actual video.
- `scripts/openclaw-release auto-publish-playlist` now requires a final uploaded 16:9 cover image before YouTube upload. The app's generated draft cover is only allowed with the explicit `--allow-generated-draft-cover` escape hatch.
- Full OpenClaw playlist publishing now expects two final 16:9 images: a video cover via `--cover` and a text-based YouTube thumbnail via `--thumbnail`. Reusing the cover as the thumbnail is only allowed with `--allow-cover-as-thumbnail`.
- Visual asset rules are channel-specific and documented in `docs/openclaw-channel-profiles/`. OpenClaw should choose the channel first, read only the returned profile, and apply human visual requests consistently to cover, thumbnail, and loop video. The YouTube thumbnail should be generated from the final cover as a reference/edit derivative so characters, positions, outfit colors, lighting, palette, and background stay continuous. All generated visuals should stay animated/anime/illustrated/stylized, not photorealistic or live-action.
- Every channel now requires a consistent large, readable lower-left channel-name brand label on the video cover/first-frame and inside the Dreamina/Seedance loop video. The cover/first-frame should contain only that channel name. Thumbnails should use large click text plus a channel-name brand line whose size/style stays consistent with the cover label. Target roughly 18-24% of image width, or about 5-6% of image height for text cap height.
- OpenClaw channel visual rules are also split into `docs/openclaw-channel-profiles/`. OpenClaw can run `scripts/openclaw-release channel-profile` to infer the target channel and get the exact profile doc to read before making visual assets.
- OpenClaw should generate static cover/thumbnail images with OpenAI GPT Image models, preferably `gpt-image-2` when available, not Dreamina. Dreamina is reserved for the moving visual clip.
- `Tokyo Daydream Radio` thumbnails should use the approved consistent channel layout: large `J-POP` and smaller `TOKYO DAYDREAM RADIO` beneath it, using the same full-bleed system for Tokyo/city, forest/nature, and beach variants. Do not add `1 HOUR`, `60 MIN`, `1時間`, or duration badges. The main default/requested subject must stay centered; text should fit around it without pushing it sideways.
- OpenClaw can also pass an 8 second Dreamina/Seedance MP4 via `--loop-video`. Browser automation should use Dreamina/Seedance `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, and exactly `8 seconds` through UI controls. The first-frame image should be the cover or a separate first-frame image with only the large, readable lower-left channel label, not the YouTube text thumbnail, because large generated title text can flicker or disappear. The generated clip should end close to its opening composition so it can be reused across the full release.
- Dreamina/Seedance prompts must preserve the exact lower-left channel text for the full clip, and OpenClaw should reject/regenerate clips where the label flickers, morphs, disappears, moves drastically, changes spelling/style, or becomes unreadable.
- Long video rendering now encodes the reusable short visual unit once, then extends that unit with ffmpeg concat stream-copy for the final video instead of re-encoding every frame of a one-hour release.
- The web release detail UI now supports direct upload/replace actions for video cover, text YouTube thumbnail, and 8 second loop video as separate assets.
- After a successful YouTube upload, the app deletes the long rendered local MP4 and keeps the YouTube video id/link as the watch surface. Re-uploading requires rendering a new local video first.
- Workspace API responses now include `youtube_channel_id` and `youtube_channel_title` next to `youtube_video_id`, so the dashboard and OpenClaw can confirm which channel a published release was uploaded to.
- The app can send a "make the next playlist" Slack request to the OpenClaw channel after a release is published. Configure `AIMP_OPENCLAW_SLACK_CHANNEL_ID`; the web UI shows `Request Next Playlist` on published releases, and `AIMP_OPENCLAW_AUTO_REQUEST_NEXT_ON_PUBLISH=true` sends the request automatically after successful YouTube upload with per-video dedupe. Real app-originated OpenClaw task messages are prefixed with `AIMP_OPENCLAW_SLACK_TRIGGER_PREFIX` (default `OPENCLAW_RUN:`). Slack event routing and mention-only behavior belongs in the Slack App/OpenClaw listener configuration, not in the music release skill docs.
- OpenClaw's continuous automation entry point is `docs/openclaw-next-release-planner.md`. After a publish, the app asks OpenClaw to run that planner first. The planner rotates active channels, avoids recent concept repetition, chooses the next channel/concept, then runs the automatic private playlist publisher.
- Track uploads now accept optional lyrics/content notes and Suno style/settings. Both are stored in track metadata and exposed through release/timeline context for later thumbnail, loop-video, metadata, remake, and standalone single workflows.
- Track intake now probes uploaded local audio duration with ffprobe and rejects empty audio uploads. Playlist audio render also validates every source file before concat and fails if the rendered output is materially shorter than the source tracks, preventing 0-byte or corrupt uploads from being published as short YouTube videos.
- OpenClaw helper audio uploads retry each file up to 3 times. Playlist automation continues uploading later tracks after a failed file, posts a Slack warning with the failed titles/files, and stops before render/publish until the failed sources are re-uploaded.
- YouTube metadata timelines now use `HH:MM:SS` for one-hour-plus releases, starting at `00:00:00`, so timestamps after one hour remain linkable. Japan/J-pop localized descriptions should use Japanese track titles plus Korean translations in the Korean/default version, Japanese titles in the Japanese version, English titles in the English version, and Spanish titles in the Spanish version.
- YouTube uploads set `status.containsSyntheticMedia` from `AIMP_YOUTUBE_CONTAINS_SYNTHETIC_MEDIA`; the default is `false`, so private publish/re-upload declares that the video does not contain realistic altered or synthetic media. Set it to `true` only for realistic AI/altered content that needs disclosure. Uploads also always set `status.selfDeclaredMadeForKids=false`, so YouTube receives "No, it's not made for kids" on every publish/re-upload.

### Cover art

- Manual cover upload is the preferred operator path when final art already exists
- `Generate Draft Cover` creates a simple local PNG placeholder with Pillow
- The app does not currently call Codex/OpenAI image generation for covers; OpenClaw should create final static art externally with OpenAI GPT Image models and upload the files.
- A generated draft can be replaced from the web UI with `Upload Cover`

### Dreamina

- Implemented through `useapi.net` integration
- Used only for single-track video mode
- Needs Dreamina/useapi credentials in `.env`

### Suno

- Browser session status and helper endpoints exist
- Full generation automation is not the main completed path
- Current operational assumption is manual audio intake

## Current UI Shape

The current UI intentionally follows this structure:

1. Header
2. Toolbar
3. Quick Upload section
4. Workspace card grid
5. Workspace detail board below

The user specifically preferred:

- workspace cards at the top
- upload section above the workspace cards
- detail board below the cards
- approved tracks playable inline
- approved tracks movable back to awaiting approval

## Current Local Demo Data

The local DB was intentionally cleaned up to leave only:

- `butter-fly`
- `summer`

These are demo workspaces used to validate the review UI.

At the time of writing, the intended state is:

- each workspace has some approved tracks
- each workspace has some awaiting-approval tracks

This was done to make the UI easier to test without old clutter.

## What Is Done

- web-first workspace dashboard
- quick upload with drag-and-drop
- manual audio intake
- original-filename file storage with dedupe suffix
- workspace-specific review queue
- approved track inline playback
- approved track `Hold` back to awaiting approval
- playlist workspace mode
- single-track video workspace mode
- background worker for render/publish jobs
- YouTube upload integration
- Dreamina loop-video integration
- generated YouTube metadata for single-track releases

## What Is Not Done Yet

### 1. Real Suno generation automation

The project does not yet fully automate song generation from Suno in the same way the rest of the release pipeline is automated.

### 2. Production-grade worker separation

The worker is DB-backed, but currently runs with the app process rather than as a fully separate production worker service.

### 3. Real MCP client transport

The MCP-compatible review abstraction exists, but the real MCP transport/client integration is still not complete.

### 4. UI polish

The current UI is functionally aligned with the user's preferred structure, but it is still a practical internal dashboard rather than a polished final product.

### 5. Google login protection in front of the public app

The intended production direction is now documented as:

- domain
- HTTPS
- `oauth2-proxy`
- Nginx `auth_request`

This is prepared in repo deployment templates, but not yet applied on the live VM.

## Recommended Next Steps

If continuing work from another session, the most useful next tasks are:

1. Run one full real-world publish from the UI
   - upload track
   - approve into workspace
   - publish
   - verify YouTube result
2. Finish UI polish
   - cleaner spacing
   - stronger visual hierarchy
   - better workspace card summaries
3. Improve failure recovery
   - retry publish jobs
   - retry Dreamina jobs
   - retry YouTube uploads
4. Separate the background worker into its own process for production use
5. Put Google login in front of the public app
6. Decide whether Suno automation is still needed, or whether manual intake is the permanent operating model

## Important Files

- `README.md`
- `docs/google-login-protection.md`
- `docs/openclaw-youtube-metadata.md`
- `app/static/index.html`
- `app/static/app.js`
- `app/static/styles.css`
- `app/routes/tracks.py`
- `app/routes/playlists.py`
- `app/workflows/playlist_automation.py`
- `app/services/background_worker.py`
- `app/services/dreamina_service.py`
- `app/services/release_metadata_service.py`
- `app/services/youtube_service.py`
- `tests/test_playlist_automation.py`

## Test Status

Most recent verified state during this session:

- `.venv/bin/python -m pytest -q`
- result: `56 passed`
