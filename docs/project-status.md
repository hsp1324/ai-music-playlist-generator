# Project Status

Last updated: 2026-05-21

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

## Recent Operating Notes

- Suno credit status: the 2026-06-05 no-new-audio restriction is lifted after the human added 500 credits. OpenClaw may resume Suno generation, but should spend credits conservatively: for normal non-scripture playlist releases, create only roughly 10 minutes of new approved audio, then fill the rest with previous same-channel, similar-genre approved tracks, preferring liked tracks and excluding disliked/copyright-blocked/reuse-disabled tracks. Existing audio already generated/downloaded can still be uploaded and used because the credit was already spent.
- Storylight OST playlist production is reuse-only by default. OpenClaw should not start new Suno generation for Storylight OST unless the human explicitly asks for it; it should create/select a playlist workspace, reuse existing approved Storylight-compatible tracks, and only generate new cover/thumbnail/loop-video assets. Existing Storylight audio can still be uploaded and used when it has already been generated/downloaded, because the credit has already been spent. Existing approved Storylight tracks can also be reused when short.

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

- the app fallback style is a transparent 18-bar spectrum near the lower-right of the video; the bar overlay is 420px wide, 1.5x the earlier compact 280px width, so it reads more clearly on still-image lyric renders without taking over the frame
- the final loop video is normalized to 30fps, and the audio-reactive visualizer overlay is generated at 30fps so spectrum motion matches the rendered video cadence
- linear visualizer overlays fade out at both horizontal edges, so bars do not appear abruptly cut off
- the app samples the cover/loop-video frame and chooses colors that fit the visual palette
- the app can move the overlay away from bright text-heavy areas so it does not cover useful thumbnail/first-frame wording
- `AIMP_VIDEO_SPECTRUM_OVERLAY_ENABLED=false` disables it
- `AIMP_VIDEO_SPECTRUM_OVERLAY_STYLE` can be `bars`, `mirror-bars`, `calm-bars`, or `none`
- `bars` is the production default; `bars` and `mirror-bars` draw center-weighted Gaussian EQ bar groups whose columns bounce in place instead of flowing waveform motion or dense left-to-right equalizer sweeps, `calm-bars` uses fewer/lower-opacity bars for meditative visuals, and `none` skips the spectrum overlay for the fastest/cleanest render. Busy or fast-looking presets have been retired: small dots/particles, the thin waveform used on `아침 온실 피아노 BGM`, and the spectrum style used on `창세기 창조의 빛` should not be used. Legacy `dot` / `dots` / `particles` / `thinwave` / `thin-wave` / `clean-wave` / `multiwave` / `radial` / `pulse` values fall back to clean `bars`.
- the web `Render Video` action and OpenClaw auto-publish commands can pass a per-render visualizer preset; if omitted, `bars` is used. OpenClaw should choose and pass the preset that best fits the release art instead of relying on the fallback. Use `none` for long urgent renders where speed matters more than the audio-reactive visualizer, for very calm BGM where the overlay distracts, and for all religious channels.
- OpenClaw should not bake spectrum bars, waveform graphics, equalizers, or audio meters into the static cover or Dreamina loop video; the app adds those during final render
- YouTube publish now auto-adds lyric CC captions for vocal releases that have saved lyrics. The main VM uses faster-whisper line timing against the final rendered audio, uploads the source-language `.srt`, translates the same cue lines with Codex, and uploads caption tracks for the supported languages: `ko`, `ja`, `en`, `es`, `vi`, `th`, `hi`, `fil`, `id`, `tr`, `pt-BR`, `pt-PT`, `fr`, `de`, `ar`, `zh-CN`, `zh-TW`. `AIMP_YOUTUBE_LYRICS_CAPTIONS_ENABLED=false` disables this, `AIMP_YOUTUBE_LYRICS_CAPTIONS_LANGUAGES` narrows the language list, and `AIMP_YOUTUBE_LYRICS_CAPTIONS_TRANSLATE=false` uploads only the source-language captions.
- Video render can burn line-level lyric subtitles into the final MP4 for releases with saved singable lyrics when OpenClaw/UI requests the lyric overlay. 불송 always uses the transparent-background `center_breath_serif` style in the center of the frame. Other lyric releases use `AIMP_VIDEO_LYRICS_OVERLAY_STYLE=auto`, which chooses between transparent-background `soft_bottom_fade` and `editorial_lower_left` from the channel/release context; HaruHaru, sundaze, Solwave Radio, and Tokyo Daydream Radio lean editorial lower-left, quieter BGM/OST/club/cinematic/BibliaCanto contexts lean soft bottom, and ambiguous custom releases use a stable per-release mixed choice. HaruHaru, sundaze, Solwave Radio, and Tokyo Daydream Radio photorealistic Japanese hip-hop/R&B/rap releases are vocal/lyrics still-image render contexts, and their normal visual render burns lower-left lyric subtitles over a still image with lower-right spectrum. The default `AIMP_VIDEO_LYRICS_ALIGNMENT_MODE=whisper` uses faster-whisper ASR word timestamps from the final rendered audio and maps them back to saved lyric lines, then applies ASS subtitles as the final ffmpeg pass. This is line-by-line timing, not word-by-word karaoke. `AIMP_VIDEO_LYRICS_ALIGNMENT_MODE=timeline` remains available only as a rough fallback. `AIMP_VIDEO_LYRICS_ALIGNMENT_MODEL` defaults to `tiny` so 1GB Oracle workers can run it; stronger desktop workers may set `base` or `small` for better lyric timing. `AIMP_VIDEO_LYRICS_OVERLAY_FONT` controls the sans-serif ASS font, and `AIMP_VIDEO_LYRICS_OVERLAY_SERIF_FONT` controls the centered serif style. Render workers should have CJK-capable fonts such as `fonts-noto-cjk` installed before using lyric burn-in. External render workers must advertise `faster_whisper` / `lyrics_alignment_modes` support before the app will assign Whisper lyric burn-in jobs to them, and CJK lyric overlay jobs additionally require advertised CJK font support. This prevents stale or misconfigured workers from producing timeline-only lyric videos or square-glyph Korean/Japanese/Chinese subtitles.
- Workspaces and queued `build_video` jobs now carry `release_vocal_mode`, `release_has_singable_lyrics`, and `release_vocal_mode_source`. The app infers this from the target YouTube channel first: 불송, BibliaCanto, HaruHaru, Tokyo Daydream Radio, sundaze, and Solwave Radio are treated as vocal/lyric channels; Soft Hour Radio, Storylight OST, Cinematic Pulse, and Club Bloom are treated as instrumental/no-lyrics channels. Unknown/manual channels fall back to saved track lyrics. Render workers that prefer no-lyric jobs use this flag when claiming work, and Whisper lyric jobs are only assigned to workers that advertise Whisper support.
- To keep the Oracle VM below the disk cap while faster desktop workers are active, the web app pauses new external render-worker claims at the local-video cleanup threshold. Defaults: `AIMP_LOCAL_VIDEO_CLEANUP_DISK_THRESHOLD_PERCENT=80` and `AIMP_RENDER_WORKER_CLAIM_DISK_SAFETY_MARGIN_PERCENT=0`, so new claims pause at about 80% disk usage and resume automatically after cleanup lowers usage. Cleanup first deletes public-retention-expired uploaded final MP4 files; if usage is still above threshold and `AIMP_LOCAL_VIDEO_CLEANUP_EMERGENCY_ENABLED=true`, it deletes the oldest already-uploaded local final MP4 files, including scheduled/private YouTube uploads, while leaving the YouTube video, audio, cover, thumbnail, and loop/source assets intact. This does not interrupt an already claimed render.
- External render upload retries are protected against stale partial files. When a queued job is claimed by a different worker, the app clears any leftover `storage/tmp/render-worker/JOB_ID.mp4.part`; when `/complete` fails size or checksum verification, the app also clears that partial so the next worker starts upload from byte zero.

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
- The background worker checkpoints the YouTube video id immediately after `videos.insert` succeeds, before slower thumbnail/localization/caption/playlist steps. If a post-upload step fails or the VM is interrupted, retries preserve the uploaded video id instead of uploading another duplicate. For interrupted retry jobs that never stored an id, the worker can adopt a recent matching upload from the same channel/title instead of re-uploading.
- Past scheduled-public YouTube uploads are treated as public in the web app. The background worker reconciles due `youtube_scheduled_publish_at` values into `youtube_public_at` / `youtube_published_at` and clears the stale scheduled marker so old dates do not keep showing as upcoming scheduled releases.
- Caption tracks are uploaded by the app for vocal releases with saved lyrics. The app still infers and sends `snippet.defaultAudioLanguage` when the title/description/tags clearly identify J-pop/K-pop/pop language; BGM/instrumental/no-vocal releases omit captions and audio language unless explicitly requested.
- Cafe/solo-piano playlist metadata now generates a Korean YouTube title, use-case description, timestamped tracklist, and music hashtags
- Approved metadata can be regenerated from the release action area, which creates a new draft that must be approved before re-upload
- OpenClaw can write and approve YouTube metadata through `scripts/openclaw-release approve-metadata`, passing title, multiline description, and comma-separated tags
- OpenClaw should use the external-render lookahead flow: prepare audio/cover/thumbnail/visual source, run `scripts/openclaw-release render-audio`, `approve-cover`, and `render-video` without `--wait`, then release the lock. Moving-video channels use a short provider loop video; HaruHaru, sundaze, Solwave Radio, and Tokyo Daydream Radio's photorealistic Japanese hip-hop/R&B/rap lane use the still cover image with `--allow-still-image-video --video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars --lyrics-overlay --lyrics-overlay-style editorial-lower-left`. Tokyo Daydream Radio's animated J-pop/city-pop/anime-pop lane still uses the provider loop-video flow. Club Bloom also uses the still cover image with `--allow-still-image-video --video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars`, but no lyric overlay by default. External render workers render video; when rendering completes and the MP4 is uploaded back, the app asks OpenClaw to approve metadata and queue publish through `scripts/openclaw-release publish-release --release-id RELEASE_ID --youtube-channel-title CHANNEL_TITLE --no-wait`. OpenClaw should not wait for a YouTube id after `upload_youtube` is queued; the app upload worker owns that background upload. Cinematic Pulse now follows the normal short-loop flow unless a human explicitly requests a still-image fallback.
- YouTube metadata can now store `ko`, `ja`, `en`, `es`, `vi`, `th`, `hi`, `fil`, `id`, `tr`, `pt-BR`, `pt-PT`, `fr`, `de`, `ar`, `zh-CN`, and `zh-TW` localized title/description drafts. Releases should provide every configured localization where possible; the publish flow sends the selected default metadata language and sends the other localized title/description drafts as YouTube localizations. YouTube supports Arabic as `ar`; it does not expose a separate `ar-EG` Egyptian Arabic localization code.
- Playlist Release YouTube titles now start with `[playlist]` for the default title and every localized title across all channels. Redundant playlist words like `플레이리스트` / `Playlist` are removed from the title body. Single Release titles remain unprefixed.
- Playlist/BGM YouTube titles should include a real listening situation or viewer intent directly in the title instead of only mood/genre wording. The use case must match the actual music and concept; do not default to study/work/walk/rest wording by habit.
- Korean YouTube metadata must not use the transliterated words `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`; use `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡` instead.
- OpenClaw can get final-order timestamps through `scripts/openclaw-release metadata-context` and should use `display_timestamp_lines` in YouTube descriptions when available, so awkward `A` / `B` suffixes are not shown while timestamps stay fixed. After audio render, metadata timestamps prefer the saved `rendered_timeline` snapshot from actual ffprobe source-file durations instead of recalculating from rounded DB track durations.
- When `AIMP_CODEX_METADATA_ENABLED=true`, the web `Generate Metadata` / `Regenerate Metadata Draft` actions ask the VM's local Codex CLI to write the YouTube title, description, and tags. The app limits this to one Codex run at a time and falls back to the template generator on CLI failure, timeout, or invalid JSON.
- OpenClaw playlist automation now uses step commands for continuous lookahead: upload/approve tracks, upload cover/thumbnail/visual source, render audio, queue external video render, then stop. Moving-video channels upload a provider loop video. HaruHaru, sundaze, Solwave Radio, and Tokyo Daydream Radio photorealistic Japanese hip-hop/R&B/rap releases skip loop-video upload and queue a 1080p `still_image` render with lower-left `editorial-lower-left` lyrics and lower-right `bars` spectrum. Tokyo Daydream Radio animated J-pop/city-pop/anime-pop releases still use the normal provider loop-video flow. Club Bloom skips loop-video upload too and queues a 1080p `still_image` render with lower-right `bars` spectrum only. Cinematic Pulse also needs a provider loop video by default, using photorealistic cinematic first-frame art, a `Seedance Mini 2.0` first-frame-only 10 second clip when those providers are used, final 720p render unless a human asks otherwise, and `bars` spectrum. The app asks OpenClaw again after the external worker completes render/upload so metadata/publish can finish while render workers process the next queued release. After a successful publish, the app also waits for the OpenClaw lock to clear and sends one compact backlog request as a fallback, so a partially prepared release stuck before video render, such as `audio_ready`, can continue instead of stalling the loop. OpenClaw can still run `scripts/openclaw-release auto-publish-single` for a human-approved end-to-end single upload. When `AIMP_YOUTUBE_SCHEDULE_PUBLIC_ENABLED=true`, the app uploads each video as a scheduled public release in `AIMP_YOUTUBE_SCHEDULE_TIMEZONE`; scripture releases on `BibliaCanto` have two app-managed daily slots, Old Testament at 07:00 and New Testament at 16:00; Buddhist scripture-inspired `불송` releases are scheduled daily at 07:00. Solo-piano BGM releases route to `Soft Hour Radio`; mainstream J-pop/Japanese pop/Tokyo pop and Japanese rap/hip-hop/R&B releases route to `Tokyo Daydream Radio`; Korean/K-pop vocal releases route to `HaruHaru`; playful no-vocal Japanese-style game/anime OST, arcade/fantasy-game BGM, and happy amusement park/theme-park BGM routes to `Storylight OST`; no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, and game-focus music routes to `Cinematic Pulse`; no-vocal EDM/house/techno/trance/workout/night-drive music routes to `Club Bloom`; Old Testament and New Testament Bible scripture-inspired music routes to `BibliaCanto`; Buddhist scripture-inspired vocal music routes to `불송`; English/American pop playlist lanes route to `sundaze`, including pop-rock, country pop, Americana pop, indie/bedroom/alt-pop, singer-songwriter/folk-pop, soft rock, pop-punk, Y2K/recession pop, disco/funk pop, Afrobeats, Afropop, and Amapiano-pop; Latin/Spanish pop routes to `Solwave Radio`. MusicSun is manual-only and excluded from continuous automation. Signal Room/Signal Desk/Midnight Cue names are retired unless explicitly revived.
- OpenClaw backlog request cooldown suppresses duplicate Slack requests that have not produced an app-side backlog state change. Merely finishing an OpenClaw lock no longer bypasses cooldown; a new release, workflow-state change, or newly finishable render/publish update can bypass it. Finishable work such as `metadata_review`, `publish_ready`, or retryable non-quota `youtube_upload_failed` is prioritized before creating new backlog for the shortest scheduled-through channel. Publish should not be blocked only because a rendered release is shorter than one hour or below its preferred target; OpenClaw should publish already-rendered `publish_ready` releases with `publish-release --no-wait` and reserve one-hour filling for pre-render production. `publish_queued` is app-owned and should not make OpenClaw wait for a YouTube id.
- YouTube API upload quota blockers are not OpenClaw production blockers. If an app-managed upload fails or stalls because of `Video Uploads per day`, `rateLimitExceeded`, `quotaExceeded`, HTTP 403 quota, or HTTP 429 rate limit, OpenClaw should not retry publish in the same pass and should not stop. The rendered release stays in the app for the next quota window, while OpenClaw continues with the next eligible unfinished workspace or new playlist assets.
- OpenClaw auto-publish helpers now refuse to re-upload an already published release unless `--allow-reupload` is explicitly passed, preventing accidental duplicate YouTube uploads.
- OpenClaw should create or select the target app release before opening Suno. Use `scripts/openclaw-release create-release` for fresh Single/Playlist Release work, keep the returned `release.id`, and upload later Suno outputs with `--release-id`.
- `scripts/openclaw-release upload-audio` also auto-approves tracks when the target release is a Playlist Release. Use `--pending-review` only when one-by-one playlist review is explicitly desired.
- OpenClaw should provide standalone playlist track titles, not Suno pair labels. The helper also rewrites trailing A/B, 1/2, and older `Morning` / `Evening` style variants into natural standalone display titles.
- BGM/background/study/sleep/cafe production defaults to instrumental music. Soft Hour Radio is piano-first by default: OpenClaw should generate roughly the first 10 minutes as new solo piano / felt piano / quiet piano tracks and upload those tracks first. The app prefers previous same-channel similar solo-piano tracks for the back half; if there are not enough piano tracks to approach one hour, it may fill the remaining back half with similar existing Soft Hour music instead of blocking. Do not generate new lofi beats, guitar, Rhodes, strings, pads, drums, percussion, jazz trio, bossa, or mixed-instrument BGM for Soft Hour unless the human explicitly changes this rule. For Soft Hour Radio or other no-vocal Suno work, OpenClaw must follow `docs/suno-v55-instrumental-format.md`: enable Instrumental when available, use bracket-only metatag lines in Suno's lyrics/custom-lyrics field, and upload that exact file with `--lyrics-file`. Soft Hour titles should naturally mention piano/solo piano and a real use case such as study, work, reading, sleep, cafe, focus, or relaxation when the fresh lead block is piano. J-pop/K-pop/pop/Japanese pop/anime-pop production defaults to vocal songs with lyrics. OpenClaw should not generate instrumental/no-vocal pop-family tracks unless explicitly asked, and should upload lyrics for every pop-family track with `--lyrics` or `--lyrics-file`.
- For vocal Suno work, OpenClaw should set Suno `More options` / `Vocal gender` when the lead vocal is known: `male` for male lead and `female` for female lead. Mixed-gender, duet, group/choir, alternating male/female, or intentionally unspecified lead vocals should leave Vocal Gender unselected. The setting should stay stable across retries for the same track unless the vocal concept changes.
- Suno work should fill Advanced Options excluded styles with artificial noise blockers on every channel unless the human explicitly asks for vinyl/LP/noise texture: white noise, static noise, vinyl crackle, record crackle, LP crackle, tape hiss, cassette hiss, analog hiss, noise floor, lo-fi noise, old record noise, dust noise, crackle, and hiss. No-vocal work should also include vocal-related exclusions such as vocals, voice, singing, humming, choir, spoken word, narration, rap, ad-libs, scat, vocal chops, and lyrics. Lyric/vocal work should also include vocal-clarity exclusions such as muddy vocals, muffled vocals, washed-out vocals, distant vocals, buried vocals, unclear lyrics, heavy reverb, excessive reverb, large echo, concert hall echo, arena reverb, stadium reverb, live concert vocals, crowd ambience, and room boom.
- Suno generation guidance now explicitly avoids producer tags and specific artist references in lyrics, bracketed metatags, style, prompts, tags, and excluded styles. Known blocked example: `lowlight` can be rejected as a producer tag, so OpenClaw should rewrite it to generic wording like `low-lit`, `dim`, `shadowy`, or `soft ambient` before retrying.
- Playlist automation now avoids putting duration caps or lower-bound duration phrases such as `less than 4 minutes`, `under 4 minutes`, `at least 2 minutes`, `minimum 2 minutes`, or `2 minutes or longer` into Suno prompts, lyrics, style strings, or bracketed metatags unless a human explicitly asks for that wording. Each Suno generation should be treated as a credit-bearing full song/cue, not a short sketch. OpenClaw should prompt structurally for a complete around-4-minute-or-longer result: natural intro, developed first and second verse/section flow, chorus or central motif returns where appropriate, bridge/breakdown/rap-sung contrast or instrumental variation when useful, final lift, and a resolved ending. Vocal songs need enough written lyrics to support that structure instead of short verse/chorus fragments. Instrumental/no-vocal work needs longer bracket-only section metatags with real development, not a few short arrangement notes. Suno has no guaranteed minimum-duration field, so validate the generated file after download. Tracks shorter than 4:00 are still valid uploads when they fit the release; playlist tracks from 1:00 to 1:59 should be uploaded/used and recorded for later analysis; only stop and report tracks under 1:00 unless the channel-specific workflow says otherwise. Complete 5+ minute tracks are allowed on every channel.
- OpenClaw helper commands now reject pop-family uploads with empty lyrics before publish unless the concept explicitly says BGM/instrumental/no-vocal. YouTube metadata approval also appends a visible public hashtag line when OpenClaw/Codex provides API tags but forgets description hashtags.
- YouTube metadata generation and approval now filters AI/process/tool tags from API tags and public hashtags on every channel. Avoid `AIMusic`, `AI music`, `AI generated`, `AI visualizer`, `Suno`, `OpenClaw`, and `Codex`.
- OpenClaw generation guidance now requires track-level variation inside a release: distinct prompts, titles, lyrics concepts, chorus hooks, and preferably per-track Suno style/settings, while keeping the overall channel/release mood coherent.
- BibliaCanto should rotate Bible release-level music lanes across uploads, but the lane must be trendy and secular-pop-adjacent, such as scripture hip-hop, Bible R&B, K-pop-inspired scripture pop, scripture rap-pop, trap-soul scripture songs, boom-bap Bible rap, alt-R&B scripture songs, neo-soul scripture songs, Afropop/Amapiano-pop scripture songs, dark street-pop scripture, or synth-pop scripture songs. New BibliaCanto music must not sound like Gospel music, worship, holy worship, church choir, hymns, praise band, CCM, congregational singing, piano worship ballads, or church-service music; OpenClaw should add those terms to Suno excluded styles. 불송 is hip-hop-first by default: new releases should normally use 불교 힙합, 불경 힙합, mindful hip-hop, Korean Buddhist rap, mellow boom bap, Buddhist hip-hop soul, or restrained Buddhist trap-soul. Use R&B, jazz, acoustic, pop, lo-fi, or cinematic lanes only when the human explicitly asks or when finishing an already-started release in that lane. One release must stay in one coherent lane so the YouTube title and description can truthfully name that genre. Public 불송 titles must include the verified Buddhist source/chapter/section when known, or the verified theme when an exact chapter is not known; do not use generic `불경` alone when a source/theme exists, do not invent scripture chapter/verse coverage, and do not waste Korean/default title space on redundant labels such as `한국어 랩` or `한국어 힙합`. Public 불송 titles, thumbnail phrases, descriptions, and tags must avoid obscure coined genre labels; use plain wording such as `반야심경 랩`, `금강경 힙합`, `법구경 힙합`, `정어와 구업 힙합`, `불교 힙합`, `불경 힙합`, `Buddhist hip-hop`, or `Korean Buddhist rap`. 불송 Suno prompts/excluded styles should explicitly avoid trot, ppongjjak, old Korean cabaret-pop, trot vocal ornaments, and accordion/brass trot clichés.
- Playlist workspaces no longer auto-queue audio render just because the target duration is reached. The operator or OpenClaw must explicitly start render after all intended tracks have finished uploading.
- Audio/video rendering now snapshots the ordered track ids used for the render and stores a `rendered_timeline` based on actual probed source-file durations. If OpenClaw or the UI adds tracks while audio/video render is running, the stale render is rejected and a fresh render is queued or required before publish, preventing YouTube timelines from outlasting the actual video.
- Audio render supports optional playlist order randomization. The web UI asks whether to randomize before `Render Mix` / `Re-render Audio`, and the API accepts `random: true` (`randomize_order: true` is still accepted for compatibility). When randomized, the app saves the shuffled order before render, so final order, rendered audio, and description timestamps stay aligned. For Soft Hour Radio, randomization preserves the fresh solo-piano lead block before any auto/manual reused back-half tracks so the newly generated first 10 minutes stays at the front.
- Playlist automation requires a final uploaded 16:9 cover image before YouTube upload. The app's generated draft cover is only a manual placeholder.
- Full OpenClaw playlist publishing now expects two final 16:9 images for normal channels: a cleaner video cover/first-frame via `--cover` and a YouTube thumbnail via `--thumbnail`. Reusing the cover as the thumbnail is only allowed with `--allow-cover-as-thumbnail`. Exception: `불송` may use one respectful contemporary Buddhist music visual package for cover, thumbnail, and first frame, but it should rotate fresh subjects instead of repeating a fixed old devotional scene.
- Visual asset rules are channel-specific and documented in `docs/openclaw-channel-profiles/`. OpenClaw should choose the channel first, read the returned `concept_doc` for next-release planning and `profile_doc` for visual execution, and apply human visual requests consistently to cover, thumbnail, loop video, or still-image render. Do not put YouTube channel names, logos, or brand labels into covers, thumbnails, first-frame images, or loop videos on any channel. If text is useful, use only a short natural genre, style, use-case, or passage phrase such as `J-POP`, `J-RAP`, `TOKYO R&B`, `LOFI`, `TECH HOUSE`, `CINEMATIC ORCHESTRA`, `Genesis 1:1-5`, or `법구경 힙합`, integrated into the artwork without detached badges or hard boxes. Text on thumbnails/covers/first-frames must have a transparent background: letters sit directly on the artwork, with readability from font weight, color, subtle shadow, thin outline, or local contrast only; reject black boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, stickers, badges, pills, capsules, and any filled label shape behind text. Provider loop videos must preserve that transparent-text treatment and must be rejected/regenerated if Gemini, Dreamina, or Seedance adds a black/semi-transparent text panel, gradient scrim, sticker, badge, pill, capsule, rectangle, or any filled label shape behind existing first-frame text. Put that style/passage phrase in upper-left safe negative space when possible so it does not collide with lower-left lyric overlays. Most generated visuals should stay animated/anime/illustrated/stylized, not photorealistic or live-action. Tokyo Daydream Radio is now a split exception: animated J-pop/city-pop/anime-pop releases keep animated/anime/illustrated covers and provider loop videos, while Japanese rap/hip-hop/R&B/neo-soul releases should alternate in as photorealistic friend-taken Japanese street/lifestyle still images with no provider loop video and app-managed lower-left lyrics plus lower-right spectrum. Soft Hour Radio is now an explicit exception: it should use high-resolution photorealistic quiet solo-piano BGM environments by default, preserving the existing calm cafe/study/work/sleep/reading background feeling, and provider loop videos must use a static locked-off camera with no camera movement at all. HaruHaru is an explicit exception: it should use text-free photorealistic Korean lifestyle still images by default, visible adult faces allowed, friend-taken Hongdae/Seoul street snapshot framing with hip adult streetwear and slight motion/focus softness preferred over straight-on AI-beauty or idol-style close-ups, and app-managed lower-right spectrum plus lower-left lyrics during `still_image` render. sundaze is also an explicit exception: it must use photorealistic English/American friend-taken smartphone lifestyle still images by default, visible adult faces allowed, natural road-trip/rooftop/cafe/beach/downtown/country/Americana/indie-room/festival/night-drive scenes preferred, no anime/illustrated/stylized/abstract/generic graphic covers for normal releases, and app-managed lower-right spectrum plus lower-left lyrics during `still_image` render. Solwave Radio is also an explicit exception: it should use photorealistic Latin/Spanish friend-taken smartphone lifestyle still images by default, visible adult faces allowed, one short integrated Latin/Spanish lane phrase on the thumbnail when useful, and app-managed lower-right spectrum plus lower-left lyrics during `still_image` render. Club Bloom is also an explicit exception: it should use text-free photorealistic friend-taken smartphone/Instagram nightlife still images by default with attractive clearly adult women in revealing YouTube-safe club outfits in club/bar/lounge/festival settings, no provider loop video in normal automation, and app-managed lower-right spectrum only during `still_image` render. Cinematic Pulse is also an exception: it should use original photorealistic cinematic film-still / premium movie-poster realism for cover/first-frame art with one tasteful upper-left style phrase such as `MOVIE OST`, `CINEMATIC ORCHESTRA`, `FILM SCORE`, or `TRAILER MUSIC`, then create a subtle provider loop video from that first frame and final render with clean `bars` spectrum. `불송` is also an exception: use respectful contemporary Buddhist music visuals by default, rotating natural adult temple-stay/Hongdae streetwear practitioners with headphones or earbuds, Buddha/statue plus modern listener scenes, duet pairs for duet songs, or animated/stylized hip monk concepts. Avoid stale Buddha-only, generic sutra-desk monk, temple/lotus background-only, and statue-wallpaper images. Its one visual package may contain one short Korean passage/theme + hip-hop style phrase, but never `불송`.
- HaruHaru visual prompts should be photorealistic, non-explicit, and adult-only: default to a stylish adult Korean/Korean-fashion woman in hip streetwear on or near a Hongdae street, record shop, small bar, late-night cafe exterior, club-side alley, subway exit, Itaewon night street, rainy crosswalk, rooftop after dark, streetwear boutique, or similar Seoul nightlife/street setting. Handsome stylish adult men or tasteful adult couple/friend pairs are allowed when the concept supports it. Do not hide faces by default, but avoid tight straight-on face-filling portraits; prefer natural side/three-quarter/candid angles, medium or farther framing, slight phone-photo imperfection, mild motion blur or focus shake, and an ordinary friend-taken Korean hip-hop/R&B street mood for hip-hop/R&B/trap/boom bap lanes. Avoid mixing city-pop visual/music cues into non-city-pop HaruHaru releases; if an existing or explicitly requested HaruHaru release is city-pop, keep its music/backfill city-pop-related instead of mixing unrelated hip-hop/R&B/ballad tracks. Avoid generic idol-pop, school uniforms, celebrity/idol-member likenesses, and glossy studio/fashion-campaign styling. Do not bake in lyrics/spectrum/logos/title text. Queue `scripts/openclaw-release render-video --release-id RELEASE_ID --allow-still-image-video --video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars --lyrics-overlay --lyrics-overlay-style editorial-lower-left`.
- sundaze visual prompts should be photorealistic, non-explicit, and adult-only: default to clearly English/American pop-coded lifestyle still images with stylish adult women/men, tasteful adult couple/friend scenes, open highways, summer car stops, city rooftops, beach boardwalks, cafe terraces, country roads, Americana diners, bedroom-pop rooms, indie record shops, festival lawns, neon night drives, or casual downtown walks. Prefer friend-taken smartphone/Instagram framing: natural side or three-quarter angles, candid smiles/laughs, medium or farther framing, slight crop/focus/motion imperfection, and enough environment to feel real. Avoid anime, illustrated, stylized, abstract, generic graphic covers, studio portraits, glossy fashion campaigns, tight straight-on AI-beauty close-ups, minors, teen-coded styling, and celebrity lookalikes. Do not bake in lyrics/spectrum/logos/title text. Queue `scripts/openclaw-release render-video --release-id RELEASE_ID --allow-still-image-video --video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars --lyrics-overlay --lyrics-overlay-style editorial-lower-left`.
- Solwave Radio visual prompts should be photorealistic, non-explicit, and adult-only: stylish adult Latina/Latino subjects, tasteful adult couple/friend pair, coastal cafe terrace, warm city street after rain, beach road at golden hour, rooftop fiesta, tropical rain window, plaza dance night, seaside drive, open-air bar, summer balcony, night-market street, or resort walkway. Prefer casual friend-taken phone-photo/Instagram framing: side or three-quarter angle, phone-glance/candid moment, medium or farther framing, slight crop/motion imperfection, and enough environment to feel real. Avoid professional photographer shoots, studio portraits, glossy fashion campaigns, tight straight-on AI-beauty close-ups, doll-like symmetry, and over-retouched model faces. Do not hide faces by default, do not use minors/school uniforms/celebrity likenesses, and do not bake in lyrics/spectrum/logos/title text. Queue `scripts/openclaw-release render-video --release-id RELEASE_ID --allow-still-image-video --video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars --lyrics-overlay --lyrics-overlay-style editorial-lower-left`.
- Club Bloom visual prompts should be photorealistic, adult-only, and YouTube-safe: use the same natural friend-taken smartphone/Instagram still-image feel as HaruHaru, but place the scene in a club, bar, lounge, rooftop club, beach club, pool party, festival VIP, DJ booth, dance floor, neon city terrace, or yacht/harbor party. Prefer attractive clearly adult women in revealing club fashion, natural side/three-quarter angles, medium or farther framing, visible but not face-filling subjects, slight motion/focus imperfection, and candid party energy. Keep the mood hot, energetic, and click-stopping without full nudity, exposed nipples/genitals, sexual acts, minors, teen-coded styling, school uniforms, fetish framing, celebrity likenesses, protected brands, porn-style composition, glossy fashion-campaign styling, or centered AI-model headshots. Do not bake in lyrics/spectrum/logos/title text. Queue `scripts/openclaw-release render-video --release-id RELEASE_ID --allow-still-image-video --video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars` without lyric overlay. `BibliaCanto` renders with `video_spectrum_overlay_style=none`; `불송` renders with very low-motion `calm-bars`.
- Channel-name visual labels are retired on every channel. If OpenClaw sees old releases with `Tokyo Daydream Radio`, `HaruHaru`, `BibliaCanto`, `불송`, or any other channel name baked into a cover, thumbnail, or loop video, treat that as legacy style and avoid repeating it in new assets.
- OpenClaw channel visual rules are also split into `docs/openclaw-channel-profiles/`. OpenClaw can run `scripts/openclaw-release channel-profile` to infer the target channel and get the exact profile doc to read before making visual assets.
- OpenClaw channel concept planning is now split into `docs/openclaw-channel-concepts/`. The next-release planner chooses the channel, then reads that channel's concept doc to avoid recent repetition before it reads the visual profile.
- OpenClaw should generate static cover/thumbnail images with OpenAI GPT Image models, preferably `gpt-image-2` when available, not Dreamina. Dreamina is reserved for the moving visual clip.
- `Tokyo Daydream Radio` thumbnails may use large `J-POP` or a short scene/style phrase, but must not include `TOKYO DAYDREAM RADIO` or other channel branding. Do not add `1 HOUR`, `60 MIN`, `1時間`, or duration badges. The main default/requested subject must stay centered; text should fit around it without pushing it sideways.
- OpenClaw should pass a short provider-generated MP4 via `--loop-video` for normal moving-video publish automation while a provider is available and must tag it with `--loop-video-provider gemini|dreamina|seedance`; the app stores this in `loop_video_provider` and `loop_video_history[].provider`. HaruHaru, sundaze, Solwave Radio, Tokyo Daydream Radio photorealistic Japanese hip-hop/R&B/rap releases, and Club Bloom are explicit still-image exceptions: do not upload `--loop-video`; pass `--allow-still-image-video --video-render-source-mode still_image`. Tokyo Daydream Radio animated J-pop/city-pop/anime-pop releases still use a provider loop video when available, but may use the human-approved still-image fallback when Dreamina/Seedance is blocked by credit/account/quota/CAPTCHA/browser/provider failure and Gemini has already used all 3 successful videos in the active 24 hour window. The video render API rejects renders without an uploaded loop video unless `allow_still_image_fallback` is explicitly set for HaruHaru, sundaze, Solwave Radio, Tokyo Daydream Radio photorealistic Japanese hip-hop/R&B/rap releases, Club Bloom, or a human-approved exception. Storylight OST is stricter by default: it should use a provider-generated loop MP4, but provider-exhausted fallback can use still-image render rather than staying stuck. Cinematic Pulse also uses a provider loop MP4 by default, with `--video-render-source-mode loop_video --video-render-resolution 720p --video-spectrum-overlay-style bars` unless provider exhaustion forces the approved still-image fallback. Browser automation should try Gemini first by clicking `Create image` / the creation entry that accepts image+prompt, attaching the cover/first-frame image, generating video, downloading the MP4, and counting only successful Gemini video outputs toward the 3 videos per 24 hour quota. Gemini prompts should not mention duration; upload the generated Gemini MP4 as-is after inspection. Before clicking Generate in Gemini, Dreamina, or Seedance, OpenClaw must run `scripts/openclaw-release provider-video-start --release-id RELEASE_ID --first-frame FIRST_FRAME --provider PROVIDER`. If Gemini is already generating for the same release and first-frame image, OpenClaw must wait and keep the OpenClaw lock alive; it must not start Dreamina/Seedance for the same image until `provider-video-status` shows no remaining wait. If Gemini has no usable MP4 after 20 minutes, mark it `timed_out` with `provider-video-finish`, then start Dreamina/Seedance. After the 3rd successful Gemini video, OpenClaw should use Dreamina/Seedance until 24 hours have passed from that 3rd generation. If Dreamina/Seedance fails, OpenClaw should not create a local motion-loop workaround; it should try Gemini if quota is available, or use the approved still-image fallback if Gemini quota is exhausted. Copyright/policy blocks before Gemini creates a video do not count and should be retried with safer prompts up to 10 times before falling back to Dreamina/Seedance. Dreamina/Seedance normally uses `Seedance Mini 2.0`, first-frame/start-frame only, no Omni Reference, no last-frame/end-frame reference, `16:9`, `720p`, and exactly `10 seconds` through UI controls. Do not upload both first and last frames, because Dreamina switches that setup back to `Seedance 2.0 Fast`. The app smooth loop crossfade defaults to 1.5 seconds, but Gemini-tagged loop videos use 2.0 seconds because Gemini clips are usually around 10 seconds. The first-frame image should be the cover or a dedicated first-frame image, not a text-heavy YouTube thumbnail, because large generated title text can flicker or disappear. The generated clip should end close to its opening composition so it can be reused across the full release.
- If Seedance/Dreamina's duration control is hidden when the screen opens, OpenClaw must gently drag/scroll the settings/control row to the right until the duration option is visible, then confirm exactly `10 seconds` before Generate. `Seedance Mini 2.0` should be set to `10 seconds`; if the UI offers `5 seconds` or `10 seconds`, always choose `10 seconds`. Do not create an initial 5 second or other wrong-duration clip to reach the correct setting.
- Existing releases that already have loop videos remain valid. The `Seedance Mini 2.0` 10-second rule is for new OpenClaw-created Seedance/Dreamina clips going forward. Gemini clips are uploaded as generated.
- Loop-video upload validates only that the file is readable video. The app does not reject low-motion clips or alternate clip lengths; visual quality and the normal 10 second Seedance/Dreamina setting are handled by human/OpenClaw review before render/publish.
- Gemini/Dreamina/Seedance prompts must preserve composition and any short style/passage phrase already present, but must not ask providers to add or preserve channel names. Prompt visible state instead of conceptual labels: avoid words like `playlist`, `music visual`, `seamless loop`, `repeat`, `cyclic`, and scripture-framework terms that can imply multiple narrative stages. Prefer positive fixed-shot wording such as `single fixed camera shot`, `locked-off camera`, `one uninterrupted calm environmental take`, and `same composition from first to last frame`.
- Gemini/Veo provider logos or watermarks, usually in the bottom-right corner, are allowed provider artifacts and are not a reason to regenerate an otherwise valid loop video. The no-logo rule only forbids OpenClaw-requested/generated extra logos, UI, brand marks, or unrelated text.
- Gemini/Dreamina/Seedance content-safety or copyright rejections are retried with sanitized prompts. Gemini copyright/policy blocks do not count against the 3 successful-video quota unless Gemini actually creates a video. If Dreamina/Seedance cannot create a clip, OpenClaw should try Gemini again when quota is available. If all 3 Gemini videos are already spent and Dreamina/Seedance is unavailable because of credit/account/quota/CAPTCHA/browser/provider failure, use the approved still-image fallback with `--allow-still-image-video --video-render-source-mode still_image` instead of deferring the release.
- Long video rendering now encodes the reusable short visual unit once, then extends that unit with ffmpeg concat stream-copy for the final video instead of re-encoding every frame of a long-form release.
- The web release detail UI now supports direct upload/replace actions for video cover, text YouTube thumbnail, and loop video as separate assets.
- Already-uploaded releases can replace the loop video from the release detail UI. Replacing the loop video marks the release as needing a new video render before re-upload while keeping the previous YouTube video id visible until the new render starts.
- After a successful YouTube upload, the app normally keeps the long final rendered local MP4 for `AIMP_LOCAL_VIDEO_CLEANUP_PUBLIC_RETENTION_DAYS` days after the video is actually public (default `3`). It records `local_video_retained_after_youtube_upload` and keeps `output_video_path` during the retention window so a recently uploaded video can be inspected or re-used without re-rendering.
- The app keeps disk usage under control by deleting final rendered local MP4 files, oldest first, then recording `local_video_deleted_after_youtube_upload`, clearing `output_video_path`, and leaving the YouTube video id/link as the watch surface. Normal cleanup only deletes public-retention-expired uploaded YouTube videos. Emergency cleanup runs only while disk usage remains above `AIMP_LOCAL_VIDEO_CLEANUP_DISK_THRESHOLD_PERCENT`; with `AIMP_LOCAL_VIDEO_CLEANUP_EMERGENCY_ENABLED=true`, it may delete already-uploaded local final MP4 files before the public-retention window expires, subject to `AIMP_LOCAL_VIDEO_CLEANUP_EMERGENCY_MIN_UPLOADED_AGE_HOURS` (default `0`). This cleanup does not delete rendered audio, cover, thumbnail, or short Gemini/Dreamina/Seedance loop/source videos. The check runs periodically and immediately after OpenClaw loop-video uploads, external render-worker chunk uploads, and external render completion.
- Workspace API responses now include `youtube_channel_id` and `youtube_channel_title` next to `youtube_video_id`, so the dashboard and OpenClaw can confirm which channel a published release was uploaded to.
- Workspace lists are API-sorted by Published order: unpublished releases first, then scheduled YouTube publish time when present, otherwise actual YouTube publish/upload time, otherwise release creation time. The web UI uses that order by default for all-channel and per-channel views, while offering per-view toggles for Published, Updated, and Created sorting in either direction.
- Slack channel routing is intentionally split. `AIMP_SLACK_OPS_CHANNEL_ID` must point to `#all-ai-music-playlist-generator` / `C0ATYMCMLLE` for operational notices such as render-worker claim/complete, timeout requeue, and YouTube publish-complete. Those notices attach the release thumbnail/cover when available, resize Slack preview artwork to a `480` px max edge by default, and omit internal job IDs from visible Slack text. `AIMP_OPENCLAW_SLACK_CHANNEL_ID` points to `#openclaw` / `C0AVBUYP150` for `OPENCLAW_RUN:` command traffic only. Do not send render-worker status notices to `#openclaw`.
- The same ops channel can receive read-only Codex answers for human messages. With `AIMP_SLACK_CODEX_QA_ENABLED=true`, messages from real Slack users in `AIMP_SLACK_CODEX_QA_CHANNEL_ID` or, if unset, `AIMP_SLACK_OPS_CHANNEL_ID` are queued as `slack_codex_qa` jobs. The worker runs the local Codex CLI in read-only mode and posts only the final answer back in the source thread. It ignores bot messages and Slack subtypes, so app progress notices do not trigger self-replies.
- The app can send a "next release" Slack request to the OpenClaw channel after a release is uploaded or scheduled. Configure `AIMP_OPENCLAW_SLACK_CHANNEL_ID`; the web UI shows `Request Next Playlist`, and `AIMP_OPENCLAW_AUTO_REQUEST_NEXT_ON_PUBLISH=true` sends a compact fallback request after successful YouTube upload with per-video dedupe. In VM-render lookahead mode this publish fallback waits until the OpenClaw lock is clear and uses the backlog request shape, not the old long publish prompt. `AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED` is optional and should remain disabled in conservative VM-render mode. If YouTube rejects a 14+ minute video because the account is not phone/account verified for long uploads, the app now keeps the rendered release for later retry. `AIMP_OPENCLAW_AUTO_REQUEST_NEXT_MAX_UPLOADS=N` caps the loop after N successful YouTube uploads; `0` means unlimited. Human Slack messages in the configured OpenClaw channel such as `OpenClaw 자동화 멈춰` stop the app from sending more automatic `OPENCLAW_RUN:` requests, and `OpenClaw 자동화 다시 시작` resumes. Real app-originated OpenClaw task messages are prefixed with `AIMP_OPENCLAW_SLACK_TRIGGER_PREFIX` (default `OPENCLAW_RUN:`). Slack event routing and mention-only behavior belongs in the Slack App/OpenClaw listener configuration, not in the music release skill docs.
- OpenClaw's continuous automation entry point is `docs/openclaw-backlog-queue.md`, then `docs/openclaw-next-release-planner.md`. In normal VM-render mode, OpenClaw should finish one release end-to-end before starting another: choose the next non-excluded channel, create/upload assets, render audio, render video on the VM app, wait for completion, approve metadata, and publish. The planner reads `/youtube/status`, rotates connected non-excluded channels, reads the selected channel's concept planner/profile, avoids recent concept repetition, chooses the next channel/concept, then follows the production/publish instructions.
- Empty duplicate workspace shells are cleanup, not blockers. If a `collecting` Playlist Release has 0 tracks and no audio, cover, thumbnail, or loop video while the same title/channel already has an uploaded or scheduled release, the backlog summary auto-archives it with `empty_duplicate_shell_auto_archived=true` and OpenClaw should skip it instead of stopping for human confirmation. Similar already-published concepts should guide variety, but must not stop production by themselves.
- New release channel priority now favors connected automated channels with the shortest future scheduled-public horizon, not the highest existing backlog. The intended behavior is date-balanced: all automated channels should have the earliest upcoming date covered before any channel is pushed further out to later dates, so a channel scheduled through May 21 is filled before one already scheduled through May 27. Slack `OPENCLAW_RUN:` messages stay compact and do not inline backlog snapshots; OpenClaw must fetch channel priorities, unfinished counts, scheduled-through dates, blockers, and lock state through the app API, such as `scripts/openclaw-release openclaw-backlog-status`, before choosing work.
- OpenClaw must call `scripts/openclaw-release openclaw-lock-start`, refresh with `openclaw-lock-heartbeat` every 1-2 minutes, and call `openclaw-lock-finish` when done/blocked. The app stores this lock in `storage/openclaw-runtime-state.json`; the backlog scheduler will not send another Slack request while the lock is active, and stale locks expire through `AIMP_OPENCLAW_LOCK_TTL_SECONDS`.
- BibliaCanto uses the deployed web app as the Bible scripture sequence source of truth for both Old Testament and New Testament branches. The app stores `storage/openclaw-scripture-sequence.json` on the VM and exposes OpenClaw helper commands through `scripts/openclaw-release openclaw-scripture-status`, `openclaw-scripture-reserve`, `openclaw-scripture-complete`, and `openclaw-scripture-fail`. OpenClaw must create the release, reserve the next app-owned passage before Suno generation, and mark it scheduled/published after upload. OpenClaw must not compare against a local scripture ledger or block only because title wording differs. 불송 is a separate Buddhist scripture-inspired channel and does not use the Bible scripture ledger.
- Track uploads now accept optional lyrics/content notes, Suno style/settings, and Suno excluded styles/negative tags. These are stored in track metadata and exposed through release/timeline context for later thumbnail, loop-video, metadata, remake, and standalone single workflows.
- HaruHaru, Tokyo Daydream Radio, sundaze, and Solwave Radio now require one explicit genre lane per release, such as K-pop hip-hop, Korean R&B, explicit HaruHaru city-pop, Tokyo animated J-pop, Tokyo city-pop, anime-pop, Japanese rap, Japanese hip-hop, Tokyo R&B, Japanese neo-soul, sundaze Pop R&B, dance-pop, country pop, Americana pop, indie pop, Afropop, Amapiano-pop, Pop Latino, reggaeton pop, bachata pop, or Latin R&B, with that lane named naturally in title/metadata and reflected in Suno style prompts. For HaruHaru, Korean/default titles should use a click-led hook shape such as `[playlist] 나랑 데이트 할래? | 데이트하기 전 기분 좋아지는 K-POP 힙합 노래모음`: short tasteful emotional hook first, then truthful situation plus genre. Tokyo Daydream Radio alternates visual systems when practical: animated/anime moving-video for J-pop/city-pop/anime-pop lanes and photorealistic friend-taken Japanese street/lifestyle still-image renders for Japanese rap/hip-hop/R&B/neo-soul lanes. The cover/thumbnail mood must match the hook while remaining text-free by default where the channel profile says so. New default HaruHaru planning should favor hip-hop/R&B/trap/boom bap/neo-soul/dark street-pop, but if a release is explicitly or already city-pop then reuse/backfill should stay city-pop-related; non-city-pop HaruHaru releases must not be backfilled with city-pop tracks. HaruHaru, Tokyo Daydream Radio, sundaze, and Solwave Radio reuse/backfill now require detailed-lane token matching, such as boom-bap to boom-bap, Tokyo R&B to R&B/neo-soul, country-pop to country-pop, and reggaeton to reggaeton/urbano, instead of broad `K-pop` / `J-pop` / `English pop` / `Latin pop` overlap; if matching material is exhausted, do not force unrelated same-channel pop to reach one hour, and preserve the fresh/same-lane lead block before reused back-half tracks even if randomization is requested.
- Track intake now probes uploaded local audio duration with ffprobe and rejects empty audio uploads. Playlist audio render also validates every source file before concat and fails if the rendered output is materially shorter than the source tracks, preventing 0-byte or corrupt uploads from being published as short YouTube videos.
- OpenClaw helper audio uploads retry each file up to 3 times. Playlist automation continues uploading later tracks after a failed file, posts a Slack warning with the failed titles/files, and stops before render/publish until the failed sources are re-uploaded.
- YouTube metadata timelines use `HH:MM:SS` for one-hour-plus releases, starting at `00:00:00`, so timestamps after one hour remain linkable. Normal automated non-scripture playlist releases ask OpenClaw for `600` seconds / about 10 minutes of new approved audio; if Suno is unstable, OpenClaw should upload only the usable tracks already made and call audio render instead of waiting or burning credits on retries. Before playlist audio render, the app tries to extend the base block to roughly `3600` seconds / 60 minutes or longer by reusing previous same-channel, similar-genre tracks that appeared in the back half of already uploaded YouTube videos. Track intake now caches reusable deterministic `genre_tokens` in each track's metadata from title/prompt/style/tags/genre fields, and the reuse matcher uses those cached tokens instead of reparsing every candidate track on every workspace; legacy tracks are lazily cached the first time they are inspected. Lyrics are intentionally excluded from genre-token extraction so lyric words do not distort genre matching. `scripts/backfill_track_genre_tokens.py --mode rules --apply` backfills deterministic tokens for all stored tracks, and `--mode codex --apply` can optionally ask Codex CLI to add `ai_genre_tokens` for genres not covered by fixed rules; matching uses current deterministic and AI tokens together when the stored source hash still matches the track metadata. Eligible reuse candidates must match channel and similar genre first; liked tracks are selected before neutral tracks, disliked/copyright-blocked/reuse-disabled tracks are never reused, then the app prefers least-used and recent back-half material. If similar reuse material is not available, publish can still proceed below one hour instead of being blocked by duration alone. BibliaCanto and 불송 stay passage-based: OpenClaw should create roughly `3600` seconds / 60 minutes of new audio, and the app must not backfill them from old releases. The optional final-video repeat feature is disabled by default during the trial period (`AIMP_PLAYLIST_FINAL_VIDEO_REPEAT_ENABLED=false`), so render workers currently upload only the rendered base block. Japan/J-pop localized descriptions should use Japanese track titles plus Korean translations in the Korean/default version, Japanese titles in the Japanese version, and translated song titles in every other localized version. sundaze/English-American pop playlist localized descriptions keep English song titles in every timeline. HaruHaru/K-pop uses Korean as the default metadata language and Korean lyrics by default.
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

## Recent Ops Notes

- Channel genre taxonomy is now documented in `docs/openclaw-channel-genre-taxonomy.md`.
- New publish jobs classify each release into one detailed style lane and one broader YouTube playlist bucket. The actual video concept should stay detailed, such as K-pop trap, boom bap, bachata pop, Soft Hour solo piano, or tech house, while YouTube playlist assignment uses the broader bucket such as `K-pop Hip-Hop`, `Bachata Pop`, `Piano BGM`, or `House Music`.
- Existing releases were backfilled in DB with `channel_style_lane`, `channel_broad_genre`, and `youtube_genre_playlist_titles`. Soft Hour Radio and part of sundaze were also assigned through YouTube API. HaruHaru and Solwave Radio YouTube playlist assignment needs channel reconnect because the stored channel token failed during playlist API calls.

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
