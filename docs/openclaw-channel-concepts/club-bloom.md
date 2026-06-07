# OpenClaw Channel Concept Planner: Club Bloom

Use this after the selected channel is `Club Bloom`. This document decides the next playlist concept. Use `../openclaw-channel-profiles/club-bloom.md` afterward for cover, thumbnail, and still-image render rules.

## Channel Promise

Club Bloom is a no-vocal club music channel: instrumental EDM, house, techno, trance, club, workout, night-drive, gaming, festival, and party-energy releases.

It fills the high-energy instrumental dance lane that is currently separate from sundaze pop, Tokyo J-pop, Solwave Latin pop, and HaruHaru K-pop.

The audience should immediately understand: modern no-vocal dance music for movement, nightlife, gaming, workout, driving, and party warmup.

Titles should be broad dance/EDM packaging first, with the exact genre or subgenre visible immediately after `[playlist]`. Use clear YouTube mix language such as `Progressive Trance x EDM Mix`, `Tech House Workout Mix`, `Hype Trap x EDM Mix`, `Melodic Techno Night Drive`, `Bass House Workout Mix`, or `Bass Boosted EDM & Electro House Mix`. Add one or two public listening hooks after the separator, using natural phrasing such as `Heavy EDM for Gaming & Night Drive`, `Running Beats and Club Bass`, or `Night Drive & Gaming Club Music`. Do not list three awkward use cases as the main title, do not use abstract keyword tails like `Gaming Night & Workout Energy`, and do not make narrow scene names the title hook unless the scene is also a strong public search phrase.

Before finalizing metadata, check the main title and every localized title in its own language. If any language turns the hook into the equivalent of `게임 밤과 운동 에너지`, `밤길, 게임 집중, 클럽 드라이브`, or another awkward noun chain, rewrite it for that audience. Keep the genre clear and use a natural club-mix promise with one or two situations.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `Club Bloom` releases and avoid repeating:

- The same dance lane, such as house, future house, dance-pop, festival EDM, techno-pop, night drive, workout, or gaming mix.
- The same venue/performance setting, such as beach-club adult female DJ/BJ deck, rooftop skyline adult female DJ set, packed nightclub booth, concert/festival main stage, warehouse rave, pool-party deck, open-air desert/mountain stage, yacht/harbor party, cyber club, gym event stage, highway/night-drive visual, or DJ booth.
- The same energy curve, such as warmup, peak-time, late-night, workout sprint, or chill-house.
- The same thumbnail phrase, such as `EDM MIX`, `HOUSE MUSIC`, `NIGHT DRIVE`, or `WORKOUT EDM`.
- The same visual scene if used recently.

If the latest Club Bloom release was generic neon club or night drive, choose a stronger venue-based adult female DJ/BJ performance setup next, such as beach club, rooftop skyline, concert/festival stage, warehouse rave, pool party, open-air stage, or cyber club.

## Club Style Lanes

Every Club Bloom playlist must choose one primary club style lane and stay inside that lane for the whole release. Do not make a generic all-purpose EDM playlist that mixes unrelated club subgenres. The visual concept, title, Suno style prompts, metadata, and thumbnail text should all match the selected lane.

Good style lanes:

- Deep house: smooth late-night groove, warm bass, clean four-on-the-floor, stylish lounge/club energy.
- Tech house: tighter drums, bouncy bassline, minimal vocal-free hooks, modern club floor momentum.
- Progressive house: emotional chord builds, wide synths, steady lift, euphoric but controlled energy.
- Future house: bright synth stabs, glossy sidechain pulse, clean drop energy without vocal chops.
- Melodic techno: darker hypnotic arps, pulsing kick, cinematic club atmosphere, neon/night visuals.
- Peak-time techno: harder kick, driving bass, warehouse/strobe energy, intense but clean.
- Trance / progressive trance: rolling bass, uplifting leads, long builds, highway/night-sky momentum.
- Big-room / festival EDM: big kicks, simple anthem leads, laser-stage energy, no crowd-chant vocals.
- Bass house: aggressive bass movement, punchy drums, darker club attitude.
- Electro house: sharp synth riffs, high-energy drops, retro-futuristic club feel.
- Garage / UK garage: shuffling rhythm, bouncy bass, late-night city movement, no vocal samples.
- Drum and bass / liquid DnB: fast breakbeats, rolling bass, liquid pads for running/gaming energy.
- Tropical house / beach club: warm percussion, sunset deck mood, light dance rhythm, no vocal hooks.
- Afro house: organic percussion, deep groove, hypnotic club pulse, no chant/vocal phrases.
- Synthwave club: retro neon arps, driving electronic drums, night-drive energy.
- Workout EDM: punchy instrumental club tracks optimized for running, gym, cycling, or sprint sets.
- Gaming dance mix: cyber/neon instrumental club music for arcade, racing, FPS, or fast focus.

