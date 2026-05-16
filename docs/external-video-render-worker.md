# External Video Render Worker

Use this when the main Oracle VM should only manage the web app, database, YouTube OAuth, YouTube publish, and OpenClaw coordination, while another machine renders long MP4 files.

## Roles

- Main VM: FastAPI app, SQLite state, media storage, YouTube publish, Slack/OpenClaw coordination.
- OpenClaw machine: creates workspaces, generates/uploads audio, cover, thumbnail, and short loop video.
- Render worker machine: polls the main VM for queued video-render jobs, downloads audio/cover/loop-video assets, renders the final MP4 locally, and uploads the MP4 back to the main VM.

The main VM must run with:

```bash
AIMP_VIDEO_RENDER_EXECUTION_MODE=external
AIMP_RENDER_WORKER_SHARED_TOKEN=LONG_RANDOM_SECRET
```

When this mode is enabled, the main app background worker will not claim `build_video` jobs. It still processes audio renders, Slack jobs, and YouTube uploads.

## Install On A Render Worker Machine

Clone and install the repo:

```bash
git clone https://github.com/hsp1324/ai-music-playlist-generator.git
cd ai-music-playlist-generator
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
sudo apt update
sudo apt install -y ffmpeg
```

Set the API URL and token:

```bash
export AIMP_RENDER_WORKER_API_BASE="https://ai-music.168.107.34.175.sslip.io/api"
export AIMP_RENDER_WORKER_SHARED_TOKEN="PASTE_THE_MAIN_VM_TOKEN_HERE"
```

Run once for a smoke test:

```bash
scripts/render-worker --once --worker-id "$(hostname)-render"
```

Run continuously:

```bash
scripts/render-worker --worker-id "$(hostname)-render" --poll-seconds 20
```

Keep `--worker-id` stable. If the worker disconnects during upload, restarting with the same worker id lets it resume the same claimed job and continue the chunked upload from the server's current byte offset.

After a worker claims a job, the web app shows that `worker_id` in the release render status card. Click `Set Nickname` there to assign a human-readable name such as `Oracle Render 1`, `Home Desktop`, or `Laptop GPU`. The nickname is stored on the main VM in `storage/render-workers.json`, so the external machine does not need its own nickname configuration.

## Slack Notifications

External render-worker lifecycle notices are operational messages. They must go to `#all-ai-music-playlist-generator`, currently Slack channel ID `C0ATYMCMLLE`, through `AIMP_SLACK_OPS_CHANNEL_ID`.

Do not route render-worker claim/complete/upload/timeout notices to `#openclaw` / `C0AVBUYP150`. That channel is reserved for OpenClaw command-loop traffic configured through `AIMP_OPENCLAW_SLACK_CHANNEL_ID`.

## Resume Behavior

The upload path is resumable:

- The worker uploads the rendered MP4 in `Content-Range` chunks.
- The server stores partial uploads in `storage/tmp/render-worker/JOB_ID.mp4.part`.
- The worker asks `/api/render-worker/jobs/JOB_ID/upload-status` before every chunk and continues from `received_bytes`.
- If the worker process dies and restarts with the same `--worker-id`, the claim endpoint returns the existing running job instead of creating a duplicate.
- The server records `worker_id`, hostname, capabilities, and the optional server-side nickname in the job's `external_render_worker` metadata, so operators can tell which compute resource owns each render.
- If a claimed job has no heartbeat for `AIMP_RENDER_WORKER_CLAIM_TIMEOUT_SECONDS`, default 21600 seconds, the main VM requeues it for any render worker.

This handles network drops during final MP4 upload. If the local render itself is interrupted before upload, rerun the worker with the same cache directory and worker id; it can reclaim the same job if the claim has not timed out.

## API Summary

Render workers use only `/api/render-worker/*` and authenticate with either:

```text
X-Render-Worker-Token: TOKEN
Authorization: Bearer TOKEN
```

Endpoints:

- `POST /api/render-worker/jobs/claim`: claim or resume a video render job.
- `GET /api/render-worker/jobs/{job_id}/assets/audio`: download rendered release audio.
- `GET /api/render-worker/jobs/{job_id}/assets/cover`: download approved cover image.
- `GET /api/render-worker/jobs/{job_id}/assets/loop-video`: download short loop video.
- `POST /api/render-worker/jobs/{job_id}/progress`: update web progress.
- `GET /api/render-worker/jobs/{job_id}/upload-status`: get current resumable upload offset.
- `PUT /api/render-worker/jobs/{job_id}/upload`: upload a `Content-Range` chunk.
- `POST /api/render-worker/jobs/{job_id}/complete`: finalize the uploaded MP4 and move the release to metadata review.

## Nginx

The deployment configs already expose `/api/render-worker/` with large upload support and request buffering disabled:

```nginx
location /api/render-worker/ {
    client_max_body_size 4G;
    proxy_request_buffering off;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
    proxy_pass http://127.0.0.1:8000;
}
```

If you deploy a new VM or change Nginx manually, keep this block.

## Operational Notes

- Multiple render workers can run at the same time. Each worker claims only one queued video job at a time.
- The main VM remains the only machine that uploads to YouTube.
- OpenClaw should still call `scripts/openclaw-release render-video` after audio/cover/thumbnail/loop-video are ready. That creates the queued video job; render workers do the actual MP4 work.
- Do not run `scripts/render-worker` on the main VM if the goal is to keep the main VM free from video rendering.
- If a rendered release is stuck, check `/api/render-worker/status`, the workspace progress, and `storage/tmp/render-worker/` partial files.
