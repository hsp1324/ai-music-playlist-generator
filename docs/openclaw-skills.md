# OpenClaw Skills For AI Music Releases

Use this document as the instruction source when asking OpenClaw to create or run release-production skills for this repo.

OpenClaw must run commands from its repo checkout. In the current OpenClaw runtime this is normally:

```bash
cd ~/repos/ai-music-playlist-generator
```

If that path is missing, try `~/repos/ai리포` or the current checkout. Do not require `/opt/ai-music-playlist-generator`; that path is the deployed Oracle VM service path.

Use `scripts/openclaw-release` against the deployed AI Music app API. `AIMP_LOCAL_API_BASE` must point to the deployed VM app API or a tunnel to that API. Do not use OpenClaw's own local dev API; if `/youtube/status` returns `configured=false`, `authenticated=false`, `ready=false`, or `channels=[]`, stop before generation/publish because the API target is wrong.

Recommended API target:

- On the Oracle VM, use `AIMP_LOCAL_API_BASE=http://127.0.0.1:8000/api`.
- On a laptop/OpenClaw machine, use an SSH/Tailscale tunnel to the VM FastAPI process and point `AIMP_LOCAL_API_BASE` at the tunnel.
- The public `https://ai-music.168.107.34.175.sslip.io/api` URL is behind Google login. It requires `AIMP_API_COOKIE` from a logged-in browser session before `scripts/openclaw-release` can upload tracks, create releases, or publish.
- `AIMP_OPENCLAW_SHARED_TOKEN` only covers OpenClaw coordination endpoints such as lock/backlog when the backend is reachable. It is not a replacement for Google-login cookie or direct/tunneled backend access.

Never open `/youtube/status`, `/api/youtube/status`, `/youtube/connect`, `/api/youtube/connect`, Google OAuth, or YouTube Studio in a browser from an automation run. YouTube connection is a human setup task. Automation must only read status through CLI/API calls such as `scripts/openclaw-release youtube-status` or `curl -fsS "$AIMP_LOCAL_API_BASE/youtube/status"` and pass the selected connected channel title/id to the helper scripts.

## Continuous Next Release Planning

When the app asks OpenClaw to create the next release after an upload/scheduled publish completes, first use [openclaw-next-release-planner.md](openclaw-next-release-planner.md). That planner chooses the next channel, reads the selected channel's concept planner from [openclaw-channel-concepts](openclaw-channel-concepts/README.md), then hands off to this document's automatic playlist publisher.

## Channel-First Workflow

Before generating cover art, YouTube thumbnails, or Dreamina/Seedance/Gemini loop videos, OpenClaw must choose the target channel first and read that channel's profile.

```bash
scripts/openclaw-release channel-profile \
  --release-title "RELEASE_TITLE" \
  --description "RELEASE_CONCEPT" \
  --prompt "PROMPT_OR_STYLE" \
  --tags "comma,separated,tags"
```

If the human explicitly named a channel, pass it:

```bash
scripts/openclaw-release channel-profile \
  --release-title "RELEASE_TITLE" \
  --description "RELEASE_CONCEPT" \
  --youtube-channel-title "Soft Hour Radio"
```

Then read the returned `concept_doc` from [openclaw-channel-concepts](openclaw-channel-concepts/README.md) for concept planning and the returned `profile_doc` from [openclaw-channel-profiles](openclaw-channel-profiles/README.md) for cover, thumbnail, and loop-video rules. Do not mix concept or visual signatures across channels.

## Shared Rules

- Never approve, reject, render, publish, or upload to YouTube unless the human explicitly asks.
- Before opening Suno or generating audio, create or select the target app workspace/release. Use one Single Release workspace for one standalone song candidate set, and one Playlist Release workspace for one playlist/mix. Do not scatter one Suno request or one playlist run across multiple workspaces.
- If continuing existing work, run `scripts/openclaw-release list-releases` and use the existing `release.id` with `--release-id`. If starting fresh, first run `scripts/openclaw-release create-release` and keep the returned `release.id`; then generate Suno audio and upload everything into that same `release.id`.
- Do not wait until after Suno generation to create the app workspace. The release id should exist before the first Suno prompt is submitted so all later audio, lyrics, style, cover, thumbnail, and video assets have one clear destination.
- OpenClaw creates audio candidates and uploads them to the app review queue.
- Use Suno v5.5 for new audio generation whenever the Suno account exposes it. The app API default is already `V5_5`. Suno's public pricing page currently lists v5 and v5.5 in the same paid-plan advanced-model allowance with the same song/credit allowance, so do not fall back to v5 just to save credits. If the Suno UI or API ever shows v5.5 costing more credits than v5 for the same generation, stop before bulk generation and report the exact credit difference to the human.
- If cover art is ready with the audio, upload the cover in the same command with `--cover`.
- Human review happens in Slack or the web UI.
- Single Release means one final song, but it may contain up to two review candidates from Suno.
- If two Suno candidates from one prompt are both good, publish them as two separate Single Releases. Do not combine them into one song.
- Playlist Release normally means automatic app-managed YouTube publishing. If the human asks for a playlist production run, upload generated tracks as already approved, render everything, generate/approve metadata, and upload through the app to YouTube.
- When uploading audio, include lyrics or song-content notes with `--lyrics` or `--lyrics-file` whenever available. For instrumental work, save and upload the exact bracket-only Suno instrumental metatag file so later metadata/visual work can understand the track.
- BGM/background/lofi/study/sleep/cafe music defaults to instrumental/no vocals unless the human explicitly asks for vocals. For Soft Hour Radio or other instrumental BGM, follow [suno-v55-instrumental-format.md](suno-v55-instrumental-format.md) before pressing Create in Suno.
- If a Soft Hour Radio concept uses lofi / lo-fi, include lofi as an explicit genre in every track's Suno style/settings and in the public YouTube title, localized titles, and first description paragraph. Do not make lofi only an internal prompt texture while publishing generic BGM metadata.
- For Soft Hour Radio instrumental work, do not put plain prose in Suno's lyrics/custom-lyrics field. Every non-empty line in that field must start with `[` and end with `]`. Bare arrangement sentences can be interpreted as sung lyrics.
- For Soft Hour Radio instrumental work, open Suno Advanced Options and fill the excluded styles/negative style field with vocal-related exclusions: `vocal, vocals, voice, voices, singing, singer, lead vocal, backing vocals, choir, choral, humming, hum, whisper, spoken word, speech, narration, rap, ad-libs, scat, vocal chops, ooh, aah, la la, lyrics, sung lyrics, topline`.
- For lyric/vocal songs, open Suno Advanced Options and fill the excluded styles/negative style field with vocal clarity blockers so the lead voice does not sound like a distant live concert recording: `muddy vocals, muffled vocals, washed-out vocals, distant vocals, buried vocals, unclear lyrics, heavy reverb, excessive reverb, long reverb tail, large echo, echoey vocals, concert hall echo, arena reverb, stadium reverb, live concert vocals, crowd ambience, room boom`.
- For every Suno generation on every channel, add artificial noise blockers to Advanced Options excluded styles unless the human explicitly asks for vinyl/LP/noise texture: `white noise, static noise, vinyl crackle, record crackle, LP crackle, turntable noise, tape hiss, cassette hiss, analog hiss, noise floor, lo-fi noise, old record noise, dust noise, crackle, hiss`.
- Instrumental metatags must be concrete enough to steer Suno toward the intended arrangement. Include an instrumental guardrail, tempo/feel, instrument palette, section-by-section musical flow, dynamics, and transitions inside bracketed lines. Do not write singable lyric lines. Example shape:
  `[Instrumental only: no sung words, no humming, no spoken words]`
  `[Intro: 8 bars, felt piano motif alone, wide room, soft rain ambience]`
  `[Main Theme: brushed drums enter, upright bass plays long roots, nylon guitar answers the piano]`
  `[Development: warm Rhodes pad opens, piano melody becomes slightly brighter, percussion stays soft]`
  `[Instrumental Break: harp harmonics and soft cymbal swells, melody carried by piano and guitar]`
  `[Bridge: drums drop to rim clicks, bass holds long notes, strings widen gradually]`
  `[Final Theme: piano motif returns, guitar answers every 4 bars, gentle lift without a vocal hook]`
  `[Outro: piano motif returns with rain ambience]`
  `[End]`
