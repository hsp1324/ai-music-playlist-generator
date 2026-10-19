# Weekly publishing

## Publishing schedule — effective 2026-10-19

Every channel publishes at most one video each Wednesday at 07:00 Asia/Seoul (Tuesday 22:00 UTC). This overrides all older daily, dual-slot, and branch-specific times below. Upload/render/metadata preparation may continue on other days; public publication must use the server-calculated weekly slot.
Cinematic Pulse shares ONE weekly channel slot: orchestra on 2026-10-21, cute_game on 2026-10-28, orchestra on 2026-11-04, alternating every week thereafter. Each lane therefore publishes every 14 days, always at 07:00. Set the exact lane; do not schedule two videos on the same Wednesday. Do not manually reintroduce daily timestamps. Follow `docs/openclaw-weekly-publishing.md`.

The Oracle server owns the publication calendar. OpenClaw queues normal uploads through the app; external PCs keep rendering and uploading artifacts as before. The background worker recalculates a slot at upload time, so stale daily timestamps cannot override the new calendar. Listener comment priority inserts and shifts whole weeks.

Existing public videos are preserved. Future YouTube reservations must be updated through YouTubeService.update_video_schedule as well as the app database; changing only local metadata does not reschedule a YouTube video. Keep a migration journal and verify the resulting YouTube status.

The fixed Cinematic Pulse anchor makes concept order independent of upload/render completion order. Missing one lane does not allow the other lane to steal its week. Its backlog summary includes each lane's anchor date and fourteen-day interval.
