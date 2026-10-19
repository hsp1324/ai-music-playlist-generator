# OpenClaw Channel Concept Planner: 불송

## Publishing schedule — effective 2026-10-19

Every channel publishes at most one video each Wednesday at 07:00 Asia/Seoul (Tuesday 22:00 UTC). This overrides all older daily, dual-slot, and branch-specific times below. Upload/render/metadata preparation may continue on other days; public publication must use the server-calculated weekly slot.
Cinematic Pulse shares ONE weekly channel slot: orchestra on 2026-10-21, cute_game on 2026-10-28, orchestra on 2026-11-04, alternating every week thereafter. Each lane therefore publishes every 14 days, always at 07:00. Set the exact lane; do not schedule two videos on the same Wednesday. Do not manually reintroduce daily timestamps. Follow `docs/openclaw-weekly-publishing.md`.

## Prospective policy update — 2026-10-02

Read [audience-first image copy](../openclaw-thumbnail-copy-policy.md) and [Suno v6 generation/reuse](../openclaw-suno-v6-policy.md) before new work. Preserve existing songs, images, releases, jobs, and approved briefs; continue them unchanged. For new releases, bare genre labels are not primary image hooks; new songs use verified standard v6, reuse is v6-only except human-Good legacy tracks at the tail, and global shuffle must not defeat that order. Existing text-free defaults and routing exclusions remain in force.

New copy direction for this channel: a text-free mainstream music image; put a hook such as `잡고 있던 걸 놓는 밤` in the title. These are examples, not fixed slogans; keep the actual music promise and channel language truthful.
Use this after the selected channel is `불송`. `불송` is a Korean vocal channel internally inspired by Buddhist sources/themes, but new releases should sound and read like accessible mainstream songs.

Mandatory vocal arrangement override: read
[../openclaw-vocal-arrangement-policy.md](../openclaw-vocal-arrangement-policy.md)
first. Every new 불송 vocal release uses exactly one of themed large-scale
orchestral vocal, piano-only vocal, or acoustic-guitar-only vocal. The legacy
rap/R&B/electronic lanes below guide Korean lyrics, delivery, discovery
packaging, and catalog labels only; they cannot add beat-led or full-band
accompaniment. The old mixed-lane reuse exception no longer applies.

## Channel Promise

불송 is for modern Korean vocal music that faithfully transforms Buddhist scripture into universal pop language. Every release must carry a concrete teaching from a verified Buddhist source; the instruction to avoid Buddhist vocabulary is only a wording rule, never permission to replace the teaching with generic breakup, comfort, or self-help lyrics. Keep the source/theme and source-to-lyric mapping in planning and app metadata, while sung lyrics and public metadata avoid Buddhist technical vocabulary unless the human explicitly requests a source-explicit release.

This is not a chanting archive, sermon channel, literal scripture-reading channel, trot channel, or old Korean cabaret-pop channel. OpenClaw should create modern lyric songs that communicate the emotional idea in accessible language. The internal source/theme is fixed, but the music lane and artwork should vary widely. Hip-hop/rap remains a strong lane, but OpenClaw should also explore R&B, quiet piano-only vocal songs, acoustic-guitar-only vocal songs, fresh Korean indie-acoustic pop, trip-hop, glitch-hop, drum and bass, hyperpop, art-pop, psychedelic soul, avant-jazz rap, dark pop, new-age electronica, cinematic trap, spoken-word rap, or other coherent modern lanes when they make the release feel fresh.

The audience should immediately feel: bold modern Korean songs with emotional depth, not old devotional music and not lyrics full of religious terms.

## Analytics-Driven Packaging Rules

