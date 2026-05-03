# OpenClaw Upload Workflow

Use this when OpenClaw has generated an audio file and needs to hand it to the AI Music web app.

For higher-level OpenClaw skill instructions, including "make one single", "build a one-hour playlist", and "write YouTube metadata", see [openclaw-skills.md](openclaw-skills.md).
For the metadata-specific command and prompt, see [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).

Run these commands on the Oracle VM from the repo root:

```bash
cd /opt/ai-music-playlist-generator
```

Do not use the public `https://ai-music...sslip.io` URL from OpenClaw. Public traffic is protected by Google login. Use the local API through the helper script instead.

## Upload A New Single Candidate Set

Use this when Suno/OpenClaw produced one or two candidates for the same single release. Suno usually returns two songs; upload both to the same new Single Release so a human can choose. If both are good, the second approved candidate becomes its own Single Release instead of being combined.

Preferred flow: create the Single Release before opening Suno, then upload the candidates to the returned `release.id`.

```bash
scripts/openclaw-release create-release \
  --workspace-mode single \
  --release-title "Song Title" \
  --description "Short concept for this single candidate set"

scripts/openclaw-release upload-single-candidates \
  --release-id RELEASE_ID \
  --audio /absolute/path/to/song-a.mp3 \
  --audio /absolute/path/to/song-b.mp3 \
  --cover /absolute/path/to/cover-a.png \
  --cover /absolute/path/to/cover-b.png \
  --lyrics-file /absolute/path/to/song-a-lyrics.txt \
  --lyrics-file /absolute/path/to/song-b-lyrics.txt \
  --style "Suno style/settings used for this prompt" \
  --prompt "Short generation prompt or notes" \
  --tags "ai music, single"
```

The command returns JSON with:

- `release.id`
- `release.title`
- `tracks[].id`
- next action

After this, both candidates appear in the web/Slack review queue. A human can approve one candidate. If both candidates are good, approve both; the app keeps the first selected track in the original Single Release and splits the second selected track into a new Single Release. If both candidates are rejected, the Single Release is automatically archived instead of deleted. It can be restored from the web UI archive.

Cover behavior:

- `--cover` is optional.
- `--release-id` should be the id returned by `create-release` before Suno generation. Use `--release-title` only as a fallback when OpenClaw did not precreate the workspace.
- Use one `--cover` to share the same cover across all uploaded candidates.
- Use one `--cover` per `--audio` to upload candidate-specific covers.
- When a Single Release candidate is approved, its uploaded cover is automatically registered as that release's cover. If both candidates are approved, each approved song should continue with its own cover/thumbnail/loop-video assets.

Lyrics/content behavior:

- `--lyrics` or `--lyrics-file` is optional only for BGM/instrumental/unknown-lyrics material. OpenClaw should provide it whenever Suno generated lyrics, meaningful song content, or instrumental arrangement notes.
- If lyrics are truly unknown, omit the flag or pass an empty value. For planned instrumental work, prefer non-sung arrangement notes over an empty field.
- BGM/background/lofi/study/sleep/cafe tracks are instrumental/no-vocal by default unless the human explicitly asks for vocals. For Soft Hour Radio or other instrumental BGM, do not leave the Suno lyrics/custom-lyrics field completely blank. Write detailed non-sung arrangement notes and upload those notes with `--lyrics` or `--lyrics-file`. The notes should include a no-vocal guardrail, tempo/feel, instrument palette, section-by-section musical flow, dynamics/transitions, and an avoid-list for vocals/humming/spoken words/choirs/vocal chops.
- J-pop/K-pop/pop/Japanese pop/anime-pop tracks are vocal by default. Unless the human explicitly requested instrumental/BGM/lofi/no vocals, create or capture original lyrics and pass them with `--lyrics` or `--lyrics-file` for every uploaded pop-family track. Use Japanese lyrics for J-pop/Japanese pop/anime-pop, Korean lyrics for K-pop, and the requested language or natural English/Korean lyrics for generic pop. The helper now rejects pop-family uploads with empty lyrics before publish unless the concept explicitly says BGM/instrumental/no-vocal.
- Lyrics are stored with the track so future thumbnail, Dreamina loop-video, metadata, or standalone single publishing work has song-content context.

Style behavior:

- `--style` is optional, but OpenClaw should provide it whenever the Suno style/settings are known.
- Use one `--style` for a shared prompt style, or one `--style` per `--audio` when candidates used different settings.
- For playlist releases, prefer one `--style` per `--audio`. Do not reuse the exact same style string for many tracks unless the human explicitly asks for a very uniform BGM set.
- Even inside the same genre, vary tempo, energy, instruments, rhythm feel, vocal tone, mood, and production details across tracks. The goal is a coherent playlist, not duplicated songs.
- Style is stored with the track so future remake, thumbnail, Dreamina loop-video, and metadata work can see how the song was generated.

