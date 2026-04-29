# OpenClaw Skills For AI Music Releases

Use this document as the instruction source when asking OpenClaw to create or run release-production skills for this repo.

OpenClaw must run commands on the Oracle VM from:

```bash
cd /opt/ai-music-playlist-generator
```

Use the local API or the helper script. Do not use the public `https://ai-music...sslip.io` URL because it is protected by Google login.

```bash
export AIMP_LOCAL_API_BASE=http://127.0.0.1:8000/api
```

## Shared Rules

- Never approve, reject, render, publish, or upload to YouTube unless the human explicitly asks.
- OpenClaw creates audio candidates and uploads them to the app review queue.
- If cover art is ready with the audio, upload the cover in the same command with `--cover`.
- Human review happens in Slack or the web UI.
- Single Release means one final song, but it may contain up to two review candidates from Suno.
- Playlist Release means many candidate songs. The human later approves enough songs, reorders them, renders audio, then continues cover/video/publish.
- Always return the final JSON result and mention `release.id` plus uploaded `track.id` values.
- If a command fails, stop and report the exact error. Do not retry blindly more than once.
- For YouTube title/description/tag writing, use [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).

## Skill 1: Single Release Candidate Set

Use this skill when the user asks for one standalone song/single.

### Goal

Generate one Single Release candidate set. Suno normally returns two candidate songs for one prompt. Upload both candidates into the same Single Release so the human can listen and choose one. If both are bad, the human rejects both; the app archives that release automatically and it can be restored later.

### OpenClaw Skill Prompt

```text
You are creating one Single Release for the AI Music app.

Work in /opt/ai-music-playlist-generator on the Oracle VM.
Use the local app API only through scripts/openclaw-release.

Goal:
- Generate one standalone song/single.
- If Suno returns two candidates, upload both candidates to one new Single Release.
- If only one usable candidate exists, upload one candidate to one new Single Release.
- If candidate cover images exist, upload them with the audio candidates.
- When the human approves one candidate, its uploaded cover is automatically registered as the release cover. The human still reviews/approves that cover before video rendering.
- Do not approve, reject, render, publish, or upload to YouTube.
- Return release.id, release.title, and all uploaded track ids.

After audio generation, run one of these:

For two Suno candidates:
scripts/openclaw-release upload-single-candidates \
  --release-title "RELEASE_TITLE" \
  --audio ABSOLUTE_AUDIO_PATH_A \
  --audio ABSOLUTE_AUDIO_PATH_B \
  --cover ABSOLUTE_COVER_PATH_A \
  --cover ABSOLUTE_COVER_PATH_B \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags"

For one candidate:
scripts/openclaw-release upload-single-candidates \
  --release-title "RELEASE_TITLE" \
  --audio ABSOLUTE_AUDIO_PATH \
  --cover ABSOLUTE_COVER_PATH \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags"

If no cover image is ready, omit every `--cover` argument. If one shared cover should be used for both candidates, provide one `--cover`; if each candidate has a different cover, provide one `--cover` per `--audio` in the same order.

Report the command output JSON. The human will approve one candidate in Slack or the web UI.
```

### Required Output

OpenClaw should finish with a concise report:

```text
Single release candidates uploaded.
release.id: ...
release.title: ...
tracks:
- ...
- ...
Next: human should approve exactly one candidate or reject both.
```

### Safety Checks

- Do not create two separate Single Releases for the two Suno outputs. Both candidates must be in one release.
- Do not upload more than two candidates to a Single Release.
- Do not upload cover images separately after this command if they were already uploaded with the candidate audio.
- If a release already has a selected/approved track, create a new Single Release instead of uploading more candidates to it.
- If both candidates are rejected later, the app archives the release automatically. Do not manually delete it.

## Skill 2: One-Hour Playlist Candidate Builder

Use this skill when the user asks for a playlist, mix, or approximately one-hour release.

### Goal

Create or continue one Playlist Release and generate/upload candidate tracks until the review queue has at least 60 minutes of material. The human will later approve the best tracks and render the final playlist audio.

### Important Duration Rule

Do not rely only on `workspace.actual_duration_seconds`, because that counts approved tracks only. Before human review, most generated tracks are still `pending_review`.

For OpenClaw generation progress, count all non-rejected candidate tracks assigned to the playlist:

- `pending_review`
- `held`
- `approved`
- `uploaded`

Stop generating when that candidate total is at least `3600` seconds. A practical buffer of `3900` seconds is acceptable so the human can reject weaker tracks and still have enough music.

### OpenClaw Skill Prompt

