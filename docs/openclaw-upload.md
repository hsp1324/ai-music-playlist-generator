# OpenClaw Upload Workflow

Use this when OpenClaw has generated an audio file and needs to hand it to the AI Music web app.

For higher-level OpenClaw skill instructions, including "make one single", "build vocal playlists entirely from new audio", "build instrumental playlists from a fresh block plus lyricless same-genre reuse", and "write YouTube metadata", see [openclaw-skills.md](openclaw-skills.md).
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
- When a Single Release candidate is approved, its uploaded cover is automatically registered as that release's cover. If both candidates are approved, each approved song should continue with its own cover/thumbnail and required visual-source assets.

Lyrics/content behavior:

- `--lyrics` or `--lyrics-file` is optional only for BGM/instrumental/unknown-lyrics material. OpenClaw should provide it whenever Suno generated lyrics, meaningful song content, or an instrumental Suno metatag file.
- If lyrics are truly unknown, omit the flag or pass an empty value. For planned instrumental work, prefer the exact bracket-only Suno instrumental metatag file over an empty field.
- BGM/background/lofi/study/sleep/cafe tracks are instrumental/no-vocal by default unless the human explicitly asks for vocals. Soft Hour Radio is piano-first in two equal alternating lanes: `classic_piano` is solo/felt/quiet piano, while `anime_game_ost` is original Japanese anime/game-OST-style piano that may be calm or gently lively and may use only a restrained explicitly planned support color. Do not use lofi beats, Rhodes, guitar-led, pad-led, jazz-trio, bossa, drum/percussion, or unrelated mixed-instrument BGM. Follow [suno-v55-instrumental-format.md](suno-v55-instrumental-format.md), enable Suno Instrumental when available, and make the lyrics/custom-lyrics field bracket-only.
- For Soft Hour Radio or other instrumental BGM in Suno Advanced Options, always suppress vocal behavior. For `classic_piano`, exclude all non-piano arrangement drift. For `anime_game_ost`, exclude drums, beats, percussion, lofi, jazz trio, bossa, EDM, rock band, trailer music, epic battle orchestra, dark ambient, horror, and every support instrument not deliberately allowed by the selected concept.
- For lyric/vocal songs in Suno Advanced Options, use the excluded styles/negative style field to keep the vocal clean and close instead of concert-like or echo-heavy: `muddy vocals, muffled vocals, washed-out vocals, distant vocals, buried vocals, unclear lyrics, heavy reverb, excessive reverb, long reverb tail, large echo, echoey vocals, concert hall echo, arena reverb, stadium reverb, live concert vocals, crowd ambience, room boom`.
- For every Suno generation on every channel, add artificial noise blockers to Advanced Options excluded styles unless the human explicitly asks for vinyl/LP/noise texture: `white noise, static noise, vinyl crackle, record crackle, LP crackle, turntable noise, tape hiss, cassette hiss, analog hiss, noise floor, lo-fi noise, old record noise, dust noise, crackle, hiss`.
- J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop tracks are vocal by default. Unless the human explicitly requested instrumental/BGM/lofi/no vocals, create or capture original lyrics and pass them with `--lyrics` or `--lyrics-file` for every uploaded pop-family track. Use Japanese lyrics for J-pop/Japanese pop/anime-pop, Korean lyrics for K-pop, English lyrics for sundaze/English/American pop, and Spanish lyrics for Solwave/Latin/Spanish pop. The helper now rejects pop-family uploads with empty lyrics before publish unless the concept explicitly says BGM/instrumental/no-vocal.
- Suno can reject lyrics/custom-lyrics, style, prompts, tags, or excluded styles that look like producer tags or specific artist references. Do not use producer names, artist names, label names, artist-like aliases, `type beat` credit text, or exact imitation phrases. Known blocked example: `lowlight` can trigger `Your lyrics contain producer tag lowlight`. Replace flagged terms with generic mood words such as `low-lit`, `dim`, `shadowy`, `muted night`, or `soft ambient`, then retry before uploading the track.
- Lyrics are stored with the track so future thumbnail, moving visual or still-image package, metadata, or standalone single publishing work has song-content context.

Style behavior:

- `--style` is optional, but OpenClaw should provide it whenever the Suno style/settings are known. `--exclude-style` is also optional and should be provided whenever Suno excluded styles/negative tags were used.
- Use one `--style` for a shared prompt style, or one `--style` per `--audio` when candidates used different settings.
- For playlist releases, prefer one `--style` per `--audio`. Do not reuse the exact same style string for many tracks unless the human explicitly asks for a very uniform BGM set.
- For lyric/vocal tracks, `--style` must preserve the intended lead vocal tone, timbre, delivery, register, or attitude used in Suno, not just genre and BPM. If the captured Suno style is too generic, append a detailed voice identity before upload. Include at least three concrete voice traits such as register/range, timbre texture, delivery, mic distance, emotional attitude, and language/accent when useful. Vary that voice phrase across the all-new tracks in one release. Do not store generic-only voice tags such as `female vocal`, `male rap`, `Korean vocal`, or `pop vocal`.
- When Suno custom lyrics were used, the lyrics file should also contain a short bracketed voice cue near the top, matching the style string, for example `[Lead vocal: breathy intimate Korean female alto, close-mic, light rasp]`. For duets or alternating sections, add short section cues such as `[Male verse: restrained low-register baritone rap]` and `[Female hook: airy R&B head voice]`. Upload the final lyrics/metatag file with those cues intact so future remake and sync work can see how the voice was directed.
- For 불송 audio, male lead vocals, male duet, male/female duet, female lead vocals, and mixed vocals are all allowed. Do not infer vocal gender from the visual artwork direction. Preserve the actual intended vocal concept in `--style`, especially when two male voices, a male lead, or a duet is part of the song.
- Even inside the same genre, vary tempo, energy, instruments, rhythm feel, vocal tone, mood, and production details across tracks. The goal is a coherent playlist, not duplicated songs.
- Do not put duration caps or lower-bound duration phrases such as `less than 4 minutes`, `under 4 minutes`, `at least 2 minutes`, `minimum 2 minutes`, or `2 minutes or longer` into Suno prompts, style fields, lyrics, or bracketed metatags unless the human explicitly asks for that wording. Those phrases can make Suno end too early or behave unpredictably. Ask structurally for a credit-efficient full song/cue that naturally lands around 4 minutes or longer. For vocal tracks, use a distinct intro on only about one out of every five songs and start the rest directly on a verse, hook, chorus, rap verse, or brief vocal pickup; develop later verses, chorus returns, bridge/breakdown, final lift, and the ending to reach full length. For instrumental tracks, keep channel-appropriate intros and longer bracket-only metatags. Still verify the downloaded duration because Suno has no guaranteed minimum-duration field. Do not block upload only because a usable track is under 4:00.
- Style is stored with the track so future remake, thumbnail, moving visual or still-image package, and metadata work can see how the song was generated.

Audio duration and integrity:

- Do not rely on guessed or planned duration values from Suno/OpenClaw. The server probes uploaded local audio with ffprobe and uses the real file duration when it can read the file.
- If an upload returns an empty/unreadable audio error, the source file did not transfer correctly. Re-download or re-export that Suno track and upload it again; do not continue to render or publish with that release.
- The helper retries each audio upload up to 3 times. If a playlist automation track still fails, it records a Slack warning, continues uploading the remaining tracks, then stops before render/publish so a partial release cannot reach YouTube.
- Treat the command JSON as the upload receipt. A successful upload includes `ok: true`, the uploaded `track.id`, `track.status`, and the probed `duration_seconds`. If `duration_seconds` is `0`, missing, or far from the local file duration, fix and re-upload before continuing.
- Do not put duration caps or lower-bound duration phrases such as `less than 4 minutes`, `under 4 minutes`, `at least 2 minutes`, `minimum 2 minutes`, or `2 minutes or longer` into Suno prompts, style strings, lyrics, or bracketed metatags unless the human explicitly asks for that wording. Ask structurally for a credit-efficient full song/cue that naturally lands around 4 minutes or longer, with enough lyric or instrumental section development to avoid short sketches, but verify the downloaded duration because Suno has no guaranteed minimum-duration field. Tracks shorter than 4:00 are still valid uploads when they fit the release. Playlist tracks from 1:00 to 1:59 should be uploaded/used and recorded for later analysis; only stop and report tracks under 1:00 unless the channel-specific workflow says otherwise. Complete 5+ minute tracks are allowed on every channel.
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
For vocal playlist releases, also write a different vocal identity for every generated track before pressing Create. Put that voice identity in both the Suno style/settings field and, when custom lyrics are used, the first bracketed lyric metatag. Avoid repeating the same default AI-like singer across a release; vary register, texture, delivery, mic distance, attitude, and hook-vs-verse vocal role while keeping the genre lane coherent.
Do not put duration caps or lower-bound duration phrases such as `less than 4 minutes`, `under 4 minutes`, `at least 2 minutes`, `minimum 2 minutes`, or `2 minutes or longer` into Suno prompts, style strings, lyrics, or bracketed metatags unless the human explicitly asks for that wording. Ask structurally for a credit-efficient full song/cue that naturally lands around 4 minutes or longer, with enough lyric or instrumental section development to avoid short sketches, but verify the downloaded duration because Suno has no guaranteed minimum-duration field. Tracks shorter than 4:00 are still valid uploads when they fit the release. Playlist tracks from 1:00 to 1:59 should be uploaded/used and recorded for later analysis; only stop and report tracks under 1:00 unless the channel-specific workflow says otherwise. Complete 5+ minute tracks are allowed on every channel.

