# ai-music-playlist-generator

Web-first automation backend for an AI music playlist pipeline:

1. Generate Suno candidate tracks
2. Send review tasks to Slack
3. Approve or reject tracks
4. Build playlists from approved tracks
5. Extend to YouTube upload
6. Gradually replace human review with MCP-driven agents

This repository is intentionally structured so that:

- the web workspace is the current operating surface
- MCP-compatible agents can become the decision maker later
- The backend remains the source of truth for state and automation

## Current Scope

This scaffold provides:

- FastAPI application
- Built-in web workspace console at `/` and `/ui`
- Manual Suno candidate intake via JSON API or web file upload
- SQLite-backed data model
- Slack OAuth installation persistence
- Slack interaction endpoint
- App Home publishing
- Suno generation request intake
- Suno webhook ingestion
- Suno browser session status and re-login flow
- Track intake and decision APIs
- Multi-playlist web workspaces with per-playlist approval routing
- Single-track video release mode with automatic publish
- Playlist build planning
- `ffmpeg`-based audio concatenation for approved tracks
- Automatic playlist build when approved local tracks reach the target duration
- DB-backed background worker for playlist render and publish jobs
- Publish approval step with generated PNG cover art
- MCP-callable review engine interface with HTTP fallback to local rules

It does not yet provide:

- Real MCP transport/client integration

Those are left as pluggable services so the system can evolve without rewriting the core workflow.

## Architecture

The system is split into three layers.

### 1. Control Plane

The backend orchestrates state transitions:

- track created
- review requested
- decision applied
- playlist build requested
- playlist rendered
- uploaded

This state lives in the database, not in Slack and not in the agent.

### 2. Operator Surfaces

The web workspace is the primary operator UI, and Slack remains available for notifications and fallback review:

- import queue candidates
- route approved tracks into a chosen playlist workspace
- review playlist status and publish readiness
- optionally send or receive Slack review actions

### 3. MCP Decision Layer

Today:

- human reviews dominate
- agent review is optional

Later:

- agent reviews every track
- agent applies approval policy automatically
- agent decides when to build and upload playlists
- humans only handle exceptions

The code already separates `decision source` into `human`, `agent`, and `system` so the workflow can evolve without changing the schema.

## Project Layout

```text
app/
  main.py
  config.py
  db.py
  models/
  routes/
  schemas/
  services/
  workflows/
tests/
```

Key modules:

- `app/routes/slack.py`: Slack events and interactive actions
- `app/routes/suno.py`: generation request intake and completion webhooks
- `app/routes/tracks.py`: Track intake, review, and Slack message generation
- `app/routes/playlists.py`: Approved-track selection and playlist rendering
- `app/services/mcp_orchestrator.py`: MCP-ready review engine abstraction
- `app/services/slack_service.py`: Slack signature verification and Block Kit payloads
- `app/services/suno_service.py`: provider abstraction for generation submission and webhook normalization
- `app/services/playlist_builder.py`: `ffmpeg` audio build path
- `app/workflows/approvals.py`: authoritative decision application logic
- `app/workflows/review_dispatch.py`: automatic agent review plus Slack escalation

## Environment

Copy `.env.example` to `.env` and update values as needed.

Important variables:

- `AIMP_DATABASE_URL`
- `AIMP_PUBLIC_BASE_URL`
- `AIMP_SLACK_SIGNING_SECRET`
- `AIMP_SLACK_CLIENT_ID`
- `AIMP_SLACK_CLIENT_SECRET`
- `AIMP_SLACK_REDIRECT_URI`
- `AIMP_SLACK_BOT_TOKEN`
- `AIMP_SLACK_REVIEW_CHANNEL_ID`
- `AIMP_AUTO_APPROVAL_MODE`
- `AIMP_MCP_AGENT_NAME`
- `AIMP_MCP_REVIEW_URL`
- `AIMP_MCP_API_KEY`
- `AIMP_SUNO_PROVIDER_MODE`
- `AIMP_SUNO_API_BASE_URL`
- `AIMP_SUNO_API_KEY`
- `AIMP_SUNO_DEFAULT_MODEL`
- `AIMP_SUNO_WEBHOOK_SECRET`

## Local Run

Create an environment and install dependencies:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