- J-pop/K-pop/pop/Japanese pop/anime-pop/Latin pop/Spanish pop/English pop releases default to vocal songs with lyrics. Use Japanese lyrics for J-pop/Japanese pop/anime-pop, Korean lyrics for K-pop, Spanish lyrics for Solwave Radio/Latin/Spanish pop, and English lyrics for sundaze/English/American pop. Do not make these instrumental, no-vocal, lyricless, or hum-only unless the human explicitly asks for instrumental/BGM/lofi/no vocals. For every pop-family track, create or capture the final lyrics and upload them with `--lyrics` or `--lyrics-file`. The helper rejects pop-family uploads with empty lyrics before publish unless the concept explicitly says BGM/instrumental/no-vocal.
- For every vocal Suno generation, decide the intended lead vocal gender before pressing Create. In Suno `More options` / `Vocal gender`, select `male` when the song should have a male lead vocal and select `female` when it should have a female lead vocal. If the song is mixed-gender, duet, group/choir, alternating male/female, or the lead gender is intentionally unspecified, leave Vocal gender unselected. Do not change this setting between retries for the same track unless you intentionally change the vocal concept; otherwise Suno may swap vocal timbre mid-song or across variants.
- When uploading audio, include the Suno style/settings with `--style` and Suno excluded styles/negative tags with `--exclude-style` whenever available. These are stored with the track for future cover, thumbnail, loop-video, metadata, and remake work.
- Within one release, intentionally vary every generated track. Do not reuse the exact same Suno prompt, lyrics theme, chorus hook, title pattern, or style string across multiple tracks unless the human explicitly asks for a uniform album. Keep the release coherent by genre/mood, but vary tempo, energy, instruments, rhythm feel, vocal tone, season/time/place imagery, lyrical story, and hook.
- For every channel, YouTube titles are public packaging and discovery copy. Make titles broad, searchable, and easy for normal viewers to understand: genre/channel identity plus a real listening reason such as workout, running, getting ready, party warmup, drive, study, sleep, reading, focus, gaming, battle, fantasy writing, heartbreak, confidence, or feel-good energy. Do not lead with narrow visual-scene names, props, exact locations, or workspace concepts unless that niche phrase is already broadly searchable.
- HaruHaru, sundaze, and Solwave Radio must choose one explicit genre lane per release and keep the whole playlist inside it. Name that lane naturally in the YouTube title, description, Suno style prompts, thumbnail text when useful, and localized titles. Use lanes such as K-pop hip-hop, Korean R&B, K-pop dance-pop, synth-pop, pop-rock, soul/neo-soul, Pop R&B, pop hip-hop, dance-pop, English synth-pop, Pop Latino, reggaeton pop, urbano latino, bachata pop, salsa pop, cumbia pop, Latin R&B, or Latin soul. Do not make vague mixed-pop samplers unless the human explicitly asks.
- For every vocal channel, separate the playlist packaging from the song lyrics. The YouTube playlist title/use case can be `dance practice room`, `night walk`, `drive`, `study`, `getting ready`, `workout`, `beach`, or similar, but the lyrics should not literally explain that setting unless it naturally makes a good song. Match the melody, beat, tempo, energy, and vocal attitude to the playlist use case; write lyrics as standalone original songs that real listeners would enjoy even outside the playlist context.
- Song quality is the first priority for every vocal track. The lyrics must fit the song's melody, beat, structure, vocal tone, hook, and emotional arc before they fit the release title, thumbnail, visual scene, or workspace name. It is acceptable, and often preferred, for a song lyric to be unrelated to the playlist title if the song itself is stronger.
- Do not force keywords from the YouTube title, thumbnail text, workspace name, or visual scene into every lyric. Avoid cringe or over-literal lines such as singing directly about practicing dance, using the playlist, studying, walking, driving, or the channel concept. Use natural pop songwriting: believable emotion, relationship tension, confidence, longing, release, youth, nightlife, summer, heartbreak, or personal story, with a strong chorus hook.
- Lyrics must fit the song's own style and vocal delivery first. A dance/workout playlist can contain love, confidence, breakup, or night-out lyrics if the beat and energy fit; a walking/drive playlist can contain any good pop song that feels right while walking or driving. The playlist situation is a listening context, not a required lyric topic.
- Before pressing Create in Suno, sanitize lyrics, bracketed instrumental metatags, style strings, prompts, titles, tags, and excluded styles for producer tags or specific artist references. Do not include producer names, artist names, label names, artist-like aliases, `type beat` credit text, or exact imitation phrases.
- Known Suno failure: `Your lyrics contain producer tag lowlight - we don't reference specific artists on Suno, please change your lyrics and try again.` If this or a similar blocked-term error appears, replace the flagged term with generic descriptive language such as `low-lit`, `dim`, `shadowy`, `muted night`, or `soft ambient`, then retry the Suno generation with the sanitized lyrics/style/prompt.
- For playlist releases, prefer one `--style` per `--audio` and one `--lyrics-file` per vocal track. Shared style is allowed only for a narrow BGM/instrumental set where the human wants consistency; even then, vary titles and prompts.
- Do not put duration caps such as `less than 4 minutes` or `under 4 minutes` into Suno prompts, style strings, lyrics, or bracketed metatags unless the human explicitly asks for that cap. Those caps can cause Suno to end too early. Prompt for a complete song/cue instead: natural intro, developed verse/section flow, chorus or central motif where appropriate, bridge/breakdown when useful, and a resolved ending. The helper rejects playlist tracks shorter than 2:00 by default and allows tracks up to 4:20 by default for most channels. `Soft Hour Radio` and `Cinematic Pulse` are exempt from the max-track rule: do not force those tracks under 4 minutes, and do not reject complete longer tracks just because of duration.
- For J-pop/K-pop/English pop/Latin pop/Spanish pop vocal tracks, keep the style and lyric plan natural to the genre, with distinct hooks and stories per track. The lyric plan should be a real song concept, not a literal description of the playlist title or visual scene.
- For J-pop/K-pop/English pop/Latin pop/Spanish pop playlists, each song needs its own original lyrics and chorus concept. Do not create multiple songs with near-identical verse/pre-chorus/chorus wording, repeated phrases, or only swapped nouns.
- Always return the final JSON result and mention `release.id` plus uploaded `track.id` values.
- If a command fails, stop and report the exact error. Do not retry blindly more than once.
- For YouTube title/description/tag writing, use [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).
- Every YouTube description, including `ko`, `ja`, `en`, `es`, `vi`, `th`, `hi`, `fil`, `id`, `tr`, `pt-BR`, `pt-PT`, `fr`, `de`, `ar`, `zh-CN`, and `zh-TW` localized descriptions, must end with a visible public hashtag line. The `--tags` option is separate API metadata and does not create visible hashtags in the description.
- For playlist publishing, choose the YouTube channel by release concept:
- Default background/cafe/sleep/study/chill playlists go to `Soft Hour Radio`.
- Mainstream J-pop/Japanese pop releases go to `Tokyo Daydream Radio`. Treat these as Tokyo Daydream candidates when the title, prompt, tags, or concept includes Tokyo, Shibuya, Shinjuku, J-pop, Japanese pop, city pop, Japanese dance-pop, Japanese synth-pop, Japanese pop-rock, anime-pop, vaporwave, 도쿄, 시티팝, 제이팝, 東京, 渋谷, 新宿, Jポップ, or シティポップ. Anime/OST-like music is allowed inside the channel, but the channel is broader mainstream J-pop/pop, not anime OST-only.
- English-language pop, American pop, US/UK pop, western pop, mainstream English vocal pop, dance-pop, synth-pop, pop-rock, or similar English pop releases go to `sundaze`. Treat this as the English/US-pop counterpart to Tokyo Daydream Radio.
- Latin/Spanish-language pop, Latin pop, Spanish pop, urbano latino, reggaeton pop, bachata pop, salsa pop, cumbia pop, tropical dance-pop, verano latino, or similar Spanish vocal releases go to `Solwave Radio`. Treat this as the Spanish/Latin counterpart to Tokyo Daydream Radio.
- Korean-language pop, K-pop, Korean dance-pop, Korean synth-pop, Korean pop-rock, Korean R&B pop, idol-pop inspired music, or similar Korean vocal releases go to `HaruHaru`. Music defaults to original Korean lyrics.
- Playful no-vocal Japanese-style game/anime OST, arcade game BGM, fantasy game BGM, cute RPG music, anime side-story BGM, item-shop music, mini-game music, or light adventure instrumental BGM goes to `Storylight OST`.
- No-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, sci-fi, dark fantasy, heroic, or game-focus instrumental music goes to `Cinematic Pulse`.
- No-vocal EDM, house, techno, trance, festival, workout, night-drive, gaming, club, or party-energy releases go to `Club Bloom`. Club Bloom must choose one club style lane per playlist and stay inside it.
- Old Testament, New Testament, Genesis, Matthew, Gospel, Jesus words, Psalms, Proverbs, Bible verse music, scripture-inspired worship, grace music, or ancient biblical music goes to `BibliaCanto`. It is a vocal/lyrics channel by default; make original English lyric songs unless the human explicitly asks for instrumental/BGM or a different lyric language.
- `불송` YouTube channel is now for Buddhist scripture-inspired modern vocal music: Dhammapada/법구경-inspired songs, Heart Sutra/반야심경-inspired songs, Buddhist jazz, Buddhist hip-hop, Buddhist R&B/soul, dharma songs, mindfulness songs, and modern sutra-inspired music. Use Korean lyrics by default unless the human asks otherwise. Do not route Bible/Gospel/New Testament worship there.
- Retired Signal Room/Signal Desk/Midnight Cue research/debate concepts should not be selected for new automation unless the human explicitly asks to revive a research/debate BGM channel.
- If the human explicitly names a target channel, that explicit channel overrides automatic channel inference and also controls the visual skill. Example: `Soft Hour Radio에 올려줘` means use the Soft Hour channel profile even if the music has light Japan/city-pop influence.
- Do not use `MusicSun` unless the human explicitly requests it. MusicSun is manual-only and excluded from continuous automatic rotation.
- For continuous next-release automation, newly connected YouTube channels are active by default unless these docs explicitly mark them inactive/excluded. MusicSun remains excluded by default. If a selected connected channel has no dedicated profile/concept docs yet, `scripts/openclaw-release channel-profile` returns the `custom-channel` docs; read those and infer the channel identity from the channel title, local release history, and human instructions.
- For scripture releases, read [openclaw-scripture-sequence.md](openclaw-scripture-sequence.md), create the release with upload channel `BibliaCanto`, reserve the next app-owned canonical passage with `scripts/openclaw-release openclaw-scripture-reserve` before Suno generation, include the returned `entry.passage_range` in the main and localized YouTube titles, and mark it scheduled/published with `scripts/openclaw-release openclaw-scripture-complete` after successful upload/scheduling. Reserve Old Testament with `--channel-title "BibliaCanto"` and New Testament with `--channel-title "New Testament"`, but publish both branches with `--youtube-channel-title "BibliaCanto"`. Do not compare against a local scripture ledger, and never duplicate or skip a passage unless the human explicitly says so and the app ledger is updated accordingly.
- In continuous lookahead automation, do not use `auto-publish-playlist` for new playlist production. Use the step commands below so external video rendering can run in parallel with OpenClaw preparing the next release.
- YouTube visibility is app-managed. With `AIMP_YOUTUBE_SCHEDULE_PUBLIC_ENABLED=true`, the app uploads as a scheduled public release at the next free slot for the selected YouTube channel; schedules on other channels do not block that channel. Scripture releases on `BibliaCanto` have two daily slots in the schedule timezone: Old Testament at 07:00 and New Testament at 16:00. Otherwise it falls back to `AIMP_YOUTUBE_PRIVACY_STATUS`. Do not manually change visibility from OpenClaw.
- For `불송` Buddhist releases, publish through the app normally. The app schedules them public daily at 07:00 Asia/Seoul.
- Do not upload videos directly through `youtube.com` or YouTube Studio. Use `scripts/openclaw-release publish-release` or the app's local `/approve-publish` API for playlist finish passes. Use `scripts/openclaw-release auto-publish-single` only for explicit single-release automation. The app uploads through the YouTube Data API and stores the resulting `youtube_video_id`/channel metadata.
- Do not run `auto-publish-playlist` or `auto-publish-single` against a release that already has `youtube_video_id` unless the human explicitly asks for a re-upload. Create a fresh release for a new video. The helper rejects accidental re-uploads unless `--allow-reupload` is passed.
- YouTube Studio is only for human final checks after the API upload, such as watching the scheduled/private video, confirming the scheduled public time, reviewing app-uploaded CC captions, or manual cleanup.
- Do not try to enable captions through browser automation. For vocal releases with saved lyrics, the app uploads YouTube CC caption tracks through the API at publish time using faster-whisper line timing and Codex translations. For BGM/instrumental/no-vocal releases, do not set captions or audio language unless the human explicitly requests manual captions.
- YouTube metadata supports localized title/description for `ko`, `ja`, `en`, `es`, `vi`, `th`, `hi`, `fil`, `id`, `tr`, `pt-BR`, `pt-PT`, `fr`, `de`, `ar`, `zh-CN`, and `zh-TW`. For `Tokyo Daydream Radio`, `HaruHaru`, `Storylight OST`, `Cinematic Pulse`, `Club Bloom`, `BibliaCanto`, `불송`, `sundaze`, `Solwave Radio`, or any pop-family/story-BGM/scripture-music release, OpenClaw must write every configured version. Use Korean as the default for Tokyo/Soft Hour/HaruHaru and Buddhist `불송` unless the channel profile says otherwise. Use `--default-language en` for `sundaze`, `Storylight OST`, `Cinematic Pulse`, `Club Bloom`, and `BibliaCanto`; use `--default-language es` for `Solwave Radio`. Always pass `--ko-title`, `--ko-description-file`, `--ja-title`, `--ja-description-file`, `--en-title`, `--en-description-file`, `--es-title`, `--es-description-file`, `--vi-title`, `--vi-description-file`, `--th-title`, `--th-description-file`, `--hi-title`, `--hi-description-file`, `--fil-title`, `--fil-description-file`, `--id-title`, `--id-description-file`, `--tr-title`, `--tr-description-file`, `--pt-title`, `--pt-description-file`, `--pt-pt-title`, `--pt-pt-description-file`, `--fr-title`, `--fr-description-file`, `--de-title`, `--de-description-file`, `--ar-title`, `--ar-description-file`, `--zh-title`, `--zh-description-file`, `--zh-tw-title`, and `--zh-tw-description-file` to `scripts/openclaw-release approve-metadata`. YouTube does not expose a separate `ar-EG` localization code; use `ar` for Arabic and make it natural for Arabic/Egyptian audiences.
- Treat localized titles as transcreation, not literal translation. In every language, the video title should sound natural and clickable for that audience. If a direct translation becomes awkward, weak, too long, or less clickable, change the wording, order, or exact hook while keeping the release identity, genre/lane, and use case truthful.
- For Playlist Releases on every channel, start the main YouTube title and every localized title exactly with `[playlist]`. Do not add this prefix to Single Releases.
- After `[playlist]`, do not repeat playlist nouns such as `플레이리스트`, `Playlist`, `プレイリスト`, or `lista de reproducción`; use music/mix/radio wording instead.
- Playlist/BGM YouTube titles must include a real listening situation or viewer intent in the title itself. Do not write only a mood/genre title, but also do not reuse the same SEO use cases by habit.
- Across all channels, title the release for a broad audience first. Use the cover/video scene as atmosphere, not as the main title hook, unless it is truly the strongest mainstream search phrase. Prefer `신나는 K-POP 믹스 | 운동, 러닝, 외출 준비, 파티 웜업` over a narrow scene-led title like `비 갠 옥상 위로 K-POP 믹스`.
- Listening use cases must fit the actual rendered music, channel concept, and visual setting. Do not force generic focus/study/work/walk wording just because it is common SEO text.
- Use `walk` / `산책` only when walking, commuting on foot, street movement, beach/forest walks, crosswalks, or similar movement is genuinely central to the concept. For arcade, game-center, karaoke, friend-hangout, party, rooftop, club, dance-pop, bass-heavy, or workout-ready releases, prefer use cases such as arcade, gaming, friends, night out, getting ready, workout, running, party warmup, driving, nightlife, confidence, or weekend energy.
- For Japan/J-pop/Tokyo Daydream Radio titles, do not over-emphasize the language. Prefer `J-POP`, the actual Japan scene, city-pop/mainstream pop substyle, mood, and listening use cases. Avoid Korean title phrases like `일본어 J-pop`, `일본어 보컬`, or `일본어 카페 재즈` unless the human explicitly asks to highlight the language. If language matters, mention it naturally in the description instead; the thumbnail text can carry `J-POP`.
- `Tokyo Daydream Radio` is the channel brand, not a required title keyword. Do not put `Tokyo` / `도쿄` in every title. Use it only when the concept is specifically Tokyo, Shibuya, Shinjuku, Tokyo commute, Tokyo skyline, or another clearly Tokyo-coded scene. Otherwise use the real concept wording, such as arcade night, seaside train, summer coast, Kyoto evening, Osaka weekend, school-after-hours, karaoke, festival night, or bright J-pop.
- For `HaruHaru`, `Storylight OST`, `Cinematic Pulse`, `Club Bloom`, `BibliaCanto`, `불송`, `sundaze`, and `Solwave Radio`, YouTube titles should feel like curated editorial or `Essential` playlist titles, not raw workspace names. Use a vivid situation/emotion plus channel genre identity plus listening use case. Avoid short generic labels like `KPOP`, `Korean Pop`, `Fantasy OST`, `Battle Music`, `EDM`, `Bible Music`, `Worship Music`, `Buddhist Music`, `Golden Hour Drive Pop`, `Ruta Dorada Pop`, `English Pop`, `Spanish Pop`, or `Latin Pop` by themselves.
- `sundaze` title example: `[playlist] Sunset Highway Pop Drive | Windows Down Road Trip Music`.
- `Solwave Radio` title example: `[playlist] Pop Latino para Ruta al Atardecer | Carretera, Verano y Buenas Vibras`.
- `HaruHaru` title example: `[playlist] 신나는 K-POP 믹스 | 운동, 러닝, 외출 준비, 파티 웜업`.
- `Storylight OST` title examples: `[playlist] Cute Arcade Game OST | Playful Japanese BGM for Gaming and Focus`, `[playlist] Fantasy RPG Town Music | Light Anime Game BGM for Reading and Play`.
- `Cinematic Pulse` title style references, not fixed templates: `[playlist] Final Battle Scene Cinematic Music | Dark Fantasy Orchestra`, `[playlist] Epic Dark Fantasy Orchestra | Cinematic Film Score for Epic Scenes`, `[playlist] Cinematic Orchestra Music | Movie OST for Focus and Epic Scenes`, `[playlist] Emotional Film Score | Piano, Strings and Hopeful Cinematic Music`, `[playlist] Sci-Fi Action Trailer Music | Cyber Chase, Combat and Workout Energy`, `[playlist] Dark Mystery Orchestra | Tension Music for Writing and Focus`.
- For `Cinematic Pulse`, avoid juvenile game-menu title wording such as `Boss BGM`, `Final Boss Music`, `Final Boss Focus Music`, `보스`, `보스전`, or bare `BGM`. The channel should feel grand, solemn, filmic, and broadly searchable; rotate among cinematic orchestra and film-score lanes such as final battle, dark fantasy, heroic trailer, emotional score, sci-fi action, mystery tension, grand journey, orchestral battle, writing music, and movie OST focus. Repeating a strong channel-fit title shape is better than forcing novelty that weakens the channel, but do not repeatedly copy only the listed examples.
- For `Club Bloom`, the title must make the genre or subgenre obvious immediately after `[playlist]`, using mainstream mix language such as `Progressive Trance x EDM Mix`, `Tech House Workout Mix`, `Hype Trap x EDM Mix`, `Melodic Techno Night Drive`, `Bass House Club Mix`, or `Festival EDM Mix`. Put one or two public listening hooks after the separator, such as night drive, gaming, workout, running, club, festival, or party warmup. Do not write awkward use-case strings like `[playlist] Progressive Trance for Night Roads, Gaming Focus and Club Drive`; the genre/mix identity should be clearer than the situation list. Strong examples: `[playlist] Progressive Trance x EDM Mix | Night Drive & Gaming Club Music`, `[playlist] Hype Trap x EDM Mix | Workout, Gaming and Club Energy`, `[playlist] Tech House Workout Mix | Running Beats and Club Bass`, `[playlist] Melodic Techno Night Drive | Dark Club Mix for Gaming`.
- For scripture releases on `BibliaCanto`, rotate the release-level music lane across uploads instead of defaulting to generic holy worship every time. Pick one lane before Suno generation, keep the entire release in that lane, and name the lane naturally in the title/description: scripture jazz, gospel R&B/soul, acoustic scripture folk/gospel, modern worship pop, piano worship ballads, choir-backed worship/gospel, cinematic scripture/Gospel worship, or neo-soul prayer songs. If the title says jazz, every track should be jazz-based; if it says R&B, every track should be R&B/soul-based. The app adds each uploaded scripture video to an Old/New Testament playlist and to one style playlist when the lane is clear.
- `BibliaCanto` title examples: `[playlist] Genesis Scripture Jazz | Old Testament Music for Worship and Reflection`, `[playlist] Abraham Covenant R&B Songs | Bible Music for Prayer, Hope and Waiting`.
- `불송` title examples: `[playlist] 마음을 다스리는 불경 힙합 | 법구경에서 영감을 받은 한국어 랩`, `[playlist] 반야심경 R&B | 집착을 내려놓는 불교 노래`, `[playlist] Buddhist Jazz for Letting Go | Dhammapada-Inspired Songs`.
- In Korean YouTube titles/descriptions/localizations, do not use the transliterated words `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`. Prefer `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡`.
- In Japan/J-pop localized descriptions, timestamped tracklists must use Japanese titles in the Korean/default description with Korean translations in parentheses, Japanese titles only in the Japanese description, and translated song titles in every other localized description. Keep the same timestamps and order in all languages.
- In `sundaze` English/American pop metadata, localized video titles may be natural adaptations in each language instead of exact English copies. In localized descriptions, timestamped tracklists should keep the English song/track titles in every language. Translate the intro, recommended-for line, and hashtags, but do not translate the song names after each timestamp.
- Use the release's base-block `rendered_timeline` for the tracklist. If the optional final-repeat feature is enabled later, do not add repeated second/third-pass timestamps. If the base timeline itself reaches 60 minutes or longer, use `HH:MM:SS` timestamps for the whole tracklist, starting at `00:00:00`.
- After audio render, metadata timestamps come from the release's saved `rendered_timeline` snapshot, which uses actual ffprobe source-file durations. Always call `scripts/openclaw-release metadata-context` after render and use its returned timeline; do not manually add rounded track durations.
- If a playlist contains consecutive Suno pair outputs that may feel repetitive, use randomized render order before audio render. In the API this is `random: true`; in `scripts/openclaw-release render-audio` this is `--randomize-order`. The app saves the shuffled order before rendering, so final order and metadata timestamps remain consistent.
- Do not leave trailing `A` / `B`, `1` / `2`, `Morning` / `Evening`, or similar pair labels in uploaded playlist track titles.
- Treat every playlist track as its own song title. If Suno returns two outputs from one prompt, rename both as independent editorial titles, not as variants of the same title.
- Full playlist publishing needs two 16:9 images:
- `cover`: video visual shown during playback and used as the Dreamina/Seedance/Gemini first-frame reference. It should look good for the full video duration and must not include a channel name or logo. If visual text is useful, use a short style, genre, use-case, or passage phrase.
- `thumbnail`: YouTube click thumbnail. It should include short readable text such as `CAFE PIANO`, `DEEP SLEEP`, `FOCUS MUSIC`, `TOKYO NIGHT`, `CITY POP`, or `J-POP`. Do not add the channel name or duration text such as `1 HOUR`, `60 MIN`, `1時間`, or time badges.
- Text should be plain integrated typography, not a UI button. Do not place text inside a rounded pill, capsule, badge, sticker, label tag, or detached floating plaque unless the human explicitly requests that treatment.
- Keep every text block comfortably inside safe margins. Reject/regenerate cover or thumbnail assets where text is clipped, crowded against an edge, cramped inside a shape, visually detached from the layout, pasted over the art, or overlapping the main subject.
- For cover, thumbnail, and loop-video visual creation, follow [openclaw-visual-assets.md](openclaw-visual-assets.md).
- Channel-specific concept selection rules are split into [openclaw-channel-concepts](openclaw-channel-concepts/README.md), and channel-specific cover, thumbnail, and loop-video rules are split into [openclaw-channel-profiles](openclaw-channel-profiles/README.md). Use `scripts/openclaw-release channel-profile` first, then read the returned `concept_doc` for planning and `profile_doc` for visual execution.
- For title, thumbnail text, and music-direction strategy, also read [openclaw-channel-market-analysis.md](openclaw-channel-market-analysis.md). Use the prewritten channel section there; do not perform live YouTube competitor research during normal release automation unless the human explicitly asks.
- Asset generation order is mandatory: create the final cover/first-frame first without channel names, then create the YouTube thumbnail as an image-to-image edit/reference derivative of that exact final cover. Do not create the thumbnail as a fresh unrelated image.
- When generating the thumbnail from the cover reference, preserve the exact requested subject, relative positions, silhouettes, clothing colors, major props, background landmarks, lighting, palette, and camera angle. Only add click text, crop/contrast/readability adjustments, and small layout refinements. Example: if the right subject has a red cloak in the cover, the thumbnail must keep that cloak red.
- If the generated thumbnail changes character identity, clothing color, subject count, subject placement, or core background compared with the cover, reject it and regenerate before uploading.
- Preferred thumbnail format: full-bleed image background, no card or panel, and large genre/mood text in safe negative space. For Japan/J-pop releases, use natural J-pop lane text such as `J-POP`, `CITY POP`, or `ANIME POP`; do not add the channel name.
- Channel visual signatures are separate:
- Tokyo Daydream Radio/Japan/J-pop uses exactly three people walking toward the viewer by default. The camera/viewer sees the people from the front, preferably medium-wide or full-body rather than close-up faces. For loop video, the camera should move backward at the same speed as the people so the subjects stay the same size; use side/background parallax and environmental motion for the loop instead of zooming into the people.
- Soft Hour Radio/default BGM uses its own channel profile: calm, restrained, long-listening visuals without a fixed recurring mascot, character count, scene list, or camera composition.
- HaruHaru, Storylight OST, Cinematic Pulse, Club Bloom, BibliaCanto, 불송, sundaze, and Solwave Radio do not have fixed visual signatures yet. Use the selected channel profile and let the playlist concept drive the cover, thumbnail, and short loop video. For photorealistic HaruHaru adult-woman clips, keep the subject the same size/crop for the full clip; if she moves, the camera tracks with her at the same speed/distance and the loop motion comes from background parallax/environment, not zoom, push-in, pull-back, lens breathing, or subject scale changes. Cinematic Pulse uses photorealistic cinematic first-frame art and now also uses a subtle provider loop video by default.
- For `Club Bloom`, do not accept calm, polite, low-energy, wallpaper-like, empty-venue, or generic abstract neon visuals. Unless the human asks otherwise, the cover, thumbnail, and short loop video should look like an active DJ/performance moment in a premium dance venue: beach-club deck, rooftop skyline DJ set, packed nightclub booth, concert/festival stage, warehouse rave, pool-party deck, open-air stage, yacht/harbor party, neon city terrace, or cyber club. Use strong neon/stage contrast and visible rhythmic motion.
- For `BibliaCanto`, do not make the thumbnail only a broad label such as `GOSPEL SONGS`, `BIBLE MUSIC`, or `SCRIPTURE SONGS` when the release has a known passage. Include a short passage/book/theme/prayer-worship cue when it improves clarity, while keeping the wording natural and not overfitted to one repeated template. For `불송`, the cover, YouTube thumbnail, first-frame, and loop video should use one clean image package with a short Korean passage/theme + style phrase such as `팔정도 명상팝` or `자비 트립합`; never add the `불송` channel name. 불송 is photorealistic/premium cinematic-real by default, but occasional cute/gentle animation is allowed when the music lane also fits that softer visual.
- Explicit channel requests override genre-based visual routing. If the requested channel is `Soft Hour Radio`, use the Soft Hour profile returned by `scripts/openclaw-release channel-profile`.
- Human visual requests override the selected channel visual skill. If the human asks for a specific scene, subject, action, camera angle, object, animal, character type, or video concept, use that request consistently for the cover, thumbnail, and loop video.
- When a channel/default signature is used, the main subject must stay centered in thumbnails. Text must not push it to the side, crop it, cover it, or make it feel secondary. Place text in safe negative space, usually lower-left or lower area.
- When a human visual request overrides the default, keep the requested subject/action/composition centered and visually important in thumbnails; text must fit around the requested composition rather than replacing it.
- The background should come from the selected channel profile and the release concept, not from a hard-coded scene list.
- All static images and Dreamina/Seedance/Gemini loop clips must look animated, anime, illustrated, or stylized unless the selected channel profile says otherwise. Cinematic Pulse and 불송 are explicit photorealistic/premium cinematic-real exceptions; 불송 also allows occasional cute/gentle animation when the release music lane fits it. Cinematic Pulse should use restrained photorealistic cinematic motion in the provider loop video rather than animated/anime styling.
- Generate static images with OpenAI GPT Image models, not Dreamina. Prefer `gpt-image-2` when available; otherwise use the currently available GPT Image model in the OpenAI/Image tool environment. Do not use Dreamina for static image generation. Do not assume the OpenAI API is free; use the available Codex/ChatGPT image tool if that is the operator-approved path, or use API billing/credentials when explicitly configured.
- Use Gemini first for the moving visual clip, then fall back to Dreamina/Seedance when Gemini is unavailable, blocked after retries, or on cooldown. If Dreamina/Seedance cannot create the video, go back to Gemini when Gemini quota is available. If Gemini has already spent all 3 successful videos in the current 24 hour window, defer that release's loop-video work until the Gemini cooldown clears; do not render/publish with a missing loop video. For normal publish automation, OpenClaw must generate one short MP4 and pass it with `--loop-video` plus `--loop-video-provider gemini|dreamina|seedance` so the app records where it came from. For Gemini, do not ask for a duration; upload the generated MP4 as-is after inspection with `--loop-video-provider gemini`. For Dreamina/Seedance, set the UI duration parameter to the channel's required duration, normally exactly `7 seconds` and `6 seconds` for `불송`, then upload with `--loop-video-provider dreamina` or `--loop-video-provider seedance`. Gemini is allowed through the human's quota for up to 3 successful video generations in a 24 hour window. The app rejects video render without an uploaded loop video unless the human explicitly approves the `--allow-still-image-video` fallback. The clip should end close to its opening composition so it can be reused across the full release. OpenClaw should not render a long MP4 itself.
- Existing releases that already have loop videos remain valid and should not be regenerated only because the default changed. For all new OpenClaw-created Seedance/Dreamina clips, use the channel's required duration: normally `7 seconds`, or `6 seconds` for `불송`. For Gemini clips, use the generated MP4 as-is.
- The app does not reject low-motion loop videos or alternate clip lengths. It checks that the upload is a readable video. OpenClaw should still visually inspect the loop and regenerate if the motion is too static or if Seedance/Dreamina was generated with the wrong duration setting, but this is a generation-quality decision rather than an app upload blocker.
- Do not substitute a locally synthesized motion loop, app-rendered still-image animation, Ken Burns pan/zoom, or other non-provider workaround when Dreamina/Seedance fails. Dreamina/Seedance failure should route to Gemini if quota is available; if Gemini quota is exhausted, defer that release and continue with the next eligible release.
- Keep these assets separate for normal moving-video channels: `--thumbnail` is the click image, `--cover` is the playback visual/first frame, and `--loop-video` is the short moving visual used inside the rendered video. Do not put channel names or logos on any of them. For `불송`, use one cover/thumbnail/first-frame package with a short Korean passage/theme + style phrase when useful.
- The short loop video must visually match the thumbnail's scene, but it should start from the cover or a dedicated first-frame image that is not overloaded with thumbnail text. Do not use a text-heavy thumbnail as the Dreamina/Seedance/Gemini first-frame reference, because generated video often makes large text flicker, disappear, or reappear during the loop.
- Channel labels are no longer allowed inside rendered videos. If visual text is needed, use only a short style, genre, use-case, or passage phrase already designed into the first frame.
- Do not put text on a solid black rectangle, opaque dark box, plaque, banner, pill, capsule, sticker, or detached background shape. If readability needs help, use integrated typography, subtle shadow, thin outline, or gentle local contrast that still feels part of the artwork.
- Do not add extra title sentences, duration text, lyrics, subtitles, UI, logos, channel names, or unrelated words to the cover/first-frame or loop video.
- Exception: if Gemini/Veo adds its own provider logo or watermark, usually in the bottom-right corner, accept it as an unavoidable provider artifact. Do not reject or regenerate a loop video only because that Gemini/Veo logo or watermark is visible. The "no logos" rule only forbids OpenClaw-requested or generated in-scene logos, brand marks, UI, and unrelated text.
- Do not create or bake in spectrum bars, waveform graphics, equalizers, audio meters, or other audio-reactive overlays in the cover, thumbnail, or Dreamina/Seedance/Gemini loop clip. The app adds the final audio-reactive visualizer during video render. Keep the uploaded loop video visually clean except for the requested scene motion and any short style/passage phrase already in the first frame.
- Do not rely on the default app-rendered visualizer preset. For each final render, choose the visualizer preset that best fits the cover/loop video, channel, and composition, then pass it explicitly with `--video-spectrum-overlay-style bars|mirror-bars|calm-bars|none`. Use only clean, natural-moving `bars` or `mirror-bars` when a spectrum helps, `calm-bars` for very low-motion meditative visuals, or `none` when the overlay would distract. For `BibliaCanto`, always pass `--video-spectrum-overlay-style none`; Bible releases must not have an app spectrum. For `불송`, pass `--video-spectrum-overlay-style calm-bars`; Buddhist releases use only a very low-motion, low-opacity spectrum. For Cinematic Pulse, always pass `--video-spectrum-overlay-style bars` unless the human explicitly asks otherwise. Do not use removed busy/fast presets: radial, pulse, multiwave, dots/particles, thin waveform, or the spectrum style used on `창세기 창조의 빛`; legacy values fall back to `bars`.
- For vocal/lyrics releases, always upload clean line-broken lyrics with `--lyrics-file` / `--lyrics`. The app creates YouTube CC captions at publish time from those saved lyrics, using faster-whisper line timing and Codex translations for all supported languages. The app also auto-burns the original-language lyric lines into the rendered video when singable lyrics are present. Do not add subtitle boxes or background plates: burned lyrics must be transparent-background text only. 불송 always uses `center-breath-serif` centered in the frame; other lyric releases use `soft-bottom-fade` by default or `editorial-lower-left` only when that composition is clearly better. Use `--lyrics-alignment-mode timeline` only as a rough fallback when ASR alignment is unavailable.
- Cinematic Pulse is no longer a standing still-image exception. For normal Cinematic Pulse releases, create photorealistic 2560x1440 or 1920x1080 cover/first-frame art, generate a subtle 7 second provider loop video, upload it with `--loop-video`, and queue `scripts/openclaw-release render-video --release-id RELEASE_ID --video-render-source-mode loop_video --video-render-resolution 720p --video-spectrum-overlay-style bars`. Use `--allow-still-image-video --video-render-source-mode still_image` only when a human explicitly asks for a still-image fallback.
- After Dreamina/Seedance/Gemini generation with baked-in text, visually inspect the downloaded MP4 before upload. Reject and regenerate if the style/passage phrase flickers, morphs, changes spelling, changes position drastically, becomes unreadable, or if the provider invents a channel name.
- For browser-based Gemini generation, open Gemini in the authenticated browser session, click the `Create image` / creation entry that accepts an image attachment and prompt, attach the cover/first-frame image as the first image, paste the selected channel profile's motion prompt, generate a video, download the MP4, inspect it, and pass that file path as `--loop-video`.
- Gemini quota accounting: count only successful Gemini attempts where a video is actually generated. Copyright/policy/moderation blocks before video generation do not count. A generated but visually rejected MP4 does count because the video quota was spent. After the 3rd successful Gemini video, treat Gemini as on cooldown for 24 hours from that 3rd generation time; during cooldown, use Dreamina/Seedance first, but if Dreamina/Seedance cannot create the needed clip, leave the release deferred for Gemini instead of using a still-image fallback. When the cooldown clears, process deferred Gemini loop-video releases before starting fresh loop-video work.
- For browser-based Dreamina/Seedance generation, OpenClaw should use `https://dreamina.capcut.com/ai-tool/home/`. Select Seedance/Dreamina `2.0 Fast`, first/last-frame mode if the UI asks, provide the first frame only, leave the last frame empty, set ratio to `16:9` when selectable, quality to `720p`, duration to the channel's required duration, normally exactly `7 seconds` and `6 seconds` for `불송`, then create/download the MP4, save it locally, and pass the downloaded file path as `--loop-video`. Exception: HaruHaru photorealistic releases use Seedance `2.0`, `1080p`, exactly `7 seconds`, and final render `--video-render-resolution 1080p`.
- Dreamina/Seedance has a duration parameter and it must be set. If the duration control is hidden when the screen opens, gently drag/scroll the settings/control row to the right until it is visible. Do not click Generate while the duration control is hidden or while you are not certain it is set to the channel's required duration. Re-open the duration selector and confirm the required duration immediately before the final Generate click. For Gemini, do not mention duration in the prompt or UI instructions; use the generated MP4 as-is.
- Do not create a draft/test video first and then create the correct-duration version. That wastes credits/time and is treated as an automation error. The first generated Dreamina/Seedance clip for normal OpenClaw work should already use the channel's required duration.
- After download, check the MP4 duration for awareness. If Seedance/Dreamina did not produce the requested channel duration, discard it, return to Seedance/Dreamina, set the required duration, regenerate, and only then upload/pass `--loop-video`. For Gemini, inspect quality/text/motion and upload the generated MP4 as-is.
- Do not put duration values such as `7 seconds` or `6 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina/Seedance prompt. Do not mention duration in the Gemini prompt. Set duration, ratio, and quality only through provider controls when available. Use the selected channel profile for camera behavior. For `Soft Hour Radio`, keep the camera locked and animate calm but clearly visible environmental motion across several layers throughout the full clip; do not ask for zoom, dolly, camera breathing, or camera drift.
- If Gemini blocks generation for copyright, protected IP, moderation, policy, artist/style imitation, logo, brand, or celebrity reasons, retry Gemini up to 10 blocked attempts for that release without counting those blocked attempts against the 3 successful-video quota. Do not retry the same prompt. Before every retry, post Slack progress with `scripts/openclaw-release slack-notify --text "Gemini 영상 생성이 저작권/정책 이슈로 막혀서 프롬프트를 수정해 다시 시도합니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`. If Gemini still cannot create a video after 10 blocked attempts, move on to Dreamina/Seedance for that release.
- If Dreamina/Seedance blocks generation for inappropriate content, copyright, moderation, policy, account, payment, quota, or browser-automation reasons, retry safely within the shared 10 total video-generation recovery attempts when retrying can reasonably help. Do not retry the same prompt. Before every retry, post Slack progress with `scripts/openclaw-release slack-notify --text "영상 만들기 실패해서 프롬프트를 수정해 다시 만듭니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`.
- If Dreamina/Seedance still cannot create the clip, try Gemini again if fewer than 3 successful Gemini videos have been generated in the active 24 hour window. If Gemini quota is already exhausted, post `scripts/openclaw-release slack-notify --text "Gemini 3개 영상 쿼터가 끝났고 Dreamina/Seedance도 실패해서 이 릴리즈의 loop video를 보류합니다. 24시간 쿨다운 후 Gemini로 먼저 다시 만들겠습니다. RELEASE_TITLE"` and stop before render/publish. On the next pass after cooldown, create and upload this deferred release's Gemini loop video before making new loop videos for other releases.
- For every retry, sanitize the prompt: remove named artists, studios, franchises, copyrighted characters, brands, logos, celebrity names, exact song/video titles, `in the style of` phrases, real-person likenesses, sexualized wording, minors, weapons, gore, and other moderation-risk terms. Replace them with original generic descriptors while preserving mood, first-frame continuity, and motion intent.
- If the uploaded first frame appears to be the moderation trigger, regenerate a safer cover/first-frame image first. If all 10 video-generation attempts fail and Gemini quota is available, try Gemini again with a sanitized prompt. If all providers fail or Gemini quota is exhausted, post `scripts/openclaw-release slack-notify --text "영상 생성이 실패해서 중단했습니다. RELEASE_TITLE: ERROR_SUMMARY"` and stop before render/publish unless the human explicitly approves a still-image fallback. If Gemini quota is exhausted, mark the release as deferred for Gemini and resume after the 24 hour cooldown before any new loop-video work. If the human explicitly approves a still-image fallback, pass `--allow-still-image-video`.

