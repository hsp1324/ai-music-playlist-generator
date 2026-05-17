# OpenClaw YouTube Metadata Skill

Use this when the release already has rendered video and the human asks OpenClaw to write YouTube metadata.

OpenClaw should write:

- YouTube title
- YouTube description
- YouTube tags as one comma-separated string

The app stores those values as approved metadata. Later, when the human clicks publish or re-upload, the app sends that exact title, description, and tags to YouTube.

The web UI can also generate a draft from the VM's local Codex CLI when `AIMP_CODEX_METADATA_ENABLED=true`.
Use `Generate Metadata` or `Regenerate Metadata Draft` in the release action area.
If Codex is unavailable, times out, or returns invalid JSON, the app falls back to the deterministic template generator and marks the draft with a fallback warning.

## Rules

- Work in the OpenClaw repo checkout, normally `~/repos/ai-music-playlist-generator`; if missing, try `~/repos/ai리포` or the current checkout.
- Use `scripts/openclaw-release` against the deployed AI Music app API. `AIMP_LOCAL_API_BASE` must point to the deployed VM app API or a tunnel to that API, not OpenClaw's local dev API.
- Do not publish or re-upload to YouTube unless the human explicitly asks.
- The release must already have a rendered video before metadata can be approved.
- For tags, provide comma-separated plain tags without `#`, for example `Piano,CafePiano,StudyMusic,WorkMusic`.
- YouTube API tags and public description hashtags are separate. `--tags` sends hidden YouTube tags; the description text itself must also end with one public hashtag line.
- Every main description and every localized description must end with 5-8 public hashtags, for example `#Jpop #TokyoDaydreamRadio #CityPop #DriveMusic #WorkMusic`. Do not assume `--tags` will appear publicly.
- Never use AI/process/tool hashtags or YouTube tags on any channel. Do not write `AIMusic`, `AI music`, `AI generated`, `AI visualizer`, `Suno`, `OpenClaw`, or `Codex` as tags or public hashtags.
- Playlist metadata approval is blocked unless every configured language is present and the main description plus every localized description contains a timestamped tracklist.
- Keep the title under 100 characters.
- For Playlist Releases on every channel, every YouTube title in every language must start exactly with `[playlist]`. Single Releases must not use this prefix.
- After `[playlist]`, do not repeat playlist nouns such as `플레이리스트`, `Playlist`, `プレイリスト`, or `lista de reproducción`; use music/mix/radio wording instead.
- Across every channel, the title should be broad, searchable, and immediately understandable to a normal viewer. Lead with the channel's genre identity and a real listening reason, not a narrow visual scene, prop, exact location, or internal workspace concept. The cover/video concept can be specific, but the title and first description paragraph should be more public and useful. Title-shape repetition is acceptable when the repeated shape is mainstream, natural, and channel-fit; do not force novelty by inventing awkward niche wording.
- For `Club Bloom`, lead with the exact dance genre, subgenre, or genre fusion immediately after `[playlist]`, using mainstream mix language such as `Progressive Trance x EDM Mix`, `Tech House Workout Mix`, `Hype Trap x EDM Mix`, `Melodic Techno Night Drive`, `Bass House Workout Mix`, `Bass Boosted EDM & Electro House Mix`, or `Festival EDM Mix`. Put one or two public listening hooks after the separator. Avoid awkward keyword-stuffed title shapes like `[playlist] Progressive Trance for Night Roads, Gaming Focus and Club Drive`, and never use machine-translated keyword tails like `[playlist] Bass House Club Mix | Gaming Night & Workout Energy`; prefer `[playlist] Bass House Workout Mix 2026 | Heavy EDM for Gaming & Night Drive` or `[playlist] Progressive Trance x EDM Mix | Night Drive & Gaming Club Music`.
- For playlist/BGM titles, include a clear listening situation in the title itself, not only in the description. Choose the situation from the actual concept and sound; do not repeat `study`, `work`, `walk`, or `rest` as defaults. Normal automated playlists target 40+ minutes, so do not write `1시간` unless the rendered duration is actually close to or above one hour. Good Korean BGM patterns when they genuinely fit: `공부할 때 듣기 좋은 숲길 BGM 40분`, `산책·드라이브할 때 듣기 좋은 해변 BGM 40분`, `작업할 때 틀어놓기 좋은 카페 피아노 40분`.
- Title and description use cases must match the actual music energy, arrangement, lyrics, and channel concept. Do not add generic `study`, `focus`, `work`, or `night walk` wording just because it is common SEO text. Use `walk` / `산책` only when walking, commuting on foot, street movement, beach/forest walks, crosswalks, or similar movement is central. If the tracklist feels high-energy, club-like, dance-pop, rooftop, bass-heavy, arcade/game-like, friend-hangout, or workout-ready, use cases should be things like gaming, arcade, friends, night out, getting ready, workout, running, party warmup, driving, confidence, weekend energy, or nightlife instead of concentration/study/walk.
- For vocal releases, the title and description are packaging, not lyric instructions. Do not judge or rewrite lyrics based on whether they mention the title's use case. The lyrics only need to be good songs that match the melody, beat, vocal delivery, hook, and emotion.
- Description can be multiline; write it to a temporary UTF-8 text file and pass `--description-file`.
- In Korean titles/descriptions, never use the transliterated words `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`. Use natural Korean such as `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡` instead.
- If the release is a playlist, include a timestamped tracklist from the final order.
- Always run `scripts/openclaw-release metadata-context` first and use its timeline in the description.
- If the release has already rendered audio, `metadata-context` uses the release's saved `rendered_timeline` snapshot from actual ffprobe source-file durations. Do not recalculate timestamps from visible track durations.
- `metadata-context` includes track `prompt`, `style`, `tags`, and `lyrics` when available. Use them as private creative context, but do not paste raw Suno settings into the public description.
- Prefer `display_timestamp_lines` when available. It keeps the same timestamps but removes awkward `A` / `B`, `1` / `2`, and old pair-style suffixes.
- Do not guess timestamps. The helper calculates them from the app's final order and track durations.
- Treat each timestamp as a fixed playback position. If a title is corrected, only change the title text; do not move or swap the timestamp.
- Do not sort track titles alphabetically or by A/B label in the metadata. The playback order is the source of truth.
- Do not show trailing `A` / `B`, `1` / `2`, or pair labels like `Morning` / `Evening` in the YouTube description. If two tracks would read like variants of the same title, rename only the displayed title text so every row feels like a standalone song.
- For releases that reach or exceed one hour, keep every timestamp in `HH:MM:SS` format. The first row should be `00:00:00`, and rows after one hour should be like `01:02:03`. This keeps YouTube timestamp links reliable past the one-hour mark.
- For Japan/J-pop/Tokyo Daydream Radio releases with localized metadata, write the timestamped tracklist differently per language:
- Korean/default description: use the Japanese track title first, followed by the Korean translation in parentheses, for example `00:03:22 海辺のきらめき (해변의 반짝임)`.
- Japanese description: use the Japanese title only, for example `00:03:22 海辺のきらめき`.
- English description: use the English translated title only, for example `00:03:22 Seaside Sparkle`.
- Spanish description: use the Spanish translated title only, for example `00:03:22 Destello junto al mar`.
- For `sundaze` English pop releases, use English as the main/default metadata language with `--default-language en`. Localized video titles should be rewritten naturally for each language when a literal English translation would feel awkward or less clickable. The English description should contain English track titles; every other localized description should keep the same English song titles in timestamped tracklist rows while translating the surrounding prose, use-case line, and hashtags.
- For `Solwave Radio` Latin/Spanish pop releases, use Spanish as the main/default metadata language with `--default-language es`. The Spanish description should contain Spanish track titles; every other localized description should translate only the displayed title text while keeping timestamps fixed.
- For `HaruHaru` K-pop releases, use Korean as the main/default metadata language with `--default-language ko`. The Korean description should contain Korean track titles. Localized descriptions may translate track titles naturally, but timestamps and row order must stay fixed.
- For `Storylight OST`, `Cinematic Pulse`, `Club Bloom`, `The Old Verse`, and `The New Verse`, use English as the main/default metadata language with `--default-language en`.
- Keep the exact same timestamps and playback order in Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese descriptions. YouTube supports Egyptian-facing Arabic through the `ar` localization; it does not expose a separate `ar-EG` code.
- If using the web `Regenerate Metadata Draft` button, still review the generated title, description, and tags before approving.
- For channel-specific market positioning and title/content rules, read [openclaw-channel-market-analysis.md](openclaw-channel-market-analysis.md). Use the prewritten selected-channel section; do not perform live YouTube competitor research during normal metadata work unless the human explicitly asks.

