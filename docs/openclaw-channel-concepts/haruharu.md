# OpenClaw Channel Concept Planner: HaruHaru

Use this after the selected channel is `HaruHaru`. This document decides the next playlist concept. Use `../openclaw-channel-profiles/haruharu.md` afterward for cover, thumbnail, and still-image render production rules.

## Channel Promise

HaruHaru is a Korean-language vocal channel centered on hipper Korean pop: K-pop hip-hop, rap-pop, Korean trap-pop, boom bap-influenced Korean pop, Korean R&B, neo-soul pop, and street-style Korean vocal tracks. Do not choose city-pop as the default new HaruHaru direction unless the human explicitly asks for that lane or an existing in-progress release is already clearly city-pop.

The audience should immediately understand: Korean vocal songs with rap/hip-hop/R&B attitude, strong hooks, and a modern street-style mood rather than generic idol K-pop.

Visual scenes can be specific, especially Hongdae street, record shops, small bars, late-night cafes, subway exits, street corners, parking lots, rainy crosswalks, or Itaewon night streets. The public Korean/default title should now lead with a short clickable emotional hook that feels like a real viewer thought or line of dialogue, then use the second half to explain the listening situation and genre.

Before finalizing metadata, read the Korean/default title as normal Korean YouTube copy and check every localized title in its own language. Reject direct keyword piles like `연습실 밤과 운동 에너지`, `Seoul Music`, `Korean Pop`, or any localized title that sounds like nouns pasted together. The title should feel like something local viewers would actually click: a slightly provocative but tasteful hook such as a crush, date, confidence, glow-up, getting-ready, night-out, breakup-revenge, or first-message line, followed by a truthful playlist promise.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `HaruHaru` releases and avoid repeating:

- The same scene, such as Seoul night walk, school hallway, rainy bus stop, Han River, rooftop, convenience store, beach trip, cafe date, or dance practice room.
- The same K-pop substyle, especially K-pop hip-hop, rap-pop, trap-pop, boom bap, Korean R&B, neo-soul pop, darker street-pop, or explicit city-pop. Do not choose city-pop for a new HaruHaru lane unless the human asked for it or the release is already a city-pop release that should be completed consistently.
- The same lyric premise, such as first confession, last text, missed timing, reunion, moving on, summer crush, or confidence glow-up.
- The same thumbnail phrase, such as `K-POP`, `SEOUL POP`, `DANCE POP`, `HEARTBREAK`, or `SUMMER KPOP`.
- Generic translated title shapes that do not say what the playlist is for.
- The same clickable hook shape. Do not repeat only `나랑 데이트 할래?` / date-beforegoing / confidence titles; rotate between crush, night-out, getting ready, breakup recovery, self-confidence, walk, drive, and weekend energy.

If the latest HaruHaru upload could be summarized by the same scene plus same emotion, choose a different concept.

## Concept Lanes

Use one broad Korean hip-hop/R&B listening promise plus one explicit detailed genre lane. Keep the whole release in that lane so the YouTube title, Suno prompts, style/settings, cover, thumbnail, and metadata all agree.

Also follow [../openclaw-channel-genre-taxonomy.md](../openclaw-channel-genre-taxonomy.md). HaruHaru videos should be more detailed than the broad YouTube playlist bucket: make separate videos for K-pop trap, K-pop boom bap, rap-pop, Korean R&B, Korean neo-soul, and dark street-pop. The app groups detailed hip-hop lanes such as trap and boom bap into the broad `K-pop Hip-Hop` YouTube playlist.

- K-pop hip-hop / rap-pop: confident hooks, rap verses, tight drums, cool night-out energy.
- K-pop boom bap: dusty but clean drums, head-nod groove, confident Korean rap-pop verses, modern sung hooks.
- K-pop trap / trap-pop: crisp 808s, hi-hats, darker Hongdae/Itaewon night-out confidence, melodic rap hooks.
- Korean R&B: smooth vocals, late-night romance, breakup recovery, warm bass, understated drums.
- Korean neo-soul / soul-pop: warm chords, mature vocals, relaxed groove, romantic tension, tasteful live-feel drums.
- Dark street-pop: moody Korean vocal hooks, half-rapped verses, minimal synth/bass, rain-night confidence.
- K-pop dance-pop / idol-pop, synth-pop, pop-rock, and ballad-pop are secondary lanes only. Do not select them when planning new HaruHaru work unless the human explicitly requests that sound.
- City-pop, city-pop influenced K-pop, and retro city-pop grooves are not the default HaruHaru direction anymore. Route Japanese city-pop to Tokyo Daydream Radio. If a HaruHaru release is explicitly city-pop or already in progress as city-pop, keep the whole release and any reused/backfill tracks city-pop-related; if the release is hip-hop, rap-pop, trap, R&B, neo-soul, street-pop, ballad, pop-rock, or another non-city-pop lane, do not add city-pop tracks or city-pop wording.

