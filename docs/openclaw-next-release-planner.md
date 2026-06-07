# OpenClaw Next Release Planner Skill

Use this skill when the AI Music web app asks OpenClaw to choose the next playlist concept for the backlog queue.

This is the channel/concept selection step inside the continuous automation loop. For queue sizing and producer/finisher behavior, read [openclaw-backlog-queue.md](openclaw-backlog-queue.md) first. This planner chooses the next channel, delegates channel-specific concept selection to `docs/openclaw-channel-concepts/`, then hands off to the production/publish instructions in [openclaw-skills.md](openclaw-skills.md).

## Slack Trigger Contract

The AI Music web app starts the continuous loop by posting a Slack message into the configured OpenClaw channel. Real app-originated automation requests start with this exact prefix:

```text
OPENCLAW_RUN:
```

When the OpenClaw Slack listener receives a channel message that starts with `OPENCLAW_RUN:`, it should strip the prefix and execute the remaining instruction as an approved automation request. Do not require an `@OpenClaw` mention for these app-originated messages.

For safety, ignore ordinary channel messages that do not start with `OPENCLAW_RUN:` unless the human explicitly addresses OpenClaw through the listener's normal manual command path. The prefix is what separates web-app automation from casual Slack conversation.

Slack command text is intentionally compact so the human monitoring channel stays readable. Do not expect the Slack message to include channel priorities, release lists, blockers, or backlog snapshots. After receiving `OPENCLAW_RUN:`, pull the latest `main`, then call the app APIs through `scripts/openclaw-release openclaw-status` and `scripts/openclaw-release openclaw-backlog-status` to get the detailed queue, lock, channel, and scheduler context.

The web app may cap this automatic loop with `AIMP_OPENCLAW_AUTO_REQUEST_NEXT_MAX_UPLOADS`. `0` means unlimited. If the cap is reached after a successful YouTube upload, or if the human posts a stop command in the configured OpenClaw Slack channel, the app intentionally stops sending `OPENCLAW_RUN:` messages. Do not treat silence after a completed publish as an error unless the human asks.

## Goal

Choose the next channel and a fresh playlist concept that fits that channel, avoids recent repetition, and can be pushed into the backlog queue safely. Suno credits are available again after the human added 500 credits on 2026-06-05, so OpenClaw may select concepts that need new Suno generation. Spend credits conservatively: non-scripture channels normally need about 10 minutes of new audio, then app-side same-channel/similar-genre reuse fills the rest. `Storylight OST` remains reuse-only by default unless the human explicitly asks for new Storylight music. BibliaCanto and 불송 still need about 40 minutes of new passage-based audio.

The active channel roster is dynamic. Always read `/youtube/status` and use every connected channel in its `channels` list unless a channel is explicitly marked inactive/excluded in these docs. `MusicSun` is manual-only and is excluded from automatic rotation. Current known active channels include:

- `Tokyo Daydream Radio`
- `Soft Hour Radio`
- `sundaze`
- `Solwave Radio`
- `HaruHaru`
- `Storylight OST`
- `Cinematic Pulse`
- `Club Bloom`
- `BibliaCanto`
- `불송`

Current known connected channels excluded from automatic playlist rotation:

- `MusicSun`: manual-only channel. Never select it for automatic next-release rotation unless the human explicitly requests MusicSun.
- `Signal Room Radio`, `Signal Desk Radio`, and `Midnight Cue Radio`: retired names. Do not select them unless the human explicitly revives those channels.

Future channels do not need code changes before entering rotation. Newly connected channels are active by default. If a connected channel does not have dedicated files, use the custom fallback files:

- `docs/openclaw-channel-profiles/custom-channel.md`
- `docs/openclaw-channel-concepts/custom-channel.md`

When the human later wants a stronger identity for that channel, add dedicated channel files and the planner will use them after the repo is updated.

## Source Of Truth

Use the deployed AI Music app API through `scripts/openclaw-release`. Do not infer current state from Python settings imports, stale logs, browser pages, local dev servers, or memory.