For full automatic playlist publishing, two final 16:9 images are required for normal channels.

- `--cover /absolute/path/to/video-cover.png`: playback visual and, for moving-video channels, Gemini/Dreamina/Seedance first-frame reference. For HaruHaru, sundaze, Solwave Radio, Club Bloom, and 불송, this is the `still_image` render source. It must not contain channel names or logos. If text is useful, use only a short style, genre, use-case, or passage phrase; HaruHaru should not add style text by default, and sundaze/Solwave/Club Bloom should usually keep any lane phrase small and integrated.
- `--thumbnail /absolute/path/to/youtube-thumbnail.png`: YouTube click thumbnail. Use short readable click text on channels that call for text and never add the selected channel name or logo. For HaruHaru, use a normally text-free derivative of the selected theme-first cover in the same medium. For sundaze, use a photorealistic English/American friend-taken phone-photo lifestyle thumbnail derived from the cover with one short integrated English-pop lane phrase when useful. For Solwave Radio, use a photorealistic friend-taken phone-photo lifestyle thumbnail derived from the cover with one short integrated Latin/Spanish lane phrase when useful. For Club Bloom, use a text-free derivative of its approved club or record-culture cover by default, with one short transparent-background club lane phrase only when the image needs it. For `불송`, pass the same theme-first non-Buddhist cover/first-frame package as the thumbnail or use `--allow-cover-as-thumbnail`.

Do not rely on the app's generated draft cover for YouTube upload. Do not reuse the cover as the thumbnail unless the human explicitly approves one image for both roles or the selected profile uses one image package (`불송`). The thumbnail is for clicks and should have concise text except on HaruHaru and Club Bloom, where it should normally stay text-free and preserve the approved cover concept; sundaze, Solwave Radio, and Club Bloom thumbnails may add one short integrated lane phrase only when the image needs it. The cover is the video first-frame reference or still-image render source and should stay cleaner.

Static image creation rules:

- Before static image creation, run `scripts/openclaw-release channel-profile` and read the returned `profile_doc`. That profile controls cover, thumbnail, loop-video, and still-image render direction.
- Follow the selected channel profile. Do not mix visual signatures across channels.
- Do not use Dreamina for static cover or YouTube thumbnail images.
- Use OpenAI GPT Image models for static image generation. Prefer `gpt-image-2` when available; otherwise use the currently available GPT Image model in the running OpenAI/Image tool environment. Do not assume OpenAI API usage is free; use the available image tool or configured API credentials.
- If `gpt-image-2` is unavailable in the actual tool/API environment, fall back to the best available GPT Image model instead of using Dreamina for static images.
- Produce 16:9 images, preferably `1280x720` or `1920x1080`.
- Create the final cover/first-frame first. Do not put channel names or logos on it. Then create the YouTube thumbnail from that exact final cover as an image-to-image edit/reference derivative. Do not make the thumbnail as a fresh unrelated generation. For HaruHaru, preserve the selected theme-first photographic, cinematic, animated/illustrated, graphic, object-led, environment-led, collage, or surreal medium and keep both images text-free by default. For sundaze and Solwave Radio, keep both images photorealistic and friend-taken smartphone/Instagram-like. For Club Bloom, preserve the approved premium club or record-culture still-image direction and reject unsafe or celebrity-like imagery. For `불송`, create one theme-first text-free mainstream Korean-song cover/first-frame image and reuse it as the thumbnail when appropriate; exclude overt Buddhist/source imagery unless the human explicitly requests source-explicit packaging.
- For `Tokyo Daydream Radio` or Japan/J-pop releases, use the Tokyo Daydream Radio profile unless the human requested a different visual concept.
- For `Soft Hour Radio` or solo-piano BGM/cafe/sleep/study/chill releases, use the Soft Hour Radio profile.
- For `sundaze` or English/American pop playlist releases, including pop-rock, country pop, Americana pop, indie/bedroom/alt-pop, singer-songwriter/folk-pop, soft rock, pop-punk, Y2K/recession pop, disco/funk pop, Afrobeats, Afropop, and Amapiano-pop, use the sundaze profile. It now defaults to photorealistic English/American friend-taken smartphone lifestyle still-image cover/thumbnail visuals and app `still_image` video render with lower-left lyric subtitles and lower-right `bars` spectrum, not provider loop video.
- For `Solwave Radio` or Latin/Spanish pop releases, use the Solwave Radio profile. It now defaults to photorealistic Latin/Spanish friend-taken smartphone lifestyle still-image cover/thumbnail visuals and app `still_image` video render with lower-left lyric subtitles and lower-right `bars` spectrum, not provider loop video. Lyrics are Spanish by default, and normal Solwave MP4 renders burn those lyric subtitles into the video.
- For `HaruHaru` or Korean/K-pop releases, use the HaruHaru profile. It uses theme-first creative still-image cover/thumbnail visuals and app `still_image` video render, not provider loop video. There is no default woman, portrait, location, or medium. Read the actual music and lyrics, draft at least three different visual-family candidates, compare recent channel covers, and choose the most truthful, distinctive, small-thumbnail-readable concept. Lyrics are Korean by default.
- Do not use `Storylight OST` for new automatic uploads; the human manages it manually.
- For playful no-vocal Japanese-style game/anime OST, arcade-game BGM, fantasy-game BGM, cute RPG music, item-shop music, mini-game music, amusement/theme-park BGM, and light adventure instrumental releases, route to `Cinematic Pulse` but treat the release as the former Storylight lane. Use truthful cute game/anime/BGM cover, thumbnail, and metadata language.
- For `Cinematic Pulse` cinematic lanes, use the Cinematic Pulse profile for no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, sci-fi, dark fantasy, heroic, premium game orchestra, anime action-RPG OST, and game-focus instrumental music.
- `Cinematic Pulse` playlists use Gemini/Veo image-to-video during normal automation whenever Gemini is available. This channel-specific rule overrides the generic legacy provider-fallback language later in this document: do not use Dreamina, Seedance, CapCut, Ken Burns motion, or a locally synthesized loop for new Cinematic Pulse work. If Gemini is unavailable or unusable, use the approved still-image fallback.
- Make each Cinematic Pulse Gemini clip usable for indefinite app-managed repetition without asking Gemini to create a loop. Camera movement, subject size/position/pose changes, and transient subjects entering/leaving are allowed. Ask for one uninterrupted shot whose closing base composition, background, camera viewpoint, lighting, and color state are broadly similar to the opening base scene. A bird may fly into frame and disappear before the end. Preview at least three consecutive repeats and reject/regenerate only when the join has an obvious discontinuity, unrelated scene change, lighting reset, or text flicker.
- For `Club Bloom`, use the Club Bloom profile for no-vocal modern club music and broader DJ culture, including 1990s/2000s boom bap, jazz-hop, trip-hop, rare groove, funk/soul breaks, disco/boogie, broken beat, and instrumental R&B/neo-soul. Focused releases stay within one style; an explicit adjacent-genre DJ-crate journey may bridge styles coherently. Club Bloom uses photorealistic still-image cover/thumbnail visuals and app `still_image` render, not a provider loop. Modern dance releases may use candid club/bar/lounge/festival scenes; retro releases may use modern record bars, vinyl rooms, listening booths, practice rooms, or record-shop settings.
- For `BibliaCanto`, use the BibliaCanto profile for lyric-based Old Testament and New Testament scripture-inspired songs. Both Bible branches upload to `BibliaCanto`; reserve Old Testament with `--channel-title "BibliaCanto"` and New Testament with `--channel-title "New Testament"`.
- For `불송`, use the 불송 profile for Korean vocal music internally inspired by Buddhist sources/themes. New 불송 releases are diversity-first: choose one coherent mainstream lane and rotate across hip-hop, boom bap, trap-soul, dark R&B, trip-hop, glitch-hop, drum and bass, UK garage, phonk, hyperpop, psychedelic soul, avant-jazz rap, spoken-word rap, new-age electronica, cinematic trap, art-pop, or other modern lanes. Korean lyrics are the default; new lyrics and public metadata should avoid overt Buddhist/source vocabulary unless the human explicitly asks for source-explicit wording. The app schedules uploads public daily at 07:00 Asia/Seoul.
- For `불송`, the cover, YouTube thumbnail, first-frame, and still-image render source are the same text-free mainstream Korean-song visual package. Every new visual should be click-stopping and meaningfully different from recent uploads: rotate street/lifestyle, R&B city-night, rainy room or car-window, adult portrait, duet/couple tension, cinematic city, surreal nonreligious, anime/illustrated modern music, dark editorial, object-led, and bold graphic concepts. Avoid all Buddhist-looking imagery and source/genre labels unless the human explicitly requests source-explicit packaging.
- `불송` is always a still-image video channel in normal automation. Do not create, upload, or wait for a Gemini, Dreamina, or Seedance loop video for 불송; pass still-image render flags instead. This is not a quota fallback or provider-failure workaround unless the human explicitly changes the 불송 still-image rule in the current request.
- If the human explicitly names the upload channel, that channel controls visual routing.
- Human visual requests override the selected channel visual skill. If the human asks for a specific scene, subject, action, camera angle, object, character type, or video concept, use that request consistently for the cover, thumbnail, and loop video or still-image render.
- For thumbnails, the main default/requested subject must stay centered and visually important. Text must not push it to the side, crop it, cover it, or make it feel secondary. Put short style/passage text into safe negative space around the centered composition, preferably upper-left so it does not collide with lower-left lyric overlays.
- Use the medium required by the selected channel profile. HaruHaru and 불송 use the selected theme-first photographic, cinematic, animated/illustrated, graphic, object-led, environment-led, collage, or surreal still-image direction. sundaze and Solwave Radio use a casual friend-taken smartphone look, while Club Bloom uses lane-specific premium nightlife or record-culture still images.
- The cover should be the clean requested scene without channel names. The YouTube thumbnail should usually use the same composition plus large readable click text, except HaruHaru and Club Bloom where it should usually stay text-free. sundaze and Solwave Radio should keep a photorealistic friend-taken phone-photo lifestyle look and use at most one short integrated lane phrase. Club Bloom should preserve its approved lane-specific scene and use a short transparent-background club lane phrase only when needed.
- When deriving the thumbnail from the cover, preserve exact subject count, relative positions, silhouettes, clothing colors, major props, background landmarks, lighting, palette, and camera angle. Only add concise click text, crop/contrast/readability adjustments, and small layout refinements. Example: if a cloak is red in the cover, it must stay red in the thumbnail.
- If the thumbnail changes character identity, clothing color, subject placement, or core background compared with the cover, reject it and regenerate before upload.
- For Japan/J-pop releases on `Tokyo Daydream Radio`, use large natural J-pop lane text such as `J-POP`, `CITY POP`, `ANIME POP`, `J-POP DRIVE`, or `SUMMER J-POP`, without the channel name.
- For `Soft Hour Radio`, use lane-matched thumbnail wording. `classic_piano` can use `SOLO PIANO`, `CAFE PIANO`, `FOCUS PIANO`, `RAINY PIANO`, `STUDY PIANO`, or `SLEEP PIANO`; `anime_game_ost` can use `ANIME PIANO OST`, `GAME PIANO OST`, `FANTASY PIANO`, or `HEALING GAME OST`. Never claim an official named-franchise soundtrack.
- For `sundaze`, use thumbnail wording such as `POP HITS`, `SUMMER POP`, `NIGHT DRIVE`, `DANCE POP`, `POP R&B`, `FEEL GOOD POP`, or `HEARTBREAK POP`.
- For `Solwave Radio`, use thumbnail wording such as `LATIN POP`, `REGGAETON`, `VERANO LATINO`, `SPANISH POP`, `FIESTA LATINA`, `BACHATA POP`, or `NOCHE LATINA`.
- For `HaruHaru`, do not add thumbnail wording by default. Preserve the selected theme-first photographic, cinematic, animated/illustrated, graphic, object-led, environment-led, collage, or surreal cover concept in the thumbnail derivative. If the human explicitly requests text later, keep it small, integrated, and never use the channel name.
- For former Storylight-style releases on `Cinematic Pulse`, use thumbnail wording such as `GAME OST`, `ANIME BGM`, `ARCADE BGM`, `CUTE GAME BGM`, `HAPPY GAME MUSIC`, `PLAYFUL OST`, `FANTASY GAME`, or `THEME PARK BGM`.
- For `Cinematic Pulse` cinematic lanes, use thumbnail wording such as `MOVIE OST`, `CINEMATIC ORCHESTRA`, `EPIC BATTLE`, `DARK FANTASY`, `HEROIC MUSIC`, `SCI-FI ACTION`, `TRAILER MUSIC`, or `FILM SCORE`. Avoid `FINAL BOSS`, `BOSS BGM`, `보스`, and `보스전` unless the human explicitly asks for game-combat packaging. Do not use these dark/epic/film-score phrases on cute/playful former Storylight audio.
- For `Club Bloom`, do not add thumbnail wording by default. If the image needs a lane cue, use one short transparent-background phrase such as `DEEP HOUSE`, `TECH HOUSE`, `TRANCE MIX`, `BOOM BAP`, `JAZZ-HOP`, `TRIP-HOP`, `RARE GROOVE`, `VINYL SET`, `DISCO & BOOGIE`, or `AFTER HOURS` according to the actual music.
- For `Club Bloom`, reject visual assets that are too mild for a club channel: calm abstract neon, empty low-energy backgrounds, polite lounge imagery, low-contrast thumbnails, random glowing objects, or any image that lacks real nightlife/party energy. The cover and thumbnail should usually show attractive clearly adult women in revealing YouTube-safe club outfits at a place where club music naturally plays: nightclub, bar, lounge, rooftop club, beach club, pool party, festival VIP area, DJ booth, dance floor, neon city terrace, or yacht/harbor party. The camera feel should match HaruHaru's natural friend-taken smartphone/Instagram style: side or three-quarter angle, medium or farther framing, slight motion/focus imperfection, and no glossy campaign or centered AI-model headshot. Reject full nudity, exposed nipples/genitals, sexual acts, minors, teen-coded styling, school uniforms, fetish framing, celebrity likenesses, protected brands, or porn-style composition.
- For `BibliaCanto`, use passage-aware thumbnail wording such as `Genesis 1:1-5`, `Matthew 1:18-25`, `OLD TESTAMENT HIP-HOP`, `NEW TESTAMENT R&B`, `BIBLE K-POP`, `SCRIPTURE RAP`, `PSALMS HIP-HOP`, or `EXODUS TRAP`. Do not add `BIBLIACANTO` or any channel name to the visual, and do not use gospel/worship/church-style visual wording for new releases.
- For `불송`, use the same cover, YouTube thumbnail, first-frame, and still-image render source package, but rotate the mainstream nonreligious visual lane aggressively. Human subjects are optional; if present, they must be clearly adult and YouTube-safe. Default to no image text and avoid all Buddhist/source cues unless the human explicitly requests source-explicit packaging.
- Do not add duration text or badges to thumbnails. Avoid `1 HOUR`, `60 MIN`, `1時間`, clocks, timers, and duration stickers.
- Do not put the YouTube channel name, channel logo, or channel-brand line on covers, thumbnails, first-frame images, or loop videos.
- Use the cover or a separate clean first-frame image for Dreamina/Seedance/Gemini video generation on moving-video channels. Do not use a text-heavy thumbnail as the first-frame reference; generated video often makes large thumbnail text flicker, disappear, or reappear. For HaruHaru, sundaze, Solwave Radio, and Club Bloom, skip provider video generation and render from the still cover image.
- Do not add titles, lyrics, subtitles, UI, logos, duration badges, channel names, or unrelated words inside the moving visual. If text is needed, use only a short style, genre, use-case, or passage phrase already present in the first frame.
- If Gemini/Veo adds its own provider logo or watermark, usually in the bottom-right corner, accept it as an unavoidable provider artifact. Do not regenerate a valid loop video only because that Gemini/Veo logo or watermark is visible. Do not add any other logos, brand marks, UI, or unrelated text yourself.

Required moving visual:

- `--loop-video /absolute/path/to/loop-video.mp4`: short Gemini/Veo visual clip for the rendered video on normal moving-video channels. Gemini clips are uploaded as generated after inspection. HaruHaru, sundaze, Solwave Radio, Club Bloom, and 불송 are not moving-video channels by default; omit `--loop-video`.
- `--loop-video-provider gemini|dreamina|seedance`: records where a clip came from for compatibility with existing/manual provider assets. New OpenClaw automation must pass `gemini`; `dreamina` and `seedance` are legacy/manual values only. The app stores this in `loop_video_provider` and `loop_video_history[].provider`; Gemini-tagged uploads render with a 2.0 second app crossfade, while the default provider path stays at 1.5 seconds.
- Do not reuse the exact same loop-video MP4 file across releases. The app records the uploaded loop video's SHA-256 and rejects duplicate bytes on a different release, because a reused provider file can put the wrong channel's visual scene on an otherwise correct audio playlist.
- OpenClaw should generate/download only the short clip. Do not export a long MP4 from OpenClaw.
- The clip should be reusable for the full release: its final moment should stay close to the first-frame composition, camera distance, lighting, palette, and subject placement so the visual can cycle cleanly.
- Keep natural motion while returning close enough to the opening composition.
- Normal moving-video auto-publish should include a Gemini-generated `--loop-video --loop-video-provider gemini` while Gemini is available. Do not use the thumbnail image, a text-heavy image, an app-rendered still image, a locally synthesized motion loop, Dreamina, Seedance, or CapCut as the moving visual. A still-image fallback is allowed when the channel profile requires it, as HaruHaru, sundaze, Solwave Radio, Club Bloom, and 불송 now do, when the human explicitly requests it, or when Gemini is unavailable or unusable. In that case, OpenClaw must pass `--allow-still-image-video --video-render-source-mode still_image` plus the channel's normal spectrum/lyrics flags and continue render/publish. Every channel must pass `--video-spectrum-overlay-style bars`. For HaruHaru, sundaze, and Solwave Radio, queue `--video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars --lyrics-overlay --lyrics-overlay-style editorial-lower-left`; the MP4 uses lower-left lyrics and lower-right spectrum. For Club Bloom, queue `--video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars` without lyric overlay. For 불송, always queue `--video-render-source-mode still_image --video-render-resolution 720p --video-spectrum-overlay-style bars --lyrics-overlay --lyrics-overlay-style center-breath-serif --lyrics-alignment-mode whisper`; 불송 never needs a provider loop video in normal automation. `Cinematic Pulse` uses the Gemini loop-video path by default and falls back to still-image render only when Gemini is unavailable or unusable.
- The app validates uploaded loop videos only for technical readability. It does not reject low-motion clips or alternate clip lengths. OpenClaw still rejects unreadable/tiny files, but it should not reject a valid Gemini MP4 because of duration or deliberately low Cinematic Pulse motion.

Gemini-first website workflow for OpenClaw:

- Use Gemini only for moving loop-video generation, not for static cover or YouTube thumbnail creation. HaruHaru, sundaze, Solwave Radio, and Club Bloom skip this workflow in normal automation.
- Use Gemini as the only provider for each new moving loop video. If Gemini is on cooldown or unavailable, use the approved still-image fallback; do not open Dreamina, Seedance, or CapCut.
- Track the human's Gemini video quota manually. The quota is 3 successful Gemini video generations in a 24 hour window.
- Start the 24 hour cooldown from the moment the 3rd successful Gemini video is generated. It is not a calendar-day midnight reset unless Gemini explicitly says otherwise.
- Count only Gemini attempts where Gemini actually creates a video result. Copyright, policy, moderation, or prompt blocks that stop generation before a video is made do not count against the 3 successful videos.
- If Gemini creates a video but OpenClaw rejects it for quality, wrong text, weak motion, or bad framing, count it as one successful Gemini generation because the quota was spent.
- If Gemini says the daily video limit is reached or OpenClaw knows 3 successful Gemini videos were generated less than 24 hours ago, stop using Gemini for now and use the approved still-image fallback instead of deferring or switching providers.
- When Gemini cooldown clears, provider loop videos can be used again for future moving-video releases. Do not hold already-rendered still-image fallback releases waiting for Gemini.
- Before clicking Gemini Generate, run `scripts/openclaw-release provider-video-start --release-id RELEASE_ID --first-frame ABSOLUTE_FIRST_FRAME_IMAGE_PATH --provider gemini`. This records the release id and first-frame hash so a duplicate provider job is not started while Gemini is still generating.
- Open Gemini in the authenticated browser session.
- Click the `Create image` / creation entry that accepts an image attachment and prompt. Use the image-to-video or video creation option when the UI offers it.
- Attach the final cover or dedicated first-frame image as the first image. This image must not contain a channel name or logo, and it should not be overloaded with thumbnail click text.
- Paste the selected channel profile's Gemini motion prompt, shortening it only if the Gemini UI requires that.
- Ask Gemini to preserve the first-frame composition, stylized/animated look, and any short style/passage phrase already present, and to animate the surrounding scene naturally. Do not ask it to add subtitles, title text, UI, logos, spectrum bars, audio-reactive graphics, or channel branding.
- A Gemini/Veo provider logo or watermark in the corner is allowed and should not be treated as a failed generation.
- Choose `16:9` when the Gemini UI exposes that control. Do not ask Gemini for a duration and do not mention clip length in the prompt. Download the generated MP4 as-is, inspect it, and upload it if text, framing, and motion are acceptable.
- While Gemini is generating, wait and keep the OpenClaw lock alive; do not open another video provider with the same first-frame image. Check `scripts/openclaw-release provider-video-status --release-id RELEASE_ID --first-frame ABSOLUTE_FIRST_FRAME_IMAGE_PATH`. If `wait_remaining_seconds` is greater than 0, keep waiting. If there is still no usable Gemini MP4 after 20 minutes, run `provider-video-finish --provider gemini --status timed_out`, then use the approved still-image fallback.
- Download the generated MP4 to the VM or OpenClaw workspace.
- Inspect the MP4 before upload. Reject it if a short style/passage phrase flickers, is misspelled, changes position/style drastically, becomes unreadable, or if a channel name appears. For Cinematic Pulse, preview at least three consecutive repeats and reject only obvious join discontinuities, unrelated scene changes, lighting resets, or visible end resets. Do not reject camera movement, subject size/position/pose changes, or a subject entering/leaving when the ending base scene connects naturally to the opening base scene.
- When Gemini succeeds, run `scripts/openclaw-release provider-video-finish --release-id RELEASE_ID --first-frame ABSOLUTE_FIRST_FRAME_IMAGE_PATH --provider gemini --status succeeded --output-video ABSOLUTE_GEMINI_MP4`.
- Upload it with `scripts/openclaw-release upload-loop-video --release-id RELEASE_ID --loop-video ABSOLUTE_GEMINI_MP4 --loop-video-provider gemini`, or pass the same path with `--loop-video-provider gemini` to `auto-publish-playlist` / `auto-publish-single`.

Gemini copyright/policy retry rule:

- If Gemini refuses or blocks generation because of copyright, protected IP, policy, moderation, artist/style imitation, logo, brand, celebrity, or similar prompt/image issues, do not count that as one of the 3 successful Gemini videos.
- Rewrite the prompt and retry Gemini up to 10 blocked attempts for that release. Each retry must remove risky wording while preserving first-frame continuity, broad mood, and motion intent.
- Before each retry, send Slack progress with `scripts/openclaw-release slack-notify --text "Gemini 영상 생성이 저작권/정책 이슈로 막혀서 프롬프트를 수정해 다시 시도합니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`.
- If Gemini still cannot create a video after 10 blocked attempts, stop Gemini for that release and use the approved still-image fallback instead of spending more time or switching providers.

Provider fallback and deferral rule:

- If Gemini cannot create the clip after safe retries, account/payment/quota failure, browser failure, timeout, or another provider-side failure, do not leave the release unreleased/unrendered. Post `scripts/openclaw-release slack-notify --text "Gemini 영상을 사용할 수 없어 still-image fallback으로 렌더합니다. RELEASE_TITLE"`, then render with `--allow-still-image-video --video-render-source-mode still_image` plus the channel's normal spectrum/lyrics flags.

Legacy Dreamina website reference:

- Do not use the following workflow for new OpenClaw automation. It remains only as a reference for an existing release that already has a human-approved Dreamina/Seedance task or when the human explicitly requests that provider in the current request.

