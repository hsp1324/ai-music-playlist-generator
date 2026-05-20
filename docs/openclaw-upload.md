# OpenClaw Upload Workflow

Use this when OpenClaw has generated an audio file and needs to hand it to the AI Music web app.

For higher-level OpenClaw skill instructions, including "make one single", "build a 40-minute playlist", and "write YouTube metadata", see [openclaw-skills.md](openclaw-skills.md).
For the metadata-specific command and prompt, see [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).
For channel-specific image/video rules, first run `scripts/openclaw-release channel-profile` and read the returned `profile_doc` in [openclaw-channel-profiles](openclaw-channel-profiles/README.md). For next-release concept planning, read the returned `concept_doc` in [openclaw-channel-concepts](openclaw-channel-concepts/README.md).

Run these commands from the OpenClaw repo checkout, normally `~/repos/ai-music-playlist-generator` in the OpenClaw runtime. If that path is missing, try `~/repos/ai리포` or the current checkout.

Use `scripts/openclaw-release` against the deployed AI Music app API. `AIMP_LOCAL_API_BASE` must point to the deployed VM app API or a tunnel to that API. Do not use OpenClaw's own local dev API; if `/youtube/status` returns `configured=false`, `authenticated=false`, `ready=false`, or `channels=[]`, stop before generation/publish because the API target is wrong.

Recommended API target:

- If OpenClaw is running on the VM, use `AIMP_LOCAL_API_BASE=http://127.0.0.1:8000/api`.
- If OpenClaw is running on a laptop, use an SSH/Tailscale tunnel to the VM's `127.0.0.1:8000` and point `AIMP_LOCAL_API_BASE` at that tunnel.
- The public `https://ai-music.168.107.34.175.sslip.io/api` route is protected by Google login. It only works for `scripts/openclaw-release` when `AIMP_API_COOKIE` contains a valid logged-in browser cookie.
- `AIMP_OPENCLAW_SHARED_TOKEN` is for app-side OpenClaw lock/backlog endpoints only. It does not authenticate track upload, playlist, YouTube status, or publish helper calls.

Do not open `/youtube/status`, `/api/youtube/status`, `/youtube/connect`, `/api/youtube/connect`, Google OAuth, or YouTube Studio in a browser as part of automation. If YouTube is not ready, report the blocker. If it is ready, use the connected channel list from `scripts/openclaw-release youtube-status` and publish through `scripts/openclaw-release` with an explicit channel title/id.

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
  --exclude-style "Suno excluded styles/negative tags used for this prompt" \
  --prompt "Short generation prompt or notes" \
  --tags "Pop,Single,Music"
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

- `--lyrics` or `--lyrics-file` is optional only for BGM/instrumental/unknown-lyrics material. OpenClaw should provide it whenever Suno generated lyrics, meaningful song content, or an instrumental Suno metatag file.
- If lyrics are truly unknown, omit the flag or pass an empty value. For planned instrumental work, prefer the exact bracket-only Suno instrumental metatag file over an empty field.
- BGM/background/lofi/study/sleep/cafe tracks are instrumental/no-vocal by default unless the human explicitly asks for vocals. For Soft Hour Radio or other instrumental BGM, follow [suno-v55-instrumental-format.md](suno-v55-instrumental-format.md): enable Suno Instrumental when available, and make the Suno lyrics/custom-lyrics field bracket-only. Every non-empty line must start with `[` and end with `]`. Do not paste plain arrangement prose into the lyrics field because Suno can sing it. Upload the exact same bracket-only file with `--lyrics-file`.
- For Soft Hour Radio or other instrumental BGM in Suno Advanced Options, use the excluded styles/negative style field to suppress vocal behavior: `vocal, vocals, voice, voices, singing, singer, lead vocal, backing vocals, choir, choral, humming, hum, whisper, spoken word, speech, narration, rap, ad-libs, scat, vocal chops, ooh, aah, la la, lyrics, sung lyrics, topline`.
- For lyric/vocal songs in Suno Advanced Options, use the excluded styles/negative style field to keep the vocal clean and close instead of concert-like or echo-heavy: `muddy vocals, muffled vocals, washed-out vocals, distant vocals, buried vocals, unclear lyrics, heavy reverb, excessive reverb, long reverb tail, large echo, echoey vocals, concert hall echo, arena reverb, stadium reverb, live concert vocals, crowd ambience, room boom`.
- For every Suno generation on every channel, add artificial noise blockers to Advanced Options excluded styles unless the human explicitly asks for vinyl/LP/noise texture: `white noise, static noise, vinyl crackle, record crackle, LP crackle, turntable noise, tape hiss, cassette hiss, analog hiss, noise floor, lo-fi noise, old record noise, dust noise, crackle, hiss`.
- J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop tracks are vocal by default. Unless the human explicitly requested instrumental/BGM/lofi/no vocals, create or capture original lyrics and pass them with `--lyrics` or `--lyrics-file` for every uploaded pop-family track. Use Japanese lyrics for J-pop/Japanese pop/anime-pop, Korean lyrics for K-pop, English lyrics for sundaze/English/American pop, and Spanish lyrics for Solwave/Latin/Spanish pop. The helper now rejects pop-family uploads with empty lyrics before publish unless the concept explicitly says BGM/instrumental/no-vocal.
- Suno can reject lyrics/custom-lyrics, style, prompts, tags, or excluded styles that look like producer tags or specific artist references. Do not use producer names, artist names, label names, artist-like aliases, `type beat` credit text, or exact imitation phrases. Known blocked example: `lowlight` can trigger `Your lyrics contain producer tag lowlight`. Replace flagged terms with generic mood words such as `low-lit`, `dim`, `shadowy`, `muted night`, or `soft ambient`, then retry before uploading the track.
- Lyrics are stored with the track so future thumbnail, Dreamina loop-video, metadata, or standalone single publishing work has song-content context.

Style behavior:

- `--style` is optional, but OpenClaw should provide it whenever the Suno style/settings are known. `--exclude-style` is also optional and should be provided whenever Suno excluded styles/negative tags were used.
- Use one `--style` for a shared prompt style, or one `--style` per `--audio` when candidates used different settings.
- For playlist releases, prefer one `--style` per `--audio`. Do not reuse the exact same style string for many tracks unless the human explicitly asks for a very uniform BGM set.
- Even inside the same genre, vary tempo, energy, instruments, rhythm feel, vocal tone, mood, and production details across tracks. The goal is a coherent playlist, not duplicated songs.
- In Suno style fields, use only `less than 4 minutes` or `under 4 minutes` when a duration hint is needed; do not add exact ranges, lower-bound targets, or extra completion/outro wording.
- Style is stored with the track so future remake, thumbnail, Dreamina loop-video, and metadata work can see how the song was generated.

Audio duration and integrity:

- Do not rely on guessed or planned duration values from Suno/OpenClaw. The server probes uploaded local audio with ffprobe and uses the real file duration when it can read the file.
- If an upload returns an empty/unreadable audio error, the source file did not transfer correctly. Re-download or re-export that Suno track and upload it again; do not continue to render or publish with that release.
- The helper retries each audio upload up to 3 times. If a playlist automation track still fails, it records a Slack warning, continues uploading the remaining tracks, then stops before render/publish so a partial release cannot reach YouTube.
- Treat the command JSON as the upload receipt. A successful upload includes `ok: true`, the uploaded `track.id`, `track.status`, and the probed `duration_seconds`. If `duration_seconds` is `0`, missing, or far from the local file duration, fix and re-upload before continuing.
- Suno duration wording should be minimal: use only `less than 4 minutes` or `under 4 minutes` when a duration hint is needed. Do not add exact ranges, lower-bound targets, or any extra ending/completion wording to prompts, style strings, lyrics, or bracketed metatags. The helper allows playlist tracks up to 4:20 by default for most channels. `Soft Hour Radio` and `Cinematic Pulse` are exempt: do not force those tracks under 4 minutes, and do not reject complete longer tracks just because of duration.
- After audio render, the app stores `rendered_timeline` from actual ffprobe source-file durations. Metadata and OpenClaw `metadata-context` should use that rendered snapshot instead of recalculating timestamps from rounded track durations.
- If a playlist was built from Suno two-output batches and paired variants sit next to each other, pass `--randomize-order` to `scripts/openclaw-release render-audio` or call `/render-audio` with `random: true`. The app persists the shuffled order before rendering, so final order and metadata timestamps still match the rendered audio.

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
  --exclude-style "Suno excluded styles/negative tags used for this song" \
  --prompt "Short generation prompt or notes" \
  --tags "Pop,Single,Music"