## Skill 1: Single Release Candidate Set

Use this skill when the user asks for one standalone song/single.

### Goal

Generate one Single Release candidate set. Suno normally returns two candidate songs for one prompt. Upload both candidates into the same Single Release so the human can listen and choose. If both are good, the human may approve both; the app splits the second approved candidate into its own Single Release instead of combining the songs. If both are bad, the human rejects both; the app archives that release automatically and it can be restored later.

### OpenClaw Skill Prompt

```text
You are creating one Single Release for the AI Music app.

Work in the OpenClaw repo checkout selected by docs/openclaw-next-release-planner.md.
Use the local app API only through scripts/openclaw-release.

Goal:
- Create or select one Single Release workspace before opening Suno or generating audio.
- Generate one standalone song/single.
- If Suno returns two candidates, upload both candidates to the precreated Single Release.
- If only one usable candidate exists, upload one candidate to the precreated Single Release.
- If two candidates come from one Suno prompt, they can share the original prompt/style, but give them independent editorial titles and preserve any candidate-specific lyrics, style notes, or differences.
- If candidate cover images exist, upload them with the audio candidates.
- If candidate lyrics or instrumental metatag files exist, upload them with the audio candidates using `--lyrics` or `--lyrics-file`. For instrumental/BGM candidates, use the exact bracket-only Suno metatag file from `docs/suno-v55-instrumental-format.md` rather than an empty field when possible. For J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop candidates, lyrics are expected by default unless the human explicitly asked for instrumental/no-vocal.
- If the Suno style/settings are known, upload them with `--style`. If excluded styles/negative tags are known, upload them with `--exclude-style`. Use one shared value or one per candidate.
- Clean awkward trailing A/B or 1/2 labels from uploaded candidate titles. If titles become duplicated, make them naturally unique without using pair labels.
- When the human approves one candidate, its uploaded cover is automatically registered as the release cover. If the human approves both candidates, the second approved candidate becomes a separate Single Release.
- The human still reviews/approves the cover before video rendering.
- Do not approve, reject, render, publish, or upload to YouTube.
- Return release.id, release.title, and all uploaded track ids.

Before opening Suno, run this first:

scripts/openclaw-release create-release \
  --workspace-mode single \
  --release-title "RELEASE_TITLE" \
  --description "Short concept for this single candidate set"

Keep the returned `release.id`. All Suno outputs from this prompt must be uploaded to that same release.

After audio generation, run one of these:

For two Suno candidates:
scripts/openclaw-release upload-single-candidates \
  --release-id RELEASE_ID \
  --audio ABSOLUTE_AUDIO_PATH_A \
  --audio ABSOLUTE_AUDIO_PATH_B \
  --cover ABSOLUTE_COVER_PATH_A \
  --cover ABSOLUTE_COVER_PATH_B \
  --lyrics-file ABSOLUTE_LYRICS_PATH_A \
  --lyrics-file ABSOLUTE_LYRICS_PATH_B \
  --style "SUNO_STYLE_OR_SETTINGS" \
  --exclude-style "SUNO_EXCLUDED_STYLES_OR_NEGATIVE_TAGS" \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags"

For one candidate:
scripts/openclaw-release upload-single-candidates \
  --release-id RELEASE_ID \
  --audio ABSOLUTE_AUDIO_PATH \
  --cover ABSOLUTE_COVER_PATH \
  --lyrics-file ABSOLUTE_LYRICS_PATH \
  --style "SUNO_STYLE_OR_SETTINGS" \
  --exclude-style "SUNO_EXCLUDED_STYLES_OR_NEGATIVE_TAGS" \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --tags "comma, separated, tags"

If no cover image is ready, omit every `--cover` argument. If one shared cover should be used for both candidates, provide one `--cover`; if each candidate has a different cover, provide one `--cover` per `--audio` in the same order. If lyrics/content are truly unavailable, omit `--lyrics`/`--lyrics-file`; the app stores an empty lyrics field. For instrumental/BGM candidates, prefer the exact bracket-only Suno metatag file instead of omitting lyrics. For J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop candidates, do not treat missing lyrics as normal; generate or capture original lyrics unless the human explicitly requested instrumental/no-vocal. If style/settings are not available, omit `--style`; otherwise always provide it. If excluded styles/negative tags are not available, omit `--exclude-style`; otherwise always provide it.

Report the command output JSON. The human will approve one candidate, approve both candidates as separate singles, or reject both in Slack or the web UI.
```