If you want the Suno browser session helper:

```bash
uv pip install -e ".[browser]"
playwright install chromium
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Web UI:

```text
http://127.0.0.1:8000/
```

Project handoff/status:

```text
docs/project-status.md
```

Oracle Always Free deployment guide:

```text
docs/deploy-oracle-always-free.md
```

Google login protection guide:

```text
docs/google-login-protection.md
```

Oracle VM runtime status:

```text
docs/oracle-vm-status.md
```

## Suno Session Flow

The web UI now includes a Suno session banner.

- `GET /api/suno/session-status`
- `POST /api/suno/session/open-login`
- `POST /api/suno/session/notify-expired`

Recommended usage:

1. Keep `AIMP_SUNO_PROVIDER_MODE=http` for stable generation now.
2. Use the session panel when you want to maintain a local Suno browser profile for future provider work.
3. If the stored browser session becomes stale, send a Slack alert and re-login manually in the opened browser window.

Environment variables for this flow:

```bash
AIMP_SUNO_BROWSER_LOGIN_URL=https://suno.com/create
AIMP_SUNO_BROWSER_NAME=chromium
AIMP_SUNO_BROWSER_EXECUTABLE_PATH=
AIMP_SUNO_SESSION_STALE_HOURS=72
AIMP_AUTO_BUILD_PLAYLISTS=true
AIMP_AUTO_BUILD_RENDER_AUDIO=true
AIMP_AUTO_BUILD_TITLE_PREFIX=Auto Playlist
```

## Manual Suno Intake

If you are generating tracks manually in Suno, import them directly instead of calling the Suno API.

- Web console: upload an audio file or paste a remote audio URL at `/`
- JSON API: `POST /api/tracks`
- Multipart API: `POST /api/tracks/manual-upload`

Each imported track is automatically dispatched into the review workflow:

- `AUTO_APPROVAL_MODE=human`: Slack review request only
- `AUTO_APPROVAL_MODE=hybrid`: agent suggestion plus Slack review
- `AUTO_APPROVAL_MODE=agent`: agent decision only

When `AIMP_AUTO_BUILD_PLAYLISTS=true`, the backend automatically creates the next playlist once enough approved tracks are available. If `AIMP_AUTO_BUILD_RENDER_AUDIO=true`, it queues the MP3 render in the background worker.

## Web Workspace Flow

The main operating surface is now the web UI.

1. Import a Suno track into the queue
2. Create one or more playlist workspaces
3. Approve a queued track into a specific workspace
4. Keep collecting until the workspace reaches its target duration
5. Approve publishing from the workspace card
6. Upload a 16:9 cover manually, or generate a local draft cover and replace it later if needed
7. If YouTube is not connected yet, connect it and approve publishing again

You can also create a `single_track_video` workspace:

1. Create a workspace in `single_track_video` mode
2. Approve one track into that workspace
3. The background worker renders audio, optionally generates a Dreamina loop clip, and uploads automatically when ready

## Cover Art

After release audio is ready, the workspace can accept a manual cover upload at any time before the YouTube upload completes.

- `Upload Cover` stores a user-provided JPG, PNG, or WebP image and moves the release to cover review.
- OpenClaw full auto-publish runs require a final uploaded 16:9 video cover and a separate 16:9 YouTube thumbnail with readable text. They can also include an 8 second Dreamina/Seedance MP4 with `--loop-video`; the app repeats that clip during final video render with a smooth crossfade ping-pong loop. The local draft cover is a manual placeholder and is not used for automatic YouTube publishing unless explicitly allowed.
- `Generate Draft Cover` creates a simple local PNG with Pillow. This is a placeholder draft, not Codex/OpenAI image generation.
- If a generated draft is not good enough, press `Upload Cover` and replace it with the real cover file.
- For best YouTube output, use a 16:9 image such as `1280x720` or `1920x1080`.

## YouTube Automation

The app can now upload to YouTube automatically after you approve publishing from the workspace.

Required setup:

1. Create OAuth **Web application** credentials for YouTube Data API v3 in Google Cloud
2. Save the downloaded JSON somewhere on disk
3. Add this redirect URI to the OAuth client:
   `https://ai-music.168.107.34.175.sslip.io/api/youtube/oauth/callback`