```

The command returns JSON with:

- `release.id`
- `release.title`
- `track.id`
- next action

After this, the track appears in the web/Slack review queue. A human should approve it before render.
If `--cover` is provided and this is a Single Release, approving the track automatically registers that image as the release cover.

## Upload One Playlist Track

When `scripts/openclaw-release upload-audio` targets an existing Playlist Release, the helper now uploads the track and immediately approves it into the playlist. It also skips the per-track Slack review message so a playlist batch does not spam Slack.

Playlist track titles should look like final tracklist titles, not Suno alternatives. Do not upload names like `Title A`, `Title B`, `Title 1`, `Title 2`, `Title - Morning`, or `Title - Evening`. Give every playlist item a standalone title that fits the mood.

```bash
scripts/openclaw-release upload-audio \
  --release-id RELEASE_ID \
  --audio /absolute/path/to/playlist-track.mp3 \
  --title "Track Title" \
  --lyrics-file /absolute/path/to/playlist-track-lyrics.txt \
  --style "Suno style/settings used for this track" \
  --exclude-style "Suno excluded styles/negative tags used for this track" \
  --prompt "Short generation prompt or notes" \
  --tags "Playlist,BackgroundMusic,Music"
```

The JSON result should include:

- `auto_approved: true`
- `track.status: approved`

Only use `--pending-review` if the human explicitly asks to review playlist tracks one by one.

If OpenClaw uploads many playlist files in one automation run, call `upload-audio` once per file with one `--title` per `--audio` so the final YouTube tracklist already has natural titles.
Also pass one `--lyrics` or `--lyrics-file` per `--audio` when lyrics or instrumental metatag files are available. For BGM/background/instrumental tracks, prefer the exact bracket-only Suno instrumental metatag file from `docs/suno-v55-instrumental-format.md` over empty lyrics. For J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop releases, lyrics are expected by default and should be uploaded for every track unless the human explicitly requested instrumental/BGM/lofi/no vocals. Pass one shared `--style` or one `--style` per `--audio` whenever Suno style/settings are known; do the same with `--exclude-style` whenever excluded styles/negative tags were used.
For pop-family releases, do not proceed without lyrics. If Suno returns a vocal song but no lyric text is visible, write/capture the final intended lyrics before uploading. If the human explicitly wants a J-pop-feeling instrumental, include BGM/instrumental/no-vocal wording in the prompt/title/tags so the helper treats empty lyrics as intentional.
For vocal playlist releases, write a different lyric concept for every track before generation. Do not reuse the same chorus hook, verse structure, or only swap a few words between songs. Each track should have a distinct emotional angle and memorable phrase.
Suno duration wording should be minimal: use only `less than 4 minutes` or `under 4 minutes` when a duration hint is needed. Do not add exact ranges, lower-bound targets, or any extra ending/completion wording to prompts, style strings, lyrics, or bracketed metatags. The helper allows playlist tracks up to 4:20 by default for most channels. `Soft Hour Radio` and `Cinematic Pulse` are exempt: do not force those tracks under 4 minutes, and do not reject complete longer tracks just because of duration.

For full automatic playlist publishing, two final 16:9 images are required for normal channels.

- `--cover /absolute/path/to/video-cover.png`: playback visual used inside the rendered video. For non-불송 channels, it must include only the selected channel name as a large, readable lower-left brand label because it is also the Gemini/Dreamina/Seedance first-frame reference. For `불송`, it must be a clean textless Buddhist visual with no channel label or other words.
- `--thumbnail /absolute/path/to/youtube-thumbnail.png`: YouTube click thumbnail. For non-불송 channels, include short readable click text plus the selected channel name as a smaller brand line. For `불송`, omit `--thumbnail` or pass `--allow-cover-as-thumbnail`; the app reuses the same clean textless cover as the YouTube thumbnail.

Do not rely on the app's generated draft cover for YouTube upload. For non-불송 channels, do not reuse the cover as the thumbnail unless the human explicitly approves one image for both roles. The thumbnail is for clicks and should have large text; the cover is the Gemini/Dreamina/Seedance first-frame reference, so it should contain only the lower-left channel brand label. For `불송`, one clean textless image is intentionally reused for cover, thumbnail, first-frame, and loop-video reference.

Static image creation rules:

- Before static image creation, run `scripts/openclaw-release channel-profile` and read the returned `profile_doc`. That profile controls cover, thumbnail, and loop-video direction.
- Follow the selected channel profile. Do not mix visual signatures across channels.
- Do not use Dreamina for static cover or YouTube thumbnail images.
- Use OpenAI GPT Image models for static image generation. Prefer `gpt-image-2` when available; otherwise use the currently available GPT Image model in the running OpenAI/Image tool environment. Do not assume OpenAI API usage is free; use the available image tool or configured API credentials.
- If `gpt-image-2` is unavailable in the actual tool/API environment, fall back to the best available GPT Image model instead of using Dreamina for static images.
- Produce 16:9 images, preferably `1280x720` or `1920x1080`.
- Create the final cover first. For non-불송 channels, it must include only the selected channel name as a large, readable lower-left brand label. Then create the YouTube thumbnail from that exact final cover as an image-to-image edit/reference derivative. Do not make the thumbnail as a fresh unrelated generation. For `불송`, create one clean textless cover and reuse that exact image as the YouTube thumbnail instead of making a text derivative.
- For `Tokyo Daydream Radio` or Japan/J-pop releases, use the Tokyo Daydream Radio profile unless the human requested a different visual concept.
- For `Soft Hour Radio` or default BGM/cafe/sleep/study/chill releases, use the Soft Hour Radio profile.
- For `sundaze` or English/American pop releases, use the sundaze profile. There is no fixed visual signature yet; the playlist concept should drive cover, thumbnail, and loop-video visuals.
- For `Solwave Radio` or Latin/Spanish pop releases, use the Solwave Radio profile. There is no fixed visual signature yet; the playlist concept should drive cover, thumbnail, and loop-video visuals.
- For `HaruHaru` or Korean/K-pop releases, use the HaruHaru profile. There is no fixed visual signature yet; the playlist concept should drive cover, thumbnail, and loop-video visuals. Lyrics are Korean by default.
- For `Storylight OST`, use the Storylight OST profile for playful no-vocal Japanese-style game/anime OST, arcade-game BGM, fantasy-game BGM, cute RPG music, item-shop music, mini-game music, and light adventure instrumental releases.
- For `Cinematic Pulse`, use the Cinematic Pulse profile for no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, sci-fi, dark fantasy, heroic, and game-focus instrumental music.
- For `Club Bloom`, use the Club Bloom profile for no-vocal EDM, house, techno, trance, festival, workout, night-drive, gaming, club, and party-energy releases. Each playlist must choose one club style lane and stay within it. Unless the human asks otherwise, Club Bloom visuals should look like an active DJ/performance moment in a premium dance venue, not abstract neon.
- For `BibliaCanto`, use the BibliaCanto profile for lyric-based Old Testament and New Testament scripture-inspired songs. Both Bible branches upload to `BibliaCanto`; reserve Old Testament with `--channel-title "BibliaCanto"` and New Testament with `--channel-title "New Testament"`.
- For `불송`, use the Buddhist profile for Buddhist scripture-inspired modern vocal music. Korean lyrics are the default, and the app schedules uploads public daily at 07:00 Asia/Seoul.
- For `불송`, the cover, YouTube thumbnail, first-frame, and loop video are the same clean textless visual package. Do not put `불송`, title text, sutra text, captions, UI, logos, or any other words in the cover, thumbnail, or video visual.
- If the human explicitly names the upload channel, that channel controls visual routing.
- Human visual requests override the selected channel visual skill. If the human asks for a specific scene, subject, action, camera angle, object, animal, character type, or video concept, use that request consistently for the cover, thumbnail, and loop video.
- For thumbnails, the main default/requested subject must stay centered and visually important. Text must not push it to the side, crop it, cover it, or make it feel secondary. Put text into safe negative space around the centered composition.
- Keep every static visual animated, anime, illustrated, or stylized unless the selected channel profile says otherwise. Cinematic Pulse and 불송 are photorealistic/premium cinematic-real exceptions, and HaruHaru has its own photorealistic rotation rule.
- For non-불송 channels, the cover should be the clean channel/requested scene with only the selected channel name as a large lower-left brand label. The YouTube thumbnail should usually use the same composition plus large readable click text and channel branding. Exception: `불송` cover, YouTube thumbnail, first-frame, and loop assets must be fully textless and should all reuse the same clean image.
- When deriving the thumbnail from the cover, preserve exact subject count, relative positions, silhouettes, clothing colors, major props, background landmarks, lighting, palette, and camera angle. Only add text, channel branding, crop/contrast/readability adjustments, and small layout refinements. Example: if a cloak is red in the cover, it must stay red in the thumbnail.
- If the thumbnail changes character identity, clothing color, subject placement, or core background compared with the cover, reject it and regenerate before upload.
- For Japan/J-pop releases on `Tokyo Daydream Radio`, keep a consistent channel thumbnail system across Tokyo/city, forest/nature, and beach variants: large `J-POP` text with smaller `TOKYO DAYDREAM RADIO` directly beneath it. Use the same full-bleed layout as the approved channel examples, with either the Tokyo three-person back-view composition or the centered human-requested visual composition.
- For `Soft Hour Radio`, use thumbnail wording such as `DEEP SLEEP`, `CAFE PIANO`, `FOCUS MUSIC`, `RAINY NIGHT`, `STUDY BGM`, or `CALM READING`, with smaller `SOFT HOUR RADIO` branding.
- For `sundaze`, use thumbnail wording such as `POP HITS`, `SUMMER POP`, `NIGHT DRIVE`, `DANCE POP`, `FEEL GOOD POP`, or `HEARTBREAK POP`, with smaller `SUNDAZE` branding.
- For `Solwave Radio`, use thumbnail wording such as `LATIN POP`, `REGGAETON`, `VERANO LATINO`, `SPANISH POP`, `FIESTA LATINA`, or `NOCHE LATINA`, with smaller `SOLWAVE RADIO` branding.
- For `HaruHaru`, use thumbnail wording such as `K-POP`, `SEOUL POP`, `DANCE POP`, `HEARTBREAK`, `SUMMER KPOP`, `RAINY KPOP`, or `K-POP DRIVE`, with smaller `HARUHARU` branding.
- For `Storylight OST`, use thumbnail wording such as `GAME OST`, `ANIME BGM`, `ARCADE BGM`, `CUTE RPG`, `KAWAII GAME`, `PLAYFUL OST`, or `FANTASY GAME`, with smaller `STORYLIGHT OST` branding.
- For `Cinematic Pulse`, use thumbnail wording such as `MOVIE OST`, `CINEMATIC ORCHESTRA`, `EPIC BATTLE`, `DARK FANTASY`, `HEROIC MUSIC`, `SCI-FI ACTION`, `TRAILER MUSIC`, or `FILM SCORE`, with smaller `CINEMATIC PULSE` branding. Avoid `FINAL BOSS`, `BOSS BGM`, `보스`, and `보스전` unless the human explicitly asks for game-combat packaging.
- For `Club Bloom`, use style-specific thumbnail wording such as `DEEP HOUSE`, `TECH HOUSE`, `MELODIC TECHNO`, `TRANCE MIX`, `BASS HOUSE`, `FESTIVAL EDM`, `WORKOUT EDM`, `UK GARAGE`, `LIQUID DNB`, `TROPICAL HOUSE`, `AFRO HOUSE`, `SYNTHWAVE DRIVE`, or `CLUB MIX`, with smaller `CLUB BLOOM` branding.
- For `Club Bloom`, reject visual assets that are too mild for a club channel: calm abstract neon, empty low-energy backgrounds, polite lounge imagery, low-contrast thumbnails, random glowing objects, or loop videos with only tiny motion. The cover, thumbnail, and short loop video should usually show active DJ/performance energy in a premium venue such as a beach-club deck, rooftop skyline DJ set, packed nightclub booth, concert/festival stage, warehouse rave, pool-party deck, open-air stage, yacht/harbor party, neon city terrace, or cyber club before upload.
- For `BibliaCanto`, use thumbnail wording such as `GENESIS SONGS`, `OLD TESTAMENT`, `NEW TESTAMENT`, `GOSPEL SONGS`, `BIBLE MUSIC`, `PSALMS MUSIC`, `SCRIPTURE SONGS`, or `EXODUS MUSIC`, with smaller `BIBLIACANTO` branding.
- For `불송`, keep the cover, YouTube thumbnail, first-frame, and loop-video visual textless and identical. Omit `--thumbnail` or pass `--allow-cover-as-thumbnail`; do not create a separate text thumbnail unless the human explicitly reverses this rule.
- Do not add duration text or badges to thumbnails. Avoid `1 HOUR`, `60 MIN`, `1時間`, clocks, timers, and duration stickers.
- Keep the channel-brand line size/style consistent between the thumbnail and the cover channel label when possible.
- Use the cover or a separate first-frame image with only the lower-left channel brand label for Dreamina/Seedance/Gemini video generation. For `불송`, use the same fully textless cover/thumbnail/first-frame image. Do not use the final text thumbnail as the first-frame reference; generated video often makes large thumbnail text flicker, disappear, or reappear.
- The large lower-left channel label is the only allowed baked-in moving-visual text unless the human explicitly asks for more. Exception: `불송` has no baked-in moving-visual text at all. Do not add titles, lyrics, subtitles, UI, logos, duration badges, genre text, or unrelated words inside the moving visual.
- If Gemini/Veo adds its own provider logo or watermark, usually in the bottom-right corner, accept it as an unavoidable provider artifact. Do not regenerate a valid loop video only because that Gemini/Veo logo or watermark is visible. Do not add any other logos, brand marks, UI, or unrelated text yourself.

Required moving visual:

- `--loop-video /absolute/path/to/loop-video.mp4`: Gemini/Dreamina/Seedance visual clip for the rendered video. Gemini clips are uploaded as generated after inspection; Dreamina/Seedance clips should be generated with the duration control set to exactly 7 seconds.
- `--loop-video-provider gemini|dreamina|seedance`: required for OpenClaw-created provider clips so the app records where the loop video came from. Use `gemini` for Gemini/Veo output, `dreamina` for Dreamina output, and `seedance` for Seedance output. The app stores this in `loop_video_provider` and `loop_video_history[].provider`.
- OpenClaw should generate/download only the short clip. Do not export a long MP4 from OpenClaw.
- The clip should be reusable for the full release: its final moment should stay close to the first-frame composition, camera distance, lighting, palette, and subject placement so the visual can cycle cleanly.
- Keep natural motion while returning close enough to the opening composition.
- Normal auto-publish must include a provider-generated `--loop-video` from Gemini, Dreamina, or Seedance. Do not use the thumbnail image, a text-heavy image, an app-rendered still image, or a locally synthesized motion loop as the moving video visual. A still-image fallback is allowed only when the human explicitly requests it, and then OpenClaw must pass `--allow-still-image-video`. `Cinematic Pulse` is an explicit standing exception: use a high-resolution photorealistic still cover as the final video visual and pass `--allow-still-image-video --video-render-source-mode still_image --video-render-resolution 2k --video-spectrum-overlay-style bars`.
- The app validates uploaded loop videos only for technical readability. It does not reject low-motion clips or alternate clip lengths. OpenClaw still rejects unreadable/tiny files, but it should not reject a valid Gemini MP4 because of duration. If Seedance/Dreamina was generated with the wrong duration setting, regenerate it at 7 seconds before upload.

Gemini-first website workflow for OpenClaw:

- Use Gemini only for moving loop-video generation, not for static cover or YouTube thumbnail creation.
- Try Gemini before Dreamina/Seedance for each loop video unless Gemini is on cooldown or unavailable.
- Track the human's Gemini video quota manually. The quota is 3 successful Gemini video generations in a 24 hour window.
- Start the 24 hour cooldown from the moment the 3rd successful Gemini video is generated. It is not a calendar-day midnight reset unless Gemini explicitly says otherwise.
- Count only Gemini attempts where Gemini actually creates a video result. Copyright, policy, moderation, or prompt blocks that stop generation before a video is made do not count against the 3 successful videos.
- If Gemini creates a video but OpenClaw rejects it for quality, wrong text, weak motion, or bad framing, count it as one successful Gemini generation because the quota was spent.
- If Gemini says the daily video limit is reached or OpenClaw knows 3 successful Gemini videos were generated less than 24 hours ago, stop using Gemini for now and use Dreamina/Seedance for the loop video. If Dreamina/Seedance also cannot create the video, defer this release until the Gemini cooldown clears instead of rendering with a missing loop video.
- When Gemini cooldown clears, process deferred releases that failed Dreamina/Seedance first. Create the Gemini loop video, upload it with `--loop-video-provider gemini`, then queue render before starting new loop-video work for other releases.
- Open Gemini in the authenticated browser session.
- Click the `Create image` / creation entry that accepts an image attachment and prompt. Use the image-to-video or video creation option when the UI offers it.
- Attach the final cover or dedicated first-frame image as the first image. This image must contain only the lower-left channel brand label and no thumbnail click text.
- Paste the same motion prompt shape used for Dreamina/Seedance, adapted only if Gemini needs shorter wording.
- Ask Gemini to preserve the first-frame composition, stylized/animated look, and exact lower-left channel label, and to animate the surrounding scene naturally. Do not ask it to add subtitles, title text, UI, logos, spectrum bars, or audio-reactive graphics.
- A Gemini/Veo provider logo or watermark in the corner is allowed and should not be treated as a failed generation.
- Choose `16:9` when the Gemini UI exposes that control. Do not ask Gemini for a duration and do not mention clip length in the prompt. Download the generated MP4 as-is, inspect it, and upload it if text, framing, and motion are acceptable.
- Download the generated MP4 to the VM or OpenClaw workspace.
- Inspect the MP4 before upload. Reject it if the channel label disappears, flickers, is misspelled, changes position/style drastically, becomes unreadable, or if the motion is too static.
- Upload it with `scripts/openclaw-release upload-loop-video --release-id RELEASE_ID --loop-video ABSOLUTE_GEMINI_MP4`, or pass the same path to `--loop-video` in `auto-publish-playlist` / `auto-publish-single`.

Gemini copyright/policy retry rule:

- If Gemini refuses or blocks generation because of copyright, protected IP, policy, moderation, artist/style imitation, logo, brand, celebrity, or similar prompt/image issues, do not count that as one of the 3 successful Gemini videos.
- Rewrite the prompt and retry Gemini up to 10 blocked attempts for that release. Each retry must remove risky wording while preserving the channel label, first-frame continuity, broad mood, and motion intent.
- Before each retry, send Slack progress with `scripts/openclaw-release slack-notify --text "Gemini 영상 생성이 저작권/정책 이슈로 막혀서 프롬프트를 수정해 다시 시도합니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`.
- If Gemini still cannot create a video after 10 blocked attempts, stop Gemini for that release and move on to Dreamina/Seedance instead of spending more time there.

