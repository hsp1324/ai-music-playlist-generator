# OpenClaw Next Release Planner Skill

Use this skill when the AI Music web app asks OpenClaw to choose the next 40+ minute playlist concept for the backlog queue.

This is the channel/concept selection step inside the continuous automation loop. For queue sizing and producer/finisher behavior, read [openclaw-backlog-queue.md](openclaw-backlog-queue.md) first. This planner chooses the next channel, delegates channel-specific concept selection to `docs/openclaw-channel-concepts/`, then hands off to the production/publish instructions in [openclaw-skills.md](openclaw-skills.md).

## Slack Trigger Contract

The AI Music web app starts the continuous loop by posting a Slack message into the configured OpenClaw channel. Real app-originated automation requests start with this exact prefix:

```text
OPENCLAW_RUN:
```

When the OpenClaw Slack listener receives a channel message that starts with `OPENCLAW_RUN:`, it should strip the prefix and execute the remaining instruction as an approved automation request. Do not require an `@OpenClaw` mention for these app-originated messages.

For safety, ignore ordinary channel messages that do not start with `OPENCLAW_RUN:` unless the human explicitly addresses OpenClaw through the listener's normal manual command path. The prefix is what separates web-app automation from casual Slack conversation.

The web app may cap this automatic loop with `AIMP_OPENCLAW_AUTO_REQUEST_NEXT_MAX_UPLOADS`. `0` means unlimited. If the cap is reached after a successful YouTube upload, or if the human posts a stop command in the configured OpenClaw Slack channel, the app intentionally stops sending `OPENCLAW_RUN:` messages. Do not treat silence after a completed publish as an error unless the human asks.

## Goal

Choose the next channel and a fresh 40+ minute playlist concept that fits that channel, avoids recent repetition, and can be pushed into the backlog queue safely.

The active channel roster is dynamic. Always read `/youtube/status` and use every connected channel in its `channels` list unless a channel is explicitly marked inactive/excluded in these docs. `MusicSun` is manual-only and is excluded from automatic rotation. Current known active channels include:

- `Tokyo Daydream Radio`
- `Soft Hour Radio`
- `sundaze`
- `Solwave Radio`
- `HaruHaru`
- `Storylight OST`
- `Cinematic Pulse`
- `Club Bloom`
- `The Old Verse`
- `The New Verse`

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
2. Apply `docs/openclaw-backlog-queue.md` first: finish ready releases, then fill channels with backlog below target.
3. Prefer the active channel with the lowest backlog count. Do not create a new release for a channel with backlog `10` or more.
4. Within the eligible channels, prefer the channel with the oldest recent published playlist unless the human explicitly asks for a channel.
5. Do not pick the same channel twice in a row unless other channels are blocked, already at backlog max, not connected, unavailable, or explicitly requested.
6. Confirm the selected YouTube channel is connected in `/youtube/status` before running publish automation.
7. When future channels are added, rotate across all connected, non-excluded channels from `/youtube/status`. `MusicSun` remains excluded because it is the only manual-only channel. Use dedicated concept/profile docs when present; otherwise use the custom fallback docs.
8. Within the selected channel, choose a fresh concept with controlled randomness across the channel's concept lanes after checking recent releases. Do not cycle through a fixed template list in the same order.

## Channel Concept Delegation

After selecting a channel, run `scripts/openclaw-release channel-profile` with the selected channel title. If the selected channel is `The Old Verse` or `The New Verse`, first read [openclaw-scripture-sequence.md](openclaw-scripture-sequence.md), inspect `scripts/openclaw-scripture-sequence status --init`, and reserve the next canonical passage before generating audio. Read both returned docs:

- `concept_doc`: choose the next playlist concept and avoid recent repetition.
- `profile_doc`: generate cover, thumbnail, and 8 second loop video without mixing channel visual signatures.

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
- For `The Old Verse` / `The New Verse`: `scripture_ledger_path`, `scripture_last_completed`, `scripture_next_start`, `selected_passage_range`, and `why_this_passage_is_next`

For every Playlist Release plan, the main YouTube title and all localized titles must start exactly with `[playlist]`. Do not use this prefix for Single Releases. After `[playlist]`, avoid duplicate playlist nouns such as `플레이리스트`, `Playlist`, `プレイリスト`, or `lista de reproducción`.

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

Run docs/openclaw-backlog-queue.md first, then choose the next 40+ minute Playlist Release using docs/openclaw-next-release-planner.md:
- Keep each active automated channel at no more than 1 unfinished Playlist Release.
- Finish metadata_review/publish_ready releases before creating new ones.
- If a video render job is queued/running, VM is handling it. If another channel is below target, prepare that next channel's release up to queued video render; do not wait idle.
- Rotate active channels instead of repeating the same channel.
- Use `/youtube/status` `channels` as the source for the active channel roster. Known channels include Tokyo Daydream Radio, Soft Hour Radio, sundaze, Solwave Radio, HaruHaru, Storylight OST, Cinematic Pulse, Club Bloom, The Old Verse, and The New Verse. Newly connected non-excluded channels must also enter rotation. MusicSun is the only manual-only connected channel and must be skipped unless the human explicitly requests it.
- Do not continue the retired Signal Room/Signal Desk/Midnight Cue research/debate concept direction unless the human explicitly revives it.
- Treat scripts/openclaw-release list-releases as the app's known YouTube upload catalog.
- Select the channel, then run scripts/openclaw-release channel-profile with that channel.
- Read the returned concept_doc to choose a fresh concept.
- Read the returned profile_doc before making cover, thumbnail, and loop video assets.
- If the selected channel is The Old Verse or The New Verse, read docs/openclaw-scripture-sequence.md, run scripts/openclaw-scripture-sequence status --init, reserve the next canonical passage with scripts/openclaw-scripture-sequence start before Suno, include that passage range in every YouTube title, and mark it scheduled/published after upload.
- If the returned docs are custom-channel docs, infer the channel identity from the channel title, local app history, and human instructions instead of copying another channel's signature.
- Pick a concept not used recently while keeping the selected channel identity clear.

After choosing the channel and concept, run the production instructions from docs/openclaw-skills.md.
Create enough audio for at least 2400 seconds, generate final cover, separate YouTube thumbnail, an 8 second loop video, render audio, queue video render, then stop and release the lock. When the app later asks after external render completion, finish metadata and private/scheduled publish. Do not skip the loop video unless the human explicitly approves a still-image fallback.

When done, report:
- selected_channel
- concept_doc
- profile_doc
- release.id
- release.title
- youtube_video_id
- privacy: private
- recent_releases_checked
- why_this_is_fresh
```
