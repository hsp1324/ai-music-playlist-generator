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

Video render now adds an app-managed audio-reactive visualizer overlay:

- the app fallback style is a transparent 28-bar spectrum near the lower-right of the video
- the final loop video is normalized to 30fps, and the audio-reactive visualizer overlay is generated at 30fps so spectrum motion matches the rendered video cadence
- linear visualizer overlays are wider than the original fallback and fade out at both horizontal edges, so bars/waves do not appear abruptly cut off
- the app samples the cover/loop-video frame and chooses colors that fit the visual palette
- the app can move the overlay away from bright text-heavy areas so it does not cover channel branding
- `AIMP_VIDEO_SPECTRUM_OVERLAY_ENABLED=false` disables it
- `AIMP_VIDEO_SPECTRUM_OVERLAY_STYLE` can be `bars`, `multiwave`, `mirror-bars`, `radial`, `pulse`, or `none`
- `bars` is the production default; `multiwave` draws layered actual audio waveform lines, `mirror-bars` draws centered mirrored bars, `radial` draws a large circular spectrum, `pulse` draws a punchy pulse line, and `none` skips the spectrum overlay for the fastest render. The former small-dot visualizer preset has been removed, and the thin waveform preset used on `아침 온실 피아노 BGM` has also been retired because it looked too visually busy; legacy `dot` / `dots` / `particles` / `thinwave` / `thin-wave` / `clean-wave` values fall back to `bars`.
- the web `Render Video` action and OpenClaw auto-publish commands can pass a per-render visualizer preset; if omitted, `bars` is used. OpenClaw should choose and pass the preset that best fits the release art instead of relying on the fallback. Use `none` for long urgent renders where speed matters more than the audio-reactive visualizer.
- OpenClaw should not bake spectrum bars, waveform graphics, equalizers, or audio meters into the static cover or Dreamina loop video; the app adds those during final render

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
- If the Google Cloud OAuth consent screen remains `External` / `Testing`, Google refresh tokens for YouTube upload scopes expire after 7 days. Reconnect affected channels weekly in testing mode, or move the OAuth app to production/verification for long-lived refresh tokens.
- YouTube uploads are API-only through the app's YouTube Data API flow (`videos.insert` plus thumbnail/localization calls). OpenClaw must not upload directly in YouTube Studio; Studio is only for human review, visibility checks, and manual cleanup after the API upload.
- Past scheduled-public YouTube uploads are treated as public in the web app. The background worker reconciles due `youtube_scheduled_publish_at` values into `youtube_public_at` / `youtube_published_at` and clears the stale scheduled marker so old dates do not keep showing as upcoming scheduled releases.
- Caption tracks are not uploaded or managed by the app. Vocal releases infer and send `snippet.defaultAudioLanguage` when the title/description/tags clearly identify J-pop/K-pop/pop language; BGM/instrumental/no-vocal releases omit it so YouTube is not told to expect speech.
- Cafe/solo-piano playlist metadata now generates a Korean YouTube title, use-case description, timestamped tracklist, and music hashtags
- Approved metadata can be regenerated from the release action area, which creates a new draft that must be approved before re-upload
- OpenClaw can write and approve YouTube metadata through `scripts/openclaw-release approve-metadata`, passing title, multiline description, and comma-separated tags
- OpenClaw should use the external-render lookahead flow: prepare audio/cover/thumbnail/short loop video, run `scripts/openclaw-release render-audio`, `approve-cover`, and `render-video` without `--wait`, then release the lock. External render workers render video; when rendering completes and the MP4 is uploaded back, the app asks OpenClaw to approve metadata and publish through `scripts/openclaw-release publish-release --release-id RELEASE_ID --youtube-channel-title CHANNEL_TITLE`. Cinematic Pulse is the high-resolution still-image exception: OpenClaw should skip provider loop-video generation and queue still-image 2k render with bars spectrum.
- YouTube metadata can now store `ko`, `ja`, `en`, `es`, `vi`, `th`, `hi`, `fil`, `id`, `pt-BR`, `pt-PT`, `fr`, `de`, `ar`, `zh-CN`, and `zh-TW` localized title/description drafts. Releases should provide every configured localization where possible; the publish flow sends the selected default metadata language and sends the other localized title/description drafts as YouTube localizations. YouTube supports Arabic as `ar`; it does not expose a separate `ar-EG` Egyptian Arabic localization code.
- Playlist Release YouTube titles now start with `[playlist]` for the default title and every localized title across all channels. Redundant playlist words like `플레이리스트` / `Playlist` are removed from the title body. Single Release titles remain unprefixed.
- Playlist/BGM YouTube titles should include a real listening situation or viewer intent directly in the title instead of only mood/genre wording. The use case must match the actual music and concept; do not default to study/work/walk/rest wording by habit.
- Korean YouTube metadata must not use the transliterated words `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`; use `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡` instead.
- OpenClaw can get final-order timestamps through `scripts/openclaw-release metadata-context` and should use `display_timestamp_lines` in YouTube descriptions when available, so awkward `A` / `B` suffixes are not shown while timestamps stay fixed. After audio render, metadata timestamps prefer the saved `rendered_timeline` snapshot from actual ffprobe source-file durations instead of recalculating from rounded DB track durations.
- When `AIMP_CODEX_METADATA_ENABLED=true`, the web `Generate Metadata` / `Regenerate Metadata Draft` actions ask the VM's local Codex CLI to write the YouTube title, description, and tags. The app limits this to one Codex run at a time and falls back to the template generator on CLI failure, timeout, or invalid JSON.
- OpenClaw playlist automation now uses step commands for continuous lookahead: upload/approve tracks, upload cover/thumbnail/loop video, render audio, queue external video render, then stop. Cinematic Pulse skips the loop-video step by default and queues a high-resolution still-image render instead. The app asks OpenClaw again after the external worker completes render/upload so metadata/publish can finish while render workers process the next queued release. After a successful publish, the app also waits for the OpenClaw lock to clear and sends one compact backlog request as a fallback, so a partially prepared release stuck before video render, such as `audio_ready`, can continue instead of stalling the loop. OpenClaw can still run `scripts/openclaw-release auto-publish-single` for a human-approved end-to-end single upload. When `AIMP_YOUTUBE_SCHEDULE_PUBLIC_ENABLED=true`, the app uploads each video as a scheduled public release in `AIMP_YOUTUBE_SCHEDULE_TIMEZONE`; scripture releases on `The Old Verse` have two app-managed daily slots, Old Testament at 07:00 and New Testament at 16:00. General BGM releases default to `Soft Hour Radio`; mainstream J-pop/Japanese pop/Tokyo pop releases route to `Tokyo Daydream Radio`; Korean/K-pop vocal releases route to `HaruHaru`; playful no-vocal Japanese-style game/anime OST and arcade/fantasy-game BGM routes to `Storylight OST`; no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, and game-focus music routes to `Cinematic Pulse`; no-vocal EDM/house/techno/trance/workout/night-drive music routes to `Club Bloom`; Old Testament and New Testament Bible scripture-inspired music routes to `The Old Verse`; Buddhist scripture-inspired vocal music routes to `The New Verse` and is private for now; English/American pop routes to `sundaze`; Latin/Spanish pop routes to `Solwave Radio`. MusicSun is manual-only and excluded from continuous automation. Signal Room/Signal Desk/Midnight Cue names are retired unless explicitly revived.
- OpenClaw backlog request cooldown only suppresses duplicate Slack requests that have not been acted on yet. If OpenClaw acquired and finished a lock after the last scheduler request, or a release becomes newly finishable after render completion, the scheduler bypasses cooldown and immediately asks OpenClaw for the next step. Finishable work such as `metadata_review`, `publish_ready`, `publish_queued`, or retryable `youtube_upload_failed` is prioritized before creating new backlog for zero-scheduled channels.
- OpenClaw auto-publish helpers now refuse to re-upload an already published release unless `--allow-reupload` is explicitly passed, preventing accidental duplicate YouTube uploads.
- OpenClaw should create or select the target app release before opening Suno. Use `scripts/openclaw-release create-release` for fresh Single/Playlist Release work, keep the returned `release.id`, and upload later Suno outputs with `--release-id`.
- `scripts/openclaw-release upload-audio` also auto-approves tracks when the target release is a Playlist Release. Use `--pending-review` only when one-by-one playlist review is explicitly desired.
- OpenClaw should provide standalone playlist track titles, not Suno pair labels. The helper also rewrites trailing A/B, 1/2, and older `Morning` / `Evening` style variants into natural standalone display titles.
- BGM/background/lofi/study/sleep/cafe production defaults to instrumental music. For Soft Hour Radio or other no-vocal Suno work, OpenClaw must follow `docs/suno-v55-instrumental-format.md`: enable Instrumental when available, use bracket-only metatag lines in Suno's lyrics/custom-lyrics field, and upload that exact file with `--lyrics-file`. If a Soft Hour Radio lane is lofi / lo-fi, OpenClaw must include lofi in Suno style/settings and carry that genre naturally into the YouTube title, localized titles, and description. J-pop/K-pop/pop/Japanese pop/anime-pop production defaults to vocal songs with lyrics. OpenClaw should not generate instrumental/no-vocal pop-family tracks unless explicitly asked, and should upload lyrics for every pop-family track with `--lyrics` or `--lyrics-file`.
- For vocal Suno work, OpenClaw should set Suno `More options` / `Vocal gender` when the lead vocal is known: `male` for male lead and `female` for female lead. Mixed-gender, duet, group/choir, alternating male/female, or intentionally unspecified lead vocals should leave Vocal Gender unselected. The setting should stay stable across retries for the same track unless the vocal concept changes.
- Suno work should fill Advanced Options excluded styles with artificial noise blockers on every channel unless the human explicitly asks for vinyl/LP/noise texture: white noise, static noise, vinyl crackle, record crackle, LP crackle, tape hiss, cassette hiss, analog hiss, noise floor, lo-fi noise, old record noise, dust noise, crackle, and hiss. No-vocal work should also include vocal-related exclusions such as vocals, voice, singing, humming, choir, spoken word, narration, rap, ad-libs, scat, vocal chops, and lyrics. Lyric/vocal work should also include vocal-clarity exclusions such as muddy vocals, muffled vocals, washed-out vocals, distant vocals, buried vocals, unclear lyrics, heavy reverb, excessive reverb, large echo, concert hall echo, arena reverb, stadium reverb, live concert vocals, crowd ambience, and room boom.
- Suno generation guidance now explicitly avoids producer tags and specific artist references in lyrics, bracketed metatags, style, prompts, tags, and excluded styles. Known blocked example: `lowlight` can be rejected as a producer tag, so OpenClaw should rewrite it to generic wording like `low-lit`, `dim`, `shadowy`, or `soft ambient` before retrying.
- Playlist automation now keeps Suno duration wording minimal: use only `less than 4 minutes` or `under 4 minutes` when a duration hint is needed. The helper allows playlist tracks up to 4:20 by default for most channels and no longer has a default lower-bound track duration. `Soft Hour Radio` and `Cinematic Pulse` are long-track exempt: do not force those tracks under 4 minutes, and do not reject complete longer tracks just because of duration.
- OpenClaw helper commands now reject pop-family uploads with empty lyrics before publish unless the concept explicitly says BGM/instrumental/no-vocal. YouTube metadata approval also appends a visible public hashtag line when OpenClaw/Codex provides API tags but forgets description hashtags.
- YouTube metadata generation and approval now filters AI/process/tool tags from API tags and public hashtags on every channel. Avoid `AIMusic`, `AI music`, `AI generated`, `AI visualizer`, `Suno`, `OpenClaw`, and `Codex`.
- OpenClaw generation guidance now requires track-level variation inside a release: distinct prompts, titles, lyrics concepts, chorus hooks, and preferably per-track Suno style/settings, while keeping the overall channel/release mood coherent.
- The Old Verse should rotate Bible release-level music lanes across uploads, such as scripture jazz, gospel R&B/soul, acoustic scripture folk/gospel, piano worship ballads, choir-backed worship/gospel, cinematic scripture/Gospel worship, or neo-soul prayer songs. The New Verse should rotate Buddhist scripture-inspired lanes such as Buddhist jazz, mindful hip-hop, Buddhist R&B/soul, dharma neo-soul, acoustic dharma songs, or cinematic meditation pop. One release must stay in one coherent lane so the YouTube title and description can truthfully name that genre.
- Playlist workspaces no longer auto-queue audio render just because the target duration is reached. The operator or OpenClaw must explicitly start render after all intended tracks have finished uploading.
- Audio/video rendering now snapshots the ordered track ids used for the render and stores a `rendered_timeline` based on actual probed source-file durations. If OpenClaw or the UI adds tracks while audio/video render is running, the stale render is rejected and a fresh render is queued or required before publish, preventing YouTube timelines from outlasting the actual video.
- Audio render supports optional playlist order randomization. The web UI asks whether to randomize before `Render Mix` / `Re-render Audio`, and the API accepts `random: true` (`randomize_order: true` is still accepted for compatibility). When randomized, the app saves the shuffled order before render, so final order, rendered audio, and description timestamps stay aligned.
- Playlist automation requires a final uploaded 16:9 cover image before YouTube upload. The app's generated draft cover is only a manual placeholder.
- Full OpenClaw playlist publishing now expects two final 16:9 images: a video cover via `--cover` and a text-based YouTube thumbnail via `--thumbnail`. Reusing the cover as the thumbnail is only allowed with `--allow-cover-as-thumbnail`.
- Visual asset rules are channel-specific and documented in `docs/openclaw-channel-profiles/`. OpenClaw should choose the channel first, read the returned `concept_doc` for next-release planning and `profile_doc` for visual execution, and apply human visual requests consistently to cover, thumbnail, and loop video. The YouTube thumbnail should be generated from the final cover as a reference/edit derivative so characters, positions, outfit colors, lighting, palette, and background stay continuous. Most generated visuals should stay animated/anime/illustrated/stylized, not photorealistic or live-action. Cinematic Pulse is the explicit exception: it should use original photorealistic cinematic film-still / premium movie-poster realism, skip provider loop video by default, and final renders should use the high-resolution still cover with clean `bars` spectrum preset.
- HaruHaru is a second controlled visual exception: it should use a photorealistic-heavy 2:1 rotation, roughly two photorealistic adult fashion/lifestyle visuals followed by one illustrated/stylized Korean pop visual. HaruHaru photorealistic releases use Seedance `2.0` at `1080p` plus final render `1080p`; HaruHaru illustrated/stylized releases use Seedance/Dreamina `2.0 Fast` at `720p`. Photorealistic HaruHaru prompts must stay non-explicit and adult-only. If a photorealistic adult woman is the main subject, the loop video should keep her the same size/crop for the full clip; any subject movement should be matched by camera tracking at the same speed/distance, with motion coming from background parallax/environment instead of zoom, push-in, pull-back, or scale changes.
- Every channel now requires a consistent large, readable lower-left channel-name brand label on the video cover/first-frame and inside the Gemini/Dreamina/Seedance loop video. The cover/first-frame should contain only that channel name. Thumbnails should use large click text plus a channel-name brand line whose size/style stays consistent with the cover label. Target roughly 18-24% of image width, or about 5-6% of image height for text cap height.
- OpenClaw channel visual rules are also split into `docs/openclaw-channel-profiles/`. OpenClaw can run `scripts/openclaw-release channel-profile` to infer the target channel and get the exact profile doc to read before making visual assets.
- OpenClaw channel concept planning is now split into `docs/openclaw-channel-concepts/`. The next-release planner chooses the channel, then reads that channel's concept doc to avoid recent repetition before it reads the visual profile.
- OpenClaw should generate static cover/thumbnail images with OpenAI GPT Image models, preferably `gpt-image-2` when available, not Dreamina. Dreamina is reserved for the moving visual clip.
- `Tokyo Daydream Radio` thumbnails should use the approved consistent channel layout: large `J-POP` and smaller `TOKYO DAYDREAM RADIO` beneath it, using the same full-bleed system for Tokyo/city, forest/nature, and beach variants. Do not add `1 HOUR`, `60 MIN`, `1時間`, or duration badges. The main default/requested subject must stay centered; text should fit around it without pushing it sideways.
- OpenClaw must pass a short provider-generated MP4 via `--loop-video` for normal publish automation and must tag it with `--loop-video-provider gemini|dreamina|seedance`; the app stores this in `loop_video_provider` and `loop_video_history[].provider`. The video render API rejects renders without an uploaded loop video unless `allow_still_image_fallback` is explicitly set for a human-approved exception or the selected channel is Cinematic Pulse. Cinematic Pulse should render from the high-resolution still cover with `--video-render-source-mode still_image --video-render-resolution 2k --video-spectrum-overlay-style bars`. Browser automation should try Gemini first by clicking `Create image` / the creation entry that accepts image+prompt, attaching the cover/first-frame image, generating video, downloading the MP4, and counting only successful Gemini video outputs toward the 3 videos per 24 hour quota. Gemini prompts should not mention duration; upload the generated Gemini MP4 as-is after inspection. After the 3rd successful Gemini video, OpenClaw should use Dreamina/Seedance until 24 hours have passed from that 3rd generation. If Dreamina/Seedance fails, OpenClaw should not create a local motion-loop workaround; it should try Gemini if quota is available, or defer that release and continue with the next eligible release if Gemini quota is exhausted. Copyright/policy blocks before Gemini creates a video do not count and should be retried with safer prompts up to 10 times before falling back to Dreamina/Seedance. Dreamina/Seedance normally uses `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, and exactly `6 seconds` through UI controls; HaruHaru photorealistic releases are the exception and use Seedance `2.0`, `1080p`, exactly `6 seconds`, plus final render `1080p`. The app smooth loop crossfade defaults to 1 second. The first-frame image should be the cover or a separate first-frame image with only the large, readable lower-left channel label, not the YouTube text thumbnail, because large generated title text can flicker or disappear. The generated clip should end close to its opening composition so it can be reused across the full release.
- Existing releases that already have loop videos remain valid. The 6 second Seedance/Dreamina rule is for new OpenClaw-created Seedance/Dreamina clips going forward; Gemini clips are uploaded as generated.
- Loop-video upload validates only that the file is readable video. The app does not reject low-motion clips or alternate clip lengths; visual quality and the normal 6 second Seedance/Dreamina setting are handled by human/OpenClaw review before render/publish.
- Gemini/Dreamina/Seedance prompts must preserve the exact lower-left channel text for the full clip, and OpenClaw should reject/regenerate clips where the label flickers, morphs, disappears, moves drastically, changes spelling/style, or becomes unreadable.
- Gemini/Veo provider logos or watermarks, usually in the bottom-right corner, are allowed provider artifacts and are not a reason to regenerate an otherwise valid loop video. The no-logo rule only forbids OpenClaw-requested/generated extra logos, UI, brand marks, or unrelated text.
- Gemini/Dreamina/Seedance content-safety or copyright rejections are retried with sanitized prompts. Gemini copyright/policy blocks do not count against the 3 successful-video quota unless Gemini actually creates a video. If Dreamina/Seedance cannot create a clip, OpenClaw should try Gemini again when quota is available. If all 3 Gemini videos are already spent, the release is deferred until the 24 hour Gemini cooldown clears and should be resumed before new loop-video work. Repeated failures stop the automation before render/publish unless the human explicitly accepts a still-image fallback and `--allow-still-image-video` is passed.
- Long video rendering now encodes the reusable short visual unit once, then extends that unit with ffmpeg concat stream-copy for the final video instead of re-encoding every frame of a long-form release.
- The web release detail UI now supports direct upload/replace actions for video cover, text YouTube thumbnail, and loop video as separate assets.
- Already-uploaded releases can replace the loop video from the release detail UI. Replacing the loop video marks the release as needing a new video render before re-upload while keeping the previous YouTube video id visible until the new render starts.
- After a successful YouTube upload, the app immediately deletes the long final rendered local MP4, records `local_video_deleted_after_youtube_upload`, clears `output_video_path`, and keeps the YouTube video id/link as the watch surface. Source assets such as the rendered audio, cover, thumbnail, and short Gemini/Dreamina/Seedance loop video are intentionally kept. Re-uploading requires rendering a new long local video first.
- The app keeps disk usage under control: when `AIMP_STORAGE_ROOT` disk usage rises above `AIMP_LOCAL_VIDEO_CLEANUP_DISK_THRESHOLD_PERCENT` (default `80`), it deletes any remaining local final rendered MP4 files for releases already uploaded to YouTube and public, oldest first, and records the deletion in release metadata. This fallback does not delete short loop/source videos. The check runs periodically and immediately after OpenClaw loop-video uploads, external render-worker chunk uploads, and external render completion.
- Workspace API responses now include `youtube_channel_id` and `youtube_channel_title` next to `youtube_video_id`, so the dashboard and OpenClaw can confirm which channel a published release was uploaded to.
- Workspace lists are API-sorted by Published order: unpublished releases first, then scheduled YouTube publish time when present, otherwise actual YouTube publish/upload time, otherwise release creation time. The web UI uses that order by default for all-channel and per-channel views, while offering per-view toggles for Published, Updated, and Created sorting in either direction.
- Slack channel routing is intentionally split. `AIMP_SLACK_OPS_CHANNEL_ID` must point to `#all-ai-music-playlist-generator` / `C0ATYMCMLLE` for operational notices such as render-worker claim/complete, timeout requeue, and YouTube publish-complete. Those notices attach the release thumbnail/cover when available, resize Slack preview artwork to a `480` px max edge by default, and omit internal job IDs from visible Slack text. `AIMP_OPENCLAW_SLACK_CHANNEL_ID` points to `#openclaw` / `C0AVBUYP150` for `OPENCLAW_RUN:` command traffic only. Do not send render-worker status notices to `#openclaw`.
- The app can send a "next release" Slack request to the OpenClaw channel after a release is uploaded or scheduled. Configure `AIMP_OPENCLAW_SLACK_CHANNEL_ID`; the web UI shows `Request Next Playlist`, and `AIMP_OPENCLAW_AUTO_REQUEST_NEXT_ON_PUBLISH=true` sends a compact fallback request after successful YouTube upload with per-video dedupe. In VM-render lookahead mode this publish fallback waits until the OpenClaw lock is clear and uses the backlog request shape, not the old long publish prompt. `AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED` is optional and should remain disabled in conservative VM-render mode. If YouTube rejects a 14+ minute video because the account is not phone/account verified for long uploads, the app now keeps the rendered release for later retry. `AIMP_OPENCLAW_AUTO_REQUEST_NEXT_MAX_UPLOADS=N` caps the loop after N successful YouTube uploads; `0` means unlimited. Human Slack messages in the configured OpenClaw channel such as `OpenClaw 자동화 멈춰` stop the app from sending more automatic `OPENCLAW_RUN:` requests, and `OpenClaw 자동화 다시 시작` resumes. Real app-originated OpenClaw task messages are prefixed with `AIMP_OPENCLAW_SLACK_TRIGGER_PREFIX` (default `OPENCLAW_RUN:`). Slack event routing and mention-only behavior belongs in the Slack App/OpenClaw listener configuration, not in the music release skill docs.
- OpenClaw's continuous automation entry point is `docs/openclaw-backlog-queue.md`, then `docs/openclaw-next-release-planner.md`. In normal VM-render mode, OpenClaw should finish one release end-to-end before starting another: choose the next non-excluded channel, create/upload assets, render audio, render video on the VM app, wait for completion, approve metadata, and publish. The planner reads `/youtube/status`, rotates connected non-excluded channels, reads the selected channel's concept planner/profile, avoids recent concept repetition, chooses the next channel/concept, then follows the production/publish instructions.
- New release channel priority now favors connected automated channels with `0` future scheduled-public YouTube uploads before adding more releases to channels that already have upcoming scheduled public videos. The backlog Slack snapshot includes each channel's unfinished count plus future scheduled-public and total YouTube upload counts so OpenClaw can make that choice explicitly.
- OpenClaw must call `scripts/openclaw-release openclaw-lock-start`, refresh with `openclaw-lock-heartbeat` every 1-2 minutes, and call `openclaw-lock-finish` when done/blocked. The app stores this lock in `storage/openclaw-runtime-state.json`; the backlog scheduler will not send another Slack request while the lock is active, and stale locks expire through `AIMP_OPENCLAW_LOCK_TTL_SECONDS`.
- The Old Verse uses the deployed web app as the Bible scripture sequence source of truth for both Old Testament and New Testament branches. The app stores `storage/openclaw-scripture-sequence.json` on the VM and exposes OpenClaw helper commands through `scripts/openclaw-release openclaw-scripture-status`, `openclaw-scripture-reserve`, `openclaw-scripture-complete`, and `openclaw-scripture-fail`. OpenClaw must create the release, reserve the next app-owned passage before Suno generation, and mark it scheduled/published after upload. OpenClaw must not compare against a local scripture ledger or block only because title wording differs. The New Verse is a separate Buddhist scripture-inspired channel and does not use the Bible scripture ledger.
- Track uploads now accept optional lyrics/content notes, Suno style/settings, and Suno excluded styles/negative tags. These are stored in track metadata and exposed through release/timeline context for later thumbnail, loop-video, metadata, remake, and standalone single workflows.
- HaruHaru, sundaze, and Solwave Radio now require one explicit genre lane per release, such as K-pop hip-hop, Korean R&B, Pop R&B, dance-pop, Pop Latino, reggaeton pop, bachata pop, or Latin R&B, with that lane named naturally in title/metadata and reflected in Suno style prompts.
- Track intake now probes uploaded local audio duration with ffprobe and rejects empty audio uploads. Playlist audio render also validates every source file before concat and fails if the rendered output is materially shorter than the source tracks, preventing 0-byte or corrupt uploads from being published as short YouTube videos.
- OpenClaw helper audio uploads retry each file up to 3 times. Playlist automation continues uploading later tracks after a failed file, posts a Slack warning with the failed titles/files, and stops before render/publish until the failed sources are re-uploaded.
- YouTube metadata timelines use `HH:MM:SS` for one-hour-plus releases, starting at `00:00:00`, so timestamps after one hour remain linkable. Normal automated playlist releases target `2400` seconds / 40 minutes. Before playlist audio render, the app tries to fill the remaining time from previous same-channel, similar-genre YouTube uploads by reusing tracks that appeared in the back half of those videos; the preferred reuse amount is at least 20 minutes when enough candidates exist. If no similar back-half candidates exist, render proceeds with the uploaded new tracks instead of blocking. Japan/J-pop localized descriptions should use Japanese track titles plus Korean translations in the Korean/default version, Japanese titles in the Japanese version, and translated song titles in every other localized version. sundaze/English pop localized descriptions keep English song titles in every timeline. HaruHaru/K-pop uses Korean as the default metadata language and Korean lyrics by default.
- YouTube uploads set `status.containsSyntheticMedia` from `AIMP_YOUTUBE_CONTAINS_SYNTHETIC_MEDIA`; the default is `false`, so publish/re-upload declares that the video does not contain realistic altered or synthetic media. Set it to `true` only for realistic AI/altered content that needs disclosure. Uploads also always set `status.selfDeclaredMadeForKids=false`, so YouTube receives "No, it's not made for kids" on every publish/re-upload.

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
- App/API generation default is `V5_5`, and OpenClaw should choose Suno v5.5 in the web UI whenever available. Suno's public pricing currently groups v5 and v5.5 under the same paid-plan advanced-model song/credit allowance; if the UI/API later shows v5.5 costing more credits than v5 for the same request, OpenClaw should stop and report the exact difference before bulk generation.

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

### 2. Render throughput

The app now supports external video render workers. In `AIMP_VIDEO_RENDER_EXECUTION_MODE=external`, the main VM keeps DB/UI/Slack/YouTube ownership but does not execute `build_video` jobs. External machines run `scripts/render-worker`, claim queued video jobs through `/api/render-worker/*`, render locally, and upload the final MP4 back with resumable chunk uploads. This lets a second Oracle instance or a home desktop handle ffmpeg work while the main VM stays responsive.

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