- Use `https://dreamina.capcut.com/ai-tool/home/` only for the explicitly approved existing/manual Dreamina/Seedance task.
- Before opening Dreamina/Seedance or clicking Generate for that explicit exception, run `scripts/openclaw-release provider-video-start --release-id RELEASE_ID --first-frame ABSOLUTE_FIRST_FRAME_IMAGE_PATH --provider dreamina` or `--provider seedance`. Never start it as an automatic fallback from Gemini.
- Use `Seedance Mini 2.0` for that existing/manual Dreamina/Seedance task.
- Do not use Omni Reference.
- Use first-frame/start-frame only. If the UI asks for a mode, do not provide a last-frame/end-frame image.
- Start from the cover image or a separate first-frame image without any channel name or logo. It should match the YouTube thumbnail scene and composition, including any explicit human visual request. It must not contain title sentences, duration text, or unrelated text.
- Leave the last-frame input empty. Do not upload a last-frame reference; adding both first and last frames makes Dreamina switch back to `Seedance 2.0 Fast` and wastes Seedance credits.
- Set ratio to `16:9` when selectable.
- Set quality to `720p` when selectable.
- Set duration to exactly `10 seconds` and re-check this visible control immediately before clicking Generate. `Seedance Mini 2.0` should be set to `10 seconds`; if the UI offers `5 seconds` or `10 seconds`, always choose `10 seconds`. If the duration control is not visible when the Seedance/Dreamina screen first opens, gently drag/scroll the settings/control row to the right until the duration option is visible, then set `10 seconds`.
- Do not click Generate while the duration control is hidden, while it shows 5 seconds, while the model has switched to `Seedance 2.0 Fast`, or while you are unsure. Do not create an initial 5 second clip, draft/test clip, or any other wrong-duration clip first.
- Generate exactly one short MP4 at `10 seconds`.
- Download the generated MP4 to the VM or OpenClaw workspace.
- Confirm the file exists locally before passing it to `--loop-video`.
- If login, CAPTCHA, subscription limits, face detection, moderation, credit/payment/quota limits, or manual approval blocks Dreamina/Seedance generation/download, do not create a local motion-loop substitute. Try Gemini if quota is available. If Gemini has already created 3 videos in the active 24 hour window, use the approved still-image fallback and move on to render/publish instead of deferring. When uploading any successful Dreamina/Seedance fallback clip, pass `--loop-video-provider dreamina` or `--loop-video-provider seedance`.
- When HaruHaru's selected theme-first concept uses a human, any clearly adult gender or grouping is allowed when it serves the story; a visible face is optional. For sundaze, Solwave Radio, and Club Bloom photorealistic still images, visible adult faces are allowed and preferred when natural. Reject/regenerate human imagery only for explicit, minor-coded, celebrity-like, policy-blocked, badly distorted, or visually unusable results.

Dreamina/Seedance fallback rejection recovery:

- If Dreamina/Seedance rejects generation for inappropriate content, copyright, policy, moderation, or similar content-safety reasons, do not retry the exact same prompt.
- Retry up to 10 total Dreamina attempts for that loop video. Each failed attempt must send Slack progress before the next retry:
  `scripts/openclaw-release slack-notify --text "영상 만들기 실패해서 프롬프트를 수정해 다시 만듭니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`
- On each retry, make the prompt more original and generic while preserving the release mood, first-frame continuity, and requested motion direction.
- Remove or generalize anything that can look like protected IP or policy-risk text: named artists, studios, franchises, characters, brands, celebrity names, song titles, exact style imitation phrases such as `in the style of`, logos, weapons, gore, sexualized wording, minors, and real-person likeness references.
- Replace risky references with generic descriptors. Examples: `Ghibli-like` becomes `soft hand-painted anime-inspired background`; `Disney style` becomes `warm family-friendly illustrated animation`; `YOASOBI music video style` becomes `bright mainstream Japanese pop visual mood`; a named character becomes `original youthful traveler silhouette`.
- If the first-frame image itself appears to trigger rejection, regenerate a safer cover/first-frame image first, keeping the same broad mood without channel names or logos.
- If all 10 Dreamina/Seedance attempts fail, try Gemini if quota is available.
- If Gemini quota is exhausted, send a fallback Slack message:
  `scripts/openclaw-release slack-notify --text "Gemini 3개 영상 쿼터가 끝났고 Dreamina/Seedance도 실패해서 still-image fallback으로 렌더합니다. RELEASE_TITLE"`
- After the fallback notice, do not stop this release only because loop-video generation is unavailable. Continue render/publish with the approved still-image fallback by passing `--allow-still-image-video --video-render-source-mode still_image` plus that channel's normal spectrum/lyrics flags. Do not create a local motion loop.

Dreamina/Seedance/Gemini motion prompt guidance:

- Ask the video provider for one continuous video shot whose final moment returns close to the first-frame composition. If the human requested a different motion/camera concept, ask for that requested continuous shot instead.
- Do not put duration, ratio, or quality in the prompt when the UI has controls for them. Set duration only in Dreamina/Seedance controls; do not ask Gemini for a duration.
- Do not include duration values such as `10 seconds` or `5 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the prompt. Do not mention duration in Gemini prompts. These words can make Seedance/Dreamina/Gemini create a shorter repeated segment inside the clip.
- Ask Dreamina/Seedance/Gemini to preserve the first-frame image's composition, lighting, palette, selected channel visual style, requested subject/action, and any short style/passage phrase already present.
- Use the selected channel profile for subject/action/motion. Use positive fixed-shot language only for profiles that require it. For Cinematic Pulse, do not use `loop`, `loop video`, `seamless loop`, `repeat`, or `cyclic`; describe one continuous cinematic shot whose closing base scene is broadly similar to its opening base scene. Always require no channel names, no extra text overlays, no subtitles, no logos, and no UI. Require no photorealism for the normal illustrated/anime/stylized channels; for `Cinematic Pulse`, use original photorealistic cinematic film-still / high-end movie-poster realism instead. Solwave Radio normally skips motion generation, but if the human explicitly requests motion, preserve its photorealistic Latin/Spanish friend-taken phone-photo lifestyle style.
- Provider-added Gemini/Veo corner logos or watermarks are allowed; the "no logos" requirement means OpenClaw must not request or create additional logos, brand marks, UI, or unrelated text.
- If the first frame contains a short style, genre, use-case, or passage phrase, ask Dreamina/Seedance/Gemini to keep that phrase stable and readable for the full clip. Do not ask for channel branding.
- After generation, inspect the downloaded MP4. Reject and regenerate if the existing short phrase is unreadable, misspelled, flickering, morphing, moving drastically, shrinking, changing style, or if a channel name appears.
- Ask for the final moment to be close to the opening composition, but not perfectly identical or static.
- If the model outputs audio, ignore it; the app uses the rendered playlist audio.

Recommended video prompt shapes are in the selected channel profile returned by `scripts/openclaw-release channel-profile`. Use the same prompt shape for Gemini after attaching the first-frame image.

Tokyo/J-pop video prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame.
Create one continuous forward-moving J-pop visual take.
Keep the channel signature: exactly three people walking toward the viewer in a front-view composition while the camera moves backward at the same speed.
The three people stay the same size and centered.
The final moment should stay close to the opening composition, camera distance, lighting, palette, and subject placement while maintaining natural motion.
Preserve the opening composition, lighting, palette, and anime/illustrated style.
If the first frame contains a short J-pop/style phrase, keep it stable and readable. Do not invent a channel name.
Adapt the background and atmosphere to the release concept.
Add side/background parallax, reflections, rain shimmer, particles, signs, trees, water, or soft light motion around the centered walking subjects.
No new text, subtitles, logos, UI, photorealism, live action, or extra people.
```

