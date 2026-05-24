# OpenClaw Backlog Queue Planner

Use this skill when the AI Music app asks OpenClaw to produce the next release through the deployed Oracle VM app.

The current production mode is external-render lookahead: the Oracle VM app owns state, Slack, and YouTube publish, while OpenClaw prepares the next release's audio, cover, thumbnail, and short loop video. A separate render worker machine claims queued video jobs and uploads the finished MP4 back to the app. Cinematic Pulse still uses photorealistic high-resolution first-frame art, but it also needs a restrained provider loop video by default.

## Core Rule

Maintain a bounded unfinished Playlist Release backlog per connected, automated channel:

- Target backlog: 10 unfinished Playlist Releases per channel.
- Maximum backlog: 10 unfinished Playlist Releases per channel.
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
5. Check YouTube status with `scripts/openclaw-release youtube-status` and build the active roster from connected channels, excluding `MusicSun` and retired names.
   Do not open `/youtube/status`, `/api/youtube/status`, `/youtube/connect`, `/api/youtube/connect`, Google OAuth, or YouTube Studio in a browser. If YouTube status is not ready, report the blocker instead of trying to authenticate.
6. First finish existing releases that are already past video render:
    - `metadata_review`: write/approve final YouTube metadata, then approve publish.
    - `publish_ready` or `publish_queued`: retry/continue publish if safe.
    - `youtube_upload_failed`: retry only if the error is transient or already fixed. If the error says the stored YouTube channel token expired/was revoked or asks to reconnect the channel, report it as a human-auth blocker. Do not make new releases for that same channel until the human reconnects it; continue only with other eligible channels.
    - `ready_for_youtube_auth` or long-video verification deferred: leave the release intact and move on.
    - loop-video deferred because Dreamina/Seedance failed and Gemini quota was exhausted: if the Gemini 24 hour cooldown has cleared, make/upload the Gemini loop video first and queue render before starting any new release. Do not replace the missing provider video with a local motion-loop workaround.
    - Gemini/Veo may add its own provider logo or watermark, usually in the bottom-right corner. This is acceptable and is not a reason to remake an otherwise valid loop video. The no-logo rule only forbids OpenClaw-requested/generated extra logos, UI, brand marks, or unrelated text.
   - Exception: if the web app request reason is `zero_scheduled_public_backlog`, prioritize creating/continuing a release for the first channel in the priority list with the shortest scheduled-through horizon. Do not let unrelated channels' metadata/publish-only finishable items cause the shortest-horizon channel to be skipped again.
7. Before creating a new release, inspect existing unfinished workspaces that are not yet past video render, especially `collecting`, `audio_ready`, `render_required`, or channel-unknown workspaces with no app-visible tracks/assets. These may be interrupted OpenClaw runs with Suno audio, cover, thumbnail, or loop-video files already prepared locally. Search the local OpenClaw workspace/logs by release id and title, then resume that workspace first: set the target YouTube channel if missing, upload missing tracks/assets, render audio, approve cover, and queue video render. If the local assets cannot be found or the workspace should be abandoned, report the blocker instead of silently creating a duplicate.
8. When creating a new release, first fill the connected automated channel with the shortest future scheduled-public horizon in the app's backlog snapshot. Future scheduled-public means a YouTube video id exists and the app has a scheduled public publish time or YouTube `publishAt` value that is still in the future. Keep dates even across channels: all channels should have the earliest upcoming date covered before any channel is pushed further into later dates. This priority is above oldest-recent-upload rotation, but do not exceed the channel's maximum unfinished backlog.
9. If a release is currently `video_rendering`, treat a render worker as busy but productive. Do not wait idle. Prepare another eligible release for any channel that is still below target, including the same channel when it has not reached the maximum.
10. OpenClaw requests should not be triggered by render-worker claim/start alone. The app may ask for more backlog work after the OpenClaw lock is released, and it asks OpenClaw to finish metadata/publish after the external worker completes and uploads the rendered MP4.
11. Stop making new releases only for channels that have reached the configured maximum backlog.
12. When creating a new release, stop after queuing video render. Release the app-side lock so the app can ask for the next finish/prepare step later.

`AIMP_LOCAL_API_BASE` should point at the deployed VM FastAPI backend. The public `https://ai-music.168.107.34.175.sslip.io/api` URL is Google-login protected and needs `AIMP_API_COOKIE`; `AIMP_OPENCLAW_SHARED_TOKEN` alone is not enough for upload/publish helper calls.

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

If the block is a Suno hCaptcha/manual verification or another human-verification gate, keep the same release/workspace as the next action. After the app's backoff, its Slack request will ask OpenClaw to resume the blocked release instead of making a new song. Do not abandon that release or start the next release unless the human explicitly says to skip it.

## Producer Mode

When creating a new release, OpenClaw should produce assets and queue rendering in the VM app, then stop:

1. Choose the channel and fresh concept using `docs/openclaw-next-release-planner.md`.
2. Read the selected channel's `concept_doc` and `profile_doc`.
3. Create the Playlist Release before Suno generation.
   - Pass `--youtube-channel-title "$CHANNEL_TITLE"` when using `scripts/openclaw-release create-release`.
   - This lets the web app count the release against the correct channel backlog before publish.