Audio duration and integrity:

- Do not rely on guessed or planned duration values from Suno/OpenClaw. The server probes uploaded local audio with ffprobe and uses the real file duration when it can read the file.
- If an upload returns an empty/unreadable audio error, the source file did not transfer correctly. Re-download or re-export that Suno track and upload it again; do not continue to render or publish with that release.
- The helper retries each audio upload up to 3 times. If a playlist automation track still fails, it records a Slack warning, continues uploading the remaining tracks, then stops before render/publish so a partial release cannot reach YouTube.
- Treat the command JSON as the upload receipt. A successful upload includes `ok: true`, the uploaded `track.id`, `track.status`, and the probed `duration_seconds`. If `duration_seconds` is `0`, missing, or far from the local file duration, fix and re-upload before continuing.

## Upload One New Single Candidate

Use this for one generated song that should become its own single release candidate.

```bash
scripts/openclaw-release upload-audio \
  --new-single \
  --audio /absolute/path/to/song.mp3 \
  --cover /absolute/path/to/cover.png \
  --title "Song Title" \
  --lyrics-file /absolute/path/to/song-lyrics.txt \
  --style "Suno style/settings used for this song" \
  --prompt "Short generation prompt or notes" \
  --tags "ai music, single"
```

The command returns JSON with:

- `release.id`
- `release.title`
- `track.id`
- next action

After this, the track appears in the web/Slack review queue. A human should approve it before render.
If `--cover` is provided and this is a Single Release, approving the track automatically registers that image as the release cover.

## Upload One Playlist Track

When `scripts/openclaw-release upload-audio` targets an existing Playlist Release, the helper now uploads the track and immediately approves it into the playlist. It also skips the per-track Slack review message so a one-hour playlist does not spam Slack.

Playlist track titles should look like final tracklist titles, not Suno alternatives. Do not upload names like `Title A`, `Title B`, `Title 1`, `Title 2`, `Title - Morning`, or `Title - Evening`. Give every playlist item a standalone title that fits the mood.

```bash
scripts/openclaw-release upload-audio \
  --release-id RELEASE_ID \
  --audio /absolute/path/to/playlist-track.mp3 \
  --title "Track Title" \
  --lyrics-file /absolute/path/to/playlist-track-lyrics.txt \
  --style "Suno style/settings used for this track" \
  --prompt "Short generation prompt or notes" \
  --tags "ai music, playlist"
```

The JSON result should include:

- `auto_approved: true`
- `track.status: approved`

Only use `--pending-review` if the human explicitly asks to review playlist tracks one by one.

If OpenClaw uploads many playlist files in one automation run, prefer `auto-publish-playlist` with one `--title` per `--audio` so the final YouTube tracklist already has natural titles.
Also pass one `--lyrics` or `--lyrics-file` per `--audio` when lyrics or instrumental arrangement notes are available. For BGM/background/instrumental tracks, prefer non-sung arrangement notes over empty lyrics. For J-pop/K-pop/pop/Japanese pop/anime-pop releases, lyrics are expected by default and should be uploaded for every track unless the human explicitly requested instrumental/BGM/lofi/no vocals. Pass one shared `--style` or one `--style` per `--audio` whenever Suno style/settings are known.
For pop-family releases, do not proceed without lyrics. If Suno returns a vocal song but no lyric text is visible, write/capture the final intended lyrics before uploading. If the human explicitly wants a J-pop-feeling instrumental, include BGM/instrumental/no-vocal wording in the prompt/title/tags so the helper treats empty lyrics as intentional.
For vocal playlist releases, write a different lyric concept for every track before generation. Do not reuse the same chorus hook, verse structure, or only swap a few words between songs. Each track should have a distinct emotional angle and memorable phrase.

For full automatic playlist publishing, two final 16:9 images are required.

- `--cover /absolute/path/to/video-cover.png`: playback visual used inside the rendered video. For releases with a moving loop video, this is text-free by default because it is also the Dreamina/Seedance first-frame reference. If the human explicitly requests channel text inside the video, it may include only the lower-left channel label.
- `--thumbnail /absolute/path/to/youtube-thumbnail.png`: YouTube click thumbnail. Include short readable text and a small brand mark for the selected channel.

Do not rely on the app's generated draft cover for YouTube upload. Do not reuse the cover as the thumbnail unless the human explicitly approves one image for both roles. The thumbnail is for clicks and should have text; the cover is the clean still-image fallback and Dreamina/Seedance first-frame reference, so it should not have text.

