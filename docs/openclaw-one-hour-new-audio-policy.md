# One-Hour Playlist Audio Policy

This is the highest-priority duration and Suno-credit rule for every new automatic Playlist Release. It supersedes older instructions that say to make only a 10- or 15-minute fresh block, prefer a reuse-only lane, publish below one hour when matching reuse is limited, or select another genre because the current lane lacks a catalog.

## Required production outcome

- Before `render-audio` or `render-video`, every new playlist must contain at least `3600` seconds (one hour) of approved, renderable audio. Aim slightly above the threshold so a rejected or failed upload cannot leave the release under one hour.
- First reuse eligible same-channel, same-detailed-lane tracks when they genuinely fit. Reuse is optional capacity, not a reason to lower the target.
- When eligible reuse does not bring the release to one hour, keep generating and uploading new Suno tracks in the *same* detailed lane until the approved total reaches the target. Do this for new/rare genres, Soft Hour solo piano, vocal arrangement families, former Storylight-style Cinematic Pulse lanes, and 불송 as well as ordinary channels.
- Do not substitute unrelated catalog tracks, broaden the selected genre, or abandon the current playlist simply because matching reuse is scarce. Generate additional new material in the selected lane instead.
- Suno credit availability is intentionally ample. Do not apply a credit-saving 10-minute-new-audio cap or a reuse-only rule while credits remain available.

## Quality guardrails stay in force

- Keep each Suno track as a complete, natural song or cue with a real introduction, developed middle, and resolved ending. Do not force awkward duration caps into prompts.
- Verify the downloaded file and app-reported duration before approval. Reject corrupt, empty, obviously unfinished, incoherent, wrong-lane, wrong-vocal-family, or otherwise unusable results.
- The normal playlist minimum remains 60 seconds unless the human explicitly approves a shorter track. There is no default maximum; complete 5+ minute tracks remain valid.
- A temporary provider outage, account/authentication failure, or a failed upload still requires normal failure handling. It is not permission to render a new release below one hour while usable Suno generation remains available.

Already-rendered or `publish_ready` legacy releases are not reopened only to add duration; publish those through the normal finish flow. This policy applies when creating or resuming new production before audio render.