## Metadata Style Prompt

Give OpenClaw this prompt:

```text
You are writing YouTube metadata for an AI music release in the AI Music app.

Read the release title, final track order, durations, mood, style, lyrics, and tags.
First run:
scripts/openclaw-release metadata-context --release-id RELEASE_ID

Use the returned timestamps exactly for the tracklist.
Use `display_timestamp_lines` as the starting point when present.
If a displayed title still reads like A/B, 1/2, or a paired alternative, rewrite only the title text so it is natural and unique.
If the release is one hour or longer, keep all timestamps in HH:MM:SS form, including 00:00:00 at the first row.
Across every channel, write YouTube titles for broad viewer discovery first. Use the visual scene as supporting atmosphere, not as the main title hook, unless it is clearly the strongest public keyword. Prefer mainstream listening promises such as workout, running, getting ready, party warmup, drive, study, sleep, reading, focus, gaming, battle, fantasy writing, heartbreak, confidence, or feel-good energy when they match the actual music.
Before approving metadata, review the main title and every localized title in its own language. Treat localization as transcreation, not literal translation: if a direct translation becomes awkward, weak, too long, or less clickable, rewrite the localized title so it sounds natural for that language's YouTube audience. Localized titles may differ in wording, order, and exact hook from the main title as long as they keep the release identity, genre/lane, and use case truthful.
Reject titles in any language that become awkward noun piles, such as `game night and workout energy`, `night roads, gaming focus and club drive`, `bonus stage music` as the main hook, `final boss focus music`, or literal equivalents in that language. The title should sound like a natural music video, mix, playlist, OST, or worship release, not like search keywords glued together.
Use only one or two clear title hooks after the separator. A strong repeated public-facing title pattern is better than a technically unique phrase that sounds obscure, machine-translated, or too minor for discovery. Examples in these docs are direction references, not fixed templates to copy every time.
For vocal releases, never make the public playlist title control the lyrics. Lyrics can be unrelated to the title/use case if they are better songs. The first priority is that each lyric fits its own melody, beat, vocal tone, hook, and emotional arc.
For Japan/J-pop/Tokyo Daydream Radio releases, write Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese descriptions. In the Korean/default tracklist, use Japanese title plus Korean translation in parentheses. In the Japanese tracklist, use Japanese title only. In the English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese tracklists, translate only the displayed title text and keep timestamps fixed.
For sundaze English pop releases, write the main title/description in English, use `--default-language en`, and provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese localized versions. Localized video titles should be natural, click-oriented titles in each language rather than exact copies of the English title when the English wording would not click locally. In every localized timestamped tracklist, keep the track title text in English exactly as in the English description; translate only the surrounding prose, use-case line, and hashtag line.
For Solwave Radio Latin/Spanish pop releases, write the main title/description in Spanish, use `--default-language es`, and provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese localized versions.
For HaruHaru K-pop releases, write the main title/description in Korean, use `--default-language ko`, and provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese localized versions.
For Storylight OST playful no-vocal Japanese-style game/anime OST, arcade-game BGM, fantasy-game BGM, cute RPG music, item-shop music, and mini-game BGM releases, write the main title/description in English, use `--default-language en`, and provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese localized versions. Storylight titles must lead with a listener benefit or easy use case such as happy mood, mood boost, gaming, work, reading, relaxing, cozy focus, or light focus, then name the broad game/anime-BGM identity. Do not make narrow internal game-scene labels such as `Bonus Stage Music`, `Item Shop BGM`, `Quest Board`, `Inventory Screen`, or `Potion Counter` the main title hook; keep those details in the description or tracklist. If the title would translate as a game menu label instead of a reason to click, rewrite it.
For Cinematic Pulse no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, battle, emotional, mystery tension, and game-combat BGM releases, write the main title/description in English, use `--default-language en`, and provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese localized versions. Titles must sound like film-score/cinematic-orchestra packaging for broad viewers; avoid juvenile game-menu phrases and abstract focus labels.
For Club Bloom no-vocal EDM/house/techno/trance releases, write the main title/description in English, use `--default-language en`, and provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese localized versions. The title and description must name the selected club style lane and describe it as instrumental/no-vocal club music. Put the exact genre or genre fusion immediately after `[playlist]`, such as `Progressive Trance x EDM Mix`, `Tech House Workout Mix`, `Hype Trap x EDM Mix`, `Melodic Techno Night Drive`, `Bass House Workout Mix`, or `Festival EDM Mix`; put only one or two public use cases after the separator. Do not write abstract keyword endings such as `Gaming Night & Workout Energy`; use natural title promises such as `Heavy EDM for Gaming & Night Drive`, `Running Beats and Club Bass`, or `Night Drive & Gaming Club Music`.
For The Old Verse Old Testament scripture-inspired releases, write the main title/description in English, use `--default-language en`, and provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese localized versions. Include the Old Testament passage reference in the main title, every localized title, and the description, and use original paraphrase, not long copied Bible text. The first description paragraph must state the selected passage and adapted theme, such as creation, covenant, wilderness trust, lament, deliverance, wisdom, or prophetic hope. The description must also include one natural sentence naming the broad music style family, such as cinematic scripture worship, acoustic folk prayer songs, ancient-worship ballads, or psalm-like piano worship. Do not use vague worship keyword tails like `Hope Energy`, `Prayer Focus Music`, or `Bible Music` with no passage/theme/style.
For The New Verse New Testament/Gospel/worship releases, write the main title/description in English, use `--default-language en`, and provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese localized versions. Include the New Testament passage reference in the main title, every localized title, and the description, and use original paraphrase, not long copied Bible text. The first description paragraph must state the selected passage and adapted theme, such as grace, mercy, discipleship, healing, prayer, resurrection hope, or kingdom teaching. The description must also include one natural sentence naming the broad music style family, such as modern worship pop, warm gospel ballads, acoustic prayer songs, cinematic worship, or intimate piano worship. Do not use vague worship keyword tails like `Grace Energy`, `Prayer Focus Music`, or `Worship Music` with no passage/theme/style.
For Japan/J-pop/Tokyo Daydream Radio titles, do not over-emphasize the language. Prefer `J-POP`, `Tokyo`, city-pop, mood, and listening use cases. Avoid Korean title phrases like `일본어 J-pop`, `일본어 보컬`, or `일본어 카페 재즈` unless the human explicitly asks to highlight the language. If language matters, mention it naturally in the description instead.
For `sundaze`, `Solwave Radio`, `HaruHaru`, `Storylight OST`, `Cinematic Pulse`, `Club Bloom`, `The Old Verse`, and `The New Verse`, titles should read like curated editorial or `Essential` playlists: vivid situation/emotion + genre identity + listening use case. Do not use raw workspace names, short generic labels, or translated noun chains such as `Golden Hour Drive Pop`, `Ruta Dorada Pop`, `English Pop`, `Spanish Pop`, `Latin Pop`, `KPOP`, `Korean Pop`, `Fantasy OST`, `Battle Music`, `EDM`, `Bible Music`, `Worship Music`, `Gaming Night & Workout Energy`, or `Focus and Club Drive` by themselves. It is better to reuse a strong public-facing title pattern than to make a technically unique title that sounds obscure, awkward, or too minor for YouTube discovery.
Good `sundaze` example: `[playlist] Sunset Highway Pop Drive | Windows Down Road Trip Music`.
For upbeat rooftop/club/dance-pop `sundaze` releases, match the use case to the energy: getting ready, workout, running, party warmup, driving, and confidence are usually better than focus, study, or quiet work.
Good `Solwave Radio` example: `[playlist] Pop Latino para Ruta al Atardecer | Carretera, Verano y Buenas Vibras`.
Good `HaruHaru` example: `[playlist] 신나는 K-POP 믹스 | 운동, 러닝, 외출 준비, 파티 웜업`.
Good `Storylight OST` examples: `[playlist] Feel-Good Arcade BGM | Happy Game Music for Gaming, Work and Mood Boost`; `[playlist] Cozy Fantasy Game BGM | Happy Music for Reading, Work and Gaming`; `[playlist] Cute Game BGM for Work | Cozy Happy Music for Focus and Relaxing`; `[playlist] Happy Anime Game BGM | Cheerful Music for Reading, Gaming and Work`.
Good `Cinematic Pulse` style references, not fixed templates: `[playlist] Final Battle Scene Cinematic Music | Dark Fantasy Orchestra`; `[playlist] Cinematic Orchestra Music | Movie OST for Focus and Epic Scenes`; `[playlist] Emotional Film Score | Piano, Strings and Hopeful Cinematic Music`; `[playlist] Sci-Fi Action Trailer Music | Cyber Chase, Combat and Workout Energy`; `[playlist] Dark Mystery Orchestra | Tension Music for Writing and Focus`; `[playlist] Grand Journey Film Score | Cinematic Orchestra for Writing`.
For `Cinematic Pulse`, rotate among broad cinematic orchestra and film-score lanes such as final battle, dark fantasy, heroic trailer, emotional score, sci-fi action, mystery tension, grand journey, orchestral battle, writing music, and movie OST focus. Do not repeatedly copy only the listed examples.
Good `Club Bloom` examples: `[playlist] Progressive Trance x EDM Mix | Night Drive & Gaming Club Music`; `[playlist] Bass House Workout Mix 2026 | Heavy EDM for Gaming & Night Drive`; `[playlist] Tech House Workout Mix | Running Beats and Club Bass`; `[playlist] Melodic Techno Night Drive | Dark Club Mix for Gaming`.
Good `The Old Verse` examples: `[playlist] Genesis 1:1-5 Creation Songs | Old Testament Music for Worship and Reflection`; `[playlist] Genesis 15 Covenant Songs | Bible Music for Prayer, Hope and Waiting`.
Good `The New Verse` examples: `[playlist] Matthew 1:1-17 Gospel Songs | New Testament Worship Music for Prayer`; `[playlist] Matthew 5:1-12 Beatitudes Worship | New Testament Music for Hope and Reflection`.
In Korean title/description/localizations, never write `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`. Say `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡` instead.
For Playlist Releases, start the main title and every localized title exactly with `[playlist]`. Do not add `[playlist]` to Single Releases.
After `[playlist]`, do not include duplicate words like `플레이리스트`, `Playlist`, `プレイリスト`, or `lista de reproducción`; write `음악`, `music`, `mix`, or a natural use-case phrase instead.
End the description with one public hashtag line containing 5-8 relevant hashtags. Also include equivalent hashtag lines in Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese localized descriptions.
Never use AI/process/tool hashtags or YouTube tags on any channel. Do not write `AIMusic`, `AI music`, `AI generated`, `AI visualizer`, `Suno`, `OpenClaw`, or `Codex` as tags or public hashtags.
Write metadata in this shape:

Title:
<Korean YouTube title, under 100 characters, starting with [playlist] for playlist releases and with a clear listening use case that fits the actual concept and sound>

Description:
<2-4 Korean paragraphs describing the mood and use cases>

Recommended for
<slash-separated use cases>

<timestamped tracklist in final order>

<hashtags line>

Tags:
<comma-separated tags without # symbols>

Localized metadata:
- Also write Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese title/description files.
- If the selected channel is sundaze, make the English file the default top-level title/description and approve with `--default-language en`.
- If the selected channel is Solwave Radio, make the Spanish file the default top-level title/description and approve with `--default-language es`.
- If the selected channel is HaruHaru, make the Korean file the default top-level title/description and approve with `--default-language ko`.
- If the selected channel is Storylight OST, Cinematic Pulse, Club Bloom, The Old Verse, or The New Verse, make the English file the default top-level title/description and approve with `--default-language en`.
- Use `--ko-title`, `--ko-description-file`, `--ja-title`, `--ja-description-file`, `--en-title`, `--en-description-file`, `--es-title`, `--es-description-file`, `--vi-title`, `--vi-description-file`, `--th-title`, `--th-description-file`, `--hi-title`, `--hi-description-file`, `--fil-title`, `--fil-description-file`, `--id-title`, `--id-description-file`, `--pt-title`, `--pt-description-file`, `--pt-pt-title`, `--pt-pt-description-file`, `--fr-title`, `--fr-description-file`, `--de-title`, `--de-description-file`, `--ar-title`, `--ar-description-file`, `--zh-title`, `--zh-description-file`, `--zh-tw-title`, and `--zh-tw-description-file` when approving metadata.

For a cafe piano playlist, use this direction:
- quiet solo piano
- cafe mood
- study, work, reading, relaxation
- warm and calm background music

Do not invent tracks that are not in the release.
Do not publish to YouTube.
After writing the metadata, approve it with scripts/openclaw-release approve-metadata.
```