Static image creation rules:

- Follow the channel-specific visual skill rules in [openclaw-visual-assets.md](openclaw-visual-assets.md). Do not apply the Tokyo/J-pop three-people-walking signature to every channel.
- Do not use Dreamina for static cover or YouTube thumbnail images.
- Use OpenAI GPT Image models for static image generation. Prefer `gpt-image-2` when available; otherwise use the currently available GPT Image model in the running OpenAI/Image tool environment. Do not assume OpenAI API usage is free; use the available image tool or configured API credentials.
- If `gpt-image-2` is unavailable in the actual tool/API environment, fall back to the best available GPT Image model instead of using Dreamina for static images.
- Produce 16:9 images, preferably `1280x720` or `1920x1080`.
- Create the final clean cover first. Then create the YouTube thumbnail from that exact final cover as an image-to-image edit/reference derivative. Do not make the thumbnail as a fresh unrelated generation.
- For `Tokyo Daydream Radio` or Japan/J-pop releases, use the Tokyo Daydream Radio visual skill: exactly three people seen from behind, walking forward away from the viewer into the scene, unless the human requests a different visual concept.
- For `Soft Hour Radio` or default BGM/cafe/sleep/study/chill releases, use the Soft Hour Radio visual skill: calm atmospheric scenes such as cafe windows, piano rooms, rain, moonlit rooms, nature, candles, desk lamps, or abstract warm light. Do not use the three-people-walking signature by default.
- Human visual requests override the selected channel visual skill. If the human asks for a specific scene, subject, action, camera angle, object, animal, character type, or video concept, use that request consistently for the cover, thumbnail, and loop video.
- For thumbnails, the main default/requested subject must stay centered and visually important. Text must not push it to the side, crop it, cover it, or make it feel secondary. Put text into safe negative space around the centered composition.
- Keep every static visual animated, anime, illustrated, or stylized. Do not use photorealistic, live-action, documentary, camera-photo, or realistic human footage.
- The cover should be a clean text-free version of the channel/requested scene. The YouTube thumbnail should use the same composition plus large readable click text and channel branding.
- When deriving the thumbnail from the cover, preserve exact subject count, relative positions, silhouettes, clothing colors, major props, background landmarks, lighting, palette, and camera angle. Only add text, channel branding, crop/contrast/readability adjustments, and small layout refinements. Example: if a cloak is red in the cover, it must stay red in the thumbnail.
- If the thumbnail changes character identity, clothing color, subject placement, or core background compared with the cover, reject it and regenerate before upload.
- For Japan/J-pop releases on `Tokyo Daydream Radio`, keep a consistent channel thumbnail system across Tokyo/city, forest/nature, and beach variants: large `J-POP` text with smaller `TOKYO DAYDREAM RADIO` directly beneath it. Use the same full-bleed layout as the approved channel examples, with either the Tokyo three-person back-view composition or the centered human-requested visual composition.
- For `Soft Hour Radio`, use thumbnail wording such as `DEEP SLEEP`, `CAFE PIANO`, `FOCUS MUSIC`, `RAINY NIGHT`, `STUDY BGM`, or `CALM READING`, with smaller `SOFT HOUR RADIO` branding.
- Do not add duration text or badges to thumbnails. Avoid `1 HOUR`, `60 MIN`, `1時間`, clocks, timers, and duration stickers.
- Use the clean cover or a separate clean no-text first-frame image for Dreamina/Seedance video generation by default. Do not use the final text thumbnail as the first-frame reference; generated video often makes text flicker, disappear, or reappear in the loop.
- Text-in-video exception: if the human explicitly asks for channel text inside the video, create the cover/first-frame with a small lower-left channel label such as `Tokyo Daydream Radio`. Let GPT Image design the font/lettering to match the scene, channel, and genre, while keeping the exact requested spelling readable. This cover/first-frame may then be used in Dreamina/Seedance.
- When using the text-in-video exception, the lower-left channel label is the only allowed baked-in moving-visual text unless the human explicitly asks for more. Do not add titles, lyrics, subtitles, UI, logos, duration badges, or unrelated words inside the moving visual.

Optional moving visual:

- `--loop-video /absolute/path/to/dreamina-loop.mp4`: exactly 8 second Dreamina/Seedance visual clip. The app repeats it during video render.
- OpenClaw should generate/download only the short clip. Do not export a one-hour MP4 from OpenClaw.
- The app uses smooth 2 second forward crossfade looping by default. It uses the actual uploaded clip length, normally 8 seconds, then fades the end of each forward pass into the beginning of the next forward pass so the join feels like a dissolve instead of a sudden jump.
- Use `--hard-loop-video` only if the clip is already a perfect seamless loop and direct repeat is preferred.
- If the human expects a moving final video, `--loop-video` must be a separate MP4 asset. Do not use the thumbnail image or text cover as the moving video visual.