Provider fallback and deferral rule:

- If Dreamina/Seedance cannot create the clip after safe retries, account/payment/quota failure, CAPTCHA, browser failure, or any provider-side generation failure, try Gemini again if fewer than 3 successful Gemini videos have been generated in the active 24 hour window.
- If Gemini quota is already exhausted, do not use `--allow-still-image-video` unless the human explicitly approves it. Leave the release unreleased/unrendered, post `scripts/openclaw-release slack-notify --text "Gemini 3개 영상 쿼터가 끝났고 Dreamina/Seedance도 실패해서 이 릴리즈의 loop video를 보류합니다. 24시간 쿨다운 후 Gemini로 먼저 다시 만들겠습니다. RELEASE_TITLE"`, and resume that release first when Gemini can make videos again.

Dreamina website workflow for OpenClaw:

- Use `https://dreamina.capcut.com/ai-tool/home/` for browser-based Dreamina/Seedance generation.
- Use Dreamina/Seedance `2.0 Fast` for normal releases. Exception: for HaruHaru photorealistic releases, use Seedance `2.0` instead of `2.0 Fast`.
- Do not use Omni Reference.
- Use the first/last-frame workflow if the UI asks which mode to use, but provide only the first-frame image.
- Start from the cover image or a separate first-frame image that contains only the large lower-left selected-channel-name brand label. It should match the YouTube thumbnail scene and composition, including any explicit human visual request. It must not contain title text, genre text, duration text, or unrelated text.
- Leave the last-frame input empty. Do not upload a last-frame reference; it makes the generated motion too static.
- Set ratio to `16:9` when selectable.
- Set quality to `720p` when selectable. Exception: for HaruHaru photorealistic releases, set quality to `1080p` and later queue final render with `--video-render-resolution 1080p`.
- Set duration to `7 seconds` and re-check this visible control immediately before clicking Generate.
- Do not click Generate while the duration control is hidden, while it shows anything other than `7 seconds`, or while you are unsure. Do not create a draft/test clip first.
- Generate exactly one `7 second` MP4.
- Download the generated MP4 to the VM or OpenClaw workspace.
- Confirm the file exists locally before passing it to `--loop-video`.
- If login, CAPTCHA, subscription limits, face detection, moderation, or manual approval blocks Dreamina/Seedance generation/download, do not create a local motion-loop substitute. Try Gemini if quota is available. If Gemini has already created 3 videos in the active 24 hour window, defer this release and move on to another eligible release. When uploading any successful Dreamina/Seedance fallback clip, pass `--loop-video-provider dreamina` or `--loop-video-provider seedance`.