### Required Output

OpenClaw should finish with a concise report:

```text
Single release candidates uploaded.
release.id: ...
release.title: ...
tracks:
- ...
- ...
Next: human should approve one candidate, approve both candidates as separate Single Releases, or reject both.
```

### Safety Checks

- Do not create two separate Single Releases before human review. Both candidates from one Suno request should start in one review release.
- Do not upload more than two candidates to a Single Release.
- Do not upload cover images separately after this command if they were already uploaded with the candidate audio.
- A Single Release can publish only one selected track. If another candidate is approved later, the app creates a separate Single Release for it.
- If both candidates are rejected later, the app archives the release automatically. Do not manually delete it.

## Skill 2: Automatic Single Publisher

Use this skill when the user explicitly asks OpenClaw to create one standalone song/single and publish it to YouTube through the app.

### Goal

Create one Single Release for one final song, generate the needed audio, auto-approve exactly one usable candidate, render the final single video, approve metadata, and upload through the app to YouTube on the correct channel.

This is different from `Single Release Candidate Set`: that skill stops for human candidate review. Use this automatic publisher only when the human says to publish/upload the single.

For mainstream J-pop/Japanese pop, Tokyo/Japan pop, city pop, dance-pop, synth-pop, pop-rock, anime-pop, or similar Japan-themed vocal pop singles, publish to `Tokyo Daydream Radio`. For Korean/K-pop singles, publish to `HaruHaru`. For playful no-vocal Japanese-style game/anime OST, arcade-game BGM, fantasy-game BGM, cute RPG music, or item-shop BGM singles, publish to `Storylight OST`. For no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, or game-focus singles, publish to `Cinematic Pulse`. For no-vocal EDM/house/techno/trance club singles, publish to `Club Bloom`. For Old Testament and New Testament scripture-inspired singles, publish to `BibliaCanto`. For Buddhist scripture-inspired vocal singles, publish to `불송`. For English/American pop singles, publish to `sundaze`. For Latin/Spanish pop singles, publish to `Solwave Radio`.

