# OpenClaw Channel Concept Planner: HaruHaru

Use this after the selected channel is `HaruHaru`. This document decides the next playlist concept. Use `../openclaw-channel-profiles/haruharu.md` afterward for cover, thumbnail, and short loop-video production rules.

## Channel Promise

HaruHaru is a Korean-language K-pop vocal channel. It is for original K-pop, Korean dance-pop, idol-pop inspired tracks, Korean synth-pop, Korean pop-rock, bright romance pop, emotional breakup pop, and Seoul/Korea everyday-scene pop.

The audience should immediately understand: Korean vocal pop with lyrics, built around a mainstream emotion, energy level, or listening use case.

Visual scenes can be specific, such as a rooftop, Seoul street, practice room, bus stop, cafe, or rainy window, but the public title should usually be broader than the visual. Lead with searchable K-pop listening reasons such as workout, running, getting ready, party warmup, dance-pop, heartbreak, night drive, confidence boost, or feel-good K-pop. Mention a niche visual scene only when it is a strong mainstream hook.

Before finalizing metadata, read the Korean/default title as normal Korean playlist copy and check every localized title in its own language. Reject direct keyword piles like `연습실 밤과 운동 에너지`, `Seoul Music`, `Korean Pop`, or any localized title that sounds like nouns pasted together. The title should feel like something local viewers would actually click, using natural equivalents of 신나는 K-POP, 기분전환, 운동/러닝, 외출 준비, 밤 드라이브, 이별 감성, 설렘, 자신감, or party warmup when the music fits.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `HaruHaru` releases and avoid repeating:

- The same scene, such as Seoul night walk, school hallway, rainy bus stop, Han River, rooftop, convenience store, beach trip, cafe date, or dance practice room.
- The same K-pop substyle, such as bright idol dance-pop, synth-pop, pop-rock, R&B pop, city-pop influenced K-pop, acoustic ballad, or emotional breakup pop.
- The same lyric premise, such as first confession, last text, missed timing, reunion, moving on, summer crush, or confidence glow-up.
- The same thumbnail phrase, such as `K-POP`, `SEOUL POP`, `DANCE POP`, `HEARTBREAK`, or `SUMMER KPOP`.
- Generic translated title shapes that do not say what the playlist is for.

If the latest HaruHaru upload could be summarized by the same scene plus same emotion, choose a different concept.

## Concept Lanes

Use one broad K-pop listening promise plus one explicit K-pop genre lane. Keep the whole release in that lane so the YouTube title, Suno prompts, style/settings, cover, thumbnail, and metadata all agree.

- K-pop hip-hop / rap-pop: confident hooks, 808s, tight drums, cool night-out energy.
- Korean R&B pop: smooth vocals, late-night romance, breakup recovery, warm bass.
- K-pop dance-pop / idol-pop: bright hooks, performance energy, getting ready, party warmup.
- Korean synth-pop: city lights, night drive, neon emotion, polished vocal layers.
- Korean pop-rock: weekend, friends, confidence, guitar-driven uplift.
- K-pop soul / neo-soul pop: warm chords, mature vocals, relaxed groove, romantic tension.
- K-pop ballad-pop: emotional breakup, reunion, moving on, piano/guitar warmth.

## Music Direction

- Original Korean lyrics are required by default.
- One release must stay in one clear genre lane such as K-pop hip-hop, Korean R&B pop, dance-pop, synth-pop, pop-rock, soul/neo-soul pop, or ballad-pop. Do not make one playlist a vague mixed K-pop sampler unless the human explicitly asks.
- Put the selected genre lane in the release title and metadata in natural Korean, English, and localized equivalents. Examples of genre words to use when accurate: `K-POP 힙합`, `Korean R&B`, `댄스팝`, `신스팝`, `팝록`, `K-POP Soul`, `감성 발라드팝`.
- Every track needs a distinct Korean lyric concept, chorus hook, title, and Suno style/settings.
- Treat the playlist title/use case as packaging and energy direction, not as the required lyric topic. If the playlist is `댄스 연습실 K-POP`, the beat, tempo, confidence, and performance energy should fit dance practice, but the lyrics do not need to mention dance practice, mirrors, choreography, or working out.
- Write each song like a real standalone K-pop track: natural Korean phrasing, believable emotion, relationship tension, confidence, crush, breakup, comeback, night-out, youth, or self-belief. Avoid over-literal or cringe lyrics that repeat the YouTube title/use case.
- Match lyrics to the melody, beat, vocal tone, and hook first. Song quality is the first priority. A song can fit a workout/getting-ready playlist because of rhythm and energy, while the lyrics are about love, confidence, moving on, or a memorable pop story unrelated to the playlist title.
- Do not upload lyricless, BGM-only, hum-only, or instrumental K-pop unless the human explicitly requests it.
- Use Korean song titles by default. Avoid `A/B`, `1/2`, or batch labels in public track titles.
- Suno duration wording should be minimal: use only `less than 4 minutes` or `under 4 minutes` when a duration hint is needed. Do not add exact ranges, lower-bound targets, or any extra ending/completion wording to prompts, style strings, lyrics, or bracketed metatags. The helper allows playlist tracks up to 4:20 by default.
- Set Suno `More options` / `Vocal gender` when the lead vocal is known: `male` for male lead, `female` for female lead, blank for mixed/duet/group/unspecified.
- Keep vocal gender stable across retries of the same track unless the track concept changes.