Dreamina/Seedance fallback rejection recovery:

- If Dreamina/Seedance rejects generation for inappropriate content, copyright, policy, moderation, or similar content-safety reasons, do not retry the exact same prompt.
- Retry up to 10 total Dreamina attempts for that loop video. Each failed attempt must send Slack progress before the next retry:
  `scripts/openclaw-release slack-notify --text "영상 만들기 실패해서 프롬프트를 수정해 다시 만듭니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`
- On each retry, make the prompt more original and generic while preserving the release mood, channel label, first-frame continuity, and requested motion direction.
- Remove or generalize anything that can look like protected IP or policy-risk text: named artists, studios, franchises, characters, brands, celebrity names, song titles, exact style imitation phrases such as `in the style of`, logos, weapons, gore, sexualized wording, minors, and real-person likeness references.
- Replace risky references with generic descriptors. Examples: `Ghibli-like` becomes `soft hand-painted anime-inspired background`; `Disney style` becomes `warm family-friendly illustrated animation`; `YOASOBI music video style` becomes `bright mainstream Japanese pop visual mood`; a named character becomes `original youthful traveler silhouette`.
- If the first-frame image itself appears to trigger rejection, regenerate a safer cover/first-frame image first, keeping only the large lower-left channel brand label and the same broad mood.
- If all 10 Dreamina/Seedance attempts fail, try Gemini if quota is available.
- If Gemini quota is exhausted, send a deferral Slack message:
  `scripts/openclaw-release slack-notify --text "Gemini 3개 영상 쿼터가 끝났고 Dreamina/Seedance도 실패해서 이 릴리즈의 loop video를 보류합니다. 24시간 쿨다운 후 Gemini로 먼저 다시 만들겠습니다. RELEASE_TITLE"`
- After deferral, stop work on this release before render/publish and continue with the next eligible release. Do not continue with a local motion loop or still-image video unless the human explicitly approves that fallback and OpenClaw passes `--allow-still-image-video`.

Dreamina/Seedance/Gemini motion prompt guidance:

- Ask the video provider for one continuous video shot whose final moment returns close to the first-frame composition. If the human requested a different motion/camera concept, ask for that requested continuous shot instead.
- Do not put duration, ratio, or quality in the prompt when the UI has controls for them. Set duration only in Dreamina/Seedance controls; do not ask Gemini for a duration.
- Do not include `7 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the prompt. Do not mention duration in Gemini prompts. These words can make Seedance/Dreamina/Gemini create a shorter repeated segment inside the clip.
- Ask Dreamina/Seedance/Gemini to preserve the first-frame image's composition, lighting, palette, selected channel visual style, channel/requested subject/action, and large lower-left channel label in the first shot.
- Use the selected channel profile for subject/action/motion. Always require stable composition, no hard cuts, no other text overlays, no subtitles, no logos, and no UI. Require no photorealism for the normal illustrated/anime/stylized channels; for `Cinematic Pulse`, use original photorealistic cinematic film-still / premium movie-poster realism instead.
- Provider-added Gemini/Veo corner logos or watermarks are allowed; the "no logos" requirement means OpenClaw must not request or create additional logos, brand marks, UI, or unrelated text.
- Ask Dreamina/Seedance/Gemini to preserve the exact lower-left channel text, spelling, font/lettering, placement, color, and readability for the full clip. Ask it not to rewrite, translate, blur, morph, move, hide, flicker, or change the text. Keep the text area stable and animate only the surrounding scene subtly.
- After generation, inspect the downloaded MP4. Reject and regenerate if the large lower-left channel label is missing, unreadable, misspelled, flickering, morphing, moving drastically, shrinking, or changing style.
- Ask for the final moment to be close to the opening composition, but not perfectly identical or static.
- If the model outputs audio, ignore it; the app uses the rendered playlist audio.

Recommended video prompt shapes are in the selected channel profile returned by `scripts/openclaw-release channel-profile`. Use the same prompt shape for Gemini after attaching the first-frame image.

Tokyo/J-pop video prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Tokyo Daydream Radio".
Create one continuous forward-moving animated music visualizer shot.
Keep the Tokyo Daydream Radio signature: exactly three people seen from behind, walking away from the camera into the scene.
The viewer should see backs and backs of heads, not front-facing faces.
The motion must progress forward naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should return close to the opening composition, camera distance, lighting, palette, and subject placement while maintaining natural motion.
Preserve the opening composition, lighting, palette, and anime/illustrated style.
Preserve the large, readable lower-left "Tokyo Daydream Radio" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, flicker, or change it.
Adapt the background and atmosphere to the release concept.
Add subtle camera-follow movement from behind, gentle environmental motion, reflections, rain shimmer, particles, or soft light motion.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI, no extra people or characters.
```

Soft Hour/default BGM video prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "Soft Hour Radio".
Create one continuous calm animated music visualizer shot for a background-music release.
Preserve the opening composition, lighting, palette, and illustrated/stylized visual language.
Preserve the large, readable lower-left "Soft Hour Radio" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, flicker, or change it.
Animate calm but clearly visible natural motion across several environmental layers already present or naturally implied by the first frame and release mood: leaves, grass, curtains, water/rain reflections, warm light shimmer, drifting particles, smoke, steam, fireflies, or soft air movement when appropriate.
Keep continuous visible motion throughout the full clip while preserving the calm long-listening mood.
The motion must progress naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should return close to the opening composition, camera distance, lighting, palette, and subject placement while maintaining natural motion.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no other text, no subtitles, no logos, no UI.
```

If the human provided a specific visual/video request, replace the selected channel default subject/action/camera details with the requested scene, subject, action, motion, and camera angle. Keep the rest of the constraints: one continuous shot, no repeated segment, no ping-pong, preserve first-frame composition/style, preserve the large lower-left channel label, no other text, no subtitles, no logos, no UI, and no extra unwanted subjects.

For any channel, include this in the video-generation prompt: `The uploaded first frame contains the exact large, readable lower-left channel brand label "{CHANNEL_NAME}" (for example, "Tokyo Daydream Radio"). The label should match the visual scale of the YouTube thumbnail's channel-brand line, roughly 18-24% of image width or 5-6% of image height for text cap height. Preserve this text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, flicker, shrink, or change the text. Keep the text area stable; animate the surrounding scene naturally. No other text, subtitles, logos, UI, or title words.`

Thumbnail text rules for OpenClaw:

- Use 2-4 large words that describe the use case or mood, for example `CAFE PIANO`, `DEEP SLEEP`, `FOCUS MUSIC`, `RUNNING BEATS`.
- Prefer the approved full-bleed style: strong image background, no card or panel, large bottom-left genre/mood text, and a smaller channel-brand line directly below.
- For Tokyo Daydream Radio releases, use the channel name as the brand line. The approved mainstream J-pop pattern is large `J-POP` with `TOKYO DAYDREAM RADIO` beneath it. Keep this same two-line treatment for Tokyo/city, forest/nature, and beach versions to create channel consistency.
- Do not add support text or duration badges. The thumbnail should not say `1 HOUR`, `60 MIN`, `1時間`, or show a time badge.
- Keep text large enough to read on a phone.
- Avoid long titles, dense paragraphs, fake UI, and obviously AI-looking distorted text.
- Keep the main default/requested subject centered and visible even when thumbnail text is added.

Localized YouTube metadata rules for OpenClaw:

- The app can upload YouTube localized metadata for `ko`, `ja`, `en`, `es`, `vi`, `th`, `hi`, `fil`, `id`, `pt-BR`, `pt-PT`, `fr`, `de`, `ar`, `zh-CN`, and `zh-TW`.
- For `Tokyo Daydream Radio`, `HaruHaru`, `Storylight OST`, `Cinematic Pulse`, `Club Bloom`, `BibliaCanto`, `불송`, `sundaze`, `Solwave Radio`, mainstream J-pop/Japanese pop, K-pop/Korean pop, English pop, Latin/Spanish pop, playful Japanese game/anime OST BGM, cinematic orchestra/movie-OST/film-score BGM, no-vocal club music, scripture music, or similar pop-family/story-BGM releases, always write every configured language version: Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese.
- Use Korean as the default upload metadata for Tokyo/Soft Hour/HaruHaru and Buddhist `불송` unless the channel profile says otherwise. Use `--default-language en` for `Storylight OST`, `Cinematic Pulse`, `Club Bloom`, `BibliaCanto`, and `sundaze`; use `--default-language es` for `Solwave Radio`.
- Pass the default-language copy through `--title` and `--description-file`, and also pass the matching localized title/description pair.
- Treat localized video titles as transcreation, not literal translation. For every language below, write a natural, clickable title for that audience; if direct translation sounds awkward or weaker, change the wording, order, or exact hook while keeping the release identity, genre/lane, and use case truthful.
- Pass Japanese through `--ja-title` and `--ja-description-file`. This should be natural Japanese YouTube copy, not a literal line-by-line translation.
- Pass English through `--en-title` and `--en-description-file`. This should be natural English YouTube copy for international listeners.
- Pass Spanish through `--es-title` and `--es-description-file`. This should be natural Spanish YouTube copy for Spanish-speaking listeners.
- Pass Vietnamese through `--vi-title` and `--vi-description-file`; make the title natural Vietnamese, not literal English/Korean word order.
- Pass Thai through `--th-title` and `--th-description-file`; make the title natural Thai, not literal English/Korean word order.
- Pass Hindi through `--hi-title` and `--hi-description-file`; make the title natural Hindi, not literal English/Korean word order.
- Pass Filipino through `--fil-title` and `--fil-description-file`; make the title natural Filipino/Tagalog YouTube copy.
- Pass Indonesian through `--id-title` and `--id-description-file`; make the title natural Indonesian YouTube copy.
- Pass Brazilian Portuguese through `--pt-title` and `--pt-description-file`; the app stores this as `pt-BR`. Make the title natural for Brazilian viewers.
- Pass European Portuguese for Portugal through `--pt-pt-title` and `--pt-pt-description-file`; the app stores this as `pt-PT`. Make the title natural for Portugal, not a Brazilian copy when phrasing differs.
- Pass French through `--fr-title` and `--fr-description-file`; make the title natural French YouTube copy.
- Pass German through `--de-title` and `--de-description-file`; make the title natural German YouTube copy.
- Pass Arabic through `--ar-title` and `--ar-description-file`. YouTube uses `ar` for Arabic; it does not expose a separate `ar-EG` localization, so write Arabic that is natural for Arabic/Egyptian audiences.
- Pass Simplified Chinese through `--zh-title` and `--zh-description-file`; the app stores this as `zh-CN`.
- Pass Traditional Chinese for Taiwan through `--zh-tw-title` and `--zh-tw-description-file`; the app stores this as `zh-TW`.
- End every localized description with a public hashtag line. `--tags` is still required, but it only sends YouTube API tags and does not replace visible description hashtags.
- For Playlist Releases on every channel, start `--title`, `--ko-title`, `--ja-title`, `--en-title`, `--es-title`, `--vi-title`, `--th-title`, `--hi-title`, `--fil-title`, `--id-title`, `--pt-title`, `--pt-pt-title`, `--fr-title`, `--de-title`, `--ar-title`, `--zh-title`, and `--zh-tw-title` exactly with `[playlist]`. Do not add this prefix to Single Releases.
- After `[playlist]`, do not repeat playlist nouns such as `플레이리스트`, `Playlist`, `プレイリスト`, or `lista de reproducción`; use music/mix/radio wording instead.
- For playlist/BGM titles, include a real listening situation or viewer intent in the title itself. The title should not be only mood plus genre, but the use case must match the actual music and concept. Do not default to study/work/walk/rest wording by habit.
- For `Cinematic Pulse`, do not use juvenile game-menu title wording such as `Boss BGM`, `Final Boss Music`, `Final Boss Focus Music`, `보스`, `보스전`, or bare `BGM`. Prefer broad film-score wording across varied lanes such as final battle scene, epic cinematic orchestra, dark fantasy film score, heroic trailer music, emotional film score, sci-fi cinematic music, mystery tension score, grand journey orchestra, orchestral battle music, writing music, and movie OST focus. Title-shape repetition is acceptable when it preserves channel fit and sounds natural to a broad YouTube audience, but examples are style references rather than fixed templates.
- For `Club Bloom`, make the club genre or subgenre obvious immediately after `[playlist]`; use mainstream mix language such as `Progressive Trance x EDM Mix`, `Tech House Workout Mix`, `Hype Trap x EDM Mix`, `Melodic Techno Night Drive`, `Bass House Club Mix`, or `Festival EDM Mix`. Put one or two public listening hooks after the separator. Avoid awkward keyword-stuffed title shapes like `[playlist] Progressive Trance for Night Roads, Gaming Focus and Club Drive`; prefer `[playlist] Progressive Trance x EDM Mix | Night Drive & Gaming Club Music`.
- Use `walk` / `산책` only when walking, commuting on foot, street movement, beach/forest walks, crosswalks, or similar movement is genuinely central. For arcade, game-center, karaoke, friend-hangout, party, rooftop, club, dance-pop, bass-heavy, or workout-ready releases, prefer arcade, gaming, friends, night out, getting ready, workout, running, party warmup, driving, nightlife, confidence, or weekend energy.
- For Japan/J-pop/Tokyo Daydream Radio titles, do not over-emphasize the language. Prefer `J-POP`, the actual Japan scene, city-pop/mainstream pop substyle, mood, and listening use cases. Avoid Korean title phrases like `일본어 J-pop`, `일본어 보컬`, or `일본어 카페 재즈` unless the human explicitly asks to highlight the language. `Tokyo Daydream Radio` is the channel brand, not a required title keyword; use `Tokyo` only for genuinely Tokyo-specific concepts. If language matters, mention it naturally in the description instead; the thumbnail/channel branding can carry `J-POP`.
- In Korean title/description/localizations, do not use the transliterated words `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`. Use `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡`.
- Keep all localized titles under 100 characters. Keep timestamps identical across languages; localize displayed track-title text and surrounding description naturally unless a channel-specific rule says to preserve original song titles.
- For Japan/J-pop/Tokyo Daydream Radio timestamped tracklists, format localized rows by language: Korean/default uses Japanese title plus Korean translation in parentheses, Japanese uses Japanese title only, and every other localized description uses translated title text only.
- For sundaze/English pop metadata, localized video titles may be natural adaptations in each language instead of exact English copies. In timestamped tracklists, keep the English song title after each timestamp in every localized description. Translate only the surrounding description prose, use-case line, and hashtags.
- If the release is 60 minutes or longer, use `HH:MM:SS` for every timestamp in every localized description. Start with `00:00:00`, not `00:00`, and use `01:00:00+` after the one-hour point so YouTube can link those chapters reliably.
- Use `scripts/openclaw-release metadata-context` after audio/video render and preserve the returned timestamp positions exactly. Those positions may come from `rendered_timeline`, which is more accurate than rounded DB durations.

Example localized metadata approval:

```bash
scripts/openclaw-release approve-metadata \
  --release-id RELEASE_ID \
  --title "[playlist] 기분 좋아지는 J-POP 믹스 | 산책, 드라이브, 작업할 때 듣기 좋은 음악" \
  --description-file /tmp/metadata-ko.txt \
  --tags "Jpop,JapanesePop,TokyoDaydreamRadio,Playlist,DriveMusic,WorkMusic" \
  --ko-title "[playlist] 기분 좋아지는 J-POP 믹스 | 산책, 드라이브, 작업할 때 듣기 좋은 음악" \
  --ko-description-file /tmp/metadata-ko.txt \
  --ja-title "[playlist] 気分が上がるJ-POPミックス | 散歩・ドライブ・作業用音楽" \
  --ja-description-file /tmp/metadata-ja.txt \
  --en-title "[playlist] Feel-Good J-Pop Mix | Walk, Drive, Work Music" \
  --en-description-file /tmp/metadata-en.txt \
  --es-title "[playlist] J-Pop alegre mix | Música para caminar, conducir y trabajar" \
  --es-description-file /tmp/metadata-es.txt \
  --vi-title "[playlist] J-Pop vui tươi mix | Nhạc đi dạo, lái xe, làm việc" \
  --vi-description-file /tmp/metadata-vi.txt \
  --th-title "[playlist] J-Pop สดใสมิกซ์ | เพลงสำหรับเดินเล่น ขับรถ ทำงาน" \
  --th-description-file /tmp/metadata-th.txt \
  --hi-title "[playlist] फील-गुड J-Pop मिक्स | वॉक, ड्राइव और काम के लिए संगीत" \
  --hi-description-file /tmp/metadata-hi.txt \
  --zh-title "[playlist] 好心情 J-Pop Mix | 散步、开车、工作音乐" \
  --zh-description-file /tmp/metadata-zh.txt \
  --zh-tw-title "[playlist] 好心情 J-Pop Mix | 散步、開車、工作音樂" \
  --zh-tw-description-file /tmp/metadata-zh-tw.txt
```

## YouTube Channel Routing

For automatic playlist publishing, create the release with the chosen `--youtube-channel-title` so backlog accounting and final publish use the intended channel.

