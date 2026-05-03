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

Profiles:

- [Soft Hour Radio](soft-hour-radio.md)
- [Tokyo Daydream Radio](tokyo-daydream-radio.md)
