# Standing Audio Pre-approval — 2026-10-16

## Publishing schedule — effective 2026-10-19

Every channel publishes at most one video each Wednesday at 07:00 Asia/Seoul (Tuesday 22:00 UTC). This overrides all older daily, dual-slot, and branch-specific times below. Upload/render/metadata preparation may continue on other days; public publication must use the server-calculated weekly slot.
Cinematic Pulse shares ONE weekly channel slot: orchestra on 2026-10-21, cute_game on 2026-10-28, orchestra on 2026-11-04, alternating every week thereafter. Each lane therefore publishes every 14 days, always at 07:00. Set the exact lane; do not schedule two videos on the same Wednesday. Do not manually reintroduce daily timestamps. Follow `docs/openclaw-weekly-publishing.md`.

Sunpyo Hong explicitly instructed that music in the AI Music workflow needs no individual approval request or listening review: treat the music as approved and continue autonomously. This latest instruction overrides older mandatory audition, Gemini/Flash/Pro audio-QC, spot-listening, confidence-score, and pending-human-review gates. It applies to every automatic channel and normal production upload, including music already waiting only for listening/quality approval.

## Normal production

- Do not ask a person to approve each song in `#all-ai-music-playlist-generator`, `#openclaw`, or another review channel. Do not post new per-track approval cards.
- Do not call an audio-listening model, wait for its quota/reply, or require a human audition before accepting an otherwise complete generated file. Old listening-QC failures or unavailable review capacity are not production blockers under this instruction. Do not invent an auditory review or a quality score: record `standing user pre-approval; no audition performed`.
- Keep non-listening checks: the actual complete file exists, has a decodable audio stream and duration, and retains the original generation identity/settings/lyrics. Do not mark a missing/corrupt/partial file as successfully downloaded or ready to render.
- For a Playlist Release, use `scripts/openclaw-release upload-audio` **without `--pending-review`**. Its established default sends `dispatch_review=false`, auto-approves into the existing playlist, and suppresses the per-track Slack review request. Verify `auto_approved=true` and `track.status=approved` in the response. Do not switch to raw intake with the default `dispatch_review=true`.
- For an already uploaded pending track in a viable, unfinished, inactive workspace, use the existing `/tracks/{track_id}/decisions` API with `decision=approve`, `source=agent`, an explicit original `playlist_id`, and rationale citing this standing instruction. Do not upload a duplicate. Preserve existing assignments, order, generated assets, ratings and provenance. Do not touch a published/archived release or active render/upload merely to clear a stale review record; production approval does not require reopening old releases. Revisit an active workspace only once its job is no longer active.
- For a normal explicitly authorized final-single publishing task, approve the chosen final audio without a song-review round. A later explicit request for review-only candidates still controls that particular task; automatic audio approval is not a new authorization to publish a standalone single or a manual-only channel.

## Boundaries that stay unchanged

Approval is **not** the human Good/like rating. Never set `user_rating=like`, erase a dislike, or mark unknown/legacy music as v6 on this basis. Keep the exact standard-v6 generation, verified-v6 reuse, optional human-Good legacy-tail rules, preserved existing work, channel/language/lyric planning, real-file provenance, complete-duration assembly, approved visual-source and app-managed render/publish requirements.

This is removal of the **audio approval/listening gate**, not removal of authentication, CAPTCHA/human-verification, billing, or file-integrity requirements. Do not change security/exec approval settings or claim all rendering/deployment issues were fixed. Keep meaningful progress/failure notices and scheduling; suppress song-approval requests, not operational notifications.

## Existing Slack cards and legacy records

Old Slack messages can remain as history; they are not an action required from the human. Existing uploaded, archived, manually disliked or file-deleted material stays intact. Do not approve-and-attach stale candidates to a published/active release: the decisions API can change workspace state and order. Use the supported quiet auto-approval path for all new production, and record precisely what legacy material was deliberately left untouched.