OpenClaw usually runs outside the Oracle VM. In that runtime, the repo checkout is normally:

```bash
~/repos/ai-music-playlist-generator
```

If that path is missing, try `~/repos/ai리포` or the current checkout before failing. Do not require `/opt/ai-music-playlist-generator`; that path is the deployed VM service path, not the OpenClaw runtime path.

`AIMP_LOCAL_API_BASE` must point to the deployed VM app API or to a tunnel that forwards to the deployed VM app. Do not use OpenClaw's own local dev API. If `scripts/openclaw-release youtube-status` returns `configured=false`, `authenticated=false`, `ready=false`, or `channels=[]`, assume you are pointed at the wrong API and stop before generation/publish.

Use one of these API access patterns:

- On the VM: `AIMP_LOCAL_API_BASE=http://127.0.0.1:8000/api`.
- On a laptop/OpenClaw worker: an SSH/Tailscale tunnel to the VM FastAPI process, then set `AIMP_LOCAL_API_BASE` to the tunnel URL.
- Public `https://ai-music.168.107.34.175.sslip.io/api` only works with a valid `AIMP_API_COOKIE` from Google login.

Do not assume `AIMP_OPENCLAW_SHARED_TOKEN` can upload tracks or publish releases by itself. That token is for OpenClaw coordination endpoints, not the release-production API surface.

Do not open `/youtube/status`, `/api/youtube/status`, `/youtube/connect`, `/api/youtube/connect`, Google OAuth, or YouTube Studio in a browser during automation. Channel tokens are managed by the human through the web app. OpenClaw should only read status through `scripts/openclaw-release youtube-status` or `curl -fsS "$AIMP_LOCAL_API_BASE/youtube/status"`, choose a connected channel, and pass the explicit channel title/id into the helper publish command.

Required first commands:

```bash
REPO_DIR="${AIMP_REPO_DIR:-$HOME/repos/ai-music-playlist-generator}"
if [ ! -d "$REPO_DIR" ] && [ -d "$HOME/repos/ai리포" ]; then
  REPO_DIR="$HOME/repos/ai리포"
fi
cd "$REPO_DIR"
git pull origin main
: "${AIMP_LOCAL_API_BASE:?Set AIMP_LOCAL_API_BASE to the deployed VM API or VM API tunnel before running OpenClaw automation.}"
scripts/openclaw-release list-releases
scripts/openclaw-release youtube-status
```

Treat `list-releases` as the app's known YouTube upload catalog. It contains release titles, channel titles, YouTube ids, durations, and recent update times. If the human says there are relevant YouTube uploads outside this app, report that limitation before claiming a concept is non-duplicated.

## Backlog-Aware Rotation Rules

1. Inspect recent Playlist Releases from `scripts/openclaw-release list-releases`.
2. Apply `docs/openclaw-backlog-queue.md` first: finish ready releases, skip quota-blocked YouTube upload retries as deferred work, then fill channels with backlog below target.
3. Prefer active automated channels with the shortest future scheduled-public horizon in the app's backlog snapshot. Future scheduled-public means the release has a YouTube video id and a scheduled public publish time or YouTube `publishAt` that is still in the future. Fill channels by date evenly: every channel should have a release for the earliest upcoming date before any channel is pushed further out to the next date. A channel scheduled through May 21 comes before a channel already scheduled through May 27.
4. Within channels with the same scheduled-through horizon, prefer the active channel with the lowest unfinished backlog count. Do not create a new release for a channel with backlog `10` or more.
5. If multiple eligible channels are tied, prefer the channel with the oldest recent scheduled/public playlist unless the human explicitly asks for a channel.
6. Do not pick the same channel twice in a row unless other channels are blocked, already at backlog max, not connected, unavailable, or explicitly requested.
7. Confirm the selected YouTube channel is connected in `/youtube/status` before running publish automation.
8. When future channels are added, rotate across all connected, non-excluded channels from `/youtube/status`. `MusicSun` remains excluded because it is the only manual-only channel. Use dedicated concept/profile docs when present; otherwise use the custom fallback docs.
9. Within the selected channel, choose a fresh concept with controlled randomness across the channel's concept lanes after checking recent releases. Do not cycle through a fixed template list in the same order.

