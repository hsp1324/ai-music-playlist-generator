# Optional Distributed Video Render Workers

Normal OpenClaw automation currently renders video on the Oracle VM app background worker. Use this document only for a deliberate/manual distributed-render experiment or emergency offload. Do not set this up as the default OpenClaw flow.

The web app already stores long-running work in the `jobs` table. External render workers use that same queue:

1. OpenClaw or the web UI queues a `build_video` job.
2. Any machine running `scripts/render-worker` polls `/api/render-worker/claim`.
3. The worker downloads the rendered audio, approved cover, and uploaded loop video.
4. The worker renders the final MP4 locally with ffmpeg.
5. The worker uploads the finished MP4 back to `/api/render-worker/jobs/{job_id}/complete`.
6. The app marks the release as `metadata_review`, exactly like an internal render.

If a worker claims a job and then dies, the app requeues that job after `AIMP_RENDER_WORKER_STALE_SECONDS`. The default is `86400` seconds, which is one day.

## Main VM Settings

Set a shared token on the web app VM. This token protects the unauthenticated render-worker API path that bypasses Google login for machine-to-machine use.

```bash
sudo sh -c 'printf "\nAIMP_RENDER_WORKER_SHARED_TOKEN=%s\n" "$(openssl rand -hex 32)" >> /etc/ai-music-playlist-generator.env'
sudo sh -c 'printf "AIMP_RENDER_WORKER_STALE_SECONDS=86400\n" >> /etc/ai-music-playlist-generator.env'
sudo systemctl restart ai-music-playlist-generator
```

When an external laptop/desktop worker should own video rendering, keep the main VM worker from claiming `build_video` jobs. Do not set this for normal VM-render automation:

```bash
sudo sh -c 'printf "AIMP_WORKER_CLAIM_VIDEO_JOBS=false\n" >> /etc/ai-music-playlist-generator.env'
sudo systemctl restart ai-music-playlist-generator
```

In normal operation, leave `AIMP_WORKER_CLAIM_VIDEO_JOBS=true` or unset so the VM handles audio render, video render, Slack sync, and YouTube upload jobs.

The protected Nginx template exposes `/api/render-worker/` without Google OAuth, allows large MP4 uploads up to `4G`, disables request buffering, and extends proxy timeouts. Apply the updated template on the VM if it is not already installed:

```bash
sudo cp deploy/oracle/nginx-ai-music-playlist-generator-protected.conf /etc/nginx/sites-available/ai-music-playlist-generator
sudo nginx -t
sudo systemctl reload nginx
```

## External Worker Setup

On any render machine with network access to the app:

```bash
git clone <repo-url> ai-music-playlist-generator
cd ai-music-playlist-generator
uv sync
sudo apt-get update
sudo apt-get install -y ffmpeg

export AIMP_LOCAL_API_BASE="https://ai-music.168.107.34.175.sslip.io/api"
export AIMP_RENDER_WORKER_SHARED_TOKEN="<same token from main VM>"
./scripts/render-worker --worker-id oracle-a1-render-1 --work-dir /mnt/render-worker
```

Use `--once` for a smoke test:

```bash
./scripts/render-worker --once --worker-id test-render-worker
```

For a persistent worker, run it inside `tmux`, `systemd`, or OpenClaw's always-on session. Multiple workers can run at the same time; each claimed job has a lease token so only the worker that claimed it can download assets or upload completion.

## Systemd Worker Example

```ini
[Unit]
Description=AI Music external render worker
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ai-music-playlist-generator
Environment=AIMP_LOCAL_API_BASE=https://ai-music.168.107.34.175.sslip.io/api
Environment=AIMP_RENDER_WORKER_SHARED_TOKEN=replace-me
ExecStart=/home/ubuntu/ai-music-playlist-generator/scripts/render-worker --worker-id %H --work-dir /home/ubuntu/render-worker
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Operational Notes

- By default, the main app worker should render jobs on the VM. External workers simply compete for queued `build_video` jobs only when you intentionally run them.
- If `AIMP_WORKER_CLAIM_VIDEO_JOBS=false` is set on the main app VM, queued `build_video` jobs are reserved for external render workers. Use this only when an external worker is stable and intentionally online.
- Workers should not create releases or call YouTube directly. They only render MP4 files and hand them back to the app.
- If the worker process is killed, the job stays `running` until the one-day stale timeout and then becomes `queued` again.
- If ffmpeg fails and the worker can still reach the API, the job is marked `video_build_failed` immediately instead of waiting a day.