4. Set `AIMP_YOUTUBE_CLIENT_SECRETS_PATH` in `.env`
5. Open the web UI and press `Connect YouTube` once
6. Finish the OAuth flow in your browser

Environment variables:

```bash
AIMP_YOUTUBE_CLIENT_SECRETS_PATH=/absolute/path/to/client_secrets.json
AIMP_YOUTUBE_OAUTH_REDIRECT_URI=https://ai-music.168.107.34.175.sslip.io/api/youtube/oauth/callback
AIMP_YOUTUBE_PRIVACY_STATUS=private
AIMP_YOUTUBE_CATEGORY_ID=10
AIMP_YOUTUBE_AUTO_UPLOAD_ON_PUBLISH=true
AIMP_CODEX_METADATA_ENABLED=false
AIMP_CODEX_METADATA_COMMAND=codex
AIMP_CODEX_METADATA_TIMEOUT_SECONDS=180
```

Runtime behavior:

- If the playlist has a rendered local audio file and YouTube is connected, publish approval will queue a background job that:
  - uses the approved cover image
  - renders an MP4 from cover + audio
  - uploads the video to YouTube
  - uploads the same cover as the custom thumbnail
- If YouTube is not connected yet, the playlist stays in a YouTube-ready state until you connect it.
- Long video renders report ffmpeg progress back to the web UI with percent, elapsed media time, ETA, and output file growth. The worker only fails a render as stalled when ffmpeg stops making progress and the output file stops growing for `AIMP_FFMPEG_STALL_TIMEOUT_SECONDS`.
- If `AIMP_CODEX_METADATA_ENABLED=true`, `Generate Metadata` / `Regenerate Metadata Draft` calls the VM's local Codex CLI to write the YouTube title, description, and tags. The app allows one Codex metadata run at a time and falls back to deterministic templates if Codex fails or times out.
- OpenClaw can run `scripts/openclaw-release auto-publish-playlist` to upload playlist tracks as approved, render audio/video, approve generated metadata, and publish privately to the selected connected YouTube channel. The helper defaults general background releases to `Soft Hour Radio` and routes Japan/Tokyo/city-pop/anime/J-pop concepts to `Tokyo Daydream Radio`.

For `single_track_video` workspaces, the app also auto-generates YouTube title, description, and tags from the track metadata and workspace description.
Single releases can approve one candidate directly, or approve two related candidates and combine them into one single-style release audio before cover/video/publish.

## Dreamina Loop Video

Dreamina integration is implemented for `useapi.net`'s Dreamina API layer. This is a third-party API wrapper around Dreamina, not an official public Dreamina developer API.

Required setup:

```bash
AIMP_DREAMINA_PROVIDER_MODE=useapi
AIMP_DREAMINA_API_TOKEN=...
AIMP_DREAMINA_ACCOUNT=US:your-dreamina-account@example.com
AIMP_DREAMINA_VIDEO_MODEL=seedance-1.5-pro
AIMP_DREAMINA_VIDEO_DURATION_SECONDS=8
```

When a `single_track_video` workspace is ready and auto-publish is enabled, the worker can:

- generate the cover PNG
- ask Dreamina for a short loop clip using the workspace or track prompt
- download the clip locally
- loop that clip to match the full song duration with `ffmpeg`
- upload the finished MP4 to YouTube with generated metadata

OpenClaw browser automation can also create a Dreamina/Seedance clip outside the API flow. Upload it with:

```bash
scripts/openclaw-release upload-loop-video --release-id RELEASE_ID --loop-video /absolute/path/to/clip.mp4
```

For full playlist automation, pass it directly:

```bash
scripts/openclaw-release auto-publish-playlist ... --loop-video /absolute/path/to/clip.mp4
```

The app repeats short clips with smooth crossfade ping-pong looping by default, so OpenClaw should upload only the 8 second source clip, not a one-hour rendered video. The renderer trims or pads the clip to 8 seconds, reverses it back toward the first frame, and fades across the direction change to avoid a hard jump.

## Slack App Setup

You need a Slack app before local review messages can be delivered.

### 1. Create the app

Create a Slack app in your workspace and enable:

- Interactivity
- Events API
- App Home

### 2. Configure redirect and request URLs

