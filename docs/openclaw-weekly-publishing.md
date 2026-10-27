# Weekly publishing

## Publishing schedule — effective 2026-10-19

Each automated channel publishes at most once weekly at 07:00 Asia/Seoul on its assigned day: Monday HaruHaru and 불송; Tuesday Solwave Radio and BibliaCanto; Wednesday Tokyo Daydream Radio; Thursday Soft Hour Radio; Friday sundaze; Saturday Cinematic Pulse; Sunday Club Bloom. Storylight OST and MusicSun remain manual-only. The app calculates the slot; do not override it with a manual timestamp.
Cinematic Pulse shares one Saturday slot, alternating orchestra and cute_game each week. The orchestra parity anchor is 2026-10-24, and cute_game is 2026-10-31. Each lane publishes every 14 days at 07:00. Set the exact lane and follow `docs/openclaw-weekly-publishing.md`.

The Oracle server owns the publication calendar. OpenClaw queues normal uploads through the app; external PCs keep rendering and uploading artifacts as before. The background worker recalculates a slot at upload time, so stale daily timestamps cannot override the new calendar. Listener comment priority inserts and shifts whole weeks.

Existing public videos are preserved. Future YouTube reservations must be updated through YouTubeService.update_video_schedule as well as the app database; changing only local metadata does not reschedule a YouTube video. Keep a migration journal and verify the resulting YouTube status.

The fixed Cinematic Pulse anchor makes concept order independent of upload/render completion order. Missing one lane does not allow the other lane to steal its week. Its backlog summary includes each lane's anchor date and fourteen-day interval.
