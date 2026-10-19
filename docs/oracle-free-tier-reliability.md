# Oracle 1 GiB VM resource guards

The production VM runs the web app and background worker as separate systemd
services. Keep `AIMP_WORKER_AUTOSTART=false` in the web app environment so jobs
are not also claimed inside Uvicorn. The render queue and YouTube upload queue
remain enabled in the separate worker; external video render workers still use
the web API.

The following drop-ins were deployed on 2026-09-16 to keep an oversized app
request from exhausting the whole VM:

| Unit | Soft memory limit | Hard memory limit | Swap limit |
| --- | ---: | ---: | ---: |
| Web app | None | 440 MiB | 512 MiB |
| Background worker | 260 MiB | 320 MiB | 256 MiB |

On 2026-09-17, the web app's 300 MiB soft limit was removed after it caused
sustained direct memory reclaim when the app grew beyond 380 MiB RSS and
reached its 256 MiB swap cap after a day of uptime. Restarting only the web
service cleared its accumulated memory; investigate recurring growth rather
than treating the restart as a permanent fix. The 440 MiB hard limit remains
to isolate an oversized request from the VM.

On 2026-09-18, kernel logs showed eight host-wide OOM kills of the web app
while more than 7 GiB of host swap was free. At an OOM snapshot both the web
app's 256 MiB and worker's 128 MiB cgroup swap caps were full. Their swap caps
were raised to 512 MiB and 256 MiB respectively, without changing their RAM
caps or restarting the worker. This lets the kernel reclaim more RAM into the
existing zram/disk swap instead of hitting the per-service caps first. Monitor
for new OOM kills and swap pressure; more total swap space is not the fix.

The web app also accepts at most 32 concurrent connections and a backlog of
128. Snapd restarts after 120 seconds instead of retrying immediately. The
Oracle Cloud Agent is a Snap service, so snapd must not be disabled casually.

To reapply the guards on this VM or a replacement using the same layout:

```bash
sudo install -D -m 0644 deploy/oracle/ai-music-web-resource-guard.conf /etc/systemd/system/ai-music-playlist-generator.service.d/zzzz-resource-guard.conf
sudo install -D -m 0644 deploy/oracle/ai-music-worker-resource-guard.conf /etc/systemd/system/ai-music-playlist-generator-worker.service.d/zzzz-resource-guard.conf
sudo install -D -m 0644 deploy/oracle/snapd-restart-backoff.conf /etc/systemd/system/snapd.service.d/90-resource-backoff.conf
sudo systemctl daemon-reload
```

Restart the web app after code or `ExecStart` changes. Restart the background
worker only when it has no active internal audio or YouTube upload job. A
systemd reload applies updated cgroup memory limits without restarting the
worker. Check the effective settings and service health:

```bash
systemctl show ai-music-playlist-generator.service ai-music-playlist-generator-worker.service -p MemoryHigh -p MemoryMax -p MemorySwapMax -p NRestarts
systemctl is-active ai-music-playlist-generator.service ai-music-playlist-generator-worker.service ssh.service nginx.service snapd.service
curl -fsS http://127.0.0.1:8000/health
```

If jobs fail after reaching a hard limit, inspect each service's
`memory.events` and journal before adjusting it. A hard limit restarts only
the affected service instead of allowing a global OOM; it does not prevent a
host-level block-storage outage. Repeated `database is locked` errors should
be investigated as long-running transactions or disk stalls, not handled by
blindly increasing SQLite timeouts.
