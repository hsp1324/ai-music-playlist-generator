# OpenClaw Backlog Queue Planner

Use this skill when the AI Music app asks OpenClaw to keep production moving while distributed video render workers process queued render jobs.

The goal is not "wait for one release to publish, then start the next one." The goal is to keep each automated YouTube channel supplied with 1-2 unfinished Playlist Releases so render workers and OpenClaw can work in parallel.

## Core Rule

Maintain a small backlog per connected, automated channel:

- Target backlog: at least 1 unfinished Playlist Release per channel.
- Maximum backlog: 2 unfinished Playlist Releases per channel.
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
2. Run `scripts/openclaw-release list-releases`.
3. Check `/youtube/status` and build the active roster from connected channels, excluding `MusicSun` and retired names.
4. First finish existing releases that are already past video render:
   - `metadata_review`: write/approve final YouTube metadata, then approve publish.
   - `publish_ready` or `publish_queued`: retry/continue publish if safe.
   - `youtube_upload_failed`: retry only if the error is transient or already fixed; otherwise report the blocker.
   - `ready_for_youtube_auth` or long-video verification deferred: leave the release intact and move on.
5. Then fill backlog for channels below the target.
6. Stop making new releases for any channel that already has 2 unfinished Playlist Releases.

## Producer Mode

When creating a new release to fill backlog, OpenClaw should produce assets and queue rendering, then move on instead of waiting for the long render:

1. Choose the channel and fresh concept using `docs/openclaw-next-release-planner.md`.
2. Read the selected channel's `concept_doc` and `profile_doc`.
3. Create the Playlist Release before Suno generation.
4. Generate and upload enough approved audio for at least 40 minutes.
5. Upload final cover, YouTube thumbnail, and 8 second Dreamina/Seedance loop video.
6. Render audio with `scripts/openclaw-release render-audio --release-id RELEASE_ID --randomize-order`.
7. Approve the uploaded cover with `scripts/openclaw-release approve-cover --release-id RELEASE_ID`.
8. Queue video render with `scripts/openclaw-release render-video --release-id RELEASE_ID --video-spectrum-overlay-style PRESET`.
9. Choose the visualizer preset that fits the release art; do not rely on the default when the visual mood clearly calls for another preset.
10. Once the video render job is queued/running, do not wait for completion if another channel still needs backlog.

The render worker laptop/VM will claim the queued video render job. OpenClaw should later finish that release on the next backlog request after the video render completes.

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
- channels currently at backlog 0, 1, or 2
- blockers that need human action

Do not spam Slack for every small substep. Report only stage completion, retries, and blockers.

## Safety

- Never use a local dev app API when automation should affect the deployed service.
- Never upload directly in YouTube Studio. YouTube upload must go through the app API.
- Do not create more than 2 unfinished Playlist Releases for the same channel.
- Do not use MusicSun for automatic backlog.
- If a release is stuck because a render worker failed, leave the evidence in the release and report it instead of creating duplicates.