## Music Direction

- Original Korean lyrics are required by default.
- One release must stay in one clear genre lane such as K-pop hip-hop, rap-pop, K-pop trap, boom bap K-pop, Korean R&B, neo-soul pop, or dark street-pop. Do not make one playlist a vague mixed K-pop sampler unless the human explicitly asks.
- Put the selected genre lane in the release title and metadata in natural Korean, English, and localized equivalents. Examples of genre words to use when accurate: `K-POP 힙합`, `랩팝`, `K-POP 트랩`, `붐뱁 K-POP`, `Korean R&B`, `K-POP Neo Soul`, `스트릿 K-POP`.
- Korean/default YouTube title shape: `[playlist] 짧은 클릭 훅 | 상황에 듣기 좋은 장르 노래모음`. The first half should be a punchy natural Korean phrase or question, not a keyword list. The second half should say the real listening use case and genre, such as `데이트하기 전 기분 좋아지는 K-POP 힙합 노래모음`, `약속 전 자신감 올리는 K-POP 트랩 노래모음`, `홍대 나가기 전 듣기 좋은 랩팝 노래모음`, or `썸 타기 전 설레는 Korean R&B 노래모음`.
- Use mild YouTube-clickable tension without becoming misleading, explicit, insulting, or unrelated to the music. Good hook families: `나랑 데이트 할래?`, `오늘 좀 예뻐 보이고 싶어`, `전남친이 후회하게`, `너도 나 좋아하잖아`, `오늘은 내가 주인공`, `답장 오기 전까지`, `홍대 가기 전에 틀어줘`, `괜히 자신감 생기는 밤`.
- Every track needs a distinct Korean lyric concept, chorus hook, title, and Suno style/settings.
- Treat the playlist title/use case as packaging and energy direction, not as the required lyric topic. If the playlist is `댄스 연습실 K-POP`, the beat, tempo, confidence, and performance energy should fit dance practice, but the lyrics do not need to mention dance practice, mirrors, choreography, or working out.
- Write each song like a real standalone K-pop track: natural Korean phrasing, believable emotion, relationship tension, confidence, crush, breakup, comeback, night-out, youth, or self-belief. Avoid over-literal or cringe lyrics that repeat the YouTube title/use case.
- Match lyrics to the melody, beat, vocal tone, and hook first. Song quality is the first priority. A song can fit a workout/getting-ready playlist because of rhythm and energy, while the lyrics are about love, confidence, moving on, or a memorable pop story unrelated to the playlist title.
- Do not upload lyricless, BGM-only, hum-only, or instrumental K-pop unless the human explicitly requests it.
- Use Korean song titles by default. Avoid `A/B`, `1/2`, or batch labels in public track titles.
- Do not put duration caps or two-minute lower-bound wording into Suno fields unless the human explicitly asks for that exact wording. Prompt for an around 4 minute full-length complete Korean pop song with a natural intro, verse/pre-chorus/chorus flow, bridge or final chorus lift where useful, and resolved ending; regenerate or explicitly report tracks shorter than 1:00. Tracks under 2:00 are accepted but recorded for later analysis. Complete 5+ minute tracks are allowed.
- Set Suno `More options` / `Vocal gender` when the lead vocal is known: `male` for male lead, `female` for female lead, blank for mixed/duet/group/unspecified.
- Keep vocal gender stable across retries of the same track unless the track concept changes.
- Avoid generic idol-pop writing where every song has the same glossy dance-pop shape. Prefer rap verse/sung hook contrast, syncopated Korean phrasing, 808 or boom-bap drum identity, R&B bass movement, and distinct hook concepts per track.

## Visual Direction