### OpenClaw Skill Prompt

```text
You are creating and publishing one Single Release through the AI Music app.

Work in the OpenClaw repo checkout selected by docs/openclaw-next-release-planner.md.
Use scripts/openclaw-release only.

Goal:
- Create or select one Single Release workspace before opening Suno or generating audio.
- Generate an original standalone song/single.
- If the human references an existing artist such as YOASOBI, treat it only as mood/style guidance. Do not copy melodies, lyrics, titles, or a specific song.
- For J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop singles, generate a vocal song by default with original lyrics and a clear verse/pre-chorus/chorus structure. Use Japanese lyrics for J-pop/Japanese pop/anime-pop, Korean lyrics for K-pop, English lyrics for sundaze/English/American pop, and Spanish lyrics for Solwave/Latin/Spanish pop. Do not set instrumental/no-vocal unless the human explicitly asks for it.
- If Suno returns two usable candidates and the human asked for full automation, publish each good candidate as a separate Single Release by running this skill once per song.
- If publishing two good candidates from the same Suno request, treat them as separate releases after selection: give each one a distinct title, description angle, thumbnail wording, and preserved lyric/style context.
- Before upload, replace awkward trailing A/B, 1/2, or pair-style labels with independent song titles.
- Preserve lyrics or content notes during upload. Pass one `--lyrics` or `--lyrics-file` per `--audio` when available. For BGM/background/instrumental tracks, write and upload the exact bracket-only Suno instrumental metatag file when possible; J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop songs should not have empty lyrics unless the human explicitly requested an instrumental/no-vocal track.
- If this is a J-pop/K-pop/English pop/Latin pop/Spanish pop/anime-pop single and there is no final lyric text, stop and generate/capture original lyrics before calling `auto-publish-single`.
- Preserve Suno style/settings and excluded styles during upload. Pass `--style "SUNO_STYLE_OR_SETTINGS"` and `--exclude-style "SUNO_EXCLUDED_STYLES"` for each song.
- A final 16:9 cover image is required. For moving-video releases, this cover also acts as the Gemini/Dreamina/Seedance first-frame reference. Do not put the selected channel name, a channel logo, or a brand line on it. Use only a short style, genre, use-case, or passage phrase when visual text is useful.
- A separate YouTube thumbnail image with readable text is required for normal channels. For `불송`, use the same cover/first-frame package as the thumbnail, usually with the short Korean passage/theme + style phrase. For J-pop/Japan singles, use natural J-pop lane text such as `J-POP`, `CITY POP`, or `ANIME POP`, not the channel name. For HaruHaru, Storylight OST, Cinematic Pulse, Club Bloom, BibliaCanto, sundaze, and Solwave Radio, use the selected channel profile and song concept for thumbnail wording; there is no fixed recurring channel-brand signature. Do not add duration text or badges such as `1 HOUR`, `60 MIN`, or `1時間`.
- Apply the selected channel profile to both static images. For J-pop/Japan/Tokyo Daydream Radio singles, use the Tokyo profile. For Soft Hour/default BGM singles, use the Soft Hour profile. For HaruHaru, Storylight OST, Cinematic Pulse, Club Bloom, BibliaCanto, 불송, sundaze, or Solwave Radio, use that channel's profile and let the song concept drive the scene. The thumbnail should be generated from the final cover as a reference/edit derivative with the same composition plus readable click text. In thumbnails, keep the main requested subject centered; text must fit around the composition rather than moving the subject sideways.
- Before uploading the thumbnail, compare it against the cover. Character count, subject positions, silhouette, outfit colors, lighting, palette, and core background must remain visually continuous. Regenerate the thumbnail if it looks like a different scene or changes details such as cloak/shirt colors.
- Keep the visual style animated, anime, illustrated, or stylized unless the selected channel profile says otherwise. Cinematic Pulse and 불송 are photorealistic/premium cinematic-real exceptions; 불송 may occasionally use cute/gentle animation when the music lane is also soft and bright enough to match.
- Generate both static images with OpenAI GPT Image models, not Dreamina or Gemini. Prefer `gpt-image-2` when available; otherwise use the currently available GPT Image model. Gemini/Dreamina/Seedance is only for the moving short MP4. Do not assume OpenAI API usage is free; use the available image tool or configured API credentials.
- Generate one short loop-video MP4 before publish when moving visuals are requested. Try Gemini first unless its 24 hour cooldown is active; otherwise use Dreamina/Seedance. If Dreamina/Seedance cannot create the video, return to Gemini when quota is available; if all 3 Gemini videos are already spent, defer this release until Gemini cooldown clears.
- Use the cover or a separate first-frame image as the first-frame/start-frame reference for Gemini/Dreamina/Seedance so the video opening matches the thumbnail scene without overloading the provider with large click text. This first frame must not contain channel names. Use the selected channel profile for the first-frame concept. If the human requested a different visual concept, the first frame and motion prompt must follow that requested concept instead. Do not use Omni Reference or a last-frame reference.
- The thumbnail, cover, and loop video are separate assets for normal channels. The thumbnail has readable click text; the cover/loop video use the cleaner first-frame composition. None should contain channel names. The loop video must remain free of subtitles, lyrics, UI, logos, title sentences, duration text, and unrelated words.
- A Gemini/Veo provider logo or watermark in the corner is allowed and is not a reason to regenerate. Do not add any other logos or UI yourself.
- If using browser automation, use the Gemini-first workflow in `docs/openclaw-upload.md`: open Gemini, click `Create image` / the creation entry that accepts image+prompt, attach the cover/first-frame image, paste the motion prompt without any duration wording, generate/download the MP4, inspect it, and pass that absolute path as `--loop-video`. If Gemini is unavailable or on cooldown, open `https://dreamina.capcut.com/ai-tool/home/`, select `2.0 Fast`, use first/last-frame mode with only the first frame provided, do not use Omni Reference, leave the last frame empty, set `16:9`, `720p`, and the channel's required duration, re-check that the visible duration is correct, create/download the MP4, confirm the local file exists, and pass that absolute path as `--loop-video`. If the Seedance/Dreamina duration control is hidden when the screen opens, gently drag/scroll the settings/control row to the right until the duration option is visible, then set it to the required duration. Normal releases use `7 seconds`; `불송` uses `6 seconds`. Exception: HaruHaru photorealistic releases use Seedance `2.0`, `1080p`, exactly `7 seconds`, and final render `--video-render-resolution 1080p`.
- Do not include duration, ratio, or quality words in the video-generation prompt when the UI exposes those controls. Do not write duration values such as `7 seconds` or `6 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the prompt. Do not mention duration at all in Gemini prompts. Those are either UI settings or app-render responsibilities.
- Use the video prompt shape from the selected channel profile returned by `scripts/openclaw-release channel-profile`.
- If the human provided a specific visual/video request, replace the selected channel default prompt details with the requested subject/action/composition while keeping the safety/quality constraints: one continuous shot, locked/stable composition unless motion is requested, preserve first-frame composition/style, no channel names, no extra text/subtitles/logos/UI, no extra unwanted subjects.
- Always include this video prompt constraint: `The uploaded first frame must not contain a channel name or logo. If it contains a short style, genre, use-case, or passage phrase, keep that phrase stable and readable. Do not invent new text or channel branding. Keep the same composition, crop, camera distance, lighting, palette, and subject placement from first frame to final frame while animating natural environmental motion.` Keep all other constraints.
- Render audio/video, generate and approve YouTube metadata, and upload through the app.
- Publish Japanese/J-pop/Tokyo vocal-pop content to `Tokyo Daydream Radio`, Korean/K-pop content to `HaruHaru`, playful no-vocal Japanese-style game/anime OST or arcade/fantasy-game BGM to `Storylight OST`, no-vocal large-scale cinematic orchestra/movie-OST/film-score BGM to `Cinematic Pulse`, no-vocal EDM/house/techno/trance club music to `Club Bloom`, Old Testament and New Testament Bible scripture music to `BibliaCanto`, Buddhist scripture-inspired vocal music to `불송`, English/American pop to `sundaze`, and Latin/Spanish pop to `Solwave Radio`.
- Return the command output JSON, including release.id, uploaded track ids, YouTube video id, and output paths.

First, before opening Suno, create the destination release:

scripts/openclaw-release create-release \
  --workspace-mode single \
  --release-title "SINGLE_RELEASE_TITLE" \
  --description "Short concept description for metadata generation."
```

