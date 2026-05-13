# OpenClaw Upload Workflow

Use this when OpenClaw has generated an audio file and needs to hand it to the AI Music web app.

For higher-level OpenClaw skill instructions, including "make one single", "build a 40+ minute playlist", and "write YouTube metadata", see [openclaw-skills.md](openclaw-skills.md).
For the metadata-specific command and prompt, see [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).
For channel-specific image/video rules, first run `scripts/openclaw-release channel-profile` and read the returned `profile_doc` in [openclaw-channel-profiles](openclaw-channel-profiles/README.md). For next-release concept planning, read the returned `concept_doc` in [openclaw-channel-concepts](openclaw-channel-concepts/README.md).

Run these commands from the OpenClaw repo checkout, normally `~/repos/ai-music-playlist-generator` in the OpenClaw runtime. If that path is missing, try `~/repos/ai리포` or the current checkout.

Use `scripts/openclaw-release` against the deployed AI Music app API. `AIMP_LOCAL_API_BASE` must point to the deployed VM app API or a tunnel to that API. Do not use OpenClaw's own local dev API; if `/youtube/status` returns `configured=false`, `authenticated=false`, `ready=false`, or `channels=[]`, stop before generation/publish because the API target is wrong.

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
- J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop tracks are vocal by default. Unless the human explicitly requested instrumental/BGM/lofi/no vocals, create or capture original lyrics and pass them with `--lyrics` or `--lyrics-file` for every uploaded pop-family track. Use Japanese lyrics for J-pop/Japanese pop/anime-pop, Korean lyrics for K-pop, English lyrics for sundaze/English/American pop, and Spanish lyrics for Solwave/Latin/Spanish pop. The helper now rejects pop-family uploads with empty lyrics before publish unless the concept explicitly says BGM/instrumental/no-vocal.
- Suno can reject lyrics/custom-lyrics, style, prompts, tags, or excluded styles that look like producer tags or specific artist references. Do not use producer names, artist names, label names, artist-like aliases, `type beat` credit text, or exact imitation phrases. Known blocked example: `lowlight` can trigger `Your lyrics contain producer tag lowlight`. Replace flagged terms with generic mood words such as `low-lit`, `dim`, `shadowy`, `muted night`, or `soft ambient`, then retry before uploading the track.
- Lyrics are stored with the track so future thumbnail, Dreamina loop-video, metadata, or standalone single publishing work has song-content context.

Style behavior:

- `--style` is optional, but OpenClaw should provide it whenever the Suno style/settings are known.
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
- Suno duration wording should be minimal: use only `less than 4 minutes` or `under 4 minutes` when a duration hint is needed. Do not add exact ranges, lower-bound targets, or any extra ending/completion wording to prompts, style strings, lyrics, or bracketed metatags. The helper rejects playlist tracks over 4 minutes by default.
- After audio render, the app stores `rendered_timeline` from actual ffprobe source-file durations. Metadata and OpenClaw `metadata-context` should use that rendered snapshot instead of recalculating timestamps from rounded track durations.
- If a playlist was built from Suno two-output batches and paired variants sit next to each other, pass `--randomize-order` to `auto-publish-playlist` or call `/render-audio` with `random: true`. The app persists the shuffled order before rendering, so final order and metadata timestamps still match the rendered audio.

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

When `scripts/openclaw-release upload-audio` targets an existing Playlist Release, the helper now uploads the track and immediately approves it into the playlist. It also skips the per-track Slack review message so a 40+ minute playlist does not spam Slack.

Playlist track titles should look like final tracklist titles, not Suno alternatives. Do not upload names like `Title A`, `Title B`, `Title 1`, `Title 2`, `Title - Morning`, or `Title - Evening`. Give every playlist item a standalone title that fits the mood.

```bash
scripts/openclaw-release upload-audio \
  --release-id RELEASE_ID \
  --audio /absolute/path/to/playlist-track.mp3 \
  --title "Track Title" \
  --lyrics-file /absolute/path/to/playlist-track-lyrics.txt \
  --style "Suno style/settings used for this track" \
  --prompt "Short generation prompt or notes" \
  --tags "Playlist,BackgroundMusic,Music"
```

The JSON result should include:

- `auto_approved: true`
- `track.status: approved`

Only use `--pending-review` if the human explicitly asks to review playlist tracks one by one.