```text
You are creating a one-hour Playlist Release for the AI Music app.

Work in /opt/ai-music-playlist-generator on the Oracle VM.
Use the local app API and scripts/openclaw-release.

Goal:
- Create or continue one Playlist Release with target_duration_seconds=3600.
- Generate songs in batches.
- Upload cover art with each candidate when available.
- Upload every usable generated audio file to the same Playlist Release review queue.
- Continue until non-rejected candidate duration for that release is >= 3600 seconds.
- Prefer aiming for 3900 seconds if the user did not specify an exact stop.
- Do not approve, reject, reorder, render, publish, or upload to YouTube.
- Return release.id, candidate duration total, and uploaded track ids.
```

### Create A New Playlist Release

If the user did not provide an existing `release.id`, create one:

```bash
python - <<'PY'
import json
import httpx

payload = {
    "title": "PLAYLIST_TITLE",
    "target_duration_seconds": 3600,
    "workspace_mode": "playlist",
    "auto_publish_when_ready": False,
    "description": "One-hour playlist candidate set created by OpenClaw.",
    "cover_prompt": "",
    "dreamina_prompt": "",
}

with httpx.Client(base_url="http://127.0.0.1:8000/api", timeout=30.0) as client:
    response = client.post("/playlists/workspaces", json=payload)
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))
PY
```

Save the returned `id` as `RELEASE_ID`.

### Upload Each Generated Song

For every generated audio file:

```bash
scripts/openclaw-release upload-audio \
  --release-id RELEASE_ID \
  --audio ABSOLUTE_AUDIO_PATH \
  --cover ABSOLUTE_COVER_PATH \
  --title "TRACK_TITLE" \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags"
```

Upload both Suno outputs if both are usable. For a playlist, two Suno outputs are two separate playlist candidates, not one single-candidate set. If no cover image exists for a track, omit `--cover`.

### Check Candidate Duration

Use this after each upload batch:

```bash
python - <<'PY'
import json
import httpx

release_id = "RELEASE_ID"
counted_statuses = {"pending_review", "held", "approved", "uploaded"}

with httpx.Client(base_url="http://127.0.0.1:8000/api", timeout=30.0) as client:
    tracks = client.get("/tracks").json()
    workspaces = client.get("/playlists/workspaces").json()

workspace = next(item for item in workspaces if item["id"] == release_id)
candidates = [
    track
    for track in tracks
    if track["metadata_json"].get("pending_workspace_id") == release_id
    and track["status"] in counted_statuses
]
total_seconds = sum(max(track.get("duration_seconds") or 0, 0) for track in candidates)

print(json.dumps({
    "release_id": release_id,
    "title": workspace["title"],
    "target_seconds": workspace["target_duration_seconds"],
    "approved_seconds": workspace["actual_duration_seconds"],
    "candidate_seconds": total_seconds,
    "candidate_minutes": round(total_seconds / 60, 2),
    "candidate_count": len(candidates),
    "remaining_to_3600": max(3600 - total_seconds, 0),
}, ensure_ascii=False, indent=2))
PY
```

Stop when `candidate_seconds >= 3600`, or `candidate_seconds >= 3900` when building a rejection buffer.

### Required Output

OpenClaw should finish with:

```text
Playlist candidate set uploaded.
release.id: ...
release.title: ...
candidate duration: ... seconds (... minutes)
uploaded tracks:
- ...
- ...
Next: human should review/approve tracks, reorder final playlist, then render audio in the web UI.
```

### Safety Checks

- Keep all generated tracks for the same playlist in one Playlist Release.
- Do not create a Single Release for playlist candidates.
- Do not expect playlist track covers to become the final playlist cover automatically. Playlist cover selection stays at the release level.
- Do not stop at `actual_duration_seconds` unless the user explicitly asks for approved duration only.
- Do not render playlist audio. The human should choose/reorder first.
- If candidate duration cannot be calculated, stop and report the uploaded track list and the reason.

## Quick Selection Guide

Use `Single Release Candidate Set` when:

- The user asks for one song, one single, one YouTube single, or one standalone track.
- Suno returns two alternatives for the same prompt.
- The human needs to choose A or B.

Use `One-Hour Playlist Candidate Builder` when:

- The user asks for a playlist, mix, compilation, batch, or one-hour release.
- The goal is many tracks.
- The stop condition is around 60 minutes of candidate material.

Use `OpenClaw YouTube Metadata Skill` when:

- The release already has rendered video.
- The human asks OpenClaw to write YouTube title, description, and tags.
- The human wants OpenClaw to approve metadata but not publish.
- Follow [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).