### Run The Full Automation

After one generated audio file, final cover, text thumbnail, and short loop video are ready, run one command. For `불송`, use the same calm Buddhist visual package as the thumbnail and omit `--thumbnail` or pass `--allow-cover-as-thumbnail`:

```bash
scripts/openclaw-release auto-publish-single \
  --release-id RELEASE_ID \
  --description "Short concept description for metadata generation." \
  --audio ABSOLUTE_AUDIO_PATH \
  --title "INDEPENDENT_TRACK_TITLE" \
  --lyrics-file ABSOLUTE_LYRICS_PATH \
  --cover ABSOLUTE_FINAL_CLEAN_COVER_IMAGE_PATH \
  --thumbnail ABSOLUTE_YOUTUBE_TEXT_THUMBNAIL_IMAGE_PATH \
  --loop-video ABSOLUTE_GEMINI_DREAMINA_SEEDANCE_LOOP_MP4 \
  --prompt "PROMPT_USED_TO_GENERATE_AUDIO" \
  --style "SUNO_STYLE_OR_SETTINGS" \
  --exclude-style "SUNO_EXCLUDED_STYLES_OR_NEGATIVE_TAGS" \
  --tags "comma, separated, tags" \
  --youtube-channel-title "Tokyo Daydream Radio"
```

Pass exactly one `--audio`, one `--title`, one optional `--lyrics-file`, one `--style`, and one optional `--exclude-style` if excluded styles/negative tags were used. If Suno produced two good songs, prepare separate cover/thumbnail/loop-video assets and run `auto-publish-single` twice with different release titles.

Do not omit `--cover` or `--thumbnail` for a full private single publish run. If either asset is not ready, stop after audio creation and report the missing asset. The app's local draft cover is only a placeholder for manual review, not acceptable for automatic YouTube upload.

`--loop-video` is required for normal publish automation. If it is missing, stop and create/download the Gemini/Dreamina/Seedance clip first. Do not create a local motion-loop workaround. Use `--allow-still-image-video` only when the human explicitly accepts a static-cover fallback.

### Required Output

OpenClaw should finish with:

```text
Private single upload completed.
release.id: ...
release.title: ...
uploaded tracks:
- ...
youtube_video_id: ...
youtube_channel: SELECTED_CHANNEL_TITLE
privacy: scheduled public at ... if scheduling is enabled, otherwise private
Next: human can review the scheduled/private YouTube upload before it goes public.
```

### Safety Checks

- Use `auto-publish-single` only when the human explicitly asks for publishing/uploading the single.
- Do not manually upload public. The app controls visibility and scheduling.
- Do not pass two audio files to one `auto-publish-single` command. One command equals one YouTube single.
- If two Suno candidates are both good, create and publish two separate Single Releases with separate assets.
- Do not use pair labels like A/B or 1/2 in final titles.
- Do not publish without final cover and thumbnail handling for the correct YouTube channel. This means a final cover/first-frame without channel names plus a separate text thumbnail. For `불송`, this can be one cover/thumbnail/first-frame package with a short Korean passage/theme + style phrase.
- For Japanese/J-pop/Tokyo singles, pass `--youtube-channel-title "Tokyo Daydream Radio"` explicitly. For Korean/K-pop singles, pass `--youtube-channel-title "HaruHaru"`. For English/American pop, pass `--youtube-channel-title "sundaze"`. For Latin/Spanish pop, pass `--youtube-channel-title "Solwave Radio"`.

## Skill 3: Automatic Playlist Publisher

Use this skill when the user asks for a playlist, mix, compilation, or long-form release and expects OpenClaw to finish the app-managed YouTube upload.

### Goal

Create one Playlist Release, generate enough tracks, upload them as approved tracks, render audio/video, generate and approve metadata, and upload the result through the app to YouTube on the correct channel.

Use `Soft Hour Radio` for normal background/cafe/sleep/study/chill releases. Use `Tokyo Daydream Radio` for mainstream J-pop/Japanese pop, Tokyo/Japan pop, city pop, dance-pop, synth-pop, pop-rock, anime-pop, or similar Japan-themed vocal pop releases. Use `HaruHaru` for Korean/K-pop vocal releases. Use `Storylight OST` for playful no-vocal Japanese-style game/anime OST, arcade-game BGM, fantasy-game BGM, cute RPG music, item-shop music, and light adventure instrumental releases. Use `Cinematic Pulse` for no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, and game-focus instrumental releases. Use `Club Bloom` for no-vocal EDM/house/techno/trance/workout/night-drive releases. Use `BibliaCanto` for both Old Testament and New Testament scripture-inspired music. Use `불송` for Buddhist scripture-inspired modern vocal music; the app schedules it daily at 07:00 Asia/Seoul. Use `sundaze` for English/American pop. Use `Solwave Radio` for Latin/Spanish pop. If the next-release planner selected another connected non-excluded channel, pass that channel title explicitly and use the returned custom or dedicated channel docs.

The human does not review every playlist track before rendering. The human reviews the final scheduled/private YouTube upload later and only intervenes if something sounds wrong.

### Important Duration Rule

Playlist uploads are auto-approved, so `workspace.actual_duration_seconds` becomes the source of truth after upload.
After audio render, `rendered_timeline` becomes the source of truth for YouTube description timestamps.
Use randomized audio render when Suno two-output pairs are adjacent and the human did not manually arrange a deliberate final order.

Generate enough material before publishing:

- Create roughly `900` seconds / 15 minutes of new approved audio for non-scripture channels. The app will try to extend the base block to roughly `2400` seconds / 40 minutes by reusing tracks from the back half of previous same-channel, similar-genre YouTube uploads.
- For `BibliaCanto` and `불송`, create roughly `2400` seconds / 40 minutes of new passage-based audio and do not rely on reuse. Those channels are excluded from back-half reuse so Bible/Buddhist passage content is not mixed with unrelated previous chapters.
- During the trial period, final video repeat is disabled by default, so render workers upload the rendered base block only. The repeat feature remains available behind an app setting for later testing.
- If no similar back-half reuse candidates exist on non-scripture channels, render proceeds with the uploaded new tracks instead of blocking. Do not keep making unrelated songs just to force reuse.
- Every helper audio upload retries up to 3 times. If a track still fails, the helper posts a Slack warning, continues uploading the rest of the batch, and stops before render/publish. Re-download or re-export only the failed source files, upload them again, then render/publish after the full intended track set is present.
- After every successful upload, use the returned JSON as the receipt: confirm `track.id`, `track.status`, and `duration_seconds`. The duration must be close to the actual local audio length.

### OpenClaw Skill Prompt