- Treat 불송 as a modern Korean vocal channel with an internal Buddhist source/theme, not a generic meditation, worship, devotional, or temple BGM channel. Related-video discovery is currently important, so public wording must stay plain, searchable, and broad. For new mainstream releases, use labels such as `힙합`, `랩`, `R&B`, `트립합`, `아트팝`, or `밤에 듣는 노래`. Use source-heavy labels such as `불교 힙합`, `불경 힙합`, `법구경 힙합`, `반야심경 랩`, `Buddhist hip-hop`, or `Korean Buddhist rap` only when the human explicitly asks for legacy/source-explicit packaging.
- Make the Korean title sound like a current playlist recommendation, not a translated catalog label. Lead with a short conversational emotion or situation hook, then use a familiar listening phrase or broad genre after `|`. Do not put `한글 자막`, `한국어`, `Korean`, `Korean vocal`, `UK Garage`, `Korean UK Garage`, `2-step`, or similarly technical production/language labels in the Korean title unless the human explicitly asks. Keep narrow genre details in the description and tags when they are truthful. Prefer shapes such as `[playlist] 이제 진짜 안 돌아봐 | 새벽 귀가길 감성 R&B` or `[playlist] 오늘은 아무 말도 하기 싫어 | 혼자 걷는 밤에 듣는 노래`.
- Do not lead titles, thumbnail text, descriptions, or tags with obscure coined labels such as `다르마팝`, and do not overuse generic `meditation music`, `prayer`, `worship`, or devotional wording unless that is truthfully the finished asset's lane.
- The first track and first 10-20 seconds matter. Put the strongest same-lane hook, rap entry, vocal tone, or most immediately clickable song first. Avoid long slow instrumental intros on playlist lead tracks.
- Strong standout tracks should be considered for standalone singles and also reused as lead/funnel tracks in later same-lane playlists when appropriate.
- For playlist releases, use existing approved 불송 tracks that fit the same mainstream vocal family first, liked tracks first, then create enough additional same-family, same-theme Korean vocal Suno tracks to meet the one-hour policy. Rap, hip-hop, R&B, soul, and quiet piano vocal ballads may be mixed when the emotional mood works. Keep reused tracks after the fresh lead block. Do not add unrelated jazz, trot, guitar-folk/acoustic, cinematic, instrumental BGM, or generic meditation tracks just to hit one hour.

## Overnight Privacy Rule

Publish 불송 through the app normally. The app schedules 불송 uploads as public every Wednesday at 07:00 Asia/Seoul, unless the human explicitly pauses the channel.

## Source Material Direction

OpenClaw does not need to quote long scripture passages. Use short references, themes, and original paraphrase.

### Source-Fidelity Contract

- Select and verify one compact scripture passage or teaching before writing each song. Every track, not merely the playlist title or release description, must have a traceable Buddhist-source basis.
- Record an internal map for every track: `source_name`, `source_section_or_reference`, `core_teaching`, `ordinary_language_paraphrase`, and the planned verse/hook that carries it.
- Save that map as one JSON object per audio track using the exact keys `source_name`, `source_section_or_reference`, `core_teaching`, `ordinary_language_paraphrase`, and `verse_hook_expression`. Pass the matching file with `--bulsong-source-map-file` for each `--audio`. The app records missing or invalid maps as persistent quality warnings at upload and render time, but it must continue the pipeline and must never retry in a loop because of this check.
- Preserve the actual causal or ethical meaning. For example, transform teachings about anger continuing harm into a story about refusing to pass sharp words onward; transform attachment to praise or blame into a story about no longer building one's worth from another person's reaction; transform an unsettled mind shaping choices into a story where changing the next thought changes the next action.
- The banned vocabulary list is lexical only. Remove terms such as `자비`, `번뇌`, `불경`, `업`, `무상`, or `수행`, but keep their source meaning through ordinary actions, choices, consequences, relationships, and emotional change.
- Reject a lyric if the same words could have been written without reading the selected source. Generic lines about healing, letting go, being okay, or starting again are insufficient unless the verses and hook express the selected teaching's distinct logic.
- Do not invent a Buddhist claim or attribute a generic idea to a scripture. Verify the source, paraphrase in original words, and do not quote a modern copyrighted translation.

Good starting source lanes:

- Dhammapada / 법구경 internal themes: restless mind, anger, self-control, gentle speech, peace.
- Heart Sutra / 반야심경 internal themes: fear loosening, not clinging to labels, seeing a situation differently.
- Lotus Sutra / 묘법연화경 internal themes: persistence, someone slowly opening up, a hard day becoming bearable.
- Diamond Sutra / 금강경 internal themes: not holding too tightly, not building identity from praise/blame, giving without showing off.
- General internal themes: letting go, calmer speech, lighter steps, fewer grudges, starting again, softening the ego. In the sung lyric, express these as ordinary life/emotion, not Buddhist terminology.

If unsure where to start, use a Dhammapada-style internal theme sequence. Pick one compact theme section per release, not a whole scripture. Do not pretend to quote exact chapters if you did not verify the structure. For new mainstream releases, keep source names out of the public title and lyrics; store them in the release plan/metadata instead.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `불송` releases and avoid repeating:

- The same scripture/theme section.
- The same release-level music lane.
- The same thumbnail phrase.
- The same visual scene.
- The same visual lane, face/body type, prayer pose, Buddha close-up, outfit, camera angle, temple set, palette, or album-cover composition across the last 5 불송 releases when possible.

Every new plan must include a short `novelty_brief` that says why the music lane and visual lane are meaningfully different from recent 불송 uploads.

## Title Market Research Gate