- Use `Soft Hour Radio` for default background/cafe/sleep/study/chill playlists.
- Use `Tokyo Daydream Radio` for mainstream J-pop/Japanese pop, Tokyo/Japan pop, city pop, dance-pop, synth-pop, pop-rock, anime-pop, vaporwave, 도쿄, 시티팝, 제이팝, 東京, Jポップ, or シティポップ concepts.
- Use `sundaze` for English/American pop, US/UK pop, western pop, mainstream English vocal pop, dance-pop, synth-pop, pop-rock, or similar English pop concepts.
- Use `Solwave Radio` for Latin/Spanish pop, Spanish pop, urbano latino, reggaeton pop, bachata pop, salsa pop, cumbia pop, tropical dance-pop, verano latino, or similar Spanish vocal concepts.
- Use `HaruHaru` for K-pop, Korean pop, Korean dance-pop, Korean synth-pop, Korean pop-rock, Korean R&B pop, idol-pop inspired music, or similar Korean vocal concepts.
- Use `Storylight OST` for playful no-vocal Japanese-style game/anime OST, arcade-game BGM, fantasy-game BGM, cute RPG music, item-shop music, mini-game music, and light adventure instrumental concepts.
- Use `Cinematic Pulse` for no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, sci-fi, dark fantasy, heroic, and game-focus instrumental concepts.
- Use `Club Bloom` for no-vocal EDM/house/techno/trance/festival/workout/night-drive/gaming/club concepts.
- Use `BibliaCanto` for Old Testament, New Testament, Genesis, Matthew, Gospel, Jesus words, Psalms, Bible verse music, scripture-inspired worship, grace music, worship pop, or ancient biblical music concepts.
- Use `불송` for Buddhist scripture-inspired vocal music, Dhammapada/법구경-inspired songs, Heart Sutra/반야심경-inspired songs, Buddhist jazz, Buddhist hip-hop, Buddhist R&B/soul, dharma songs, mindfulness songs, and modern sutra-inspired music. The app schedules these uploads public daily at 07:00 Asia/Seoul.
- Pass `--youtube-channel-title` explicitly when the human names a target channel.
- Do not use `MusicSun` unless the human explicitly requests it. MusicSun is the only manual-only channel and must be excluded from continuous automatic rotation.
- For continuous automation, newly connected YouTube channels are active by default unless explicitly marked inactive/excluded in docs. MusicSun remains excluded by default. If the selected connected channel has no dedicated profile/concept docs yet, use the `custom-channel` docs returned by `scripts/openclaw-release channel-profile`.
- For Bible releases on `BibliaCanto`, use `docs/openclaw-scripture-sequence.md` and the app-owned `scripts/openclaw-release openclaw-scripture-reserve` / `openclaw-scripture-complete` helpers. Do not use a local scripture ledger or local mismatch checks during normal automation. `불송` Buddhist releases do not use the Bible scripture ledger.
- After publish, `/api/playlists/workspaces` exposes `youtube_video_id`, `youtube_channel_id`, `youtube_channel_title`, and when enabled `youtube_scheduled_publish_at`. OpenClaw can use those fields to confirm which channel received the upload and which slot was assigned; web UI layout changes do not affect OpenClaw because it should use the helper script or local API, not click the dashboard.
- If `AIMP_YOUTUBE_SCHEDULE_PUBLIC_ENABLED=true`, the app uploads with YouTube `status.publishAt` for the next free daily slot in `AIMP_YOUTUBE_SCHEDULE_TIMEZONE` for the selected channel. Bible releases on `BibliaCanto` have two separate daily slots: Old Testament at 07:00 and New Testament at 16:00. `불송` Buddhist uploads use a daily 07:00 slot. Other channels' schedules do not block this channel. OpenClaw should not manually change YouTube visibility in Studio.
- If YouTube rejects a 14+ minute upload because the account is not phone/account verified for long videos, keep the finished release in the app and move on to the next automation task. The human will upload/retry it later after verification.
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
- Upload all intended playlist tracks before starting audio render, video render, metadata approval, or YouTube publish. Reaching the target duration does not auto-start audio render anymore; OpenClaw must explicitly call the render step only after the upload set is complete. In normal automation, call video render without `--wait`, let an external render worker render/upload the MP4 in the background, and stop after the render is queued. The app will ask OpenClaw again when the rendered video is ready for metadata approval and publish. If late tracks are added after rendering starts, the app treats the existing render as stale and requires or queues a fresh render so the YouTube timeline cannot become longer than the actual video.
- For playlist releases, audio render can randomize order with `random: true`. Use this when Suno generated similar A/B pairs and both were uploaded, so paired tracks do not remain adjacent. Do not manually shuffle timestamps; metadata must use `metadata-context` after render.

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
Before opening Suno or generating audio, create or select the destination release in the local AI Music app from the OpenClaw repo checkout.
For a new single candidate set, first create one Single Release:

scripts/openclaw-release create-release --workspace-mode single --release-title "TITLE" --description "CONCEPT"

For a new playlist/mix, first create one Playlist Release:

scripts/openclaw-release create-release --workspace-mode playlist --release-title "TITLE" --target-seconds 2400 --description "CONCEPT"

Keep the returned release.id. Do not create Suno songs before the release.id exists.
For an existing release, use --release-id and keep all related Suno outputs in that same workspace.
When the final audio file is ready, upload it to that same release.
When Suno returns two candidate songs for one single release, run:

scripts/openclaw-release upload-single-candidates --release-id RELEASE_ID --audio ABSOLUTE_AUDIO_PATH_A --audio ABSOLUTE_AUDIO_PATH_B --cover ABSOLUTE_COVER_PATH_A --cover ABSOLUTE_COVER_PATH_B --style "SUNO_STYLE_OR_SETTINGS" --exclude-style "SUNO_EXCLUDED_STYLES_OR_NEGATIVE_TAGS" --prompt "PROMPT" --tags "TAGS"

Return the JSON result, especially release.id and tracks[].id.
Do not approve, render, or publish unless explicitly asked.
If only one candidate exists, run:

scripts/openclaw-release upload-audio --new-single --audio ABSOLUTE_AUDIO_PATH --cover ABSOLUTE_COVER_PATH --title "TITLE" --style "SUNO_STYLE_OR_SETTINGS" --exclude-style "SUNO_EXCLUDED_STYLES_OR_NEGATIVE_TAGS" --prompt "PROMPT" --tags "TAGS"

Return the JSON result, especially release.id and track.id.
Do not approve, render, or publish unless explicitly asked.
If a 16:9 cover image is also ready and the release already has rendered audio, run:

scripts/openclaw-release upload-cover --release-id RELEASE_ID --cover ABSOLUTE_COVER_PATH
```

If the human explicitly asks OpenClaw to publish one single all the way to YouTube, use the automatic single publisher instead:

```text
Create an original single release and publish it through the app.
Generate or obtain:
- one final Suno audio file per YouTube single
- a final clean 16:9 cover image
- a separate YouTube thumbnail image with readable text for normal channels; for `불송`, reuse the same clean textless cover as the thumbnail
- one short Gemini-first loop video; Seedance/Dreamina clips must be 7 seconds, while Gemini clips are uploaded as generated

Then run:

scripts/openclaw-release auto-publish-single \
  --release-id RELEASE_ID \
  --description "CONCEPT_FOR_METADATA" \
  --audio ABSOLUTE_AUDIO_PATH_01 \
  --title "INDEPENDENT_TRACK_TITLE_01" \
  --lyrics-file ABSOLUTE_LYRICS_PATH_01 \
  --style "SUNO_STYLE_OR_SETTINGS" \
  --exclude-style "SUNO_EXCLUDED_STYLES_OR_NEGATIVE_TAGS" \
  --cover ABSOLUTE_FINAL_CLEAN_COVER_IMAGE_PATH \
  --thumbnail ABSOLUTE_YOUTUBE_TEXT_THUMBNAIL_IMAGE_PATH \
  --loop-video ABSOLUTE_GEMINI_DREAMINA_SEEDANCE_LOOP_MP4 \
  --prompt "PROMPT" \
  --tags "TAGS" \
  --youtube-channel-title "Tokyo Daydream Radio"