Empty duplicate app workspaces are cleanup, not blockers. If `list-releases` shows a `collecting` Playlist Release with 0 tracks and no audio/cover/thumbnail/loop assets while the same title/channel already has an uploaded or scheduled release, the app backlog summary auto-archives or skips that empty shell; continue. Similar published concepts should guide variety, but they must not stop OpenClaw from creating a new eligible playlist.

## Channel Concept Delegation

After selecting a channel, run `scripts/openclaw-release channel-profile` with the selected channel title and read [openclaw-channel-genre-taxonomy.md](openclaw-channel-genre-taxonomy.md). Pick one underused broad YouTube playlist bucket and one detailed video style lane before Suno generation or existing-track search. If the selected channel is `BibliaCanto`, first read [openclaw-scripture-sequence.md](openclaw-scripture-sequence.md). Create the release, then reserve the next app-owned canonical Old Testament or New Testament passage with `scripts/openclaw-release openclaw-scripture-reserve` before generating audio. If the selected channel is `불송`, use its Buddhist concept/profile docs and do not use the Bible scripture ledger. Read both returned docs:

- `concept_doc`: choose the next playlist concept and avoid recent repetition.
- `profile_doc`: generate cover, thumbnail, and the required visual source without mixing channel visual signatures. This is a short loop video for moving-video channels, but a still-image render package for HaruHaru, sundaze, Solwave Radio, Tokyo Daydream Radio photorealistic Japanese hip-hop/R&B/rap releases, and Club Bloom.

Example:

```bash
scripts/openclaw-release channel-profile \
  --release-title "NEXT_RELEASE_IDEA" \
  --description "NEXT_RELEASE_CONCEPT" \
  --youtube-channel-title "Tokyo Daydream Radio"
```

Known channel concept docs are:

- `docs/openclaw-channel-concepts/tokyo-daydream-radio.md`
- `docs/openclaw-channel-concepts/soft-hour-radio.md`
- `docs/openclaw-channel-concepts/sundaze.md`
- `docs/openclaw-channel-concepts/solwave-radio.md`
- `docs/openclaw-channel-concepts/haruharu.md`
- `docs/openclaw-channel-concepts/storylight-ost.md`
- `docs/openclaw-channel-concepts/cinematic-pulse.md`
- `docs/openclaw-channel-concepts/club-bloom.md`
- `docs/openclaw-channel-concepts/the-old-verse.md`
- `docs/openclaw-channel-concepts/the-new-verse.md`
- `docs/openclaw-channel-concepts/custom-channel.md`

## Freshness Rules

Before finalizing a concept:

1. Filter recent releases by the selected `youtube_channel_title`.
2. Inspect at least the latest 5 releases on that channel when available.
3. Inspect the latest 15-20 releases globally for cross-channel repetition.
4. Extract recent setting, use case, subgenre, lyric premise, thumbnail phrase, visual scene, and title pattern.
5. Follow the selected channel's `concept_doc`.
6. Keep the channel identity stable while varying the specific concept.
7. Prefer concepts that are clear from title and thumbnail within a few seconds.
8. Prefer search/click-friendly phrases, but do not stuff keywords or make titles feel machine-generated.
9. Keep titles broad enough to match the whole playlist mood and use case. Do not trap a release inside one tiny keyword if a broader phrase such as mystery BGM, focus BGM, night drive pop, party warmup, or research music better matches the actual sound.

Do not choose a concept if it only changes adjectives while repeating the same channel, use case, setting, visual scene, and music direction as a recent upload.

## Output Plan

Return this compact plan before generating audio:

- `selected_channel`
- `concept_doc`
- `profile_doc`
- `release_title`
- `release_description`
- `music_direction`
- `visual_direction`
- `thumbnail_text`
- `metadata_language_plan`
- `recent_releases_checked`
- `why_this_is_fresh`
- For `Tokyo Daydream Radio`: selected visual system, either `animated_moving_video` for anime/J-pop/city-pop/pop-rock/dance-pop lanes or `photorealistic_still_image` for Japanese rap/hip-hop/R&B/neo-soul lanes, plus why it keeps the rough every-other-release alternation.
- For `BibliaCanto` Bible releases: `scripture_source=web_app`, `selected_passage_range`, `scripture_next_start_after_completion`, and `why_this_passage_is_next`
- For `불송` Buddhist releases: selected Buddhist source/theme, exact source/chapter/section when verified, release-level music lane, title hook plan that uses the source/theme instead of generic `불경` alone and avoids redundant `한국어 랩` / `한국어 힙합`, `schedule=daily_07:00_Asia/Seoul`, `visual_signature=respectful_photorealistic_buddha_listening_to_music_while_reading_open_sutra`, `thumbnail=same_cover_first_frame_package`, and `spectrum=calm-bars`

For every Playlist Release plan, the main YouTube title and all localized titles must start exactly with `[playlist]`. Do not use this prefix for Single Releases. After `[playlist]`, avoid duplicate playlist nouns such as `플레이리스트`, `Playlist`, `プレイリスト`, or `lista de reproducción`.

Localized titles should be planned as natural language-specific titles, not literal translations. If a direct translation of the planned title sounds awkward or less clickable in Japanese, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Turkish, Portuguese, French, German, Arabic, Simplified Chinese, Traditional Chinese, Korean, or English, rewrite that localized title while preserving the channel identity, genre/lane, and real listening use case.

If YouTube upload is blocked only because phone/account verification does not allow a 14+ minute video, keep the rendered release and metadata intact, report the deferred upload, and continue to the next release plan. Do not delete or re-render just because upload is deferred.

After the plan, continue according to [openclaw-backlog-queue.md](openclaw-backlog-queue.md): finish rendered releases first; otherwise create a new release, prepare assets, render audio, queue video render without waiting, then release the lock. An external render worker will render/upload the MP4, and the app will ask again when it is ready for metadata/publish.

## Skill Prompt