For local development, expose the server publicly with a tunnel such as `ngrok` or `cloudflared`.

Set:

- OAuth redirect URL:
  `https://YOUR_PUBLIC_URL/api/slack/oauth/callback`
- Event Request URL:
  `https://YOUR_PUBLIC_URL/api/slack/events`
- Interactivity Request URL:
  `https://YOUR_PUBLIC_URL/api/slack/interactions`

### 3. Add bot scopes

Recommended bot scopes for the current scaffold:

- `app_mentions:read`
- `channels:history`
- `channels:read`
- `chat:write`
- `commands`
- `im:history`
- `im:read`
- `im:write`
- `users:read`

### 4. Fill `.env`

Set at minimum:

```bash
AIMP_PUBLIC_BASE_URL=https://YOUR_PUBLIC_URL
AIMP_SLACK_CLIENT_ID=...
AIMP_SLACK_CLIENT_SECRET=...
AIMP_SLACK_SIGNING_SECRET=...
AIMP_SLACK_REDIRECT_URI=https://YOUR_PUBLIC_URL/api/slack/oauth/callback
AIMP_SLACK_REVIEW_CHANNEL_ID=C0123456789
AIMP_SLACK_ENABLE_SIGNATURE_VERIFICATION=true
```

If you want to skip OAuth during early testing, you can set `AIMP_SLACK_BOT_TOKEN` directly, but OAuth is the preferred path now that installation persistence exists.

### 5. Install the app

Open:

```text
https://YOUR_PUBLIC_URL/api/slack/install
```

After installation succeeds, the workspace bot token is persisted in the database.

## Example Workflow

### 1. Create a track candidate

```bash
curl -X POST http://127.0.0.1:8000/api/tracks \
  -H 'content-type: application/json' \
  -d '{
    "title": "Night Drive Candidate 01",
    "prompt": "synthwave, late night highway, warm pads, driving beat",
    "duration_seconds": 238,
    "audio_path": "storage/tracks/night-drive-01.mp3",
    "metadata": {
      "model_score": 0.91,
      "genre": "synthwave"
    }
  }'
```

### 2. Dispatch review

This route is future-facing:

- `human`: post to Slack
- `hybrid`: agent reviews first, then Slack if needed
- `agent`: agent decides automatically unless the track is held

```bash
curl -X POST http://127.0.0.1:8000/api/tracks/TRACK_ID/dispatch-review
```

### 3. Submit a Suno generation request

This now matches `docs.sunoapi.org` request fields. In `http` mode it calls `POST https://api.sunoapi.org/api/v1/generate`.

```bash
curl -X POST http://127.0.0.1:8000/api/suno/generations \
  -H 'content-type: application/json' \
  -d '{
    "title": "Night Drive Candidate 02",
    "prompt": "retro synthwave, cruising, melodic lead",
    "custom_mode": true,
    "instrumental": true,
    "model": "V5_5",
    "style": "synthwave, cinematic, neon highway",
    "metadata": {
      "playlist": "night-drive"
    }
  }'
```

### 4. Deliver a Suno completion webhook

This is the handoff point for full automation:

1. provider finishes generation
2. webhook creates the track
3. MCP review runs automatically when enabled
4. Slack escalation happens only when required by policy

```bash
curl -X POST http://127.0.0.1:8000/api/suno/webhook \
  -H 'content-type: application/json' \
  -d '{
    "code": 200,
    "msg": "All generated successfully.",
    "data": {
      "callbackType": "complete",
      "task_id": "5c79-example-task",
      "data": [
        {
          "id": "music-1",
          "audio_url": "https://cdn.example.com/music-1.mp3",
          "stream_audio_url": "https://cdn.example.com/music-1-stream",
          "image_url": "https://cdn.example.com/music-1.jpg",
          "prompt": "[Verse] Neon skyline",
          "model_name": "chirp-v3-5",
          "title": "Night Drive A",
          "tags": "synthwave, neon",
          "createTime": "2026-04-20 00:00:00",
          "duration": 201.2
        },
        {
          "id": "music-2",
          "audio_url": "https://cdn.example.com/music-2.mp3",
          "stream_audio_url": "https://cdn.example.com/music-2-stream",
          "image_url": "https://cdn.example.com/music-2.jpg",
          "prompt": "[Verse] Neon skyline",
          "model_name": "chirp-v3-5",
          "title": "Night Drive B",
          "tags": "synthwave, neon",
          "createTime": "2026-04-20 00:00:00",
          "duration": 198.6
        }
      ]
    }
  }'
```