4. Generate and upload roughly 15 minutes of new approved audio for normal non-scripture channels, or roughly 40 minutes for BibliaCanto/불송 passage-based releases. When audio render is queued, the web app automatically tries to extend non-scripture base blocks to roughly 40 minutes by reusing previous same-channel, similar-genre tracks from the back half of already uploaded YouTube videos. BibliaCanto and 불송 are excluded from reuse. During the trial period, final video repeat is disabled and render workers upload the base block only.
5. Upload final cover, YouTube thumbnail, and short loop video. Try Gemini first, then use Dreamina/Seedance when Gemini is on cooldown, unavailable, or blocked after retries. If Dreamina/Seedance cannot create the clip, try Gemini again when quota is available; if Gemini has already used all 3 successful videos in the current 24 hour window, defer this release and resume it first after cooldown. For Cinematic Pulse, use photorealistic cinematic cover/first-frame art and still create a subtle loop video by default.
6. Render audio with `scripts/openclaw-release render-audio --release-id RELEASE_ID --randomize-order`.
7. Approve the uploaded cover with `scripts/openclaw-release approve-cover --release-id RELEASE_ID`.
8. Queue video render with `scripts/openclaw-release render-video --release-id RELEASE_ID --video-spectrum-overlay-style PRESET`.
9. Choose the visualizer preset that fits the release art; do not rely on the default when the visual mood clearly calls for another preset. For `Cinematic Pulse`, queue `--video-render-source-mode loop_video --video-render-resolution 720p --video-spectrum-overlay-style bars` unless a human explicitly asks for a still-image fallback or higher resolution.
10. Do not pass `--wait` in normal automation. Do not approve metadata or publish until the app later asks again after external render completion.
11. Release the OpenClaw lock and report the queued release id.

The render worker pool owns production video rendering. The Oracle VM app only queues the job and finalizes the uploaded MP4.

## Visual Rework Requests

- If the human flags a published release's cover, thumbnail, or loop video as weak, treat it as a visual repair task, not a new music release. Keep the existing songs/audio unless the human explicitly asks for new tracks.
- For visual-only repair, replace the final cover, text YouTube thumbnail, and short loop video together, then approve the cover and queue a fresh video render. Try Gemini first for the loop video, then use Dreamina/Seedance when Gemini is on cooldown, unavailable, or blocked after retries. If Dreamina/Seedance cannot create the repair clip and Gemini quota is exhausted, defer the repair until Gemini can create videos again; when cooldown clears, finish the deferred repair before new loop-video work. After render completion, update or re-publish through the app's normal YouTube flow.
- If Dreamina/Seedance fails because of face detection, moderation, payment, quota, CAPTCHA, or browser automation issues, do not make an interim local motion loop. Either make the clip in Gemini, or defer the release if Gemini quota is exhausted, then continue with the next eligible backlog item.
- Do not spend image/video-generation credits while the human says credits are unavailable. Keep the repair note and resume only after the human says credits or generation capacity are available again.
- Current human repair note from 2026-05-15: the currently uploaded `Club Bloom` release has cover/thumbnail visuals that are too mild. Later, remake only its Club Bloom visual assets with a stronger, more click-stopping club look, then re-render from the existing music.
- Current human repair note from 2026-05-16: `[playlist] 비 오는 서울 K-POP 드라이브 | 밤공기, 자신감, 반짝이는 보컬` has the wrong uploaded 8-second loop video attached. Treat this as a loop-video-only repair: keep the existing songs, audio render, cover, and thumbnail unless the human says otherwise. First clear the bad uploaded loop video with `scripts/openclaw-release delete-loop-video --release-title "[playlist] 비 오는 서울 K-POP 드라이브 | 밤공기, 자신감, 반짝이는 보컬"`, then create the correct replacement loop video from the existing cover/first-frame. Try Gemini first with no duration wording; if Gemini is unavailable/on cooldown/blocked after retries, use Dreamina/Seedance with duration set to exactly `7 seconds`. If Dreamina/Seedance also cannot create it and Gemini quota is exhausted, defer this repair until Gemini cooldown clears, then make/upload the Gemini loop video first. Upload the replacement with `upload-loop-video`, render video again, then continue metadata/publish through the normal app flow.

## Finisher Mode

When a release has completed video render and the external worker has uploaded the MP4, OpenClaw should finish it before starting more producer work:

1. Run `scripts/openclaw-release metadata-context --release-id RELEASE_ID`.
2. Write final metadata using `docs/openclaw-youtube-metadata.md`.
3. Preserve the rendered timeline exactly.
4. Include all supported localizations.
5. Approve metadata through `scripts/openclaw-release approve-metadata`.
6. Publish through `scripts/openclaw-release publish-release --release-id RELEASE_ID --youtube-channel-title CHANNEL_TITLE`.
7. If phone/account verification blocks a 14+ minute upload, keep the release intact, report the deferred upload, and continue with backlog work.

After a successful publish, finish the current OpenClaw lock normally. The app will wait for that lock to clear and may send a compact `publish_completed` backlog request if the pipeline still has unfinished work, such as a release waiting at `audio_ready`, or a channel below target backlog. Treat that request like any other backlog pass.

## Slack Reporting

Report compactly after every backlog pass:

- finished releases and YouTube ids
- newly queued releases and release ids
- channels currently below target, near target, or at the maximum backlog limit
- channels with the shortest future scheduled-public horizon that should be filled first
- blockers that need human action

Do not spam Slack for every small substep. Report only stage completion, retries, and blockers.

## Safety

- Never use a local dev app API when automation should affect the deployed service.
- Never upload directly in YouTube Studio. YouTube upload must go through the app API.
- Do not create more than the configured maximum unfinished Playlist Releases for the same channel.
- Do not use MusicSun for automatic backlog.
- If a release is stuck because rendering failed, leave the evidence in the release and report it instead of creating duplicates.
- Production rendering happens through `scripts/render-worker` on external compute. See `docs/external-video-render-worker.md`.