Do this immediately before finalizing every 불송 YouTube title. A remembered trend or an old example in this document is not market research.

- Search current Korean YouTube playlist results with at least 3 release-relevant queries and inspect at least 8 recently active comparable videos. Match the actual listening lane and situation, such as Korean emotional R&B, late-night vocal playlists, Korean hip-hop for commuting, or quiet piano vocal songs.
- Record one JSON object with the exact fields `checked_at`, `queries`, `sampled_videos` (`title` and YouTube `url` per item), `observed_title_structures`, `overused_phrases_to_avoid`, `last_10_bulsong_titles_reviewed`, and `final_title_rationale`. Pass it through `--title-market-research-file` during metadata approval so the app can verify and retain the evidence.
- Extract patterns only. Never copy a competitor's full hook, distinctive phrase, typography, or emoji sequence. Current Korean playlist packaging often uses a short conversational confession/question, a concrete listening moment, and one familiar broad genre; apply the structure with original wording that fits the actual tracks.
- Compare against at least the last 10 불송 titles. Rotate among confession, question, scene, micro-story, and listener-intent hooks so `새벽`, `혼자 걷는`, `괜찮아`, `놓아`, or another successful phrase does not become a permanent template.
- Do not force slang such as `느좋`, exaggerated clickbait, decorative Unicode, or emojis merely because examples use them. Use current natural Korean that fits the channel and release.
- Keep specialist genres such as UK garage, 2-step, glitch-hop, or production terminology in the description/tags unless current research clearly shows that the intended Korean audience recognizes and clicks that term and the human has not prohibited it. `UK Garage` and `게러지` are prohibited in 불송 Korean titles under the current standing direction.
- If this evidence is missing, stale, or incomplete, the app records a persistent quality warning and still allows metadata approval and publishing to continue. Never invent trend claims, but do not stop the release or create a retry loop solely because live research is unavailable.

## Concept Lanes

- Boom bap: clear rhythm, Korean rap verses, sung hooks, warm bass, mellow drums, lyrics about the mind, choices, and easing anger in everyday language.
- Trap-soul: restrained 808s, modern rap cadence, spacious pads, reflective but still clearly hip-hop.
- Dark R&B: close vocal, low light, sparse drums, intimate hook, letting-go imagery without religious vocabulary.
- Trip-hop: downtempo drums, smoky bass, abstract texture, reflective spoken rap or sung hook.
- Glitch-hop: chopped percussion, digital fragments, clear vocal center, lyrics about change, illusion, or emotional release in ordinary language.
- Faster modern vocal energy may inform delivery privately, but do not select
  garage as a new release concept or public label. Stay inside the global
  orchestral-vocal, piano-only-vocal, or acoustic-guitar-only-vocal family.
- Hyperpop/art-pop: bright synthetic hooks, fragmented self-image themes, polished but not novelty comedy.
- Psychedelic soul / new-age electronica: surreal inner-world imagery, warm soul vocal or spoken rap, modern electronic texture.
- Avant-jazz rap: unusual chords, live-feeling drums, poetic Korean rap, but not old cabaret, trot, or lounge parody.
- Quiet piano vocal ballad: simple piano accompaniment, intimate Korean vocal, no beat drop, no drums required, and no long instrumental intro. This is a sung emotional song, not Soft Hour-style piano BGM or a no-vocal instrumental.
- Piano-only Korean vocal pop: vocals plus one acoustic/upright piano only. Exclude drums, percussion, bass, guitar, strings, orchestra, synths, pads, claps, snaps, and beat drops. Rotate between quiet ballad, lightly playful piano pop, and reflective singer-songwriter writing instead of making every track the same slow ballad.
- Acoustic-guitar-only Korean vocal pop: vocals plus one natural acoustic guitar only, using fingerpicking or light strumming. Exclude drums, percussion, bass, piano, electric guitar, strings, orchestra, synths, pads, stomp, and handclaps.
- Fresh Korean indie-acoustic pop: bright acoustic rhythm, clear distinctive vocals, conversational everyday language, concise hooks, and a light independent mood. The broader lane may use very light shaker, hand percussion, bass, or glockenspiel, but never call that arrangement `acoustic guitar only`.
- Use these general traits without naming or imitating a real singer, songwriter, song, melody, vocal identity, or lyric style in Suno fields. Every lyric must still preserve its verified Buddhist teaching through ordinary actions, choices, consequences, and emotion.

## Music Direction

