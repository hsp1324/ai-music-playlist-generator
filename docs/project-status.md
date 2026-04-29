# Project Status

Last updated: 2026-04-24

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
- The top of the page shows workspace cards
- Clicking `More` opens the selected workspace detail board
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
  - one approved track is enough
  - intended for one-song video publishing
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

1. approve track into workspace
2. render audio
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
- Cafe/solo-piano playlist metadata now generates a Korean YouTube title, use-case description, timestamped tracklist, and music hashtags
- Approved metadata can be regenerated from the release action area, which creates a new draft that must be approved before re-upload

### Cover art

- Manual cover upload is the preferred operator path when final art already exists
- `Generate Draft Cover` creates a simple local PNG placeholder with Pillow
- The app does not currently call Codex/OpenAI image generation for covers
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
