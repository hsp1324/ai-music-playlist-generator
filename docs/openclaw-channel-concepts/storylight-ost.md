# OpenClaw Channel Concept Planner: Storylight OST

## Prospective policy update — 2026-10-02

Read [audience-first image copy](../openclaw-thumbnail-copy-policy.md) and [Suno v6 generation/reuse](../openclaw-suno-v6-policy.md) before new work. Preserve existing songs, images, releases, jobs, and approved briefs; continue them unchanged. For new releases, bare genre labels are not primary image hooks; new songs use verified standard v6, reuse is v6-only except human-Good legacy tracks at the tail, and global shuffle must not defeat that order. Existing text-free defaults and routing exclusions remain in force.

New copy direction for this channel: `기분 좋은 게임 OST 모음` or `A Cozy Little Quest`. These are examples, not fixed slogans; keep the actual music promise and channel language truthful.
Use this after the selected channel is `Storylight OST`. This document decides the next playlist concept. Use `../openclaw-channel-profiles/storylight-ost.md` afterward for cover, thumbnail, and short loop-video production rules.

## Channel Promise

Storylight OST is a no-vocal Japanese-style game/anime OST, happy theme-park BGM, and playful background music channel.

Soft Hour Radio is practical cafe/study/rest BGM. Storylight OST should feel more playful, bright, mischievous, and game/anime-like: arcade games, fantasy games, cute RPG towns, anime side stories, mascot chases, item shops, magical menus, festival streets, happy amusement parks, theme-park parades, carousel plazas, school-game episodes, and light adventure scenes.

The audience should immediately understand: fun Japanese game/anime-style instrumental OST or feel-good amusement-park BGM that can be used for gaming, reading, light focus, mood boost, or playful background listening.

Titles should be broad, clickable, and listener-benefit-first. Lead with why someone should click or keep it on: feel-good energy, mood boost, happy background music, work focus, reading, gaming, cozy focus, relaxing, or light concentration. Game/anime-BGM identity should be clear, but exact scene names are usually description/thumbnail/tracklist material.

Do not make internal game-scene wording the main hook. `Bonus Stage Music`, `Item Shop BGM`, `Quest Board`, `Inventory Screen`, `Potion Counter`, and similar phrases are too narrow for the main title unless the human explicitly asks for that exact theme.

Before finalizing metadata, check the main title and every localized title in its own language. If a title reads like `bonus stage music`, `item shop music`, or another internal game mechanic instead of happy, cute, cozy, work, reading, gaming, or mood-boost listening, rewrite it with the listener benefit first in that language.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `Storylight OST` releases. Avoid repeating:

- The same fantasy location, such as forest village, castle road, magic train, lantern town, snowy inn, floating island, or moonlit ruins.
- The same adventure mood, such as cozy town, quest start, secret library, night market, healing forest, or final farewell.
- The same happy attraction setting, such as carousel plaza, parade street, ferris wheel, candy stand, or toy train.
- The same instrument palette, such as music box, harp, celesta, strings, flute, soft choir pads, piano, or orchestral swells.
- Repeating the same thumbnail hook or feeling; check recent copy under [the new copy policy](../openclaw-thumbnail-copy-policy.md).
- The same visual scene if used recently.

If the latest 3 Storylight releases share the same location or instrument lead, choose a different one.

## Concept Lanes

- Arcade game stage: chiptune accents, toy synths, bouncy drums, coin sounds, neon cabinets, bonus-stage energy.
- Cute fantasy RPG town: pizzicato strings, celesta, flute, marimba, light percussion, item shop, guild board, sunny plaza.
- Anime side-story BGM: playful piano, clarinet, bassoon, pizzicato strings, comedy timing, school hallway, mischievous errands.
- Magical menu or item shop: music box, mallets, plucks, tiny bells, soft synth bass, potion bottles, floating icons.
- Mascot chase or mini-game: fast staccato strings, xylophone, handclaps, cartoon percussion, silly sprint energy.
- Festival street or game market: shamisen/koto touches, taiko-lite rhythm, bright synths, lanterns, food stalls, crowd sparkle.
- Fantasy puzzle room: plucked harp, celesta, clockwork percussion, curious melody, keys, doors, tiny mechanisms.
- Happy amusement park or theme-park parade: music-box/calliope accents, glockenspiel, toy brass, bouncy drums, handclaps, carousel lights, ferris wheel, parade flags, candy stalls, confetti, bright mood-boost energy.

## Music Direction