## Music Direction

- Instrumental/no-vocal is mandatory. Do not create lyrics, sung hooks, vocal chops, chants, hype shouts, spoken-word tags, or vocal ad-libs for Club Bloom.
- Follow `../suno-v55-instrumental-format.md` for every Club Bloom track.
- In Suno advanced/excluded styles, add vocal and artificial-noise blockers such as `vocals, vocal, voice, singer, singing, lyrics, words, rap, spoken word, chant, chanting, humming, choir, crowd chant, vocal chops, acapella, topline, producer tag, white noise, static noise, vinyl crackle, record crackle, LP crackle, tape hiss, cassette hiss, analog hiss, noise floor, old record noise, dust noise, crackle, hiss`.
- Use bracketed instrumental arrangement cues only, for example `[Intro: kick and filtered bass]`, `[Build: rising synth arp]`, `[Drop: no-vocal bass house groove]`, `[Breakdown: pads and drums only]`.
- If the human asks for vocal dance-pop, route it to sundaze, HaruHaru, Tokyo Daydream Radio, or Solwave Radio depending on language/style instead of Club Bloom.
- Do not put duration caps or lower-bound duration phrases such as `less than 4 minutes`, `under 4 minutes`, `at least 2 minutes`, `minimum 2 minutes`, or `2 minutes or longer` into Suno fields unless the human explicitly asks for that wording. Prompt structurally for an around 4 minute full-length complete club track with a natural intro, groove development, breakdown/drop variation, and resolved ending. Tracks from 1:00 to 1:59 should be uploaded/used when they fit the release; only stop and report tracks under 1:00 unless the channel-specific workflow says otherwise. Complete 5+ minute tracks are allowed.
- Prioritize strong groove, clean drops, energy changes, and replayable rhythm inside the selected style lane.
- Avoid muddy mixes, overly long intros, generic mixed-genre EDM, and tracks that feel like unfinished loops.

## Visual Direction

- Illustrated/anime/stylized neon visuals. Avoid photorealistic/live-action club footage unless the human explicitly asks for photorealism.
- Visuals should communicate club/dance energy quickly through a concrete premium venue and performance action. Prefer an active adult female DJ/BJ or club-streamer performance scene over abstract neon: beach-club DJ deck, rooftop skyline DJ set, packed nightclub booth, concert/festival main stage, warehouse rave, pool-party deck, open-air desert/mountain stage, yacht/harbor party, neon city terrace, cyber club, or dance-floor crowd.
- Unless the human explicitly asks for a non-DJ concept, make the visual read as a beautiful adult female DJ/BJ performance through visible decks/mixer, performer, crowd, lighting rig, stage, or dance-floor action.
- Human figures are expected by default when the concept allows it. Use a stylish adult woman DJ/BJ with bold revealing club fashion, confident poses, glossy nightlife styling, and sexy high-energy club presence. Vary the subject, setting, camera, composition, crowd presence, outfit palette, venue type, and action so each release feels fresh.
- Keep adult nightlife imagery bold and revealing but YouTube-safe. Use daring club outfits, crop tops, metallic mini dresses, sheer outer layers, bikini-style festival tops, bodycon silhouettes, and dramatic stage lighting, but avoid full nudity, visible genitals, exposed nipples, sexual acts, minors, fetish framing, protected brands, or anything that looks unsafe or policy-risky.
- Thumbnail text should be direct and clickable: `EDM MIX`, `HOUSE MUSIC`, `NIGHT DRIVE`, `WORKOUT EDM`, `CLUB HITS`, `FESTIVAL EDM`, or `DANCE MIX`. The text is the hook; the image should sell the DJ/performance venue.

## Good Fresh Concept Shapes

- `[playlist] Progressive Trance x EDM Mix | Night Drive & Gaming Club Music`
- `[playlist] Bass House Workout Mix 2026 | Heavy EDM for Gaming & Night Drive`
- `[playlist] Tech House Workout Mix | Running Beats and Club Bass`
- `[playlist] Melodic Techno Night Drive | Dark Club Mix for Gaming`
- `[playlist] Festival EDM Mix | Big Room Drops for Party Warmup`

## Bad Directions

- Mainstream English pop that belongs on sundaze.
- Latin pop/reggaeton that belongs on Solwave Radio.
- K-pop/J-pop vocal releases.
- Cozy BGM, cinematic battle music, or fantasy OST music.
- Titles that read like keyword-stuffed use-case lists, such as `[playlist] Progressive Trance for Night Roads, Gaming Focus and Club Drive`.
- Titles that glue abstract nouns together after the separator, such as `[playlist] Bass House Club Mix | Gaming Night & Workout Energy`; this reads like a machine-translated keyword list, not a YouTube title.
- Titles that hide the EDM/house/trance/techno lane or sound like translated keywords instead of a real mix title.
