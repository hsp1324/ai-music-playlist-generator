# OpenClaw Channel Profiles

OpenClaw should decide the channel first, then read exactly one channel profile before making cover, thumbnail, or loop-video assets.

Recommended command:

```bash
scripts/openclaw-release channel-profile \
  --release-title "RELEASE_TITLE" \
  --description "RELEASE_CONCEPT" \
  --prompt "PROMPT_OR_STYLE" \
  --tags "comma,separated,tags"
```

If the human explicitly names a channel, include it:

```bash
scripts/openclaw-release channel-profile \
  --release-title "RELEASE_TITLE" \
  --description "RELEASE_CONCEPT" \
  --youtube-channel-title "Soft Hour Radio"
```

The command returns `youtube_channel_title` and `profile_doc`. Read that `profile_doc` and do not mix visual signatures from another channel.

Global branding rule for every channel:

- Every final cover/first-frame image must include the selected channel name as a small lower-left watermark.
- The cover/first-frame should contain only that channel name. Do not add title text, genre text, duration text, lyrics, UI, logos, or unrelated words to the cover/first-frame.
- The Dreamina/Seedance loop video must preserve the exact lower-left channel name for the full clip. Reject/regenerate clips where the channel name disappears, flickers, moves, morphs, changes spelling, changes style drastically, or becomes unreadable.
- The YouTube thumbnail still needs large click text above or near a smaller channel-brand line. Keep the channel-brand line size/style consistent with the cover watermark when possible.

Profiles:

- [Soft Hour Radio](soft-hour-radio.md)
- [Tokyo Daydream Radio](tokyo-daydream-radio.md)