Dreamina website workflow for OpenClaw:

- Use `https://dreamina.capcut.com/ai-tool/home/` for browser-based Dreamina/Seedance generation.
- Use Dreamina/Seedance `2.0 Fast`.
- Do not use Omni Reference.
- Use the first/last-frame workflow if the UI asks which mode to use, but provide only the first-frame image.
- Start from the clean text-free cover image or a separate clean text-free first-frame image by default. It should match the YouTube thumbnail scene and composition, including any explicit human visual request. If the human explicitly requested channel text inside the video, the first-frame image may contain only that lower-left channel label; it must not contain title text or unrelated text.
- Leave the last-frame input empty. Do not upload a last-frame reference; it makes the generated motion too static.
- Set ratio to `16:9` when selectable.
- Set quality to `720p` when selectable.
- Generate exactly one `8 second` MP4.
- Download the generated MP4 to the VM or OpenClaw workspace.
- Confirm the file exists locally before passing it to `--loop-video`.
- If login, CAPTCHA, subscription limits, or manual approval blocks generation/download, stop and report the blocked step. Do not continue without `--loop-video` unless the human explicitly accepts a still-image video.

Dreamina/Seedance motion prompt guidance:

- Do not ask Dreamina for a loop. By default, ask for one continuous forward-moving video shot. If the human requested a different motion/camera concept, ask for that requested continuous shot instead.
- Do not put duration, ratio, or quality in the prompt. Set those in Dreamina controls only.
- Do not include `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the prompt. These words can make Seedance/Dreamina create a shorter repeated segment inside the clip.
- Ask Dreamina/Seedance to preserve the clean first-frame image's composition, lighting, palette, illustrated/anime style, and channel/requested subject/action in the first shot.
- Use Tokyo-style camera-follow movement from behind only for Tokyo Daydream Radio/J-pop visuals. For Soft Hour Radio, prefer slow environmental motion such as rain, candle flicker, curtains, moonlight, ocean shimmer, forest light, or piano-room ambience. Always require stable composition, no hard cuts, no text overlays, no subtitles, no logos, no UI, no photorealism, and no extra unwanted people or characters.
- If the first-frame image intentionally includes a lower-left channel label, ask Dreamina/Seedance to preserve that exact text, spelling, font/lettering, placement, color, and readability for the full clip. Ask it not to rewrite, translate, blur, morph, move, hide, flicker, or change the text. Keep the text area stable and animate only the surrounding scene subtly.
- After generation, inspect the downloaded MP4. Reject and regenerate if the lower-left channel label is missing, unreadable, misspelled, flickering, morphing, moving drastically, or changing style.
- Do not include `start and end frames match` or equivalent wording. The app handles smooth repeat with forward crossfade rendering, and forcing the last frame to match can make the clip too static.
- Prefer atmospheric scenes that match the channel mood: cafe window, moonlit room, soft rain, abstract light, slow landscape, piano/candle detail.
- If the model outputs audio, ignore it; the app uses the rendered playlist audio.

Recommended Dreamina prompt shapes are in [openclaw-visual-assets.md](openclaw-visual-assets.md). Use the Tokyo prompt only for Tokyo/J-pop releases and the Soft Hour prompt for Soft Hour/default BGM releases.

Tokyo/J-pop Dreamina prompt shape:

```text
Use the uploaded clean text-free first-frame image as the exact starting frame.
Create one continuous forward-moving animated music visualizer shot.
Keep the Tokyo Daydream Radio signature: exactly three people seen from behind, walking away from the camera into the scene.
The viewer should see backs and backs of heads, not front-facing faces.
The motion must progress forward naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
Preserve the opening composition, lighting, palette, and anime/illustrated style.
Adapt the background and atmosphere to the release concept.
Add subtle camera-follow movement from behind, gentle environmental motion, reflections, rain shimmer, particles, or soft light motion.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no text, no subtitles, no logos, no UI, no extra people or characters.
```

Soft Hour/default BGM Dreamina prompt shape:

```text
Use the uploaded clean text-free first-frame image as the exact starting frame.
Create one continuous calm animated music visualizer shot for a background-music release.
Do not use the Tokyo three-people-walking signature unless explicitly requested.
Preserve the opening composition, lighting, palette, and illustrated/stylized visual language.
Adapt the motion to the release mood: soft rain, candle flicker, drifting dust, slow moonlight, gentle curtains, ocean shimmer, forest light, piano-room ambience, or warm abstract light.
The motion must progress naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no text, no subtitles, no logos, no UI, no unwanted people or characters.
```

If the human provided a specific visual/video request, replace the selected channel default subject/action/camera details with the requested scene, subject, action, motion, and camera angle. Keep the rest of the constraints: one continuous shot, no repeated segment, no ping-pong, preserve first-frame composition/style, no text, no subtitles, no logos, no UI, and no extra unwanted subjects.

If the human explicitly requested lower-left channel text inside the video, replace `no text` with: `The uploaded first frame contains the exact lower-left channel label "{CHANNEL_NAME}" (for example, "Tokyo Daydream Radio"). Preserve this text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, flicker, or change the text. Keep the text area stable; animate only the surrounding scene subtly. No other text, subtitles, logos, UI, or title words.`

Thumbnail text rules for OpenClaw:

- Use 2-4 large words that describe the use case or mood, for example `CAFE PIANO`, `DEEP SLEEP`, `FOCUS MUSIC`, `RUNNING BEATS`.
- Prefer the approved full-bleed style: strong image background, no card or panel, large bottom-left genre/mood text, and a smaller channel-brand line directly below.
- For Japan-related releases routed to `Tokyo Daydream Radio`, use the channel name as the brand line. The approved J-pop pattern is large `J-POP` with `TOKYO DAYDREAM RADIO` beneath it. Keep this same two-line treatment for Tokyo/city, forest/nature, and beach versions to create channel consistency.
- Do not add support text or duration badges. The thumbnail should not say `1 HOUR`, `60 MIN`, `1時間`, or show a time badge.
- Keep text large enough to read on a phone.
- Avoid long titles, dense paragraphs, fake UI, and obviously AI-looking distorted text.
- Keep the main default/requested subject centered and visible even when thumbnail text is added.

Localized YouTube metadata rules for OpenClaw:

- The app can upload YouTube localized metadata for `ko`, `ja`, `en`, and `es`.
- For `Tokyo Daydream Radio`, Japan, Tokyo, city-pop, J-pop, anime, or Japanese lofi releases, always write all four language versions.
- Use Korean as the default upload metadata. Pass Korean through `--title` and `--description-file`, and also pass `--ko-title` and `--ko-description-file`.
- Pass Japanese through `--ja-title` and `--ja-description-file`. This should be natural Japanese copy, not a literal Korean line-by-line translation.
- Pass English through `--en-title` and `--en-description-file`. This should be natural English YouTube copy for international listeners.
- Pass Spanish through `--es-title` and `--es-description-file`. This should be natural Spanish YouTube copy for Spanish-speaking listeners.
- End every localized description with a public hashtag line. `--tags` is still required, but it only sends YouTube API tags and does not replace visible description hashtags.
- For playlist/BGM titles, include listening use cases in the title itself, for example study, work, walk, drive, sleep, reading, or rest. The title should not be only mood plus genre.
- For Japan/J-pop/Tokyo Daydream Radio titles, do not over-emphasize the language. Prefer `J-POP`, `Tokyo`, city-pop, mood, and listening use cases. Avoid Korean title phrases like `일본어 J-pop`, `일본어 보컬`, or `일본어 카페 재즈` unless the human explicitly asks to highlight the language. If language matters, mention it naturally in the description instead; the thumbnail/channel branding can carry `J-POP`.
- In Korean title/description/localizations, do not use the transliterated words `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`. Use `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡`.
- Keep all localized titles under 100 characters. Keep timestamps identical across languages; translate only the displayed title text and surrounding description.
- For Japan/J-pop/Tokyo Daydream Radio timestamped tracklists, format localized rows by language: Korean/default uses Japanese title plus Korean translation in parentheses, Japanese uses Japanese title only, English uses English translated title only, and Spanish uses Spanish translated title only.
- If the release is one hour or longer, use `HH:MM:SS` for every timestamp in every localized description. Start with `00:00:00`, not `00:00`, and use `01:00:00+` after the one-hour point so YouTube can link those chapters reliably.

Example localized metadata approval:

```bash
scripts/openclaw-release approve-metadata \
  --release-id RELEASE_ID \
  --title "기분 좋아지는 J-POP 1시간 | 산책, 드라이브, 작업할 때 듣는 플레이리스트" \
  --description-file /tmp/metadata-ko.txt \
  --tags "Jpop,JapanesePop,TokyoDaydreamRadio,Playlist,DriveMusic,WorkMusic" \
  --ko-title "기분 좋아지는 J-POP 1시간 | 산책, 드라이브, 작업할 때 듣는 플레이리스트" \
  --ko-description-file /tmp/metadata-ko.txt \
  --ja-title "気分が上がるJ-POP 1時間 | 散歩・ドライブ・作業用プレイリスト" \
  --ja-description-file /tmp/metadata-ja.txt \
  --en-title "Feel-Good J-Pop 1 Hour | Walk, Drive, Work Playlist" \
  --en-description-file /tmp/metadata-en.txt \
  --es-title "J-Pop alegre 1 hora | Playlist para caminar, conducir y trabajar" \
  --es-description-file /tmp/metadata-es.txt