## Visual Direction

- No fixed recurring visual signature yet.
- Cover, thumbnail, and loop video should follow the specific playlist concept.
- Rotate HaruHaru visual mode at roughly a 2:1 ratio: make two photorealistic adult fashion/lifestyle releases, then one illustrated/anime/stylized release, then repeat. Check recent HaruHaru releases before choosing so the channel does not drift away from this photorealistic-heavy pattern.
- Illustrated mode should stay anime/stylized, Korean pop-friendly, fashion-aware, bright, emotional, and readable at thumbnail size.
- Photorealistic mode should be high-quality, glossy, and click-stopping like a premium Korean pop/fashion thumbnail: clearly adult woman, face hidden or mostly obscured by side/back angle, hat, hair, sunglasses, phone, car frame, yacht railing, beach shade, or camera crop. Use fashion, beach, yacht, car, rooftop, night city, summer resort, or luxury lifestyle settings when they fit the music lane.
- Photorealistic styling may be alluring and show skin through tasteful swimwear, summer tops, backless dresses, shorts, or light white beachwear, but keep it non-explicit: no nudity, no visible nipples/genitals, no transparent clothing revealing intimate areas, no underwear-focus, no fetish framing, no sexual acts, no minors or teen-looking subjects, and no school-uniform/childlike cues.
- In photorealistic mode, the subject should feel adult, confident, pretty, stylish, and slightly mysterious rather than pornographic. The face can be unseen, side-profile, turned away, cropped, shaded by a hat, or blocked by props.
- Seoul/Korean setting cues are good when they fit the concept, but do not force Seoul landmarks into every release.
- Thumbnail text should be short and click-readable, and should name the selected genre lane when possible: `K-POP HIPHOP`, `K-R&B`, `DANCE POP`, `SYNTH POP`, `K-POP SOUL`, `POP ROCK`, `HEARTBREAK`, `SUMMER KPOP`, or `K-POP DRIVE`.

## Good Fresh Concept Shapes

- `[playlist] K-POP 힙합 믹스 | 운동, 러닝, 외출 준비, 자신감 충전`
- `[playlist] Korean R&B 플레이리스트 | 이별, 늦은 밤, 혼자 듣는 노래`
- `[playlist] 신나는 K-POP 댄스팝 | 여름, 첫사랑, 기분 좋아지는 노래`
- `[playlist] K-POP 신스팝 드라이브 | 밤길, 도시 불빛, 자신감 충전`

## Bad Directions

- Instrumental K-pop unless explicitly requested.
- Lyrics that reuse the same chorus hook across multiple tracks.
- Lyrics that literally describe the playlist setting instead of working as a standalone song.
- Forcing title/use-case words such as `댄스 연습실`, `운동`, `산책`, `공부`, `드라이브`, or `외출 준비` into lyrics unless they naturally belong in the song.
- Titles like `KPOP Playlist`, `Korean Pop`, or `Seoul Music` by themselves.
- Titles that hide the genre lane. Avoid generic `K-POP 믹스` when the release is specifically hip-hop, R&B, dance-pop, synth-pop, soul, pop-rock, or ballad-pop.
- Overly narrow visual-scene titles such as rooftop-after-rain, pottery-studio, exact street corners, or prop-first titles when the music is really a broad workout, running, getting-ready, party, heartbreak, or mood playlist.
- Titles that sound machine-translated or keyword-stuffed instead of natural Korean K-pop playlist copy.
- Concepts that sound like J-pop/Tokyo Daydream Radio or English pop/sundaze.
- Remake/cover concepts based on existing popular songs. HaruHaru is for original K-pop.