- Vocal songs with original lyrics are the default.
- Korean lyrics are the default unless the human explicitly asks for another language.
- Every newly generated track in one release must stay inside one coherent emotional music family. Rap, hip-hop, R&B, soul, piano-only vocal songs, acoustic-guitar-only vocal songs, and fresh indie-acoustic pop can share one mainstream Korean vocal playlist when the mood and lyrics feel connected. If the public title names a narrow lane such as `붐뱁`, `트랩`, `트립합`, `피아노와 목소리만`, or `기타 한 대`, keep the entire new tracklist honest to that lane.
- Avoid trot, ppongjjak, and old Korean cabaret-pop completely unless the human explicitly asks for them. Do not use Korean trot rhythm, two-beat ppongjjak bounce, trot vocal ornaments, accordion/brass trot clichés, nightclub/cabaret trot arrangement, or old-TV trot mood.
- In Suno Advanced Options / excluded styles for 불송, include blockers such as `trot, Korean trot, ppongjjak, 뽕짝, 트로트, trot vocal, cabaret trot, old Korean trot, two-beat trot bounce, accordion trot, brass trot`.
- Use the vocabulary of the selected lane in Suno style prompts. For hip-hop: Korean hip-hop, mellow boom bap, Korean rap, spoken rap verses, sung hook. For R&B/trip-hop/electronic lanes: name the real lane, rhythm, instrument palette, and vocal texture clearly. Public titles, thumbnail phrases, descriptions, and tags must use plain audience-friendly wording, not obscure coined genre labels or source-explicit Buddhist labels.
- Lyrics should sound like real songs, not a lecture. Use images, hooks, and emotional arcs while keeping the internal theme clear without naming Buddhist terms.
- After drafting each lyric, compare it against the internal source map. The verses must dramatize the teaching and the hook must preserve its central meaning in ordinary Korean. Rewrite any song that only matches a broad mood.
- New default lyrics must avoid overt Buddhist vocabulary and scripture/source names. Do not put words such as `불교`, `불경`, `법구경`, `금강경`, `반야심경`, `법화경`, `경전`, `부처`, `부처님`, `보살`, `스님`, `법문`, `자비`, `가르침`, `업`, `업보`, `윤회`, `해탈`, `열반`, `사성제`, `팔정도`, `무상`, `무아`, `번뇌`, or `수행` in the sung Korean lyrics unless the human explicitly asks for them.
- Do not put duration caps or lower-bound duration phrases such as `less than 4 minutes`, `under 4 minutes`, `at least 2 minutes`, `minimum 2 minutes`, or `2 minutes or longer` into Suno fields unless the human explicitly asks for that wording. Build each 불송 prompt/lyrics file as a full song meant to naturally land around 4 minutes or longer. Use a distinct intro on only about one out of every five vocal tracks; start the rest directly with a verse, hook, chorus, rap verse, or brief vocal pickup. Develop the first and second verse/section flow, hook returns, bridge/breakdown or final lift, and resolved ending instead of using an intro to add length. Tracks shorter than 4:00 are still valid uploads when they fit. Tracks from 1:00 to 1:59 should be uploaded/used and recorded for later analysis; only stop and report tracks under 1:00 unless the channel-specific workflow says otherwise. Complete 5+ minute tracks are allowed.
- Do not block 불송 production on listening through a full first verse or a fixed 60-90 second QC pass. Use lightweight vocal sanity checks instead: make the Suno setup clearly vocal/lyrics-based, avoid instrumental/no-vocal options, and reject/regenerate only when the preview, metadata, or a quick spot check makes it obvious that the result is not a usable vocal/rap track.
- In no-intro tracks, do not substitute two to four sung setup lines, humming, spoken count-ins, or an unlabelled guitar/piano lead-in before the real first verse. Start the actual song section immediately.
- Do not copy long scripture text, modern translations, temple liturgy, or chants.
- Avoid naming living teachers, temples, sectarian claims, protected songs, or specific artist styles.
- Keep the tone respectful, contemplative, modern, and broadly accessible.

## Visual Direction