```text
You are creating and publishing a Playlist Release through the AI Music app. For non-scripture channels, create roughly 15 minutes of new audio; the app will try to extend the base block to about 40 minutes through same-channel similar-genre reuse. During the trial period, final video repeat is disabled.

Work in the OpenClaw repo checkout selected by docs/openclaw-next-release-planner.md.
Use scripts/openclaw-release only.

Goal:
- Create or select one Playlist Release workspace before opening Suno or generating audio.
- Select Suno v5.5 for every new generation whenever it is available. If the UI/API shows a higher credit cost than v5 for the same request, stop and report the exact difference instead of silently using v5.
- Generate songs in batches until the new approved audio duration is roughly 15 minutes for normal non-scripture channels. The app workspace target is 900 seconds for that new material, then audio render automatically tries to extend the base block toward 2400 seconds / 40 minutes from previous same-channel, similar-genre back-half tracks. If it cannot find suitable reuse candidates, it renders the uploaded new tracks instead of blocking. For BibliaCanto and 불송, generate roughly 40 minutes of new passage-based audio instead; these channels must not use back-half reuse.
- For BGM/background/lofi/study/sleep/cafe playlist requests, generate instrumental/no-vocal tracks by default unless the human explicitly asks for vocals. For Soft Hour Radio instrumental work, Suno's lyrics/custom-lyrics field must use the bracket-only format from `docs/suno-v55-instrumental-format.md`; never paste unbracketed arrangement prose into that field.
- For Soft Hour Radio lofi / lo-fi releases, put lofi in the Suno style/settings for each track and in the YouTube title/description/localizations so viewers immediately understand the genre.
- For BGM/background/lofi/study/sleep/cafe playlist requests, use Suno Advanced Options excluded styles to suppress vocals: `vocal, vocals, voice, voices, singing, singer, lead vocal, backing vocals, choir, choral, humming, hum, whisper, spoken word, speech, narration, rap, ad-libs, scat, vocal chops, ooh, aah, la la, lyrics, sung lyrics, topline`.
- For lyric/vocal playlist requests, add vocal clarity exclusions in Suno Advanced Options so the lead voice stays close, intelligible, and dry enough for streaming: `muddy vocals, muffled vocals, washed-out vocals, distant vocals, buried vocals, unclear lyrics, heavy reverb, excessive reverb, long reverb tail, large echo, echoey vocals, concert hall echo, arena reverb, stadium reverb, live concert vocals, crowd ambience, room boom`.
- For every Suno generation on every channel, add artificial noise blockers to Advanced Options excluded styles unless the human explicitly asks for vinyl/LP/noise texture: `white noise, static noise, vinyl crackle, record crackle, LP crackle, turntable noise, tape hiss, cassette hiss, analog hiss, noise floor, lo-fi noise, old record noise, dust noise, crackle, hiss`.
- Do not put duration caps such as `less than 4 minutes` or `under 4 minutes` into Suno prompts, style strings, lyrics, or bracketed metatags unless the human explicitly asks for that cap. Those caps can cause Suno to end too early. Prompt for a complete song/cue instead: natural intro, developed verse/section flow, chorus or central motif where appropriate, bridge/breakdown when useful, and a resolved ending. The helper rejects playlist tracks shorter than 2:00 by default and allows tracks up to 4:20 by default for most channels. `Soft Hour Radio` and `Cinematic Pulse` are exempt from the max-track rule: do not force those tracks under 4 minutes, and do not reject complete longer tracks just because of duration.
- For J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop, BibliaCanto, and 불송 playlist requests, generate vocal songs by default with original lyrics for each track. Use Japanese lyrics for J-pop/Japanese pop/anime-pop, Korean lyrics for K-pop, English lyrics for sundaze/English/American pop, Spanish lyrics for Solwave/Latin/Spanish pop, English lyrics for BibliaCanto scripture releases, and Korean lyrics for 불송 Buddhist releases unless the human explicitly asks for another lyric language. Do not make the batch instrumental/no-vocal unless the human explicitly asks for instrumental/BGM/lofi/no vocals.
- For every vocal Suno playlist track, set `More options` / `Vocal gender` deliberately: choose `male` for a male lead, `female` for a female lead, and leave it blank for mixed-gender, duet, group/choir, alternating male/female, or unspecified lead vocals. Keep the chosen vocal gender stable for retries of the same track unless the vocal concept changes.
- For every new Suno request in a playlist run, write a distinct prompt/style/lyrics plan before generating. Keep the channel/release mood consistent, but vary one or more of: tempo, drum pattern, bass movement, synth/guitar/piano texture, vocal energy, emotional angle, scene imagery, lyrical storyline, chorus hook, and song structure.
- If Suno returns two outputs from one request, use both outputs as separate playlist tracks when both are usable.
- Before upload, replace awkward trailing A/B, 1/2, or pair-style labels with independent song titles.
- Preserve each track's lyrics or content notes during upload. Pass one `--lyrics` or `--lyrics-file` per `--audio` when available, because good playlist tracks may later be republished as standalone singles and OpenClaw needs this context for thumbnail/loop-video generation. For J-pop/K-pop/English pop/Latin pop/Spanish pop/Japanese pop/anime-pop/BibliaCanto/불송 playlist tracks, lyrics are expected and should be uploaded for every track. For BGM/background/instrumental tracks, upload the exact bracket-only Suno instrumental metatag file used for generation instead of leaving the content blank whenever possible.
- If this is a J-pop/K-pop/English pop/Latin pop/Spanish pop/anime-pop/BibliaCanto/불송 playlist and any track lacks final lyric text, stop and generate/capture original lyrics before queuing audio/video render. Do not publish a lyricless vocal-channel playlist unless the human explicitly says it is BGM/instrumental/no-vocal.
- Preserve the Suno style/settings and excluded styles for each track. Pass one shared `--style` / `--exclude-style` if the whole batch used the same settings, or one value per `--audio` when they differ.
- Prefer track-specific `--style` values for playlist tracks. If a shared style is used, add track-specific prompt/title/lyrics variation so the playlist does not sound like one song repeated with minor edits.
- If Suno gives two outputs from the same prompt, do not name them like `Title A`, `Title B`, `Title 1`, `Title 2`, `Title - Morning`, or `Title - Evening`.
- Give each output a standalone title that fits the mood, for example `Saffron Motion` and `Open Road Cadence` instead of `Highway Saffron A` and `Highway Saffron B`.
- Upload all usable tracks to one Playlist Release.
- Upload tracks as auto-approved, not pending human review.
- If using `scripts/openclaw-release upload-audio` for individual playlist tracks, do not pass `--pending-review`; playlist uploads auto-approve by default.
- A final 16:9 cover image is required before YouTube upload.
- A separate YouTube thumbnail image with readable text is required before YouTube upload for non-불송 channels. For `불송`, the cover, YouTube thumbnail, first-frame, and loop-video visual should all reuse the same calm Buddhist image package, with at most one short Korean passage/theme + style phrase and no `불송` channel name.
- Generate or obtain the final cover image before running the full publish command, then pass it with `--cover`. Use OpenAI GPT Image models for static image creation, not Dreamina. Do not put channel names, channel logos, or channel-brand lines on the cover/first-frame. Use only a short style, genre, use-case, or passage phrase when useful.
- Generate or obtain a separate text thumbnail before running the full publish command, then pass it with `--thumbnail` for normal channels. Use OpenAI GPT Image models for static image creation, not Dreamina. The thumbnail must be created from the final cover as an image reference/edit, not as a new independent scene. Use the channel profile and playlist concept for thumbnail wording instead of fixed channel branding. For `불송`, reuse the same cover/first-frame package as the thumbnail and keep the short Korean passage/theme + style phrase when present. Do not add duration text or badges such as `1 HOUR`, `60 MIN`, or `1時間`.
- Apply the selected channel profile to both images. Use the same centered requested composition plus readable click text for the thumbnail. In thumbnails, keep the main subject centered and place text around it in negative space; never move the main subject to one side just to make room for text.
- Do not create an opaque black box or other hard background behind visual text in the cover/first-frame/loop video. Text should feel integrated into the artwork.
- The cover and thumbnail should look like the same release art package. Preserve the same characters, poses, clothing colors, background, lighting, palette, and camera angle. If the thumbnail changes those details, regenerate it before uploading.
- Keep every generated visual animated, anime, illustrated, or stylized unless the selected channel profile says otherwise. Cinematic Pulse and 불송 are explicit photorealistic/premium cinematic-real exceptions; 불송 may occasionally use cute/gentle animation when the music lane is also soft and bright enough to match. HaruHaru has a separate 2:1 visual rule: two photorealistic adult fashion/lifestyle releases, then one illustrated/stylized release, then repeat. For HaruHaru photorealistic releases only, use Seedance `2.0` at `1080p` and queue the final render with `--video-render-resolution 1080p`; for HaruHaru illustrated/stylized releases, use Seedance/Dreamina `2.0 Fast` at `720p`.
- Generate a short motion clip before running the full publish command, then pass it with `--loop-video` and `--loop-video-provider gemini|dreamina|seedance`. Try Gemini first unless Gemini is on cooldown; use Dreamina/Seedance when Gemini is unavailable, has reached 3 successful videos in the last 24 hours, or cannot create a video after 10 blocked prompt attempts. If Dreamina/Seedance cannot create the clip, try Gemini again if quota is available; if Gemini quota is exhausted, defer this release and resume it first after the 24 hour Gemini cooldown.
- The thumbnail, cover, and loop video are separate assets for normal channels. The thumbnail contains readable click text; the cover and loop video use the cleaner first-frame composition. None should contain channel names. For `불송`, use one cover/thumbnail/first-frame package with a short Korean passage/theme + style phrase when useful. Verify that Gemini/Dreamina/Seedance preserves the intended frame in the clip.
- A Gemini/Veo provider logo or watermark in the corner is allowed and is not a reason to regenerate. Do not add any other logos or UI yourself.
- Use the cover or a separate first-frame image as the visual starting reference for Gemini/Dreamina/Seedance image-to-video generation. This reference must not include channel names or logos. Use the selected channel profile for the first shot and motion direction. If the human requested a different video concept, use that requested subject/action/composition for the cover, thumbnail, and loop video. Do not use a text-heavy thumbnail as the video first frame.
- For motion clips, set duration/ratio/quality in provider controls when available, not in the prompt. Use the prompt shape from the selected channel profile. For `Soft Hour Radio`, the final moment should keep the same crop, framing, camera distance, lighting, palette, and subject placement; only ambient details may differ. For photorealistic `HaruHaru`, the final moment must preserve the main subject's size, crop, camera distance, and placement. The motion should be calm but clearly visible throughout the full clip.
- Do not include duration values such as `7 seconds` or `6 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the video-generation prompt. Do not mention duration in Gemini prompts. These terms can cause the provider to generate a shorter repeated segment inside the clip.
- If using browser automation instead of an API, use the Gemini-first workflow in `docs/openclaw-upload.md`: open Gemini, click `Create image` / the creation entry that accepts image+prompt, attach the cover/first-frame image, paste the motion prompt with no duration wording, generate/download the MP4, inspect it, and use that absolute path for `--loop-video --loop-video-provider gemini`. If Gemini is unavailable or on cooldown, open `https://dreamina.capcut.com/ai-tool/home/`, choose Seedance/Dreamina `2.0 Fast`, choose the first/last-frame workflow if the UI requires a mode, upload only the first-frame image, leave the last frame empty, do not use Omni Reference, set ratio `16:9`, quality `720p`, duration to the channel's required duration, re-check that the visible duration is correct, create the video, download the MP4, confirm the local file exists, and use that absolute path with `--loop-video-provider dreamina` or `--loop-video-provider seedance`. If the duration control is not visible at first, gently drag/scroll the settings/control row to the right until the duration option appears before setting the required duration. Normal releases use `7 seconds`; `불송` uses `6 seconds`. Exception: HaruHaru photorealistic releases use Seedance `2.0`, `1080p`, exactly `7 seconds`, and final render `--video-render-resolution 1080p`.
- Before uploading the downloaded MP4, verify the normal automation output. If Seedance/Dreamina did not produce the requested channel duration, regenerate with the duration control set correctly. For Gemini, do not reject based on duration; inspect the generated MP4 and upload it as-is when text/motion/framing are acceptable.
- If Gemini rejects the prompt/image for copyright, protected IP, policy, moderation, artist/style imitation, logo, brand, celebrity, or similar issues, retry Gemini up to 10 blocked attempts before falling back to Dreamina/Seedance. Copyright/policy blocks do not count against the 3 successful Gemini videos. If Dreamina/Seedance rejects the prompt/image for inappropriate content, copyright, moderation, policy, quota, payment, or browser reasons, retry safely before giving up, then return to Gemini if quota is available. If Gemini quota is exhausted, defer the release and resume it first after cooldown instead of rendering/publishing without a loop video. Send Slack on every failed attempt before retrying:
  `scripts/openclaw-release slack-notify --text "영상 만들기 실패해서 프롬프트를 수정해 다시 만듭니다. (ATTEMPT/10) RELEASE_TITLE: ERROR_SUMMARY"`
- On each retry, make the prompt safer and more original: remove named artists, studios, franchises, copyrighted characters, brands, logos, celebrity names, exact song/video titles, `in the style of` phrases, real-person likenesses, sexualized wording, minors, weapons, gore, and other moderation-risk terms. Keep the same broad mood, first-frame continuity, and motion direction.
- If the first-frame image itself appears to be blocked, regenerate a safer first-frame/cover image and then retry. If Dreamina/Seedance still cannot create the clip, try Gemini if quota is available. If Gemini quota is exhausted, defer this release, report the deferral in Slack, and continue with the next eligible release before render/publish unless the human explicitly accepts a still-image fallback. If accepted, pass `--allow-still-image-video`.
- If Dreamina login, CAPTCHA, payment, face detection, or human approval blocks browser automation, do not create a local motion-loop substitute. Try Gemini if quota is available; if Gemini quota is exhausted, defer this release and move on.
- Do not let the app's local draft cover stand in for final cover art.
- Render playlist audio.
- Approve the cover.
- Render video.
- Generate and approve YouTube metadata.
- Publish through the app to the selected YouTube channel. Use `Tokyo Daydream Radio` for mainstream J-pop/Japanese pop/Tokyo pop releases, `HaruHaru` for Korean/K-pop vocal releases, `Storylight OST` for playful no-vocal Japanese-style game/anime OST and arcade/fantasy-game BGM releases, `Cinematic Pulse` for no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, and game-focus releases, `Club Bloom` for no-vocal EDM/house/techno/trance club releases, `BibliaCanto` for Old Testament and New Testament scripture-inspired music, `불송` for Buddhist scripture-inspired modern vocal music, `sundaze` for English/American pop, `Solwave Radio` for Latin/Spanish pop, and `Soft Hour Radio` for default BGM/background releases. If the planner selected another connected non-excluded channel, use that exact channel title and the returned channel docs.
- Return the command output JSON, including release.id, uploaded track ids, YouTube video id, and output paths.

First, before opening Suno or submitting the first playlist prompt, create the destination release:

scripts/openclaw-release create-release \
  --workspace-mode playlist \
  --release-title "PLAYLIST_TITLE" \
  --youtube-channel-title "CHANNEL_TITLE" \
  --description "Short mood/use-case description for metadata generation."