Soft Hour lane-matched piano BGM video prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame.
Create one uninterrupted calm environmental take for a background-music release from a locked-off camera.
Preserve the opening composition, lighting, palette, and stored visual lane: high-resolution photorealism for `classic_piano`, or bright premium original Japanese-animation/game-key-art illustration for `anime_game_ost`.
If the first frame contains a short use-case/style phrase, keep it stable and readable. Do not invent a channel name.
Animate calm but clearly visible natural motion across several environmental layers already present or naturally implied by the first frame and release mood: leaves, grass, curtains, water/rain reflections, warm light shimmer, drifting particles, smoke, steam, fireflies, or soft air movement when appropriate.
Keep continuous visible motion throughout the full clip while preserving the calm long-listening mood.
The final moment should preserve the opening composition, camera distance, lighting, palette, and subject placement while maintaining natural motion.
No new text, subtitles, logos, UI, protected characters, franchise references, or switching between photorealistic and illustrated styles.
```

If the human provided a specific visual/video request, replace the selected channel default subject/action/camera details with the requested scene, subject, action, motion, and camera angle. Keep the rest of the constraints: one continuous shot, stable composition, preserve first-frame composition/style, no channel names, no extra text, no subtitles, no logos, no UI, and no extra unwanted subjects.

For any channel, include this in the video-generation prompt: `The uploaded first frame must not contain a channel name or logo. If it contains a short style, genre, use-case, or passage phrase, keep that phrase stable and readable. Do not invent new text or channel branding. Keep the same composition, crop, camera distance, lighting, palette, and subject placement from first frame to final frame while animating natural environmental motion. No new text, subtitles, logos, UI, or title words.`

Thumbnail text rules for OpenClaw:

- Use 2-4 large words that describe the use case or mood, for example `CAFE PIANO`, `DEEP SLEEP`, `FOCUS MUSIC`, `RUNNING BEATS`.
- Prefer the approved full-bleed style: strong image background, no card or panel, and large genre/mood text in safe negative space.
- For Tokyo Daydream Radio releases, use J-pop lane text such as `J-POP`, `CITY POP`, or `ANIME POP`; do not use the channel name as a brand line.
- Do not add support text or duration badges. The thumbnail should not say `1 HOUR`, `60 MIN`, `1時間`, or show a time badge.
- Keep text large enough to read on a phone.
- Avoid long titles, dense paragraphs, fake UI, and obviously AI-looking distorted text.
- Keep the main default/requested subject centered and visible even when thumbnail text is added.

Localized YouTube metadata rules for OpenClaw:

- The app can upload YouTube localized metadata for `ko`, `ja`, `en`, `es`, `vi`, `th`, `hi`, `fil`, `id`, `tr`, `pt-BR`, `pt-PT`, `fr`, `de`, `ar`, `zh-CN`, and `zh-TW`.
- For `Tokyo Daydream Radio`, `HaruHaru`, `Storylight OST`, `Cinematic Pulse`, `Club Bloom`, `BibliaCanto`, `불송`, `sundaze`, `Solwave Radio`, mainstream J-pop/Japanese pop, K-pop/Korean pop, English pop, Latin/Spanish pop, playful Japanese game/anime OST BGM, cinematic orchestra/movie-OST/film-score BGM, no-vocal club music, scripture music, or similar pop-family/story-BGM releases, always write every configured language version: Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Turkish, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese.
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
- Pass Turkish through `--tr-title` and `--tr-description-file`; make the title natural Turkish YouTube copy.
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
- For `Cinematic Pulse`, do not use juvenile game-menu title wording such as `Boss BGM`, `Final Boss Music`, `Final Boss Focus Music`, `보스`, `보스전`, or bare `BGM` for cinematic lanes. Prefer broad film-score wording across varied lanes such as final battle scene, epic cinematic orchestra, dark fantasy film score, heroic trailer music, emotional film score, sci-fi cinematic music, mystery tension score, grand journey orchestra, orchestral battle music, writing music, and movie OST focus. Title-shape repetition is acceptable when it preserves channel fit and sounds natural to a broad YouTube audience, but examples are style references rather than fixed templates. For former Storylight-style cute/playful game/anime BGM on Cinematic Pulse, use truthful game/anime/BGM wording instead, and never approve dark fantasy / epic battle / trailer / cinematic orchestra metadata for cute audio.
- For `Club Bloom`, keep the truthful genre or DJ selection easy to identify near the front, but write a natural curator-style title rather than a keyword formula. Use one main listening moment, no more than one separator, and no literal English-to-local-language word-order transfer. Never force EDM/workout/gaming wording onto retro audio.
- Use `walk` / `산책` only when walking, commuting on foot, street movement, beach/forest walks, crosswalks, or similar movement is genuinely central. For arcade, game-center, karaoke, friend-hangout, party, rooftop, club, dance-pop, bass-heavy, or workout-ready releases, prefer arcade, gaming, friends, night out, getting ready, workout, running, party warmup, driving, nightlife, confidence, or weekend energy.
- For Japan/J-pop/Tokyo Daydream Radio titles, do not over-emphasize the language. Prefer `J-POP`, the actual Japan scene, city-pop/mainstream pop substyle, mood, and listening use cases. Avoid Korean title phrases like `일본어 J-pop`, `일본어 보컬`, or `일본어 카페 재즈` unless the human explicitly asks to highlight the language. `Tokyo Daydream Radio` is the channel brand, not a required title keyword; use `Tokyo` only for genuinely Tokyo-specific concepts. If language matters, mention it naturally in the description instead; the thumbnail text can carry `J-POP`.
- In Korean title/description/localizations, do not use the transliterated words `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`. Use `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡`.
- Keep all localized titles under 100 characters. Keep timestamps identical across languages; localize displayed track-title text and surrounding description naturally unless a channel-specific rule says to preserve original song titles.
- For Japan/J-pop/Tokyo Daydream Radio timestamped tracklists, format localized rows by language: Korean/default uses Japanese title plus Korean translation in parentheses, Japanese uses Japanese title only, and every other localized description uses translated title text only.
- For sundaze/English-American pop playlist metadata, localized video titles may be natural adaptations in each language instead of exact English copies. In timestamped tracklists, keep the English song title after each timestamp in every localized description. Translate only the surrounding description prose, use-case line, and hashtags.
- Use the base-block `rendered_timeline` for every localized description. If the optional final-repeat feature is enabled later, do not add second/third-pass repeated timestamps. If the base timeline itself is 60 minutes or longer, use `HH:MM:SS` for every timestamp, starting with `00:00:00`.
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

- Use `Soft Hour Radio` for its alternating classic-piano and Japanese anime/game-OST piano background lanes. If the concept is lofi beats, guitar-led, Rhodes, jazz trio, ambient pads, or unrelated mixed-instrument BGM, do not route it to Soft Hour.
- Use `Tokyo Daydream Radio` for mainstream J-pop/Japanese pop, Tokyo/Japan pop, city pop, dance-pop, synth-pop, pop-rock, anime-pop, vaporwave, 도쿄, 시티팝, 제이팝, 東京, Jポップ, or シティポップ concepts.
- Use `sundaze` for English/American pop playlist concepts: US/UK pop, western pop, mainstream English vocal pop, dance-pop, synth-pop, pop-rock, Pop R&B, pop hip-hop, country pop, Americana pop, indie pop, bedroom pop, alt-pop, acoustic pop, singer-songwriter pop, folk-pop, soft rock, pop-punk, Y2K/recession pop, disco/funk pop, Afrobeats, Afropop, Amapiano-pop, or similar English-forward pop concepts.
- Use `Solwave Radio` for Latin/Spanish pop, Spanish pop, urbano latino, reggaeton pop, bachata pop, salsa pop, cumbia pop, tropical dance-pop, verano latino, or similar Spanish vocal concepts.
- Use `HaruHaru` for K-pop, Korean pop, Korean dance-pop, Korean synth-pop, Korean pop-rock, Korean R&B pop, idol-pop inspired music, or similar Korean vocal concepts.
- Do not use `Storylight OST` for new automatic uploads; it is manual-only.
- Use `Cinematic Pulse` for playful no-vocal Japanese-style game/anime OST, arcade-game BGM, fantasy-game BGM, cute RPG music, item-shop music, mini-game music, amusement/theme-park BGM, and light adventure instrumental concepts as the former Storylight lane.
- Use `Cinematic Pulse` for no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, sci-fi, dark fantasy, heroic, premium game orchestra, anime action-RPG OST, and game-focus instrumental concepts as the cinematic lane.
- Use `Club Bloom` for no-vocal modern club music and rhythm-led DJ-crate concepts, including boom bap, jazz-hop, trip-hop, rare groove, soul breaks, disco/boogie, broken beat, and instrumental R&B/neo-soul.
- Use `BibliaCanto` for Old Testament, New Testament, Genesis, Matthew, Jesus words, Psalms, Bible verse music, scripture-inspired songs, grace music, kingdom teaching, or ancient biblical passage concepts. New BibliaCanto songs should sound like trendy hip-hop, R&B, K-pop-inspired pop, rap-pop, trap-soul, boom bap, alt-R&B, or neo-soul, not gospel, worship, holy, hymn, church choir, praise-band, CCM, or congregational music.
- Use `불송` for Korean vocal music internally inspired by Buddhist sources/themes. Keep the source/theme in planning/app metadata, but new public lyrics/metadata should avoid overt Buddhist words. The release lane should vary across modern styles such as hip-hop, boom bap, trap-soul, dark R&B, trip-hop, glitch-hop, drum and bass, hyperpop, psychedelic soul, avant-jazz rap, spoken-word rap, new-age electronica, cinematic trap, and art-pop. Avoid trot, ppongjjak, and old Korean cabaret-pop unless explicitly requested. The app schedules these uploads public daily at 07:00 Asia/Seoul.
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
- For playlist releases, audio render can randomize order with `random: true`. Use this when Suno generated similar A/B pairs and both were uploaded, so paired tracks do not remain adjacent. Do not manually shuffle timestamps; metadata must use `metadata-context` after render. Vocal playlists contain only new tracks. Instrumental playlists keep eligible reused tracks behind the fresh lead block.

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

scripts/openclaw-release create-release --workspace-mode playlist --release-title "TITLE" --youtube-channel-title "CHANNEL_TITLE" --description "CONCEPT"

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
If a 16:9 cover image is ready, run this as soon as possible; the app accepts uploaded covers before rendered audio is available:

scripts/openclaw-release upload-cover --release-id RELEASE_ID --cover ABSOLUTE_COVER_PATH
```

After uploading the cover, approve it. If audio render is still pending, the release will wait in `pending_audio_render`. Once the approved cover and required visual source are present, OpenClaw may call `render-video` before audio render completes; moving-video channels require an uploaded loop video, while HaruHaru, sundaze, Solwave Radio, Club Bloom, and 불송 require the still cover plus `--allow-still-image-video --video-render-source-mode still_image`. The app stores the request in metadata and automatically queues the final `build_video` job when rendered audio becomes available. If audio is already rendered, `render-video` queues `build_video` immediately.