If OpenClaw uploads many playlist files in one automation run, prefer `auto-publish-playlist` with one `--title` per `--audio` so the final YouTube tracklist already has natural titles.
Also pass one `--lyrics` or `--lyrics-file` per `--audio` when lyrics or instrumental metatag files are available. For BGM/background/instrumental tracks, prefer the exact bracket-only Suno instrumental metatag file from `docs/suno-v55-instrumental-format.md` over empty lyrics. For J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop releases, lyrics are expected by default and should be uploaded for every track unless the human explicitly requested instrumental/BGM/lofi/no vocals. Pass one shared `--style` or one `--style` per `--audio` whenever Suno style/settings are known.
For pop-family releases, do not proceed without lyrics. If Suno returns a vocal song but no lyric text is visible, write/capture the final intended lyrics before uploading. If the human explicitly wants a J-pop-feeling instrumental, include BGM/instrumental/no-vocal wording in the prompt/title/tags so the helper treats empty lyrics as intentional.
For vocal playlist releases, write a different lyric concept for every track before generation. Do not reuse the same chorus hook, verse structure, or only swap a few words between songs. Each track should have a distinct emotional angle and memorable phrase.
Suno duration wording should be minimal: use only `less than 4 minutes` or `under 4 minutes` when a duration hint is needed. Do not add exact ranges, lower-bound targets, or any extra ending/completion wording to prompts, style strings, lyrics, or bracketed metatags. The helper rejects playlist tracks over 4 minutes by default.

For full automatic playlist publishing, two final 16:9 images are required.

- `--cover /absolute/path/to/video-cover.png`: playback visual used inside the rendered video. It must include only the selected channel name as a large, readable lower-left brand label because it is also the Dreamina/Seedance first-frame reference.
- `--thumbnail /absolute/path/to/youtube-thumbnail.png`: YouTube click thumbnail. Include short readable click text plus the selected channel name as a smaller brand line.

Do not rely on the app's generated draft cover for YouTube upload. Do not reuse the cover as the thumbnail unless the human explicitly approves one image for both roles. The thumbnail is for clicks and should have large text; the cover is the Dreamina/Seedance first-frame reference, so it should contain only the lower-left channel brand label.

Static image creation rules:

- Before static image creation, run `scripts/openclaw-release channel-profile` and read the returned `profile_doc`. That profile controls cover, thumbnail, and loop-video direction.
- Follow the selected channel profile. Do not mix visual signatures across channels.
- Do not use Dreamina for static cover or YouTube thumbnail images.
- Use OpenAI GPT Image models for static image generation. Prefer `gpt-image-2` when available; otherwise use the currently available GPT Image model in the running OpenAI/Image tool environment. Do not assume OpenAI API usage is free; use the available image tool or configured API credentials.
- If `gpt-image-2` is unavailable in the actual tool/API environment, fall back to the best available GPT Image model instead of using Dreamina for static images.
- Produce 16:9 images, preferably `1280x720` or `1920x1080`.
- Create the final cover first. It must include only the selected channel name as a large, readable lower-left brand label. Then create the YouTube thumbnail from that exact final cover as an image-to-image edit/reference derivative. Do not make the thumbnail as a fresh unrelated generation.
- For `Tokyo Daydream Radio` or Japan/J-pop releases, use the Tokyo Daydream Radio profile unless the human requested a different visual concept.
- For `Soft Hour Radio` or default BGM/cafe/sleep/study/chill releases, use the Soft Hour Radio profile.
- For `sundaze` or English/American pop releases, use the sundaze profile. There is no fixed visual signature yet; the playlist concept should drive cover, thumbnail, and loop-video visuals.
- For `Solwave Radio` or Latin/Spanish pop releases, use the Solwave Radio profile. There is no fixed visual signature yet; the playlist concept should drive cover, thumbnail, and loop-video visuals.
- For `HaruHaru` or Korean/K-pop releases, use the HaruHaru profile. There is no fixed visual signature yet; the playlist concept should drive cover, thumbnail, and loop-video visuals. Lyrics are Korean by default.
- For `Storylight OST`, use the Storylight OST profile for playful no-vocal Japanese-style game/anime OST, arcade-game BGM, fantasy-game BGM, cute RPG music, item-shop music, mini-game music, and light adventure instrumental releases.
- For `Cinematic Pulse`, use the Cinematic Pulse profile for no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, sci-fi, dark fantasy, heroic, and game-focus instrumental music.
- For `Club Bloom`, use the Club Bloom profile for no-vocal EDM, house, techno, trance, festival, workout, night-drive, gaming, club, and party-energy releases. Each playlist must choose one club style lane and stay within it.
- For `The Old Verse`, use the Old Verse profile for lyric-based Old Testament scripture-inspired songs that follow the Bible sequence from Genesis onward. Vocal songs with original English lyrics are expected unless the human explicitly asks for instrumental/BGM or another lyric language.
- For `The New Verse`, use the New Verse profile for lyric-based New Testament/Gospel/worship songs that follow the Bible sequence from Matthew onward. Vocal songs with original English lyrics are expected unless the human explicitly asks for instrumental/BGM or another lyric language.
- If the human explicitly names the upload channel, that channel controls visual routing.
- Human visual requests override the selected channel visual skill. If the human asks for a specific scene, subject, action, camera angle, object, animal, character type, or video concept, use that request consistently for the cover, thumbnail, and loop video.
- For thumbnails, the main default/requested subject must stay centered and visually important. Text must not push it to the side, crop it, cover it, or make it feel secondary. Put text into safe negative space around the centered composition.
- Keep every static visual animated, anime, illustrated, or stylized. Do not use photorealistic, live-action, documentary, camera-photo, or realistic human footage.
- The cover should be the clean channel/requested scene with only the selected channel name as a large lower-left brand label. The YouTube thumbnail should use the same composition plus large readable click text and channel branding.
- When deriving the thumbnail from the cover, preserve exact subject count, relative positions, silhouettes, clothing colors, major props, background landmarks, lighting, palette, and camera angle. Only add text, channel branding, crop/contrast/readability adjustments, and small layout refinements. Example: if a cloak is red in the cover, it must stay red in the thumbnail.
- If the thumbnail changes character identity, clothing color, subject placement, or core background compared with the cover, reject it and regenerate before upload.
- For Japan/J-pop releases on `Tokyo Daydream Radio`, keep a consistent channel thumbnail system across Tokyo/city, forest/nature, and beach variants: large `J-POP` text with smaller `TOKYO DAYDREAM RADIO` directly beneath it. Use the same full-bleed layout as the approved channel examples, with either the Tokyo three-person back-view composition or the centered human-requested visual composition.
- For `Soft Hour Radio`, use thumbnail wording such as `DEEP SLEEP`, `CAFE PIANO`, `FOCUS MUSIC`, `RAINY NIGHT`, `STUDY BGM`, or `CALM READING`, with smaller `SOFT HOUR RADIO` branding.
- For `sundaze`, use thumbnail wording such as `POP HITS`, `SUMMER POP`, `NIGHT DRIVE`, `DANCE POP`, `FEEL GOOD POP`, or `HEARTBREAK POP`, with smaller `SUNDAZE` branding.
- For `Solwave Radio`, use thumbnail wording such as `LATIN POP`, `REGGAETON`, `VERANO LATINO`, `SPANISH POP`, `FIESTA LATINA`, or `NOCHE LATINA`, with smaller `SOLWAVE RADIO` branding.
- For `HaruHaru`, use thumbnail wording such as `K-POP`, `SEOUL POP`, `DANCE POP`, `HEARTBREAK`, `SUMMER KPOP`, `RAINY KPOP`, or `K-POP DRIVE`, with smaller `HARUHARU` branding.
- For `Storylight OST`, use thumbnail wording such as `GAME OST`, `ANIME BGM`, `ARCADE BGM`, `CUTE RPG`, `KAWAII GAME`, `PLAYFUL OST`, or `FANTASY GAME`, with smaller `STORYLIGHT OST` branding.
- For `Cinematic Pulse`, use thumbnail wording such as `EPIC BATTLE`, `FINAL BOSS`, `DARK FANTASY`, `HEROIC MUSIC`, `SCI-FI ACTION`, `TRAILER MUSIC`, or `BATTLE OST`, with smaller `CINEMATIC PULSE` branding.
- For `Club Bloom`, use style-specific thumbnail wording such as `DEEP HOUSE`, `TECH HOUSE`, `MELODIC TECHNO`, `TRANCE MIX`, `BASS HOUSE`, `FESTIVAL EDM`, `WORKOUT EDM`, `UK GARAGE`, `LIQUID DNB`, `TROPICAL HOUSE`, `AFRO HOUSE`, `SYNTHWAVE DRIVE`, or `CLUB MIX`, with smaller `CLUB BLOOM` branding.
- For `The Old Verse`, use thumbnail wording such as `GENESIS SONGS`, `OLD TESTAMENT`, `BIBLE MUSIC`, `PSALMS MUSIC`, `SCRIPTURE SONGS`, or `EXODUS MUSIC`, with smaller `THE OLD VERSE` branding.
- For `The New Verse`, use thumbnail wording such as `GOSPEL SONGS`, `NEW TESTAMENT`, `JESUS MUSIC`, `GRACE MUSIC`, `SCRIPTURE SONGS`, or `WORSHIP POP`, with smaller `THE NEW VERSE` branding.
- Do not add duration text or badges to thumbnails. Avoid `1 HOUR`, `60 MIN`, `1時間`, clocks, timers, and duration stickers.
- Keep the channel-brand line size/style consistent between the thumbnail and the cover channel label when possible.
- Use the cover or a separate first-frame image with only the lower-left channel brand label for Dreamina/Seedance video generation. Do not use the final text thumbnail as the first-frame reference; generated video often makes large thumbnail text flicker, disappear, or reappear.
- The large lower-left channel label is the only allowed baked-in moving-visual text unless the human explicitly asks for more. Do not add titles, lyrics, subtitles, UI, logos, duration badges, genre text, or unrelated words inside the moving visual.

Required moving visual:

- `--loop-video /absolute/path/to/dreamina-loop.mp4`: exactly 8 second Dreamina/Seedance visual clip for the rendered video.
- OpenClaw should generate/download only the short clip. Do not export a long MP4 from OpenClaw.
- The clip should be reusable for the full release: its final moment should stay close to the first-frame composition, camera distance, lighting, palette, and subject placement so the visual can cycle cleanly.
- Keep natural motion while returning close enough to the opening composition.
- Normal auto-publish must include `--loop-video`. Do not use the thumbnail image or any text-heavy image as the moving video visual. A still-image fallback is allowed only when the human explicitly requests it, and then OpenClaw must pass `--allow-still-image-video`.
- The app validates uploaded loop videos only for technical readability. It does not reject low-motion clips or alternate clip lengths. However, `scripts/openclaw-release` rejects short loop clips by default for normal OpenClaw upload/publish commands. If the normal OpenClaw automation accidentally generates Dreamina's 5 second default clip, regenerate it before upload unless the human explicitly asked to use the shorter clip and you pass `--allow-short-loop-video`.

Dreamina website workflow for OpenClaw:

- Use `https://dreamina.capcut.com/ai-tool/home/` for browser-based Dreamina/Seedance generation.
- Use Dreamina/Seedance `2.0 Fast`.
- Do not use Omni Reference.
- Use the first/last-frame workflow if the UI asks which mode to use, but provide only the first-frame image.
- Start from the cover image or a separate first-frame image that contains only the large lower-left selected-channel-name brand label. It should match the YouTube thumbnail scene and composition, including any explicit human visual request. It must not contain title text, genre text, duration text, or unrelated text.
- Leave the last-frame input empty. Do not upload a last-frame reference; it makes the generated motion too static.
- Set ratio to `16:9` when selectable.
- Set quality to `720p` when selectable.
- Set duration to `8 seconds` and re-check this visible control immediately before clicking Generate.
- Do not click Generate while the duration control still says `5 seconds`, while it is hidden, or while you are unsure. Do not create a 5 second draft/test clip first.
- Generate exactly one `8 second` MP4.
- Download the generated MP4 to the VM or OpenClaw workspace.
- Confirm the file exists locally before passing it to `--loop-video`.
- If login, CAPTCHA, subscription limits, or manual approval blocks generation/download, stop and report the blocked step. Do not continue without `--loop-video` unless the human explicitly accepts a still-image video and OpenClaw passes `--allow-still-image-video`.

Dreamina content/copyright rejection recovery:

- If Dreamina/Seedance rejects generation for inappropriate content, copyright, policy, moderation, or similar content-safety reasons, do not retry the exact same prompt.
- Retry up to 10 total Dreamina attempts for that loop video. Each failed attempt must send Slack progress before the next retry:
  `scripts/openclaw-release slack-notify --text "영상 만들기 실패해서 프롬프트를 수정해 다시 만듭니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`
- On each retry, make the prompt more original and generic while preserving the release mood, channel label, first-frame continuity, and requested motion direction.
- Remove or generalize anything that can look like protected IP or policy-risk text: named artists, studios, franchises, characters, brands, celebrity names, song titles, exact style imitation phrases such as `in the style of`, logos, weapons, gore, sexualized wording, minors, and real-person likeness references.
- Replace risky references with generic descriptors. Examples: `Ghibli-like` becomes `soft hand-painted anime-inspired background`; `Disney style` becomes `warm family-friendly illustrated animation`; `YOASOBI music video style` becomes `bright mainstream Japanese pop visual mood`; a named character becomes `original youthful traveler silhouette`.
- If the first-frame image itself appears to trigger rejection, regenerate a safer cover/first-frame image first, keeping only the large lower-left channel brand label and the same broad mood.
- If all 10 attempts fail, send a final Slack message:
  `scripts/openclaw-release slack-notify --text "영상 생성이 10회 실패해서 중단했습니다. RELEASE_TITLE: ERROR_SUMMARY"`
- After 10 failures, stop the automation before render/publish. Do not continue with a still-image video unless the human explicitly approves that fallback and OpenClaw passes `--allow-still-image-video`.

Dreamina/Seedance motion prompt guidance:

- Ask Dreamina for one continuous video shot whose final moment returns close to the first-frame composition. If the human requested a different motion/camera concept, ask for that requested continuous shot instead.
- Do not put duration, ratio, or quality in the prompt. Set those in Dreamina controls only.
- Do not include `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the prompt. These words can make Seedance/Dreamina create a shorter repeated segment inside the clip.
- Ask Dreamina/Seedance to preserve the first-frame image's composition, lighting, palette, illustrated/anime style, channel/requested subject/action, and large lower-left channel label in the first shot.
- Use the selected channel profile for subject/action/motion. Always require stable composition, no hard cuts, no other text overlays, no subtitles, no logos, no UI, and no photorealism.
- Ask Dreamina/Seedance to preserve the exact lower-left channel text, spelling, font/lettering, placement, color, and readability for the full clip. Ask it not to rewrite, translate, blur, morph, move, hide, flicker, or change the text. Keep the text area stable and animate only the surrounding scene subtly.
- After generation, inspect the downloaded MP4. Reject and regenerate if the large lower-left channel label is missing, unreadable, misspelled, flickering, morphing, moving drastically, shrinking, or changing style.
- Ask for the final moment to be close to the opening composition, but not perfectly identical or static.
- If the model outputs audio, ignore it; the app uses the rendered playlist audio.

Recommended Dreamina prompt shapes are in the selected channel profile returned by `scripts/openclaw-release channel-profile`.

Tokyo/J-pop Dreamina prompt shape:

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

Soft Hour/default BGM Dreamina prompt shape:

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

For any channel, include this in the Dreamina prompt: `The uploaded first frame contains the exact large, readable lower-left channel brand label "{CHANNEL_NAME}" (for example, "Tokyo Daydream Radio"). The label should match the visual scale of the YouTube thumbnail's channel-brand line, roughly 18-24% of image width or 5-6% of image height for text cap height. Preserve this text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, flicker, shrink, or change the text. Keep the text area stable; animate the surrounding scene naturally. No other text, subtitles, logos, UI, or title words.`

Thumbnail text rules for OpenClaw:

- Use 2-4 large words that describe the use case or mood, for example `CAFE PIANO`, `DEEP SLEEP`, `FOCUS MUSIC`, `RUNNING BEATS`.
- Prefer the approved full-bleed style: strong image background, no card or panel, large bottom-left genre/mood text, and a smaller channel-brand line directly below.
- For Tokyo Daydream Radio releases, use the channel name as the brand line. The approved mainstream J-pop pattern is large `J-POP` with `TOKYO DAYDREAM RADIO` beneath it. Keep this same two-line treatment for Tokyo/city, forest/nature, and beach versions to create channel consistency.
- Do not add support text or duration badges. The thumbnail should not say `1 HOUR`, `60 MIN`, `1時間`, or show a time badge.
- Keep text large enough to read on a phone.
- Avoid long titles, dense paragraphs, fake UI, and obviously AI-looking distorted text.
- Keep the main default/requested subject centered and visible even when thumbnail text is added.

Localized YouTube metadata rules for OpenClaw:

- The app can upload YouTube localized metadata for `ko`, `ja`, `en`, `es`, `vi`, `th`, `hi`, `fil`, `id`, `pt-BR`, `fr`, `de`, `ar`, `zh-CN`, and `zh-TW`.
- For `Tokyo Daydream Radio`, `HaruHaru`, `Storylight OST`, `Cinematic Pulse`, `Club Bloom`, `The Old Verse`, `The New Verse`, `sundaze`, `Solwave Radio`, mainstream J-pop/Japanese pop, K-pop/Korean pop, English pop, Latin/Spanish pop, playful Japanese game/anime OST BGM, cinematic orchestra/movie-OST/film-score BGM, no-vocal club music, scripture music, or similar pop-family/story-BGM releases, always write all fifteen language versions: Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese.
- Use Korean as the default upload metadata for Tokyo/Soft Hour/HaruHaru unless the channel profile says otherwise. Use `--default-language en` for `Storylight OST`, `Cinematic Pulse`, `Club Bloom`, `The Old Verse`, `The New Verse`, and `sundaze`; use `--default-language es` for `Solwave Radio`.
- Pass the default-language copy through `--title` and `--description-file`, and also pass the matching localized title/description pair.
- Pass Japanese through `--ja-title` and `--ja-description-file`. This should be natural Japanese copy, not a literal Korean line-by-line translation.
- Pass English through `--en-title` and `--en-description-file`. This should be natural English YouTube copy for international listeners.
- Pass Spanish through `--es-title` and `--es-description-file`. This should be natural Spanish YouTube copy for Spanish-speaking listeners.
- Pass Vietnamese through `--vi-title` and `--vi-description-file`.
- Pass Thai through `--th-title` and `--th-description-file`.
- Pass Hindi through `--hi-title` and `--hi-description-file`.
- Pass Filipino through `--fil-title` and `--fil-description-file`.
- Pass Indonesian through `--id-title` and `--id-description-file`.
- Pass Brazilian Portuguese through `--pt-title` and `--pt-description-file`; the app stores this as `pt-BR`.
- Pass French through `--fr-title` and `--fr-description-file`.
- Pass German through `--de-title` and `--de-description-file`.
- Pass Arabic through `--ar-title` and `--ar-description-file`.
- Pass Simplified Chinese through `--zh-title` and `--zh-description-file`; the app stores this as `zh-CN`.
- Pass Traditional Chinese for Taiwan through `--zh-tw-title` and `--zh-tw-description-file`; the app stores this as `zh-TW`.
- End every localized description with a public hashtag line. `--tags` is still required, but it only sends YouTube API tags and does not replace visible description hashtags.
- For Playlist Releases on every channel, start `--title`, `--ko-title`, `--ja-title`, `--en-title`, `--es-title`, `--vi-title`, `--th-title`, `--hi-title`, `--fil-title`, `--id-title`, `--pt-title`, `--fr-title`, `--de-title`, `--ar-title`, `--zh-title`, and `--zh-tw-title` exactly with `[playlist]`. Do not add this prefix to Single Releases.
- After `[playlist]`, do not repeat playlist nouns such as `플레이리스트`, `Playlist`, `プレイリスト`, or `lista de reproducción`; use music/mix/radio wording instead.
- For playlist/BGM titles, include a real listening situation or viewer intent in the title itself. The title should not be only mood plus genre, but the use case must match the actual music and concept. Do not default to study/work/walk/rest wording by habit.
- Use `walk` / `산책` only when walking, commuting on foot, street movement, beach/forest walks, crosswalks, or similar movement is genuinely central. For arcade, game-center, karaoke, friend-hangout, party, rooftop, club, dance-pop, bass-heavy, or workout-ready releases, prefer arcade, gaming, friends, night out, getting ready, workout, running, party warmup, driving, nightlife, confidence, or weekend energy.
- For Japan/J-pop/Tokyo Daydream Radio titles, do not over-emphasize the language. Prefer `J-POP`, the actual Japan scene, city-pop/mainstream pop substyle, mood, and listening use cases. Avoid Korean title phrases like `일본어 J-pop`, `일본어 보컬`, or `일본어 카페 재즈` unless the human explicitly asks to highlight the language. `Tokyo Daydream Radio` is the channel brand, not a required title keyword; use `Tokyo` only for genuinely Tokyo-specific concepts. If language matters, mention it naturally in the description instead; the thumbnail/channel branding can carry `J-POP`.
- In Korean title/description/localizations, do not use the transliterated words `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`. Use `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡`.
- Keep all localized titles under 100 characters. Keep timestamps identical across languages; translate only the displayed title text and surrounding description.
- For Japan/J-pop/Tokyo Daydream Radio timestamped tracklists, format localized rows by language: Korean/default uses Japanese title plus Korean translation in parentheses, Japanese uses Japanese title only, and every other localized description uses translated title text only.
- For sundaze/English pop metadata, keep every localized YouTube title exactly the same as the English title. In timestamped tracklists, keep the English song title after each timestamp in every localized description. Translate only the surrounding description prose, use-case line, and hashtags.
- If the release is 40+ minutes or longer, use `HH:MM:SS` for every timestamp in every localized description. Start with `00:00:00`, not `00:00`, and use `01:00:00+` after the one-hour point so YouTube can link those chapters reliably.
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