```

### Slack Command Example

If the human gives this instruction through Slack, interpret it as approval to run the full playlist automation:

```text
카페 피아노 40분 플레이리스트 만들어서 Soft Hour Radio에 업로드까지 해줘.
Suno가 두 곡씩 주면 둘 다 playlist 트랙으로 쓰고, 트랙별 A/B 표시는 제목에서 빼줘.
마지막 업로드/예약이 끝나면 YouTube video id와 예약 공개 시간을 알려줘.
```

Japan routing example:

```text
도쿄 시티팝 40분 플레이리스트 만들어서 Tokyo Daydream Radio에 업로드까지 해줘.
Suno가 두 곡씩 주면 둘 다 playlist 트랙으로 쓰고, 트랙별 A/B 표시는 제목에서 빼줘.
썸네일에는 큰 J-POP 같은 장르/분위기 문구만 넣고 채널명은 넣지 마.
```

English pop routing example:

```text
Summer night drive English pop 40분 플레이리스트 만들어서 sundaze에 업로드까지 해줘.
Suno가 두 곡씩 주면 둘 다 playlist 트랙으로 쓰고, 영어 가사를 각 곡마다 다르게 만들어서 같이 업로드해줘.
커버, 썸네일, 짧은 loop video은 playlist 컨셉에 맞게 만들고 고정된 시그니처 구도는 쓰지 마.
```

Latin/Spanish routing example:

```text
Verano latino reggaeton pop 40분 플레이리스트 만들어서 Solwave Radio에 업로드까지 해줘.
Suno가 두 곡씩 주면 둘 다 playlist 트랙으로 쓰고, 스페인어 가사를 각 곡마다 다르게 만들어서 같이 업로드해줘.
커버, 썸네일, 짧은 loop video은 playlist 컨셉에 맞게 만들고 고정된 시그니처 구도는 쓰지 마.
```

### Run The Lookahead Producer Pass

After all generated audio files and visual assets are ready, use step commands and stop after video render is queued:

```bash
scripts/openclaw-release upload-audio --release-id RELEASE_ID --audio ABSOLUTE_AUDIO_PATH_01 --title "INDEPENDENT_TRACK_TITLE_01" --lyrics-file ABSOLUTE_LYRICS_PATH_01 --style "SUNO_STYLE_OR_SETTINGS_01" --exclude-style "SUNO_EXCLUDED_STYLES_OR_NEGATIVE_TAGS_01" --prompt "PROMPT_USED_TO_GENERATE_AUDIO" --tags "comma, separated, tags"
scripts/openclaw-release upload-audio --release-id RELEASE_ID --audio ABSOLUTE_AUDIO_PATH_02 --title "INDEPENDENT_TRACK_TITLE_02" --lyrics-file ABSOLUTE_LYRICS_PATH_02 --style "SUNO_STYLE_OR_SETTINGS_02" --exclude-style "SUNO_EXCLUDED_STYLES_OR_NEGATIVE_TAGS_02" --prompt "PROMPT_USED_TO_GENERATE_AUDIO" --tags "comma, separated, tags"
scripts/openclaw-release upload-cover --release-id RELEASE_ID --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH
scripts/openclaw-release upload-thumbnail --release-id RELEASE_ID --thumbnail ABSOLUTE_YOUTUBE_THUMBNAIL_IMAGE_PATH
scripts/openclaw-release upload-loop-video --release-id RELEASE_ID --loop-video ABSOLUTE_DREAMINA_SEEDANCE_LOOP_MP4
scripts/openclaw-release render-audio --release-id RELEASE_ID --randomize-order
scripts/openclaw-release approve-cover --release-id RELEASE_ID
scripts/openclaw-release render-video --release-id RELEASE_ID --video-spectrum-overlay-style PRESET
scripts/openclaw-release openclaw-lock-finish --run-id "$RUN_ID" --status completed --message "Queued video render for RELEASE_ID"
```

Do not pass `--wait` to `render-video` during continuous automation. Do not approve metadata or publish a newly queued release in the same producer pass. An external render worker will render/upload the long MP4 and the app will ask OpenClaw again when the release is ready for metadata/publish.

Do not omit `--cover`, `--thumbnail`, or `--loop-video` for normal playlist production. If any asset is not ready, stop and report the missing asset. The app's local draft cover is only a placeholder for manual review, not acceptable for automatic YouTube upload.

Use `--randomize-order` when the uploaded playlist contains similar Suno two-output pairs next to each other. Omit it when the human already arranged a deliberate final order.

If the release is mainstream J-pop/Japanese pop/Tokyo pop, set the release channel to `Tokyo Daydream Radio`. If it is Korean/K-pop, use `HaruHaru`. If it is playful no-vocal Japanese-style game/anime OST, arcade-game BGM, fantasy-game BGM, cute RPG music, or item-shop BGM, use `Storylight OST`. If it is no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, or game-focus music, use `Cinematic Pulse`. If it is no-vocal EDM/house/techno/trance/workout/night-drive club music, use `Club Bloom`. If it is Old Testament/Bible sequence music or New Testament/Gospel/worship music, use `BibliaCanto`. If it is Buddhist scripture-inspired modern vocal music, use `불송`; the app schedules it daily at 07:00 Asia/Seoul. If it is English/American pop, use `sundaze`. If it is Latin/Spanish pop, use `Solwave Radio`. Otherwise use `Soft Hour Radio`.

### Run The Finisher Pass

When the app asks again after external video render completion, finish the rendered release:

```bash
scripts/openclaw-release metadata-context --release-id RELEASE_ID
scripts/openclaw-release approve-metadata --release-id RELEASE_ID --title "..." --description-file DESCRIPTION.md --tags "comma, separated, tags" ...
scripts/openclaw-release publish-release --release-id RELEASE_ID --youtube-channel-title "SELECTED_CHANNEL_TITLE"
```

For New Testament scripture releases, `SELECTED_CHANNEL_TITLE` is still `BibliaCanto`.

Only use `--force-under-target` if the human explicitly accepted a shorter playlist.

### Required Output

OpenClaw should finish with:

```text
Producer pass queued, or finisher pass completed.
release.id: ...
release.title: ...
uploaded tracks:
- ...
- ...
youtube_video_id: ... if published
youtube_channel: SELECTED_CHANNEL_TITLE
privacy: scheduled public at ... if published and scheduling is enabled, otherwise private
Next: video rendering is queued, or human can review the scheduled/private YouTube upload before it goes public.
```

### Safety Checks

- Keep all generated tracks for the same playlist in one Playlist Release.
- Do not create a Single Release for playlist candidates.
- Do not use the `MusicSun` channel for playlist publishing unless the human explicitly overrides the channel. MusicSun is manual-only and excluded from automatic next-release rotation.
- Do not manually upload public. The app controls visibility and scheduling.
- Do not publish if the selected YouTube channel is not connected. Current intended routing is `Soft Hour Radio` for general BGM releases, `Tokyo Daydream Radio` for mainstream J-pop/Japanese pop releases, `HaruHaru` for Korean/K-pop vocal releases, `Storylight OST` for playful no-vocal Japanese-style game/anime OST and arcade/fantasy-game BGM releases, `Cinematic Pulse` for no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery-tension, and game-focus releases, `Club Bloom` for no-vocal EDM/house/techno/trance club releases, `BibliaCanto` for both Old Testament and New Testament Bible scripture-inspired music, `불송` for Buddhist scripture-inspired vocal music, `sundaze` for English/American pop, and `Solwave Radio` for Latin/Spanish pop.
- Do not publish if final cover art was not uploaded.
- Do not publish if final YouTube thumbnail handling is missing. For normal channels, final YouTube thumbnail art must be uploaded. For `불송`, reuse the same cover/first-frame package as the thumbnail, with the short Korean passage/theme + style phrase when present.
- Do not use Dreamina or Gemini to create static cover or thumbnail images. Use OpenAI GPT Image models for static images, then use Gemini-first video generation to animate the cover or first-frame image into a short loop video. Do not put channel names, channel logos, or channel-brand lines on any generated visual.
- Static cover and thumbnail images must follow the selected channel profile returned by `scripts/openclaw-release channel-profile`.
- In thumbnails, keep the main channel/requested subject centered; text must not push it sideways.
- Do not use `--allow-generated-draft-cover` unless the human explicitly says a placeholder cover is acceptable for this upload.
- Do not use `--allow-cover-as-thumbnail` unless the human explicitly says one image is acceptable for both the video visual and YouTube thumbnail. Exception: for `불송`, one cover/first-frame package may also be the thumbnail.
- Do not create a long MP4 in OpenClaw. Upload only the short loop clip with `--loop-video` and a provider tag via `--loop-video-provider`; the app handles the long render.
- Do not add subtitles, lyric overlays, UI elements, title sentences, duration text, channel names, logos, or unrelated words inside the loop video. The selected channel profile controls the default visual action. An explicit human visual/video request overrides that channel default. If the first-frame reference has too much text, regenerate a cleaner first frame before using Dreamina/Seedance.
- Do not use Dreamina Omni Reference for loop-video generation. Use first-frame/start-frame input only and leave last-frame input empty.
- Do not accidentally use or intentionally create a Dreamina/Seedance clip with the wrong duration setting for normal auto-publish work. OpenClaw must catch the Dreamina/Seedance UI mistake before the Generate click by confirming the visible duration control shows the channel's required duration; if the control is hidden, drag/scroll the settings/control row to the right until it is visible before Generate. Never click Generate while it shows 5 seconds, is hidden, or is uncertain. Verify the downloaded file duration before upload. Gemini clips are uploaded as generated after inspection.
- Do not keep A/B, 1/2, or artificial pair suffixes in uploaded track titles.
- Do not use titles that read like numbered alternatives. Playlist tracks should look like a real album/playlist tracklist.
- Do not use AI/process/tool hashtags or YouTube tags on any channel. Avoid `AIMusic`, `AI music`, `AI generated`, `AI visualizer`, `Suno`, `OpenClaw`, and `Codex` in public hashtags and API tags.
- Do not auto-approve the app's template metadata for playlist releases. Before publish, playlist metadata must include a timestamped tracklist in the main description and every localization, plus every configured localization: Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Turkish, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese.
- If metadata is incomplete, run `scripts/openclaw-release metadata-context --release-id RELEASE_ID`, write full timeline/localized metadata, run `scripts/openclaw-release approve-metadata` with every localization file, then call publish approval.
- If YouTube upload fails because the connected account is not phone/account verified for 14+ minute videos, do not delete the release and do not restart generation. Keep the rendered audio/video, cover, thumbnail, loop video, and approved metadata in the app for later upload after verification, report the deferred upload in Slack, and continue to the next automatic playlist request.
- Do not create a Slack review message for every playlist track during automatic playlist publishing.
- If the automation times out while waiting for render/upload, report the exact stage and current release state. Do not start a duplicate publish blindly.

## Quick Selection Guide

Use `Single Release Candidate Set` when:

- The user asks for one song, one single, one YouTube single, or one standalone track.
- Suno returns two alternatives for the same prompt.
- The human needs to choose A or B.

Use `Automatic Single Publisher` when:

- The user asks for one song, one single, or one standalone track and explicitly says to publish/upload it.
- The goal is an app-managed YouTube upload without stopping for candidate review.
- The release needs a final cover/first-frame without channel names, a separate text thumbnail, a short Gemini-first loop video, metadata approval, and app-managed upload. Exception: `불송` can use one cover/thumbnail/first-frame package with a short Korean passage/theme + style phrase.

Use `Automatic Playlist Publisher` when:

- The user asks for a playlist, mix, compilation, batch, or long-form release.
- The goal is many tracks.
- The human expects OpenClaw to upload through the app to YouTube and review only the final result.

Use `OpenClaw YouTube Metadata Skill` when:

- The release already has rendered video.
- The human asks OpenClaw to write YouTube title, description, and tags.
- The human wants OpenClaw to approve metadata but not publish.
- The human can alternatively use the web `Generate Metadata` / `Regenerate Metadata Draft` button, which may call the VM's local Codex CLI when enabled.
- OpenClaw must first run `scripts/openclaw-release metadata-context --release-id RELEASE_ID` and use `display_timestamp_lines` when available.
- Follow [openclaw-youtube-metadata.md](openclaw-youtube-metadata.md).