If the human explicitly asks OpenClaw to publish one single all the way to YouTube, use the automatic single publisher instead:

For liked existing app tracks, use a different path: do not re-upload the audio file and do not create a duplicate track. Search candidates with `scripts/openclaw-release search-tracks --user-rating like --exclude-single-uploaded --full`, create a fresh Single Release, then attach exactly one existing track with `scripts/openclaw-release reuse-track --release-id RELEASE_ID --track-id TRACK_ID`. Continue with final cover, thumbnail, render, metadata, and publish steps. The app records successful standalone YouTube uploads on the source track as `single_youtube_uploaded`, `single_youtube_video_id`, and `single_youtube_uploads`; skip tracks already marked this way unless the human explicitly asks for a replacement.

Liked-track single cover and thumbnail assets must be special single-song packaging, not normal playlist artwork. Read the song title, lyrics, style, and strongest hook before generating images. Create a clean, trendy, memorable cover/thumbnail pair that fits the one song and channel, with one clear subject or scene, minimal text, no channel name/logo, no copied playlist cover, no generic playlist label, and no black/boxed text background.

```text
Create an original single release and publish it through the app.
Generate or obtain:
- one final Suno audio file per YouTube single
- a final clean 16:9 cover image
- a separate YouTube thumbnail image with readable text for normal moving-video channels; for HaruHaru, use a normally text-free derivative of the approved theme-first cover in the same medium; for Solwave Radio, use a photorealistic friend-taken phone-photo lifestyle thumbnail with one short integrated Latin/Spanish lane phrase when useful; for Club Bloom, use a text-free derivative of the approved club or record-culture cover by default, with one short transparent-background club lane phrase only when needed; for `불송`, reuse the same theme-first non-Buddhist cover/first-frame package as the thumbnail
- one short Gemini loop video for moving-video channels, uploaded as generated after inspection with `--loop-video-provider gemini`. For HaruHaru, sundaze, Solwave Radio, Club Bloom, and 불송, skip loop video and use `still_image` render flags.

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
  --loop-video ABSOLUTE_GEMINI_LOOP_MP4 \
  --loop-video-provider gemini \
  --prompt "PROMPT" \
  --tags "TAGS" \
  --youtube-channel-title "Tokyo Daydream Radio"

For non-Japan releases, use the selected channel profile. Korean/K-pop goes to `HaruHaru`; playful mixed-instrument game/anime/arcade/theme-park music goes to the Cinematic Pulse `cute_game` lane; broad chamber, film-score, game-score, and epic orchestral music goes to Cinematic Pulse `orchestra`; no-vocal club music goes to `Club Bloom`; Bible scripture music goes to `BibliaCanto`; Korean vocal music with an internal Buddhist-source plan goes to `불송`; English/American pop goes to `sundaze`; Latin/Spanish pop goes to `Solwave Radio`. Piano-first BGM and the selected Soft Hour `anime_game_ost` piano lane stay on `Soft Hour Radio`; do not reroute that stored lane to Cinematic Pulse.
Pass exactly one --audio/--title/--lyrics-file/--style per auto-publish-single run, plus one --exclude-style if excluded styles/negative tags were used. If two Suno outputs are both good, create separate cover/thumbnail/loop-video assets and run auto-publish-single twice for moving-video channels. For HaruHaru, create a separate approved theme-first still cover/thumbnail package; for sundaze and Solwave Radio, create separate photorealistic still cover/thumbnail assets. Pass `--allow-still-image-video --video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars --lyrics-overlay --lyrics-overlay-style editorial-lower-left` instead of `--loop-video`. For Club Bloom, create separate lane-specific premium still cover/thumbnail assets and pass `--allow-still-image-video --video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars` instead of `--loop-video`. For `불송`, pass the same theme-first non-Buddhist cover/first-frame package as `--thumbnail` or use `--allow-cover-as-thumbnail`, and render with `--allow-still-image-video --video-render-source-mode still_image --video-render-resolution 720p --video-spectrum-overlay-style bars --lyrics-overlay --lyrics-overlay-style center-breath-serif --lyrics-alignment-mode whisper` instead of `--loop-video`.
```

## Safety Rules