For automatic playlist publishing, `scripts/openclaw-release auto-publish-playlist` chooses the YouTube channel from the release concept when `--youtube-channel-title` is omitted.

- Use `Soft Hour Radio` for default background/cafe/sleep/study/chill playlists.
- Use `Tokyo Daydream Radio` for mainstream J-pop/Japanese pop, Tokyo/Japan pop, city pop, dance-pop, synth-pop, pop-rock, anime-pop, vaporwave, 도쿄, 시티팝, 제이팝, 東京, Jポップ, or シティポップ concepts.
- Use `sundaze` for English/American pop, US/UK pop, western pop, mainstream English vocal pop, dance-pop, synth-pop, pop-rock, or similar English pop concepts.
- Use `Solwave Radio` for Latin/Spanish pop, Spanish pop, urbano latino, reggaeton pop, bachata pop, salsa pop, cumbia pop, tropical dance-pop, verano latino, or similar Spanish vocal concepts.
- Use `HaruHaru` for K-pop, Korean pop, Korean dance-pop, Korean synth-pop, Korean pop-rock, Korean R&B pop, idol-pop inspired music, or similar Korean vocal concepts.
- Use `Storylight OST` for playful no-vocal Japanese-style game/anime OST, arcade-game BGM, fantasy-game BGM, cute RPG music, item-shop music, mini-game music, and light adventure instrumental concepts.
- Use `Cinematic Pulse` for no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, sci-fi, dark fantasy, heroic, and game-focus instrumental concepts.
- Use `Club Bloom` for no-vocal EDM/house/techno/trance/festival/workout/night-drive/gaming/club concepts.
- Use `The Old Verse` for Old Testament, Genesis, Exodus, Psalms, Bible verse music, scripture-inspired worship, or ancient biblical music concepts.
- Use `The New Verse` for New Testament, Gospel, Jesus words, grace music, scripture worship, Bible verse songs, or worship pop concepts.
- Pass `--youtube-channel-title` explicitly when the human names a target channel.
- Do not use `MusicSun` unless the human explicitly requests it. MusicSun is the only manual-only channel and must be excluded from continuous automatic rotation.
- For continuous automation, newly connected YouTube channels are active by default unless explicitly marked inactive/excluded in docs. MusicSun remains excluded by default. If the selected connected channel has no dedicated profile/concept docs yet, use the `custom-channel` docs returned by `scripts/openclaw-release channel-profile`.
- For `The Old Verse` and `The New Verse`, use `docs/openclaw-scripture-sequence.md` and `scripts/openclaw-scripture-sequence` to remember the last completed Bible passage, reserve the next passage before generation, and prevent duplicates.
- After publish, `/api/playlists/workspaces` exposes `youtube_video_id`, `youtube_channel_id`, `youtube_channel_title`, and when enabled `youtube_scheduled_publish_at`. OpenClaw can use those fields to confirm which channel received the upload and which daily 07:00 slot was assigned; web UI layout changes do not affect OpenClaw because it should use the helper script or local API, not click the dashboard.
- If `AIMP_YOUTUBE_SCHEDULE_PUBLIC_ENABLED=true`, the app uploads with YouTube `status.publishAt` for the next free daily 07:00 slot in `AIMP_YOUTUBE_SCHEDULE_TIMEZONE`. If that date already has a scheduled app upload, the app automatically uses the following day. OpenClaw should not manually change YouTube visibility in Studio.
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
- Upload all intended playlist tracks before starting audio render, video render, metadata approval, or YouTube publish. Reaching the target duration does not auto-start audio render anymore; OpenClaw must explicitly call the render step only after the upload set is complete. If late tracks are added after rendering starts, the app treats the existing render as stale and requires or queues a fresh render so the YouTube timeline cannot become longer than the actual video.
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
Create an original single release and publish it through the app.
Generate or obtain:
- one final Suno audio file per YouTube single
- a final clean 16:9 cover image
- a separate YouTube thumbnail image with readable text
- one exactly 8 second Dreamina/Seedance loop video

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

