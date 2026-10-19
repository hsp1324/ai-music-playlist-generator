# OpenClaw Seasonal And Country Programming

## Publishing schedule — effective 2026-10-19

Every channel publishes at most one video each Wednesday at 07:00 Asia/Seoul (Tuesday 22:00 UTC). This overrides all older daily, dual-slot, and branch-specific times below. Upload/render/metadata preparation may continue on other days; public publication must use the server-calculated weekly slot.
Cinematic Pulse shares ONE weekly channel slot: orchestra on 2026-10-21, cute_game on 2026-10-28, orchestra on 2026-11-04, alternating every week thereafter. Each lane therefore publishes every 14 days, always at 07:00. Set the exact lane; do not schedule two videos on the same Wednesday. Do not manually reintroduce daily timestamps. Follow `docs/openclaw-weekly-publishing.md`.

Read this document before choosing any channel's next release concept. It applies to vocal and instrumental channels. Channel concept/profile documents still control musical identity and visual execution.

## Planning Context

Plan for the intended public date in the audience's local time, not merely the date when Suno generation starts. Record these fields before production:

- `planning_date`
- `intended_public_date`
- `target_market`
- `target_timezone`
- `seasonal_window`
- `event_or_holiday`
- `event_date`
- `lead_time_days`
- `seasonal_relevance`

Use the target market rather than the operator's location. Default market anchors are Korea for HaruHaru and 불송, Japan for Tokyo Daydream Radio, United States/global English for sundaze, a deliberately selected Spanish-speaking market or broader Latin audience for Solwave Radio, and global audiences for Soft Hour Radio, Club Bloom, Cinematic Pulse, and BibliaCanto. A global channel may still choose one explicit country when the concept genuinely benefits from it.

When internet access is available, verify changing dates, national holidays, school breaks, shopping periods, and current cultural events against official calendars or reliable local sources. Do not rely on memory for a date-sensitive concept. If reliable verification is unavailable, use a broad meteorological season and do not claim an exact holiday or event.

## Selection Rules

- Major annual windows such as Christmas, New Year, peak summer, and year-end can start 14-35 days before the date.
- Short public holidays and local observances normally need a 5-14 day lead.
- Seasonal lifestyle concepts such as beach travel, rainy season, back-to-school, autumn reading, or winter commuting can run for 2-8 weeks when locally relevant.
- Shopping and event-weekend concepts such as Black Friday should normally publish 3-14 days before the useful listening window.
- Do not publish an expired event concept unless it is explicitly retrospective.
- Do not force every upload to be seasonal. Balance timely releases with evergreen concepts and reject a weak calendar hook.
- Treat memorial days, religious observances, disasters, elections, and sensitive national events respectfully. Do not turn solemn events into casual commercial playlist hooks.

## Music And Lyrics

Seasonal programming is a release-level mood and listening context, not a command to repeat the event name in every song.

- Vocal seasonal specials may deliberately combine 4-7 compatible genres within one playlist, such as hip-hop, R&B, indie pop, synth-pop, neo-soul, acoustic pop, dance-pop, or locally relevant styles. Hold the release together with a clear energy curve, audience, vocal palette, and emotional arc.
- This is an intentional exception to a channel's normal one-genre-per-release rule. Do not make a random sampler: every transition still needs to feel plausible.
- Give every new vocal track its own singer identity, hook, story, tempo, and arrangement.
- Only a minority of tracks, normally no more than 25-35%, should literally name the holiday, vacation, beach, shopping event, weather, or season. The rest should work as standalone songs through relationships, confidence, anticipation, release, memory, friendship, movement, or everyday stories that suit the atmosphere.
- Do not repeat the same seasonal nouns in every chorus. A summer playlist is not a collection of songs all about swimming; a Christmas playlist is not a collection of songs all repeating Christmas.
- Instrumental playlists may vary orchestral, electronic, acoustic, rhythmic, and ambient palettes when the selected channel allows them. Unite them through tempo, emotional flow, instrumentation, and listening use rather than gimmicky event sound effects.
- Metadata may state the timely listening use more directly than the lyrics. Keep every public claim truthful to the audio.

## Visual Direction

- Make covers and thumbnails contemporary, editorial, and immediately legible on mobile.
- Use a modern lifestyle photograph, premium illustration, cinematic still, or tasteful object-led composition appropriate to the channel.
- Suggest the season through light, clothing, location, materials, weather, color relationships, and human activity before using literal symbols.
- Avoid clip-art holiday icons, stock-looking collages, giant calendar graphics, novelty fonts, flags used as decoration, excessive red-and-green Christmas styling, and deliberately aged or distressed layouts that read as kitsch.
- Preserve the channel's established visual system. Seasonal relevance changes the scene and details; it does not erase channel identity.

## Final Check

Before creating Suno tracks or image assets, confirm:

1. The concept will still be timely on its intended public date in the target market.
2. The event is appropriate for entertainment programming.
3. The genre palette is varied but musically coherent.
4. Most lyrics are natural standalone songs rather than literal event copy.
5. The cover communicates the mood without dated seasonal clichés.