- Use a mainstream Korean-song visual identity. The Buddhist source/theme remains internal and must not determine public artwork unless the human explicitly requests source-explicit packaging.
- Do not use previous 불송 release images as references for new cover/thumbnail/still-image work. Start from a fresh text prompt and check recent releases so the face, pose, setting, outfit, camera angle, and color palette visibly change. Use a current release cover as reference only to derive that same release's thumbnail.
- Read the verified source-to-lyric map, strongest hooks, shared emotional arc, real genre/arrangement, public title promise, season, and listening context before choosing the artwork. The visible scene should express the ordinary human meaning of the teaching without showing religious vocabulary or objects.
- Draft at least three candidates from different visual families. For each candidate, record the hero subject, visible action or tension, setting, medium, palette, composition, source/lyric connection, and honest reason a viewer would become curious. Three versions of the same portrait do not count.
- Check at least the latest eight 불송 covers when available. Avoid repeating the same human type, pose, setting, dominant color, camera distance, hero object, or metaphor. A repeat should trigger one redesign, not block the release or create an infinite retry loop.
- Rotate mainstream packages aggressively: photorealistic street/lifestyle scenes, R&B city nights, rooms or cars, relationship tension, dark fashion editorial, cinematic city stills, surreal nonreligious symbols, cyber/glitch imagery, anime/illustrated modern music art, premium still life, object-led album art, designed environments, or bold graphic album-cover realism.
- Photorealistic, premium cinematic-real, anime, painterly, surrealist, psychedelic, glitch, and mixed-media imagery are all valid when the visual lane fits the song. Do not use exact living-artist names in prompts.
- There is no default face, pose, location, or beauty-portrait lane. People are optional, but a single adult lead should default to a clearly adult woman unless the human explicitly requests otherwise. A couple, friends, group, partial figure, or silhouette may be used when the lyrics need them. Never add an attractive woman merely as generic decoration; her action, setting, and emotion must come from concrete lyric evidence.
- Select the final concept by lyric/source truthfulness, audio fit, emotional specificity, small-thumbnail clarity, contemporary visual quality, recent novelty, and a non-misleading click reason. Reject generic stock-photo, generic AI-beauty, generic anime-character, and decorative abstract results that have no song-specific idea.
- Avoid Buddha statues/faces, temples, monks, prayer poses, lotus, mandala, sutra pages, prayer beads, Dharma wheels, incense, shrines, scripture text, and other Buddhist-looking cues by default. A source-explicit visual is allowed only when the human explicitly asks for it.
- Cover, YouTube thumbnail, first-frame, and still-image render source must feel like one text-free, click-stopping mainstream song package. Keep phrases such as `삼도 힙합`, `법구경`, `법구경 힙합`, `불경 힙합`, `마음챙김 랩`, `자비 힙합`, or `반야심경 랩` out of new public metadata and artwork unless the human explicitly asks for source-explicit wording in the current request.
- Do not create a separate channel-branded thumbnail for 불송. Reuse the same cover/first-frame package as the YouTube thumbnail or pass `--allow-cover-as-thumbnail` when using the helper.

## Good Fresh Concept Shapes

- `[playlist] 오늘은 조금 가벼워져 | 흔들리는 밤에 듣는 힙합 노래`
- `[playlist] 말이 날카로워질 때 | 마음을 식혀주는 R&B 노래`
- `[playlist] 잡고 있던 걸 놓는 밤 | 혼자 걷기 좋은 트립합`
- `[playlist] 화가 가라앉을 때까지 | 조용히 듣는 붐뱁 랩`
- `[playlist] 괜찮아지는 연습 | 새벽에 듣는 어두운 소울`
- `[playlist] 다시 웃을 수 있게 | 지친 하루 끝의 아트팝`
- `[playlist] 내일은 덜 아프게 | 밤공기에 어울리는 랩과 R&B`
- `[playlist] 괜찮아질 때까지 | 피아노에 기대어 듣는 잔잔한 노래`
- `[playlist] 오늘은 조금 가볍게 | 상쾌한 인디 어쿠스틱`
- `[playlist] 기타 한 대로 충분한 마음 | 담백한 보컬 노래`
- `[playlist] 피아노와 목소리만 남은 밤 | 조용히 중심을 찾는 노래`

## Bad Directions

- Generic meditation BGM with no lyrics or teaching.
- Generic comfort, breakup, or self-help lyrics that have no specific traceable relationship to the selected scripture teaching.
- Literal scripture reading, chanting, or sermon format.
- Randomly mixing unrelated jazz, cinematic pop, instrumental BGM, and meditation tracks into one release. Guitar/piano acoustic material is allowed only as the approved lyric/vocal lanes above and must remain a coherent 불송 song package with verified source meaning.
- Using obscure coined genre labels in YouTube titles, thumbnail phrases, descriptions, or tags instead of plain public wording for the real lane.
- Repeating the same Buddhist hip-hop beat, same visual subject, same face/pose, or same devotional statue/temple image because it is familiar.
- Any trot, ppongjjak, cabaret trot, old-TV trot, or accordion/brass trot feel.
- Copying long translated sutra passages.
- Using Buddhist words as decoration in public lyrics, titles, or tags. New default releases should carry the idea without saying the religious terms.
- Forcing private visibility or bypassing the app's daily 07:00 Asia/Seoul schedule without an explicit human pause.