```

## YouTube Channel Routing

For automatic playlist publishing, `scripts/openclaw-release auto-publish-playlist` chooses the YouTube channel from the release concept when `--youtube-channel-title` is omitted.

- Use `Soft Hour Radio` for default background/cafe/sleep/study/chill playlists.
- Use `Tokyo Daydream Radio` for Japan, Tokyo, Shibuya, Shinjuku, Japanese lofi, city pop, J-pop, anime, vaporwave, 일본, 도쿄, 시티팝, 애니, 제이팝, 日本, 東京, 渋谷, 新宿, アニメ, or シティポップ concepts.
- Pass `--youtube-channel-title "Tokyo Daydream Radio"` explicitly when the human asks for Japanese/Tokyo/city-pop/anime music.
- Do not use `MusicSun` unless the human explicitly requests it.
- After publish, `/api/playlists/workspaces` exposes `youtube_video_id`, `youtube_channel_id`, and `youtube_channel_title`. OpenClaw can use those fields to confirm which channel received the private upload; web UI layout changes do not affect OpenClaw because it should use the helper script or local API, not click the dashboard.
- YouTube publish/re-upload uses the app setting `AIMP_YOUTUBE_CONTAINS_SYNTHETIC_MEDIA=false` by default, meaning uploads are submitted as not containing realistic altered/synthetic media. Do not override this unless the requested video realistically depicts altered or synthetic people, places, or events.
- YouTube publish/re-upload always declares `selfDeclaredMadeForKids=false`, meaning "No, it's not made for kids." OpenClaw does not need to set this separately.

## Web Review Surface

After OpenClaw uploads audio, the web UI shows the selected release as a music-library style list:

- Clicking a release card opens a focused `?release=...` page instead of scrolling to a lower dashboard panel.
- `Awaiting Approval` contains uploaded candidates with cover art, duration, player controls, prompt notes, and approve/hold/reject actions.
- `Final Order` contains approved tracks in playlist order. Playlist releases can be reordered by drag/drop before audio rendering.
- Single Releases end with one selected track. If two reviewed candidates are both approved, the app splits the second one into a separate Single Release instead of combining them. Playlist Releases may contain many approved tracks.
- The web UI defers automatic polling while any audio player is actively playing, so mobile playback is not interrupted by background refresh.
- Starting one web audio player pauses any other currently playing web audio player.

OpenClaw should only upload candidate files and report the returned JSON. It should not depend on the UI layout, approve tracks, reorder tracks, render audio/video, or publish unless the human explicitly asks.

## Slack Audio Preview Behavior

Slack review alerts are intended to show a playable audio preview directly in Slack:

- Local uploaded files are sent to Slack as audio files.
- Remote Suno/CDN audio URLs are downloaded by the app server and then sent to Slack as audio files.
- If Slack upload fails, the app falls back to a normal review message with an audio link so review is not blocked.

For the most reliable Slack preview, prefer passing a real local audio file path to `scripts/openclaw-release`. If OpenClaw only has a remote Suno URL, the app can still post a Slack-playable preview as long as the URL is publicly fetchable from the VM.

## Remote Audio Playback Rule

Mobile browsers can stop playback when they stream directly from temporary Suno/CDN URLs. To avoid that, the app now caches remote `audio_url`/`audio_path` values into local VM storage at intake time and serves playback from `/media/...`.

Operational rules for OpenClaw:

- Prefer uploading a local audio file path when possible.
- If only a remote Suno/CDN URL is available, submit it as `audio_url` or `audio_path`; the app will download it into local storage before creating the track.
- Do not leave release candidates pointing directly at `cdn1.suno.ai` unless the local cache step fails and the failure is reported to the human.
- Existing remote-only tracks should be backfilled to local storage before serious mobile review.
- Upload all intended playlist tracks before starting audio render, video render, metadata approval, or YouTube publish. Reaching the target duration does not auto-start audio render anymore; OpenClaw must explicitly call the render step only after the upload set is complete. If late tracks are added after rendering starts, the app treats the existing render as stale and requires or queues a fresh render so the YouTube timeline cannot become longer than the actual video.

## Upload To Existing Release

First list release ids:

```bash
scripts/openclaw-release list-releases
```

Then upload audio to a chosen release:

```bash
scripts/openclaw-release upload-audio \
  --release-id RELEASE_ID \
  --audio /absolute/path/to/song.mp3 \
  --cover /absolute/path/to/cover.png \
  --title "Standalone Track Title" \
  --prompt "Short generation prompt or notes" \
  --tags "playlist candidate"