For non-Japan releases, use the selected channel profile. Korean/K-pop goes to "HaruHaru", playful no-vocal Japanese-style game/anime OST and arcade/fantasy-game BGM goes to "Storylight OST", no-vocal large-scale cinematic orchestra/movie-OST/film-score BGM goes to "Cinematic Pulse", no-vocal EDM/house/techno/trance club music goes to "Club Bloom", Old Testament and New Testament Bible scripture music goes to "BibliaCanto", Buddhist scripture-inspired vocal music goes to "불송", English/American pop goes to "sundaze", Latin/Spanish pop goes to "Solwave Radio", and default BGM/background goes to "Soft Hour Radio" unless the human says otherwise.
Pass exactly one --audio/--title/--lyrics-file/--style per auto-publish-single run, plus one --exclude-style if excluded styles/negative tags were used. If two Suno outputs are both good, create separate cover/thumbnail/loop-video assets and run auto-publish-single twice. For `불송`, omit `--thumbnail` or pass `--allow-cover-as-thumbnail` so the same clean textless cover is used as the thumbnail.
```

## Safety Rules

- Do not call `Approve Publish` automatically unless the human explicitly asks for full publishing.
- Do not upload videos directly through `youtube.com` or YouTube Studio. Use `scripts/openclaw-release publish-release` or the app's local `/approve-publish` API for playlist finish passes. The app performs the real YouTube upload through the YouTube Data API.
- Do not use an existing `--release-id` that already has `youtube_video_id` for a normal new publish. Create a new release instead. Re-upload escape hatches should be used only when the human explicitly asks to upload the same release again.
- YouTube Studio is only for human final review after the API upload, such as watching the result, confirming the scheduled public time, reviewing app-uploaded CC captions, or manual fixes.
- Do not try to turn on captions through browser automation. For vocal releases with saved lyrics, the app uploads YouTube CC caption tracks through the API at publish time using faster-whisper line timing and Codex translations. For BGM/instrumental/no-vocal releases, leave captions/audio language alone unless the human explicitly asks for manual captions.
- Do not open Suno or generate audio before creating/selecting the app release workspace. Fresh work starts with `scripts/openclaw-release create-release`; continuing work starts with `scripts/openclaw-release list-releases` and `--release-id`.
- Do not upload to YouTube automatically unless running a finisher pass for a rendered playlist release or using `auto-publish-single` after explicit human instruction.
- If cover art is ready with the audio, upload it in the same command with `--cover`; otherwise omit `--cover` and let the human add/regenerate cover later.
- If lyrics, meaningful song-content notes, or an instrumental Suno metatag file are available, upload them in the same command with `--lyrics` or `--lyrics-file`. Use an empty value only when lyrics/content are truly unknown.
- For BGM/background/lofi/study/sleep/cafe singles and playlists, instrumental/no-vocal is the default, but an empty lyrics/custom-lyrics field is not preferred. Use `docs/suno-v55-instrumental-format.md`: enable Instrumental when available, write only bracketed metatag lines in Suno's lyrics/custom-lyrics field, and upload that exact file. For J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop singles and playlists, do not leave lyrics empty by default. Generate/capture original lyrics and upload them; only use empty lyrics when the human explicitly asked for instrumental/no-vocal music or when Suno did not provide lyrics and OpenClaw reports that limitation.
- For vocal pop uploads, lyrics should be standalone song lyrics, not literal descriptions of the YouTube playlist title, thumbnail text, visual scene, or listening use case. Match the melody, beat, tempo, energy, and vocal attitude to the playlist context, but write natural pop lyrics with their own emotion, story, and hook.
- For no-vocal Suno work, also fill Advanced Options excluded styles with vocal-related exclusions: `vocal, vocals, voice, voices, singing, singer, lead vocal, backing vocals, choir, choral, humming, hum, whisper, spoken word, speech, narration, rap, ad-libs, scat, vocal chops, ooh, aah, la la, lyrics, sung lyrics, topline`.
- For lyric/vocal Suno work, fill Advanced Options excluded styles with vocal clarity blockers: `muddy vocals, muffled vocals, washed-out vocals, distant vocals, buried vocals, unclear lyrics, heavy reverb, excessive reverb, long reverb tail, large echo, echoey vocals, concert hall echo, arena reverb, stadium reverb, live concert vocals, crowd ambience, room boom`.
- For every Suno generation on every channel, add artificial noise blockers to Advanced Options excluded styles unless the human explicitly asks for vinyl/LP/noise texture: `white noise, static noise, vinyl crackle, record crackle, LP crackle, turntable noise, tape hiss, cassette hiss, analog hiss, noise floor, lo-fi noise, old record noise, dust noise, crackle, hiss`.
- Before pressing Create in Suno, remove producer tags and specific artist references from lyrics, bracketed metatags, style, prompt, tags, and excluded styles. If Suno rejects a word such as `lowlight` as a producer tag, rewrite it to a generic descriptor like `low-lit`, `dim`, `shadowy`, `muted night`, or `soft ambient`, then retry generation.
- After every audio upload, confirm that the returned `duration_seconds` is close to the actual song length. If it is `0`, much shorter than expected, or the upload fails as unreadable, fix the source file and re-upload before moving on.
- For playlist work, confirm every uploaded `duration_seconds` is at or below 260 unless the target channel is `Soft Hour Radio` or `Cinematic Pulse`, or the human explicitly approved a longer track.
- For playlist automation, if a few songs fail after the 3 upload attempts, do not abandon the rest of the batch. Let the helper upload the remaining songs, read the Slack warning, then re-upload only the failed files and rerun render/publish after the release has the full intended track set.
- If Suno style/settings are available, upload them in the same command with `--style`. If excluded styles/negative tags are available, upload them with `--exclude-style`.
- Do not generate a batch by repeating one Suno prompt/style/lyric template. Each new Suno request should have a distinct prompt/style/lyrics plan while staying inside the requested release mood.
- For HaruHaru, sundaze, and Solwave Radio playlist releases, choose one explicit genre lane before Suno generation and keep the whole playlist in that lane. Name that lane in the public title/metadata when accurate instead of writing a generic mixed-pop title.
- Do not generate vocal songs by mechanically inserting the release title/use-case words into every verse or chorus. For example, a dance-practice, walking, driving, workout, study, or party playlist should get songs whose sound fits that context; the lyrics can be about love, confidence, heartbreak, freedom, youth, or another strong pop topic.
- Treat generated draft covers in the web UI as replaceable placeholders, not final art.
- Use OpenAI GPT Image models for static cover and thumbnail images. Do not use Dreamina for static image generation.
- Static cover and thumbnail images must follow the channel profile returned by `scripts/openclaw-release channel-profile`.
- In thumbnails, keep the main channel/requested subject centered; text must not push it sideways.
- Generate the thumbnail from the final cover as a reference/edit derivative. Preserve characters, positions, outfit colors, lighting, palette, background continuity, and the channel-brand line style; only add click text/branding and readability adjustments.
- Do not use generated draft covers for full OpenClaw auto-publish runs. OpenClaw must create/upload a real final cover image first.
- Do not publish without final thumbnail handling. For non-불송 channels, OpenClaw must create/upload a text thumbnail and pass it as `--thumbnail`. For `불송`, OpenClaw must reuse the same clean textless cover as the thumbnail by omitting `--thumbnail` or passing `--allow-cover-as-thumbnail`.
- OpenClaw must create a Gemini/Dreamina/Seedance clip and pass the short MP4 as `--loop-video` before normal video render/publish. Try Gemini first unless its 24 hour cooldown is active; otherwise use Dreamina/Seedance. If Dreamina/Seedance cannot create the clip, try Gemini again when quota is available; if all 3 Gemini videos are already spent, defer this release until the 24 hour Gemini cooldown clears and process it before new loop-video work. The generated clip should end close to its opening composition so it can be reused across the long video. If the human explicitly approves a still-image fallback, pass `--allow-still-image-video`; otherwise do not render/publish. For `Cinematic Pulse`, skip loop-video work by default and render from the high-resolution still cover with `--video-render-source-mode still_image --video-render-resolution 2k --video-spectrum-overlay-style bars`.
- Keep `--cover`, `--thumbnail`, and `--loop-video` separate for non-불송 channels. `--thumbnail` should have readable YouTube text plus channel branding. `--cover` and `--loop-video` must contain only the large lower-left channel label as baked-in text. Never feed the text thumbnail into Gemini/Dreamina/Seedance as the first frame; use the cover or a dedicated first-frame image. For `불송`, use one clean textless image as cover, thumbnail, and first-frame visual. If the human requested a specific video visual, that visual request must be reflected consistently across all assets.
- A Gemini/Veo provider logo or watermark in the corner is allowed and is not a reason to regenerate the loop video.
- For Gemini, use the Gemini-first `Create image` / image+prompt workflow above, attach the cover/first-frame image, do not mention duration, count only successful video generations toward the 3 videos per 24 hour quota, and upload with `--loop-video-provider gemini`. For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, and exactly `7 seconds` through UI controls, then upload with `--loop-video-provider dreamina` or `--loop-video-provider seedance`. Exception: HaruHaru photorealistic releases use Seedance `2.0`, `1080p`, exactly `7 seconds`, and final render `--video-render-resolution 1080p`. Do not put those settings in the prompt.
- For normal OpenClaw auto-publish work, verify the MP4 after download. If Seedance/Dreamina did not produce the requested 7 second clip, discard/regenerate unless the human explicitly accepts it and OpenClaw passes `--allow-short-loop-video`. For Gemini, inspect the generated MP4 and upload it as-is when text, framing, and motion are acceptable.
- For Playlist Releases, `upload-audio` auto-approves by default. Do not add `--pending-review` unless the human explicitly asks.
- For Playlist Releases, do not use pair/number titles. Replace Suno A/B or 1/2 output labels with independent track names before upload.
- For Suno two-output generations, upload both candidates to one Single Release using `upload-single-candidates`.
- Single Release candidates are still human-reviewed; the human may approve one candidate, approve both candidates as separate Single Releases, or reject both.
- If both candidates are rejected, the app will archive the release automatically; do not delete files or database rows manually.
- If three or more songs are ready for one release, use a Playlist Release instead.