The app only creates tracks on `callbackType=complete`. Earlier `text` and `first` callbacks are acknowledged and stored as job progress without creating duplicate tracks.

### 5. Publish App Home manually

If you want to test App Home without waiting for a Slack event:

```bash
curl -X POST http://127.0.0.1:8000/api/slack/app-home/publish/U0123456789
```

### 6. Apply a human decision

```bash
curl -X POST http://127.0.0.1:8000/api/tracks/TRACK_ID/decisions \
  -H 'content-type: application/json' \
  -d '{
    "decision": "approve",
    "source": "human",
    "actor": "hong",
    "rationale": "Strong hook and stable mix"
  }'
```

### 7. Build a playlist from approved tracks

```bash
curl -X POST http://127.0.0.1:8000/api/playlists/build \
  -H 'content-type: application/json' \
  -d '{
    "title": "Night Drive Vol. 1",
    "target_duration_seconds": 3600,
    "execute_render": false
  }'
```

Set `execute_render` to `true` once the referenced local audio files exist.

## First Real Slack Review Message

The shortest real end-to-end local test is:

1. Run the API behind a public tunnel
2. Install the Slack app through `/api/slack/install`
3. Create a track with `/api/tracks`
4. Call `/api/tracks/{id}/dispatch-review`
5. Confirm the message appears in `AIMP_SLACK_REVIEW_CHANNEL_ID`
6. Click `Approve` or `Reject`
7. Verify the track status changed through `/api/tracks/{id}`

## Suno Automation Modes

### `AIMP_SUNO_PROVIDER_MODE=manual_webhook`

Best for development. Your app accepts generation requests, stores jobs, and waits for a manual or external webhook call.

### `AIMP_SUNO_PROVIDER_MODE=http`

Best when you have a real `docs.sunoapi.org` API key. The app will submit generation requests to:

- `POST {AIMP_SUNO_API_BASE_URL}/api/v1/generate`

and tell the provider to callback into:

- `{AIMP_PUBLIC_BASE_URL}{AIMP_API_PREFIX}/suno/webhook`

The scaffold also exposes:

- `GET /api/suno/generations/{task_id}` -> `GET /api/v1/generate/record-info`
- `GET /api/suno/credits` -> `GET /api/v1/generate/credit`

Default model is `V5_5`, which matches the model list shown in the current docs.

## Slack Plan

Recommended rollout:

1. Phase 1
   Human approval in Slack messages
2. Phase 2
   Slack App Home summary dashboard
3. Phase 3
   Slack modals for regeneration and policy overrides
4. Phase 4
   Agent review suggestions posted back to Slack
5. Phase 5
   Full auto-approval and upload with human exception handling only

## MCP Evolution Path

The future automation path is:

1. `AUTO_APPROVAL_MODE=human`
   Human only
2. `AUTO_APPROVAL_MODE=hybrid`
   Agent suggests, human confirms
3. `AUTO_APPROVAL_MODE=agent`
   Agent decides by policy, human audits exceptions

To move from scaffold to real MCP automation, replace the stub engine in:

- `app/services/mcp_orchestrator.py`

The engine already supports a remote HTTP decision endpoint. If `AIMP_MCP_REVIEW_URL` is set, the app sends track data and policy there first. Expected response shape:

```json
{
  "decision": "approve",
  "confidence": 0.93,
  "rationale": "Matches channel style and clears quality threshold.",
  "actor": "playlist-approval-agent"
}
```

If the remote call fails and `AIMP_MCP_FALLBACK_TO_RULES=true`, the app falls back to local rules.

From there, a real MCP client can:

- score tracks
- compare candidates
- generate Slack summaries
- decide build readiness
- decide upload readiness

## Tests

Run:

```bash
pytest
```

## Next Implementation Targets

- download generated audio into local storage before playlist render
- Slack modal-based regeneration controls
- duplicate webhook/idempotency handling
- real MCP client integration