```

Use existing playlist releases for multi-song playlist releases. A Single Release may hold up to two review candidates, but only one can be approved and selected for the final single. Track-level covers are used automatically only for approved Single Release candidates; Playlist Release covers should still be chosen at the release level.

## Upload Cover Image

Only do this after release audio is ready. Playlist releases should show `Rendered Mix`; Single Releases use the approved source audio directly.

```bash
scripts/openclaw-release upload-cover \
  --release-id RELEASE_ID \
  --cover /absolute/path/to/cover.png
```

Supported cover formats:

- `jpg`
- `jpeg`
- `png`
- `webp`

Preferred cover size is 16:9, for example `1280x720` or `1920x1080`.

After upload, the release moves to `cover_review`. A human should approve the cover in the web UI, then render video.

The web UI also has `Generate Draft Cover`, but that only creates a simple local placeholder PNG. It does not call Codex/OpenAI image generation. If OpenClaw creates better cover art elsewhere, upload that file with `upload-cover` or include it with the audio upload command.

## Suggested OpenClaw Instruction

Give OpenClaw this instruction before it starts Suno:

```text
Before opening Suno or generating audio, create or select the destination release in the local AI Music app from /opt/ai-music-playlist-generator.
For a new single candidate set, first create one Single Release:

scripts/openclaw-release create-release --workspace-mode single --release-title "TITLE" --description "CONCEPT"

