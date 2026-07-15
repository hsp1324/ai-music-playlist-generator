# Club Bloom YouTube Comment Request Pilot

This is a **Club Bloom-only** pilot. It lets a viewer explicitly request an
instrumental club-music playlist in a YouTube comment, then lets OpenClaw
produce that one request without interrupting ordinary backlog work.

Do not apply this workflow to any other channel until a human explicitly
expands the pilot.

## App API contract

The deployed app owns comment ingestion, deduplication, request state, release
provenance, and YouTube scheduling. OpenClaw must not scrape YouTube pages or
read comments with a browser.

The app should expose these authenticated coordination endpoints to
`scripts/openclaw-release` (or an equivalent app-owned helper):

1. `GET /api/openclaw/youtube-comment-requests?channel=Club%20Bloom&status=queued`
   returns only eligible, normalized explicit requests. Each item needs:
   `id`, `channel_title`, `source_video_id`, `comment_id`,
   `requester_display_name`, `requested_genres`, `requested_mood`,
   `requested_duration_seconds`, `normalized_prompt`, and `created_at`.
2. `POST /api/openclaw/youtube-comment-requests/{id}/claim` atomically claims
   one request for the current OpenClaw run and returns its latest payload.
3. `POST /api/openclaw/youtube-comment-requests/{id}/complete` records the
   resulting `release_id`, provenance, and scheduled publish time.
4. `POST /api/openclaw/youtube-comment-requests/{id}/defer` records a concise
   recoverable reason and leaves normal backlog selection unblocked.
5. `POST /api/openclaw/releases/{release_id}/prioritize-request` places a
   publish-ready request release in the request-priority lane and returns every
   changed schedule. The app, not OpenClaw, performs all date changes
   transactionally.

The comment collector must only accept direct playlist requests, reject spam
and duplicate comment IDs, retain the public commenter display name and channel
ID only for attribution, and never send raw comments to a public description.

## OpenClaw processing rules

When an app-originated `OPENCLAW_RUN:` asks for comment requests, read the
queued request endpoint before normal channel rotation.

- Claim at most one request per run, and only when `channel_title` is exactly
  `Club Bloom`.
- A request must contain a usable genre or genre fusion. Treat the request as a
  broad genre/mood direction, never as an instruction to imitate a specific
  living artist.
- Use approved, locally renderable Club Bloom tracks only. Reuse compatible
  tracks when they match the requested genre and energy, but make at least 40%
  of the final duration newly generated. If no compatible catalog exists,
  generate the whole requested playlist as new Club Bloom music.
- Keep the normal Club Bloom instrumental/no-vocal policy, visual policy,
  localization, copyright, lyric, and safety rules. A viewer request cannot
  override them.
- Store request provenance on the release: request ID, source video ID, comment
  ID, normalized genre/mood, and requester display name. Never create a second
  release for an already claimed or completed request.
- Add this first sentence to the main description, using the server-sanitized
  public display name: `Created in response to <requester_display_name>'s
  playlist request.` Use `Created in response to a listener's playlist
  request.` when no safe display name is available. Localized descriptions may
  translate the sentence but must preserve the attribution meaning.
- If claim, generation, or a required app API call fails, defer the request
  with the concrete reason, release the OpenClaw lock normally, and immediately
  continue ordinary backlog selection. Do not leave an empty workspace or a
  permanently held request claim.

## Request-priority scheduling

The app maintains two future-publish lanes:

1. **Request lane:** comment-request releases in claim order (FIFO).
2. **Normal lane:** ordinary scheduled releases in their existing order.

When a request release is publish-ready, `prioritize-request` schedules it
after the last future request-lane release and before every normal-lane release.
Every affected normal-lane release moves exactly one calendar day later per
inserted request, preserving its relative order. A later request release is
placed after the prior request release, not ahead of it. Do not change videos
that are already public, actively uploading/rendering, manually fixed, or have
an app-defined scheduling lock.

The API response is the source of truth for the final timestamps. OpenClaw must
report the request release and the shifted normal releases in Slack, but must
not edit YouTube publish times directly.