- HaruHaru now uses photorealistic still-image visual packaging by default.
- Cover and thumbnail should follow the specific playlist concept, but they should look like natural lifestyle photos or casual friend-taken street snapshots rather than graphic posters, studio portraits, or fashion-campaign images.
- Default HaruHaru visuals to a clearly adult Korean/Korean-fashion woman in hip streetwear on or near a Hongdae street, record shop, late-night cafe, subway exit, small bar, alley corner, or rainy crosswalk. Handsome stylish men or tasteful adult couple/friend pairs are allowed when the concept supports it, but the default should be a hip adult woman with a friend-taken camera feel.
- The thumbnail/cover scene must match the clickable title hook. Dating or crush hooks should look like getting ready before a date, a Hongdae street meet-up, cafe exterior, or candid couple/friend moment. Confidence/glow-up hooks should show a stylish adult outfit, streetwear confidence, night-out energy, or a mirror-free candid going-out moment. Breakup-recovery hooks should feel cool and self-possessed, not sad stock imagery. Workout/running hooks should use movement-ready styling without turning into a gym ad.
- Do not prompt for hidden faces by default. Do not hide the face with hair, phone, sunglasses, crop, or turned-back poses unless the concept naturally calls for it. Also avoid tight straight-on face close-ups that feel like AI headshots; prefer three-quarter/side/candid angles, medium or farther framing, and enough environment to make the image feel real.
- Good scene families: Hongdae street at dusk, Hongdae record shop, club-side alley with neon signs, Itaewon evening street, Seoul subway exit, rainy crosswalk, convenience-store corner, rooftop after dark, small music bar, streetwear boutique, or late-night cafe exterior.
- For hip-hop, rap-pop, trap-pop, Korean R&B, or street-pop releases, use ordinary phone-photo details: stylish streetwear, oversized jacket, denim, leather jacket, cap/beanie when natural, crossbody bag, earphones, slight motion blur, imperfect focus, mild camera shake, realistic compression, candid side glance, and visible Seoul street context. A slightly out-of-focus or motion-soft thumbnail is acceptable if it still looks intentional and readable.
- Keep styling adult, fashionable, pretty/cool, and non-explicit. No minors, school uniforms, childlike styling, celebrity likenesses, nudity, fetish framing, or pornographic posing.
- Do not put logos, channel names, title text, style labels, badges, stickers, or typography on the image package by default.
- Do not create a moving loop video for normal HaruHaru releases. The release should render from the still cover image in the app.
- Plan the cover composition so the final app video can place the spectrum near the lower-right and lyrics near the lower-left without covering the face or important subject details. Do not bake spectrum bars or lyrics into the generated image.

## Good Fresh Concept Shapes

- `[playlist] 나랑 데이트 할래? | 데이트하기 전 기분 좋아지는 K-POP 힙합 노래모음`
- `[playlist] 오늘 좀 예뻐 보이고 싶어 | 약속 전 자신감 올리는 K-POP 트랩 노래모음`
- `[playlist] 전남친이 후회하게 | 외출 준비할 때 듣기 좋은 랩팝 노래모음`
- `[playlist] 너도 나 좋아하잖아 | 썸 타기 전 설레는 Korean R&B 노래모음`
- `[playlist] 오늘은 내가 주인공 | 홍대 나가기 전 듣는 붐뱁 K-POP 노래모음`

## Bad Directions

- Instrumental K-pop unless explicitly requested.
- Accidentally mixing city-pop, city-pop influenced K-pop, retro city-pop grooves, or title/style wording such as `시티팝`, `city pop`, `city-pop`, or `neon city-pop` into a non-city-pop HaruHaru release.
- If the human explicitly asks for a HaruHaru city-pop release or an existing in-progress release is already city-pop, filling it with hip-hop, R&B, ballad, or unrelated K-pop tracks instead of city-pop-related tracks.
- Generic idol-pop/dance-pop batches that make every song feel too similar.
- Lyrics that reuse the same chorus hook across multiple tracks.
- Lyrics that literally describe the playlist setting instead of working as a standalone song.
- Forcing title/use-case words such as `댄스 연습실`, `운동`, `산책`, `공부`, `드라이브`, or `외출 준비` into lyrics unless they naturally belong in the song.
- Titles like `KPOP Playlist`, `Korean Pop`, or `Seoul Music` by themselves.
- Titles that hide the genre lane. Avoid generic `K-POP 믹스` when the release is specifically hip-hop, R&B, dance-pop, synth-pop, soul, pop-rock, or ballad-pop.
- Titles that put only the genre first without a clickable Korean hook, such as `[playlist] K-POP 힙합 믹스 | 운동, 러닝, 자신감 충전`, unless a human explicitly asks for a more neutral SEO title.
- Clickbait that lies about the music, implies explicit/sexual content, humiliates a real person/group, or uses a hook that the thumbnail cannot support visually.
- Overly narrow visual-scene titles such as rooftop-after-rain, pottery-studio, exact street corners, or prop-first titles when the music is really a broad workout, running, getting-ready, party, heartbreak, or mood playlist.
- Titles that sound machine-translated or keyword-stuffed instead of natural Korean K-pop playlist copy.
- Concepts that sound like J-pop/Tokyo Daydream Radio or English pop/sundaze.
- Remake/cover concepts based on existing popular songs. HaruHaru is for original K-pop.
