# OpenClaw Channel Concept Planner: HaruHaru

Use this after the selected channel is `HaruHaru`. This document decides the next playlist concept. Use `../openclaw-channel-profiles/haruharu.md` afterward for cover, thumbnail, and still-image render production rules.

## Channel Promise

HaruHaru is a Korean-language K-pop vocal channel. It is for original K-pop, Korean dance-pop, idol-pop inspired tracks, Korean synth-pop, Korean pop-rock, bright romance pop, emotional breakup pop, and Seoul/Korea everyday-scene pop.

The audience should immediately understand: Korean vocal pop with lyrics, built around a mainstream emotion, energy level, or listening use case.

Visual scenes can be specific, such as Hongdae, Itaewon, a Seoul cafe street, seaside road, beach trip, rooftop, bus stop, rainy window, or Han River sunset, but the public title should usually be broader than the visual. Lead with searchable K-pop listening reasons such as workout, running, getting ready, party warmup, dance-pop, heartbreak, night drive, confidence boost, or feel-good K-pop. Mention a niche visual scene only when it is a strong mainstream hook.

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
- Do not put duration caps such as `less than 4 minutes` or `under 4 minutes` into Suno fields unless the human explicitly asks for that cap. Prompt for a full-length complete Korean pop song of at least 2 minutes with a natural intro, verse/pre-chorus/chorus flow, bridge or final chorus lift where useful, and resolved ending; regenerate or explicitly report tracks shorter than 2:00. Complete 5+ minute tracks are allowed.
- Set Suno `More options` / `Vocal gender` when the lead vocal is known: `male` for male lead, `female` for female lead, blank for mixed/duet/group/unspecified.
- Keep vocal gender stable across retries of the same track unless the track concept changes.

## Visual Direction

- HaruHaru now uses photorealistic still-image visual packaging by default.
- Cover and thumbnail should follow the specific playlist concept, but they should look like natural lifestyle photos or casual friend-taken travel snapshots rather than graphic posters, studio portraits, or fashion-campaign images.
- Use attractive clearly adult Korean/Korean-fashion lifestyle subjects: a stylish woman, handsome stylish man, or tasteful adult couple/friend pair. Faces may be visible, including natural side profile, three-quarter view, soft eye contact, or candid looking-away poses.
- Do not prompt for hidden faces by default. Do not hide the face with hair, phone, sunglasses, crop, or turned-back poses unless the concept naturally calls for it. Also avoid tight straight-on face close-ups that feel like AI headshots; prefer three-quarter/side/candid angles, medium or farther framing, and enough environment to make the image feel real.
- Good scene families: Hongdae cafe window, Itaewon evening street, Seoul cafe terrace, seaside road, beach walk, coastal overlook, flower garden, Han River sunset, rainy city crosswalk, rooftop, record shop, boutique, subway exit, summer travel photo, or quiet cafe street.
- For bright chill pop, groove pop, or feel-good K-pop, use ordinary phone-photo details: adult day-trip energy, flowers or a small bouquet when natural, wind-touched hair, relaxed smile/laugh, slight overexposure, imperfect crop, mild motion softness, and a non-studio background.
- Keep styling adult, fashionable, pretty/cool, and non-explicit. No minors, school uniforms, childlike styling, celebrity likenesses, nudity, fetish framing, or pornographic posing.
- Do not put logos, channel names, title text, style labels, badges, stickers, or typography on the image package by default.
- Do not create a moving loop video for normal HaruHaru releases. The release should render from the still cover image in the app.
- Plan the cover composition so the final app video can place the spectrum near the lower-right and lyrics near the lower-left without covering the face or important subject details. Do not bake spectrum bars or lyrics into the generated image.

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