For non-Japan releases, use the selected channel profile. Korean/K-pop goes to "HaruHaru", playful no-vocal Japanese-style game/anime OST and arcade/fantasy-game BGM goes to "Storylight OST", no-vocal large-scale cinematic orchestra/movie-OST/film-score BGM goes to "Cinematic Pulse", no-vocal EDM/house/techno/trance club music goes to "Club Bloom", Old Testament scripture music goes to "The Old Verse", New Testament/Gospel/worship music goes to "The New Verse", English/American pop goes to "sundaze", Latin/Spanish pop goes to "Solwave Radio", and default BGM/background goes to "Soft Hour Radio" unless the human says otherwise.
Pass exactly one --audio/--title/--lyrics-file/--style per auto-publish-single run. If two Suno outputs are both good, create separate cover/thumbnail/loop-video assets and run auto-publish-single twice.
```

## Safety Rules

- Do not call `Approve Publish` automatically unless the human explicitly asks for full publishing.
- Do not upload videos directly through `youtube.com` or YouTube Studio. Use `scripts/openclaw-release auto-publish-single`, `scripts/openclaw-release auto-publish-playlist`, or the app's local `/approve-publish` API only. The app performs the real YouTube upload through the YouTube Data API.
- Do not use an existing `--release-id` that already has `youtube_video_id` for a normal new publish. Create a new release instead. `auto-publish-playlist` and `auto-publish-single` reject accidental re-uploads unless `--allow-reupload` is passed, and that flag should be used only when the human explicitly asks to upload the same release again.
- YouTube Studio is only for human final review after the API upload, such as watching the result, confirming the scheduled public time, reviewing automatic captions, or manual fixes.
- Do not try to turn on automatic captions through browser automation. The app does not upload caption tracks or toggle caption settings. For vocal releases, API upload can send the inferred `snippet.defaultAudioLanguage`; YouTube may generate automatic captions later. For BGM/instrumental/no-vocal releases, leave captions/audio language alone unless the human explicitly asks for manual captions.
- Do not open Suno or generate audio before creating/selecting the app release workspace. Fresh work starts with `scripts/openclaw-release create-release`; continuing work starts with `scripts/openclaw-release list-releases` and `--release-id`.
- Do not upload to YouTube automatically unless using `auto-publish-single` or `auto-publish-playlist` after explicit human instruction.
- If cover art is ready with the audio, upload it in the same command with `--cover`; otherwise omit `--cover` and let the human add/regenerate cover later.
- If lyrics, meaningful song-content notes, or an instrumental Suno metatag file are available, upload them in the same command with `--lyrics` or `--lyrics-file`. Use an empty value only when lyrics/content are truly unknown.
- For BGM/background/lofi/study/sleep/cafe singles and playlists, instrumental/no-vocal is the default, but an empty lyrics/custom-lyrics field is not preferred. Use `docs/suno-v55-instrumental-format.md`: enable Instrumental when available, write only bracketed metatag lines in Suno's lyrics/custom-lyrics field, and upload that exact file. For J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop singles and playlists, do not leave lyrics empty by default. Generate/capture original lyrics and upload them; only use empty lyrics when the human explicitly asked for instrumental/no-vocal music or when Suno did not provide lyrics and OpenClaw reports that limitation.
- For vocal pop uploads, lyrics should be standalone song lyrics, not literal descriptions of the YouTube playlist title, thumbnail text, visual scene, or listening use case. Match the melody, beat, tempo, energy, and vocal attitude to the playlist context, but write natural pop lyrics with their own emotion, story, and hook.
- For no-vocal Suno work, also fill Advanced Options excluded styles with vocal-related exclusions: `vocal, vocals, voice, voices, singing, singer, lead vocal, backing vocals, choir, choral, humming, hum, whisper, spoken word, speech, narration, rap, ad-libs, scat, vocal chops, ooh, aah, la la, lyrics, sung lyrics, topline`.
- Before pressing Create in Suno, remove producer tags and specific artist references from lyrics, bracketed metatags, style, prompt, tags, and excluded styles. If Suno rejects a word such as `lowlight` as a producer tag, rewrite it to a generic descriptor like `low-lit`, `dim`, `shadowy`, `muted night`, or `soft ambient`, then retry generation.
- After every audio upload, confirm that the returned `duration_seconds` is close to the actual song length. If it is `0`, much shorter than expected, or the upload fails as unreadable, fix the source file and re-upload before moving on.
- For playlist work, confirm every uploaded `duration_seconds` is at or below 240 unless the human explicitly approved a longer track.
- For 40+ minute playlist automation, if a few songs fail after the 3 upload attempts, do not abandon the rest of the batch. Let the helper upload the remaining songs, read the Slack warning, then re-upload only the failed files and rerun render/publish after the release has the full intended track set.
- If Suno style/settings are available, upload them in the same command with `--style`.
- Do not generate a batch by repeating one Suno prompt/style/lyric template. Each new Suno request should have a distinct prompt/style/lyrics plan while staying inside the requested release mood.
- Do not generate vocal songs by mechanically inserting the release title/use-case words into every verse or chorus. For example, a dance-practice, walking, driving, workout, study, or party playlist should get songs whose sound fits that context; the lyrics can be about love, confidence, heartbreak, freedom, youth, or another strong pop topic.
- Treat generated draft covers in the web UI as replaceable placeholders, not final art.
- Use OpenAI GPT Image models for static cover and thumbnail images. Do not use Dreamina for static image generation.
- Static cover and thumbnail images must follow the channel profile returned by `scripts/openclaw-release channel-profile`.
- In thumbnails, keep the main channel/requested subject centered; text must not push it sideways.
- Generate the thumbnail from the final cover as a reference/edit derivative. Preserve characters, positions, outfit colors, lighting, palette, background continuity, and the channel-brand line style; only add click text/branding and readability adjustments.
- Do not use generated draft covers for full OpenClaw auto-publish runs. OpenClaw must create/upload a real final cover image first.
- Do not publish without a separate YouTube thumbnail image. OpenClaw must create/upload a text thumbnail and pass it as `--thumbnail`.
- OpenClaw must create a Dreamina/Seedance clip and pass the 8 second MP4 as `--loop-video` before normal video render/publish. The generated clip should end close to its opening composition so it can be reused across the long video. If the human explicitly approves a still-image fallback, pass `--allow-still-image-video`; otherwise do not render/publish.
- Keep `--cover`, `--thumbnail`, and `--loop-video` separate. `--thumbnail` should have readable YouTube text plus channel branding. `--cover` and `--loop-video` must contain only the large lower-left channel label as baked-in text. Never feed the text thumbnail into Dreamina/Seedance as the first frame; use the cover or a dedicated first-frame image. If the human requested a specific video visual, that visual request must be reflected consistently across all three assets.
- Use Dreamina/Seedance `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, and exactly `8 seconds` through UI controls for loop video generation. Do not put those settings in the prompt.
- Dreamina/Seedance often defaults to `5 seconds`. For normal OpenClaw auto-publish work, before generating, confirm the duration UI still says `8 seconds`; do not generate a 5 second draft first. After download, verify the MP4 duration; if it is about 5 seconds because the UI stayed on the default, discard it and regenerate at 8 seconds. The app allows intentionally provided shorter clips, but `scripts/openclaw-release` requires `--allow-short-loop-video` for those cases, so do not rely on upload rejection to catch this mistake.
- For Playlist Releases, `upload-audio` auto-approves by default. Do not add `--pending-review` unless the human explicitly asks.
- For Playlist Releases, do not use pair/number titles. Replace Suno A/B or 1/2 output labels with independent track names before upload.
- For Suno two-output generations, upload both candidates to one Single Release using `upload-single-candidates`.
- Single Release candidates are still human-reviewed; the human may approve one candidate, approve both candidates as separate Single Releases, or reject both.
- If both candidates are rejected, the app will archive the release automatically; do not delete files or database rows manually.
- If three or more songs are ready for one release, use a Playlist Release instead.