- Do not call `Approve Publish` automatically unless the human explicitly asks for full publishing.
- Do not upload videos directly through `youtube.com` or YouTube Studio. Use `scripts/openclaw-release publish-release --no-wait` or the app's local `/approve-publish` API for playlist finish passes. The app performs the real YouTube upload through the YouTube Data API. In continuous automation, do not wait for the YouTube id after the app queues `upload_youtube`; release the OpenClaw lock and continue on the next backlog pass.
- Do not use an existing `--release-id` that already has `youtube_video_id` for a normal new publish. Create a new release instead. Re-upload escape hatches should be used only when the human explicitly asks to upload the same release again.
- YouTube Studio is only for human final review after the API upload, such as watching the result, confirming the scheduled public time, reviewing app-uploaded CC captions, or manual fixes.
- Do not try to turn on captions through browser automation. For vocal releases with saved lyrics, the app uploads YouTube CC caption tracks through the API at publish time using faster-whisper line timing and Codex translations. For BGM/instrumental/no-vocal releases, leave captions/audio language alone unless the human explicitly asks for manual captions.
- Do not open Suno or generate audio before creating/selecting the app release workspace. Fresh work starts with `scripts/openclaw-release create-release`; continuing work starts with `scripts/openclaw-release list-releases` and `--release-id`.
- Do not upload to YouTube automatically unless running a finisher pass for a rendered playlist release or using `auto-publish-single` after explicit human instruction.
- If cover art is ready with the audio, upload it in the same command with `--cover`; otherwise omit `--cover` and let the human add/regenerate cover later.
- If lyrics, meaningful song-content notes, or an instrumental Suno metatag file are available, upload them in the same command with `--lyrics` or `--lyrics-file`. Use an empty value only when lyrics/content are truly unknown.
- For BGM/background/lofi/study/sleep/cafe singles and playlists, instrumental/no-vocal is the default, but an empty lyrics/custom-lyrics field is not preferred. For new Soft Hour Radio audio, name the stored lane and concrete piano sound: solo/felt/quiet piano for `classic_piano`, or original Japanese anime/game-OST-style piano for `anime_game_ost`. Use `docs/suno-v55-instrumental-format.md`: enable Instrumental when available, write only bracketed metatag lines, and upload that exact file. For vocal pop lanes, do not leave lyrics empty by default.
- For vocal pop uploads, lyrics should be standalone song lyrics, not literal descriptions of the YouTube playlist title, thumbnail text, visual scene, or listening use case. Match the melody, beat, tempo, energy, and vocal attitude to the playlist context, but write natural pop lyrics with their own emotion, story, and hook.
- For no-vocal Suno work, also fill Advanced Options excluded styles with vocal-related exclusions: `vocal, vocals, voice, voices, singing, singer, lead vocal, backing vocals, choir, choral, humming, hum, whisper, spoken word, speech, narration, rap, ad-libs, scat, vocal chops, ooh, aah, la la, lyrics, sung lyrics, topline`.
- For lyric/vocal Suno work, fill Advanced Options excluded styles with vocal clarity blockers: `muddy vocals, muffled vocals, washed-out vocals, distant vocals, buried vocals, unclear lyrics, heavy reverb, excessive reverb, long reverb tail, large echo, echoey vocals, concert hall echo, arena reverb, stadium reverb, live concert vocals, crowd ambience, room boom`.
- For every Suno generation on every channel, add artificial noise blockers to Advanced Options excluded styles unless the human explicitly asks for vinyl/LP/noise texture: `white noise, static noise, vinyl crackle, record crackle, LP crackle, turntable noise, tape hiss, cassette hiss, analog hiss, noise floor, lo-fi noise, old record noise, dust noise, crackle, hiss`.
- Before pressing Create in Suno, remove producer tags and specific artist references from lyrics, bracketed metatags, style, prompt, tags, and excluded styles. If Suno rejects a word such as `lowlight` as a producer tag, rewrite it to a generic descriptor like `low-lit`, `dim`, `shadowy`, `muted night`, or `soft ambient`, then retry generation.
- After every audio upload, confirm that the returned `duration_seconds` is close to the actual song length. If it is `0`, much shorter than expected, or the upload fails as unreadable, fix the source file and re-upload before moving on.
- For playlist work, confirm every uploaded `duration_seconds` is 60 or higher unless a human explicitly approved a shorter track. Tracks from 60 to 119 seconds are accepted and recorded for later analysis. There is no default maximum track length; complete 5+ minute tracks are acceptable.
- For playlist automation, if a few songs fail after the 3 upload attempts, do not abandon the rest of the batch. Let the helper upload the remaining songs, read the Slack warning, then re-upload only the failed files and rerun render/publish after the release has the full intended track set.
- If Suno style/settings are available, upload them in the same command with `--style`. If excluded styles/negative tags are available, upload them with `--exclude-style`.
- For `불송` Suno work, choose one diversity-first modern Korean lane such as hip-hop, boom bap, trap-soul, dark R&B, trip-hop, glitch-hop, drum and bass, UK garage, phonk, hyperpop, psychedelic soul, avant-jazz rap, spoken-word rap, new-age electronica, cinematic trap, or art-pop. Do not use obscure coined genre wording or source-explicit Buddhist wording in new titles, thumbnail text, descriptions, tags, or sung lyrics unless the human explicitly asks. Generate the full target duration, normally roughly 60 minutes, as new Korean vocal music and do not attach previous tracks. Put the strongest hook/rap/vocal entry first. Existing/source-explicit uploaded videos go into the YouTube playlist `불송`; new mainstream uploads go into `노래`. Exclude trot/ppongjjak explicitly with `--exclude-style` or Suno Advanced Options and reject outputs that strongly sound like old Korean cabaret-pop.
- For `불송` vocal Suno work, do not add a mandatory first-verse or fixed 60-90 second listening gate before upload; that creates a production bottleneck. Use lightweight vocal sanity checks instead: verify the Suno setup is vocal/lyrics-based, avoid instrumental/no-vocal settings, and reject/regenerate only when the preview, metadata, or a very quick spot check makes it obvious that the file is instrumental, pad-only, hum-only, or missing a usable lead rap/vocal.
- Do not generate a batch by repeating one Suno prompt/style/lyric template. Each new Suno request should have a distinct prompt/style/lyrics plan while staying inside the requested release mood.
- For HaruHaru, sundaze, and Solwave Radio playlist releases, choose one explicit genre lane before Suno generation and keep the whole playlist in that lane. For HaruHaru, use a Korean/default title shape with a short clickable hook first and the truthful situation/genre after the separator, such as `[playlist] 나랑 데이트 할래? | 데이트하기 전 기분 좋아지는 K-POP 힙합 노래모음`. The thumbnail/cover mood should visually match that hook. sundaze lanes include Pop R&B, dance-pop, synth-pop, pop-rock, country pop, Americana pop, indie/bedroom/alt-pop, singer-songwriter/folk-pop, soft rock, pop-punk, Y2K/recession pop, disco/funk pop, Afrobeats, Afropop, and Amapiano-pop. Name that lane in the public title/metadata when accurate instead of writing a generic mixed-pop title.
- Do not generate vocal songs by mechanically inserting the release title/use-case words into every verse or chorus. For example, a dance-practice, walking, driving, workout, study, or party playlist should get songs whose sound fits that context; the lyrics can be about love, confidence, heartbreak, freedom, youth, or another strong pop topic.
- Treat generated draft covers in the web UI as replaceable placeholders, not final art.
- Use OpenAI GPT Image models for static cover and thumbnail images. Do not use Dreamina for static image generation.
- Static cover and thumbnail images must follow the channel profile returned by `scripts/openclaw-release channel-profile`.
- In thumbnails, keep the main channel/requested subject centered; text must not push it sideways.
- Generate the thumbnail from the final cover as a reference/edit derivative. Preserve characters, positions, outfit colors, lighting, palette, and background continuity; only add concise click text and readability adjustments.
- Do not use generated draft covers for full OpenClaw auto-publish runs. OpenClaw must create/upload a real final cover image first.
- Do not publish without final thumbnail handling. For non-불송 channels, OpenClaw must create/upload a text thumbnail and pass it as `--thumbnail`. For `불송`, OpenClaw may reuse the same text-free mainstream Korean-song cover/first-frame package as the thumbnail by omitting `--thumbnail` or passing `--allow-cover-as-thumbnail`; it must not contain overt Buddhist/source imagery or labels unless the human explicitly requests source-explicit packaging.
- OpenClaw should create a Gemini/Veo clip and pass the short MP4 as `--loop-video --loop-video-provider gemini` before normal moving-video render/publish while Gemini is available. If Gemini is unavailable, on cooldown, blocked after safe retries, or cannot return a usable MP4 inside the wait window, use the approved still-image fallback instead of deferring or switching providers. The generated clip should end close to its opening composition so it can be reused across the long video. For fallback, pass `--allow-still-image-video --video-render-source-mode still_image` plus that channel's normal spectrum/lyrics flags. Every channel uses `--video-spectrum-overlay-style bars`. For HaruHaru, sundaze, Solwave Radio, and Club Bloom, still-image render is the default, so pass `--allow-still-image-video --video-render-source-mode still_image --video-render-resolution 1080p --video-spectrum-overlay-style bars` and do not upload `--loop-video`; HaruHaru, sundaze, and Solwave Radio also pass `--lyrics-overlay --lyrics-overlay-style editorial-lower-left`. For `불송`, still-image render is the standing channel rule, so do not create or upload `--loop-video`; pass `--allow-still-image-video --video-render-source-mode still_image --video-render-resolution 720p --video-spectrum-overlay-style bars --lyrics-overlay --lyrics-overlay-style center-breath-serif --lyrics-alignment-mode whisper`.
- Keep `--cover`, `--thumbnail`, and `--loop-video` separate for normal moving-video channels. `--thumbnail` should have readable YouTube click text; `--cover` and `--loop-video` should use the cleaner first-frame composition without channel names. For HaruHaru, keep only `--cover` and `--thumbnail` as the selected theme-first still-image package, normally text-free, and leave lower-left/lower-right space for app lyrics/spectrum. Do not fall back to a woman, portrait, city street, or fixed medium. For Solwave Radio, keep only `--cover` and `--thumbnail` as photorealistic Latin/Spanish friend-taken phone-photo still images; avoid professional photographer shoots, studio/fashion-campaign lighting, over-retouched model faces, and tight straight-on AI-beauty close-ups. The thumbnail may use one short integrated Latin/Spanish lane phrase, and the final video uses lower-left lyrics plus lower-right spectrum. For Club Bloom, keep only `--cover` and `--thumbnail` as the approved premium club or record-culture still-image package; the final video uses lower-right spectrum and no lyric overlay by default. Club Bloom thumbnails are text-free by default and use a short transparent-background lane phrase only when needed. Never feed a text-heavy thumbnail into Gemini as the first frame; use the cover or a dedicated first-frame image. For `불송`, use one theme-first text-free cover/thumbnail/first-frame package with a fresh non-Buddhist mainstream Korean-song concept and no default gender or medium. If the human requested a specific video visual, that visual request must be reflected consistently across all assets.
- For `불송`, the fresh visual package must include a `novelty_brief` and visibly avoid recent repetition. Valid subjects include adult street/lifestyle scenes, R&B city nights, rainy rooms or car windows, duet/couple tension, cinematic city stills, surreal nonreligious symbols, anime/illustrated modern music concepts, dark editorial fashion, object-led album art, and bold graphic realism. Male, female, and mixed adult subjects are all allowed when concept-appropriate.
- For `불송`, do not use a previous release image, previous thumbnail, final still, or rejected/bad image as a reference for a new release. Generate each new 불송 visual package from a fresh text prompt after checking recent releases, and force visible variation in face, pose, setting, outfit, camera angle, and palette. Only use the current release's approved cover as a reference for its own thumbnail or still source.
- A Gemini/Veo provider logo or watermark in the corner is allowed and is not a reason to regenerate the loop video.
- For Gemini, use the `Create image` / image+prompt workflow above for moving-video channels, attach the cover/first-frame image, do not mention duration, count only successful video generations toward the 3 videos per 24 hour quota, and upload with `--loop-video-provider gemini`. Do not use Dreamina, Seedance, or CapCut for normal OpenClaw automation. HaruHaru, sundaze, Solwave Radio, and Club Bloom do not use Gemini in normal automation.
- For normal OpenClaw auto-publish work, verify the Gemini MP4 after download and upload it as-is when text, framing, motion, and channel-specific boundary continuity are acceptable. For Cinematic Pulse, preview at least three back-to-back repeats and check only for an obvious last-to-first discontinuity, unrelated scene change, lighting reset, or typography flicker. Camera/subject motion and temporary subjects entering/leaving are valid when the closing base scene remains broadly compatible with the opening base scene.
- For Playlist Releases, `upload-audio` auto-approves by default. Do not add `--pending-review` unless the human explicitly asks.
- For Playlist Releases, do not use pair/number titles. Replace Suno A/B or 1/2 output labels with independent track names before upload.
- For Suno two-output generations, upload both candidates to one Single Release using `upload-single-candidates`.
- Single Release candidates are still human-reviewed; the human may approve one candidate, approve both candidates as separate Single Releases, or reject both.
- If both candidates are rejected, the app will archive the release automatically; do not delete files or database rows manually.
- If three or more songs are ready for one release, use a Playlist Release instead.