For a new playlist/mix, first create one Playlist Release:

scripts/openclaw-release create-release --workspace-mode playlist --release-title "TITLE" --target-seconds 3600 --description "CONCEPT"

Keep the returned release.id. Do not create Suno songs before the release.id exists.
For an existing release, use --release-id and keep all related Suno outputs in that same workspace.
When the final audio file is ready, upload it to that same release.
When Suno returns two candidate songs for one single release, run:

scripts/openclaw-release upload-single-candidates --release-id RELEASE_ID --audio ABSOLUTE_AUDIO_PATH_A --audio ABSOLUTE_AUDIO_PATH_B --cover ABSOLUTE_COVER_PATH_A --cover ABSOLUTE_COVER_PATH_B --style "SUNO_STYLE_OR_SETTINGS" --prompt "PROMPT" --tags "TAGS"

Return the JSON result, especially release.id and tracks[].id.
Do not approve, render, or publish unless explicitly asked.
If only one candidate exists, run:

scripts/openclaw-release upload-audio --new-single --audio ABSOLUTE_AUDIO_PATH --cover ABSOLUTE_COVER_PATH --title "TITLE" --style "SUNO_STYLE_OR_SETTINGS" --prompt "PROMPT" --tags "TAGS"

Return the JSON result, especially release.id and track.id.
Do not approve, render, or publish unless explicitly asked.
If a 16:9 cover image is also ready and the release already has rendered audio, run:

scripts/openclaw-release upload-cover --release-id RELEASE_ID --cover ABSOLUTE_COVER_PATH
```

If the human explicitly asks OpenClaw to publish one single all the way to YouTube, use the automatic single publisher instead:

```text
Create an original single release and publish it privately.
Generate or obtain:
- one final Suno audio file per YouTube single
- a final clean 16:9 cover image
- a separate YouTube thumbnail image with readable text
- optionally one exactly 8 second Dreamina/Seedance loop video

Then run:

scripts/openclaw-release auto-publish-single \
  --release-id RELEASE_ID \
  --description "CONCEPT_FOR_METADATA" \
  --audio ABSOLUTE_AUDIO_PATH_01 \
  --title "INDEPENDENT_TRACK_TITLE_01" \
  --lyrics-file ABSOLUTE_LYRICS_PATH_01 \
  --style "SUNO_STYLE_OR_SETTINGS" \
  --cover ABSOLUTE_FINAL_CLEAN_COVER_IMAGE_PATH \
  --thumbnail ABSOLUTE_YOUTUBE_TEXT_THUMBNAIL_IMAGE_PATH \
  --loop-video ABSOLUTE_DREAMINA_SEEDANCE_8_SECOND_MP4 \
  --prompt "PROMPT" \
  --tags "TAGS" \
  --youtube-channel-title "Tokyo Daydream Radio"