- Instrumental/no-vocal by default.
- Storylight OST remains manual-only. For newly requested music, follow the standard-v6 policy: generate v6 songs and reuse only eligible v6 or explicit-Good legacy tail tracks. Existing releases/audio remain intact and continue normally.
- Create or select the Playlist Release first, then search existing app tracks with `scripts/openclaw-release search-tracks --q "storylight arcade game bgm"` or lane-specific keywords such as `cute fantasy RPG`, `anime game BGM`, `item shop`, `mini game`, `magical menu`, `playful OST`, `happy amusement park`, `theme park BGM`, `carousel`, `parade`, or `carnival`.
- Attach existing approved tracks with `scripts/openclaw-release reuse-track --release-id RELEASE_ID --track-id TRACK_ID`. Keep all selected tracks in one coherent lane; do not mix arcade, fantasy town, puzzle room, and dramatic OST cues just to reach a duration target.
- Existing approved Storylight-compatible tracks can be reused even when they are short, because the Suno credit has already been spent. Prefer stronger/full-length tracks when choosing between otherwise similar candidates, but do not block render or publish only because an already-made cue is under 1:00.
- If there are not enough matching tracks for the first concept, keep the selected concept and generate additional original same-lane Suno tracks until the new playlist meets the one-hour requirement in [openclaw-one-hour-new-audio-policy.md](../openclaw-one-hour-new-audio-policy.md). Do not switch lanes merely for catalog availability or use unrelated filler.
- Cover, thumbnail, and provider loop-video assets can still be newly generated for the selected recombination concept.
- When the human requests new Storylight music, use standard v6 and the bracket-only instrumental format; retain original lyrics-free structure and vocal/noise exclusions. The old format filename is not permission to select v5.5.
- Do not reference protected studios, franchises, characters, composers, songs, real theme parks, or specific artists in Suno or Dreamina prompts. Use safe generic wording such as `playful Japanese arcade-game OST`, `cute fantasy RPG BGM`, `anime side-story instrumental`, `kawaii game menu music`, `feel-good amusement park BGM`, `happy theme-park parade instrumental`, or `lighthearted game background music`.
- When the human requests new Storylight music, do not put duration caps or two-minute lower-bound wording into Suno fields unless the human explicitly asks for that exact wording. Build each bracket-only game/OST flow as a full cue meant to naturally land around 4 minutes or longer: intro motif, A section, B section, playful/developed variation, final theme return, and resolved ending. Tracks shorter than 4:00 are still valid uploads when they fit; only stop and report tracks under 1:00. Tracks under 2:00 are accepted but recorded for later analysis. Complete 5+ minute tracks are allowed.
- Music should be melodic, catchy, scene-rich, and loop-friendly without sounding like generic sleep music or mainstream vocal J-pop.

## Visual Direction

- Illustrated, anime, game-background, pixel-art-inspired, cel-shaded, colorful poster-art, or stylized fantasy-game look.
- Use strong scene identity: arcade cabinets, item shop, fantasy RPG plaza, magical menu, mini-game field, school-game hallway, festival street, amusement park plaza, carousel, ferris wheel, parade street, candy stall, puzzle room, toy-like dungeon, or bright quest map.
- Cover and loop video should feel like the first frame of a fun Japanese game/anime OST scene.
- Human or mascot characters are optional. If used, they should feel like small story/game figures inside the environment, not idol/pop thumbnails.
- New image copy follows [the audience-first policy](../openclaw-thumbnail-copy-policy.md): `기분 좋은 게임 OST 모음` or `A Cozy Little Quest`. Prefer one natural listener promise over a standalone genre label; text-free remains valid. Keep letters integrated directly on the artwork with no filled background.

## Good Fresh Concept Shapes

- `[playlist] Feel-Good Arcade BGM | Happy Game Music for Gaming, Work and Mood Boost`
- `[playlist] Cozy Fantasy Game BGM | Happy Music for Reading, Work and Gaming`
- `[playlist] Cute Game BGM for Work | Cozy Happy Music for Focus and Relaxing`
- `[playlist] Happy Anime Game BGM | Cheerful Music for Reading, Gaming and Work`
- `[playlist] Happy Theme Park BGM | Feel-Good Music for Work, Reading and Mood Boost`
- `[playlist] Carousel Parade BGM | Cute Happy Music for Gaming, Work and Good Mood`

## Bad Directions

- Cafe/study-only BGM that belongs on Soft Hour Radio.
- Epic battle/trailer music that belongs on Cinematic Pulse.
- Vocal pop, idol pop, J-pop songs with lyrics, K-pop, EDM, or Latin pop.
- Popular-song remakes, anime opening covers, or recognizable franchise soundtrack imitation.
- Protected IP, studio names, game titles, real theme-park names, character names, or `in the style of` wording.
- Titles that depend on narrow internal scene labels as the main hook, such as `Bonus Stage Music`, `Item Shop BGM`, `Inventory Screen`, `Quest Board`, or `Potion Counter`, when a broader mood/use-case title would be more clickable.
- Titles that sound like game-menu documentation instead of public-facing music discovery copy.