## Command

Get release context and exact final-order timestamps:

```bash
scripts/openclaw-release metadata-context --release-id RELEASE_ID
```

Use the returned JSON:

- `release.title`
- `release.actual_duration_seconds`
- `timeline`
- `display_timestamp_lines`
- `timestamp_lines` as raw fallback only

Create the description file:

```bash
cat > /tmp/youtube-description.txt <<'EOF'
카페 한쪽에서 조용히 흐르는 듯한 잔잔한 솔로 피아노 플레이리스트입니다.

부드러운 건반 소리와 따뜻한 분위기의 피아노 곡들을 모아,
공부할 때, 작업할 때, 책을 읽을 때, 혹은 잠시 쉬고 싶을 때 편하게 들을 수 있도록 구성했습니다.

Recommended for
공부 / 작업 / 독서 / 휴식 / 카페 분위기 / 조용한 배경음악

00:00 Track One
03:20 Track Two
06:45 Track Three

#Piano #CafePiano #StudyMusic #WorkMusic #RelaxingMusic #SoloPiano
EOF
```

Approve the metadata:

```bash
scripts/openclaw-release approve-metadata \
  --release-id RELEASE_ID \
  --title "[playlist] 조용한 카페 피아노 솔로 40분 | 공부, 작업, 휴식할 때 듣기 좋은 잔잔한 음악" \
  --description-file /tmp/youtube-description.txt \
  --tags "Piano,CafePiano,StudyMusic,WorkMusic,RelaxingMusic,SoloPiano"
```

The JSON result should show:

- `metadata_approved: true`
- `workflow_state: publish_ready`
- `youtube_title`
- `youtube_description`
- `youtube_tags`

## After Metadata Approval

The human should return to the web UI, choose `Publish Channel`, then click `Approve Publish` or `Re-upload to YouTube`.