For non-Japan releases, use "Soft Hour Radio" unless the human says otherwise.
Pass exactly one --audio/--title/--lyrics-file/--style per auto-publish-single run. If two Suno outputs are both good, create separate cover/thumbnail/loop-video assets and run auto-publish-single twice.
```

## Safety Rules

- Do not call `Approve Publish` automatically unless the human explicitly asks for full private publishing.
- Do not open Suno or generate audio before creating/selecting the app release workspace. Fresh work starts with `scripts/openclaw-release create-release`; continuing work starts with `scripts/openclaw-release list-releases` and `--release-id`.
- Do not upload to YouTube automatically unless using `auto-publish-single` or `auto-publish-playlist` after explicit human instruction.
- If cover art is ready with the audio, upload it in the same command with `--cover`; otherwise omit `--cover` and let the human add/regenerate cover later.
- If lyrics, meaningful song-content notes, or instrumental arrangement notes are available, upload them in the same command with `--lyrics` or `--lyrics-file`. Use an empty value only when lyrics/content are truly unknown.
- For BGM/background/lofi/study/sleep/cafe singles and playlists, instrumental/no-vocal is the default, but an empty lyrics/custom-lyrics field is not preferred. Write detailed non-sung arrangement notes that specify no vocals/no humming/no spoken words, tempo/feel, instruments, section flow, dynamics, transitions, and vocal-like sounds to avoid, then upload those notes. For J-pop/K-pop/pop/Japanese pop/anime-pop singles and playlists, do not leave lyrics empty by default. Generate/capture original lyrics and upload them; only use empty lyrics when the human explicitly asked for instrumental/no-vocal music or when Suno did not provide lyrics and OpenClaw reports that limitation.
- After every audio upload, confirm that the returned `duration_seconds` is close to the actual song length. If it is `0`, much shorter than expected, or the upload fails as unreadable, fix the source file and re-upload before moving on.
- For one-hour playlist automation, if a few songs fail after the 3 upload attempts, do not abandon the rest of the batch. Let the helper upload the remaining songs, read the Slack warning, then re-upload only the failed files and rerun render/publish after the release has the full intended track set.
- If Suno style/settings are available, upload them in the same command with `--style`.
- Do not generate a batch by repeating one Suno prompt/style/lyric template. Each new Suno request should have a distinct prompt/style/lyrics plan while staying inside the requested release mood.
- Treat generated draft covers in the web UI as replaceable placeholders, not final art.
- Use OpenAI GPT Image models for static cover and thumbnail images. Do not use Dreamina for static image generation.
- Static cover and thumbnail images must follow the channel-specific visual skills in [openclaw-visual-assets.md](openclaw-visual-assets.md). Tokyo/J-pop releases use the three-person back-view walking signature by default. Soft Hour Radio/default BGM releases use calm atmospheric visuals by default and must not use the Tokyo three-person walking signature unless explicitly requested.
- In thumbnails, keep the main channel/requested subject centered; text must not push it sideways.
- Generate the thumbnail from the final clean cover as a reference/edit derivative. Preserve characters, positions, outfit colors, lighting, palette, and background continuity; only add text/branding and readability adjustments.
- Do not use generated draft covers for full OpenClaw auto-publish runs. OpenClaw must create/upload a real final cover image first.
- Do not publish without a separate YouTube thumbnail image. OpenClaw must create/upload a text thumbnail and pass it as `--thumbnail`.
- If OpenClaw creates a Dreamina/Seedance loop clip, pass the 8 second MP4 as `--loop-video`. The app handles smooth crossfade repeat and long video rendering.
- Keep `--cover`, `--thumbnail`, and `--loop-video` separate. `--thumbnail` should have readable YouTube text. `--cover` and `--loop-video` are clean/no-text by default; if the human explicitly requests channel text inside the video, they may contain only the lower-left channel label. Never feed the text thumbnail into Dreamina/Seedance as the first frame; use the cover or a dedicated first-frame image. If the human requested a specific video visual, that visual request must be reflected consistently across all three assets.
- Use Dreamina/Seedance `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, and exactly `8 seconds` through UI controls for loop video generation. Do not put those settings in the prompt.
- For Playlist Releases, `upload-audio` auto-approves by default. Do not add `--pending-review` unless the human explicitly asks.
- For Playlist Releases, do not use pair/number titles. Replace Suno A/B or 1/2 output labels with independent track names before upload.
- For Suno two-output generations, upload both candidates to one Single Release using `upload-single-candidates`.
- Single Release candidates are still human-reviewed; the human may approve one candidate, approve both candidates as separate Single Releases, or reject both.
- If both candidates are rejected, the app will archive the release automatically; do not delete files or database rows manually.
- If three or more songs are ready for one release, use a Playlist Release instead.