```text
You are the Backlog Queue Planner for the AI Music app.

Work in the OpenClaw repo checkout, normally ~/repos/ai-music-playlist-generator.
Use scripts/openclaw-release only.

First, update the repo and inspect app state:
REPO_DIR="${AIMP_REPO_DIR:-$HOME/repos/ai-music-playlist-generator}"
if [ ! -d "$REPO_DIR" ] && [ -d "$HOME/repos/ai리포" ]; then
  REPO_DIR="$HOME/repos/ai리포"
fi
cd "$REPO_DIR"
git pull origin main
: "${AIMP_LOCAL_API_BASE:?Set AIMP_LOCAL_API_BASE to the deployed VM API or VM API tunnel. Do not use the OpenClaw local dev API.}"
scripts/openclaw-release list-releases
scripts/openclaw-release youtube-status

If YouTube status is configured=false, authenticated=false, ready=false, or channels=[], you are using the wrong API. Stop before generation/publish and report that the deployed VM API/tunnel is missing.

Run docs/openclaw-backlog-queue.md first, then choose the next Playlist Release using docs/openclaw-next-release-planner.md:
- Keep each active automated channel filled toward the configured unfinished Playlist Release target, currently 10 per channel.
- Finish metadata_review/publish_ready releases before creating new ones.
- If a video render job is queued/running, VM is handling it. If any channel is below target, prepare the next eligible release up to queued video render; do not wait idle.
- When choosing a new release channel, prioritize connected automated channels with the shortest scheduled-through horizon. Keep scheduled public dates balanced across channels before pushing any one channel further into later dates.
- Rotate active channels instead of repeating the same channel.
- Use `/youtube/status` `channels` as the source for the active channel roster. Known channels include Tokyo Daydream Radio, Soft Hour Radio, sundaze, Solwave Radio, HaruHaru, Storylight OST, Cinematic Pulse, Club Bloom, BibliaCanto, and 불송. Newly connected non-excluded channels must also enter rotation. MusicSun is the only manual-only connected channel and must be skipped unless the human explicitly requests it.
- Do not continue the retired Signal Room/Signal Desk/Midnight Cue research/debate concept direction unless the human explicitly revives it.
- Treat scripts/openclaw-release list-releases as the app's known YouTube upload catalog.
- Select the channel, then run scripts/openclaw-release channel-profile with that channel.
- Read the returned concept_doc to choose a fresh concept.
- Read the returned profile_doc before making cover, thumbnail, and loop-video or still-image render assets.
- If the selected channel is Tokyo Daydream Radio, alternate visual systems when practical: one animated/anime moving-video release, then one photorealistic friend-taken still-image release for Japanese hip-hop/R&B/rap, then repeat. Use `photorealistic_still_image` only for Japanese rap, Japanese hip-hop, J-rap, Tokyo R&B, Japanese neo-soul, trap-soul, boom-bap, or similar hip street-pop lanes; use `animated_moving_video` for anime-pop, city-pop, mainstream J-pop, dance-pop, synth-pop, pop-rock, arcade, and game-center lanes.
- If the selected channel is BibliaCanto, read docs/openclaw-scripture-sequence.md, create the app release first, reserve the next canonical Old Testament or New Testament passage from the web app with scripts/openclaw-release openclaw-scripture-reserve before Suno, include the returned passage range in every YouTube title, and mark it scheduled/published after upload with scripts/openclaw-release openclaw-scripture-complete. Do not use or compare a local scripture ledger.
- If the selected channel is 불송, use the Buddhist channel concept/profile docs instead of the Bible scripture ledger. Publish through the app normally; the app schedules 불송 public daily at 07:00 Asia/Seoul.
- For BibliaCanto, choose one Bible release-level music lane before Suno generation and rotate it across uploads, such as scripture hip-hop, Bible R&B, K-pop-inspired scripture pop, scripture rap-pop, trap-soul scripture songs, boom-bap Bible rap, alt-R&B scripture songs, neo-soul scripture songs, Afropop/Amapiano-pop scripture songs, dark street-pop scripture, or synth-pop scripture songs. New BibliaCanto music must not sound like Gospel music, worship, holy worship, church choir, hymns, praise band, CCM, congregational singing, piano worship ballads, or church-service music; add those terms to Suno excluded styles. For 불송, default to one Buddhist hip-hop/rap lane such as 불교 힙합, 불경 힙합, mindful hip-hop, Korean Buddhist rap, mellow boom bap, Buddhist hip-hop soul, or restrained Buddhist trap-soul. Use a non-hip-hop Buddhist lane only when the human explicitly asks or when finishing an already-started release in that lane. Keep the whole release in that lane so the title can truthfully name the genre. Public 불송 metadata and thumbnail text should use plain audience-friendly wording, not obscure coined genre labels. 불송 titles must include the verified Buddhist source/chapter/section when known, or the verified theme when only a theme is known; do not invent chapter/verse coverage, do not rely on generic `불경` alone when a source/theme exists, and avoid redundant `한국어 랩` / `한국어 힙합` in Korean/default titles. For 불송 Suno work, exclude trot/ppongjjak/old Korean cabaret-pop explicitly and reject outputs with strong trot rhythm or vocal ornaments.
- If the returned docs are custom-channel docs, infer the channel identity from the channel title, local app history, and human instructions instead of copying another channel's signature.
- Pick a concept not used recently while keeping the selected channel identity clear.

After choosing the channel and concept, run the production instructions from docs/openclaw-skills.md.

For non-scripture channels other than `Storylight OST`, create roughly 10 minutes of new approved audio for a 600-second app workspace target. If Suno is unstable, upload only the usable tracks already made and call audio render; do not keep retrying just to hit the 10-minute target. The app then tries to extend the base block to about 60 minutes from previous same-channel, same-bucket or similar-lane back-half tracks. For `Soft Hour Radio`, the new 10-minute lead block must be solo piano only and uploaded first. Reuse is piano-first: the app prefers previous Soft Hour solo-piano back-half tracks, but if there are not enough piano tracks to approach one hour, it may fill the remaining back half with similar existing Soft Hour music instead of blocking. Within eligible similar reuse candidates, liked tracks are selected before neutral tracks; disliked, copyright-blocked, and reuse-disabled tracks are never reused. If order randomization is used, the fresh solo-piano lead block must remain before reused tracks, and reused solo-piano tracks should stay before non-piano fallback tracks. If the app cannot find enough similar reuse material, a release over 40 minutes is still publishable and should not be blocked only because it missed an older 45-minute target. Do not fill a detailed lane with mismatched reuse tracks; for example, do not extend a HaruHaru boom bap release with ballads or dance-pop, do not extend a sundaze pop hip-hop release with generic park-walk pop, and do not extend a Tokyo Japanese hip-hop/R&B release with city-pop or anime-pop unless the track genuinely fits the same groove. `Storylight OST` is reuse-only by default: do not open Suno or upload new audio; search existing approved Storylight-compatible tracks with `scripts/openclaw-release search-tracks`, attach them with `scripts/openclaw-release reuse-track`, then render. If one Storylight lane lacks enough existing tracks, choose another fresh Storylight lane with enough reusable tracks or report the blocker instead of spending Suno credits. For `BibliaCanto` and `불송`, create roughly 40 minutes of new passage-based audio for a 2400-second target and do not rely on reuse. The optional final-video repeat feature is disabled during the trial period, so render workers currently upload only the rendered base block. Generate final cover, separate YouTube thumbnail, and the channel-required visual source as soon as those assets are ready; they can be uploaded before app audio render completes. Moving-video channels need a short loop video. For `Soft Hour Radio`, that cover/first-frame and loop video must be high-resolution photorealistic, preserve the calm BGM background feeling, and use a locked-off camera with no camera movement at all. HaruHaru, sundaze, Solwave Radio, and Tokyo Daydream Radio photorealistic Japanese hip-hop/R&B/rap releases skip provider loop videos by default and render from the still cover image with app-managed lower-left lyrics and lower-right spectrum. Tokyo Daydream Radio animated J-pop/city-pop/anime-pop releases still need the normal provider loop-video flow. Club Bloom also skips provider loop videos by default, but renders from the still cover image with lower-right spectrum only and no lyric overlay. Approve the cover after upload. After approved cover and the required visual source are present, call `render-audio` and `render-video` without waiting for audio completion; if audio is still queued/running, the app keeps the video render request pending and queues final video automatically after audio render completes. Then stop and release the lock. Exception: for `불송`, use one calm photorealistic Buddha-reading-sutra cover/thumbnail/first-frame package with at most one short Korean passage/theme + style phrase, never the `불송` channel name; do not create a separate channel-branded thumbnail, and reject background-only temple/lotus/lantern/mountain scenes before upload. If no similar reuse candidates exist on non-Storylight non-scripture channels, the app renders the uploaded new tracks instead of blocking. When the app later asks after external render completion, finish metadata and queue private/scheduled publish with `publish-release --no-wait`, then release the lock. Do not skip the loop video on moving-video channels unless the human explicitly approves a still-image fallback; HaruHaru, sundaze, Solwave Radio, Tokyo Daydream Radio photorealistic Japanese hip-hop/R&B/rap releases, and Club Bloom are explicit still-image defaults, not fallback cases.

When done, report:
- selected_channel
- concept_doc
- profile_doc
- release.id
- release.title
- youtube_video_id
- privacy: app-scheduled public if scheduling is enabled, otherwise private
- recent_releases_checked
- why_this_is_fresh
```
