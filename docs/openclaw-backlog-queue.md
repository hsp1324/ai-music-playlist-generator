# OpenClaw Backlog Queue Planner

Use this skill when the AI Music app asks OpenClaw to produce the next release through the deployed Oracle VM app.

The current production mode is the conservative VM-render flow: create or finish one release at a time, let the Oracle VM app background worker render video, wait for that render to complete, then approve metadata and publish before moving to the next release. Do not rely on laptop/external render workers for normal automation.

## Core Rule

Maintain at most one unfinished Playlist Release per connected, automated channel:

- Target backlog: at least 1 unfinished Playlist Release per channel.
- Maximum backlog: 1 unfinished Playlist Release per channel in normal VM-render mode.
- Excluded channel: `MusicSun` is manual-only and must not be filled by automatic backlog work.
- Future connected channels are included automatically unless docs explicitly mark them manual-only or retired.

An unfinished Playlist Release counts toward backlog when it belongs to a channel and is not fully uploaded/scheduled to YouTube yet. Count releases in states such as:

- collecting or uploading tracks
- audio render queued/running/complete
- cover/thumbnail/loop-video ready
- video render queued/running
- metadata review
- publish ready/queued
- YouTube upload failed or deferred because of long-video verification

Do not count archived releases, deleted releases, failed releases that require human repair, or releases already uploaded/scheduled to YouTube.

## Work Order

On each `OPENCLAW_RUN:` backlog request:

1. Update the repo and confirm `AIMP_LOCAL_API_BASE` points at the deployed VM app API.
2. Acquire the app-side OpenClaw lock before opening Suno, Dreamina, or creating a release.
3. Keep the lock alive with heartbeat while working.
4. Run `scripts/openclaw-release list-releases`.
5. Check `/youtube/status` and build the active roster from connected channels, excluding `MusicSun` and retired names.
   Do not open `/youtube/connect`, `/api/youtube/connect`, Google OAuth, or YouTube Studio. If `/youtube/status` is not ready, report the blocker instead of trying to authenticate.
6. First finish existing releases that are already past video render:
   - `metadata_review`: write/approve final YouTube metadata, then approve publish.
   - `publish_ready` or `publish_queued`: retry/continue publish if safe.
   - `youtube_upload_failed`: retry only if the error is transient or already fixed; otherwise report the blocker.
   - `ready_for_youtube_auth` or long-video verification deferred: leave the release intact and move on.
7. Then fill one channel below the target.
8. Stop making new releases for any channel that already has an unfinished Playlist Release.
9. Release the app-side lock when the backlog pass is completed or blocked.

`AIMP_LOCAL_API_BASE` should normally be `http://127.0.0.1:8000/api` on the VM, or a laptop tunnel to that same VM FastAPI backend. The public `https://ai-music.168.107.34.175.sslip.io/api` URL is Google-login protected and needs `AIMP_API_COOKIE`; `AIMP_OPENCLAW_SHARED_TOKEN` alone is not enough for upload/publish helper calls.

## Lock And Heartbeat

The web app uses this lock to avoid sending another automatic Slack request while OpenClaw is still doing browser work that may not yet be visible in the app database.

At the start of every app-originated backlog pass:

```bash
RUN_ID="${RUN_ID:-$(uuidgen)}"
scripts/openclaw-release openclaw-lock-start \
  --run-id "$RUN_ID" \
  --operation "backlog-pass" \
  --message "Starting OpenClaw backlog pass"
```

If `ok=false` and `reason=openclaw_lock_active`, stop. Another OpenClaw task is already active.

While doing Suno, Dreamina, uploads, metadata, or publish work, refresh the lock every 1-2 minutes:

```bash
scripts/openclaw-release openclaw-lock-heartbeat \
  --run-id "$RUN_ID" \
  --operation "suno-or-dreamina-or-publish" \
  --channel-title "$CHANNEL_TITLE" \
  --release-id "$RELEASE_ID" \
  --message "Short current status"
```

When the pass is done or blocked:

```bash
scripts/openclaw-release openclaw-lock-finish \
  --run-id "$RUN_ID" \
  --status "completed" \
  --message "Queued/finished backlog work"
```

Use `--status blocked` if captcha, credits, login, missing API, or YouTube verification prevents progress.

## Producer Mode

When creating a new release, OpenClaw should produce assets, queue rendering in the VM app, wait for render completion, then publish:

1. Choose the channel and fresh concept using `docs/openclaw-next-release-planner.md`.
2. Read the selected channel's `concept_doc` and `profile_doc`.
3. Create the Playlist Release before Suno generation.
   - Pass `--youtube-channel-title "$CHANNEL_TITLE"` when using `scripts/openclaw-release create-release`.
   - This lets the web app count the release against the correct channel backlog before publish.
4. Generate and upload enough approved audio for at least 40 minutes.
5. Upload final cover, YouTube thumbnail, and 8 second Dreamina/Seedance loop video.
6. Render audio with `scripts/openclaw-release render-audio --release-id RELEASE_ID --randomize-order`.
7. Approve the uploaded cover with `scripts/openclaw-release approve-cover --release-id RELEASE_ID`.
8. Queue video render with `scripts/openclaw-release render-video --release-id RELEASE_ID --video-spectrum-overlay-style PRESET --wait`.
9. Choose the visualizer preset that fits the release art; do not rely on the default when the visual mood clearly calls for another preset.
10. Wait for VM video render completion. Do not start another channel while the current release is rendering.
11. Run metadata and publish steps before starting the next release.

The Oracle VM app background worker owns normal video rendering. External render workers are optional emergency/manual mode only, not the default OpenClaw automation path.

## Finisher Mode

When a release has completed video render, OpenClaw should finish it before starting more producer work:

1. Run `scripts/openclaw-release metadata-context --release-id RELEASE_ID`.
2. Write final metadata using `docs/openclaw-youtube-metadata.md`.
3. Preserve the rendered timeline exactly.
4. Include all supported localizations.
5. Approve metadata through `scripts/openclaw-release approve-metadata`.
6. Publish through `scripts/openclaw-release publish-release --release-id RELEASE_ID --youtube-channel-title CHANNEL_TITLE`.
7. If phone/account verification blocks a 14+ minute upload, keep the release intact, report the deferred upload, and continue with backlog work.

## Slack Reporting

Report compactly after every backlog pass:

- finished releases and YouTube ids
- newly queued releases and release ids
- channels currently at backlog 0 or 1
- blockers that need human action

Do not spam Slack for every small substep. Report only stage completion, retries, and blockers.

## Safety

- Never use a local dev app API when automation should affect the deployed service.
- Never upload directly in YouTube Studio. YouTube upload must go through the app API.
- Do not create more than 1 unfinished Playlist Release for the same channel in normal VM-render mode.
- Do not use MusicSun for automatic backlog.
- If a release is stuck because rendering failed, leave the evidence in the release and report it instead of creating duplicates.
