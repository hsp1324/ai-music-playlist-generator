# OpenClaw YouTube Metadata Skill

Use this when the release already has rendered video and the human asks OpenClaw to write YouTube metadata.

OpenClaw should write:

- YouTube title
- YouTube description
- YouTube tags as one comma-separated string

The app stores those values as approved metadata. Later, when the human clicks publish or re-upload, the app sends that exact title, description, and tags to YouTube.

The web UI can also generate a draft from the VM's local Codex CLI when `AIMP_CODEX_METADATA_ENABLED=true`.
Use `Generate Metadata` or `Regenerate Metadata Draft` in the release action area.
If Codex is unavailable, times out, or returns invalid JSON, the app falls back to the deterministic template generator and marks the draft with a fallback warning.

## Rules

- Work in `/opt/ai-music-playlist-generator`.
- Use the local helper script, not the public website URL.
- Do not publish or re-upload to YouTube unless the human explicitly asks.
- The release must already have a rendered video before metadata can be approved.
- For tags, provide comma-separated plain tags without `#`, for example `Piano,CafePiano,StudyMusic,WorkMusic`.
- Keep the title under 100 characters.
- Description can be multiline; write it to a temporary UTF-8 text file and pass `--description-file`.
- If the release is a playlist, include a timestamped tracklist from the final order.
- Always run `scripts/openclaw-release metadata-context` first and use its timeline in the description.
- `metadata-context` includes track `prompt`, `style`, `tags`, and `lyrics` when available. Use them as private creative context, but do not paste raw Suno settings into the public description.
- Prefer `display_timestamp_lines` when available. It keeps the same timestamps but removes awkward `A` / `B`, `1` / `2`, and old pair-style suffixes.
- Do not guess timestamps. The helper calculates them from the app's final order and track durations.
- Treat each timestamp as a fixed playback position. If a title is corrected, only change the title text; do not move or swap the timestamp.
- Do not sort track titles alphabetically or by A/B label in the metadata. The playback order is the source of truth.
- Do not show trailing `A` / `B`, `1` / `2`, or pair labels like `Morning` / `Evening` in the YouTube description. If two tracks would read like variants of the same title, rename only the displayed title text so every row feels like a standalone song.
- If using the web `Regenerate Metadata Draft` button, still review the generated title, description, and tags before approving.

## Metadata Style Prompt

Give OpenClaw this prompt:

```text
You are writing YouTube metadata for an AI music release in the AI Music app.

Read the release title, final track order, durations, mood, style, lyrics, and tags.
First run:
scripts/openclaw-release metadata-context --release-id RELEASE_ID

Use the returned timestamps exactly for the tracklist.
Use `display_timestamp_lines` as the starting point when present.
If a displayed title still reads like A/B, 1/2, or a paired alternative, rewrite only the title text so it is natural and unique.
Write metadata in this shape:

Title:
<Korean YouTube title, under 100 characters>

Description:
<2-4 Korean paragraphs describing the mood and use cases>

Recommended for
<slash-separated use cases>

<timestamped tracklist in final order>

<hashtags line>

Tags:
<comma-separated tags without # symbols>

For a cafe piano playlist, use this direction:
- quiet solo piano
- cafe mood
- study, work, reading, relaxation
- warm and calm background music

Do not invent tracks that are not in the release.
Do not publish to YouTube.
After writing the metadata, approve it with scripts/openclaw-release approve-metadata.
```

## Command

Get release context and exact final-order timestamps:

```bash
scripts/openclaw-release metadata-context --release-id RELEASE_ID
```

Use the returned JSON:

- `release.title`
- `release.actual_duration_seconds`
- `timeline`
- `display_timestamp_lines`
- `timestamp_lines` as raw fallback only

Create the description file:

```bash
cat > /tmp/youtube-description.txt <<'EOF'
카페 한쪽에서 조용히 흐르는 듯한 잔잔한 솔로 피아노 플레이리스트입니다.

부드러운 건반 소리와 따뜻한 분위기의 피아노 곡들을 모아,
공부할 때, 작업할 때, 책을 읽을 때, 혹은 잠시 쉬고 싶을 때 편하게 들을 수 있도록 구성했습니다.

Recommended for
공부 / 작업 / 독서 / 휴식 / 카페 분위기 / 조용한 배경음악

00:00 Track One
03:20 Track Two
06:45 Track Three

#Piano #CafePiano #StudyMusic #WorkMusic #RelaxingMusic #SoloPiano
EOF
```

Approve the metadata:

```bash
scripts/openclaw-release approve-metadata \
  --release-id RELEASE_ID \
  --title "조용한 카페 피아노 솔로 1시간 | 공부, 작업, 휴식할 때 듣는 잔잔한 플레이리스트" \
  --description-file /tmp/youtube-description.txt \
  --tags "Piano,CafePiano,StudyMusic,WorkMusic,RelaxingMusic,SoloPiano"
```

The JSON result should show:

- `metadata_approved: true`
- `workflow_state: publish_ready`
- `youtube_title`
- `youtube_description`
- `youtube_tags`

## After Metadata Approval

The human should return to the web UI, choose `Publish Channel`, then click `Approve Publish` or `Re-upload to YouTube`.
