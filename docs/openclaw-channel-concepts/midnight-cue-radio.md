# OpenClaw Channel Concept Planner: Midnight Cue Radio

Use this after the selected channel is `Midnight Cue Radio`, or while the connected channel still appears as legacy `AI썰전`. This document decides the next playlist concept. Use `../openclaw-channel-profiles/midnight-cue-radio.md` afterward for cover, thumbnail, and 10 second loop-video production rules.

## Channel Promise

Midnight Cue Radio is a cinematic mystery/storytelling BGM channel. It makes instrumental background music for mystery videos, documentary narration, investigation stories, urban legends, dark essays, thriller writing, noir scenes, and late-night focus.

The audience should immediately understand: dark cinematic instrumental music for stories, mysteries, and documentaries.

This is not a talk/debate channel yet. The current AI Music app automation is built for music releases, so this channel should produce one-hour instrumental playlists rather than narrated videos until a separate narration/video pipeline exists.

## Rename Requirement

The connected YouTube channel currently appears as `AI썰전`. The recommended public channel name is:

```text
Midnight Cue Radio
```

OpenClaw should use `Midnight Cue Radio` as the visual brand label and metadata channel identity. If `/youtube/status` still shows `AI썰전`, treat it as the same connected channel until the human manually renames/reconnects it.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `Midnight Cue Radio` or `AI썰전` releases and avoid repeating:

- The same story lane, such as cold case, urban legend, abandoned place, conspiracy mood, space mystery, ancient ruins, cyber investigation, courtroom tension, or haunted road.
- The same musical palette, such as low piano, ticking percussion, string ostinato, analog drones, noir jazz, granular pads, or pulse synths.
- The same thumbnail phrase, such as `MYSTERY`, `DARK CASE`, `NOIR`, `INVESTIGATION`, `URBAN LEGEND`, or `DOCUMENTARY`.
- The same visual scene, such as red evidence board, rainy alley, old archive room, surveillance screens, forest road, empty train station, or moonlit ruins.

If the latest releases all lean horror, choose investigation/noir/documentary next. If they all lean detective, choose space/ancient/urban legend next.

## Concept Lanes

Combine one storytelling use case, one scene, and one instrumental palette:

- Mystery documentary: archive room, low piano, soft strings, distant tape noise.
- Investigation/cold case: evidence board, muted pulse synth, ticking percussion, tense bass.
- Urban legend: empty road, dark ambient pads, eerie bells, slow percussion.
- Noir city: rainy alley, brushed drums, upright bass, muted trumpet textures, piano.
- Space mystery: dark sky, analog drones, slow arps, deep sub pulses.
- Ancient ruins: stone corridor, low choir-like synths without vocals, frame drums, bowed strings.
- Cyber investigation: monitor glow, glitch pulses, cold synth bass, sparse piano.
- Late-night writing/focus: dim desk, steady pulse, minimal piano, low ambient texture.

## Music Direction

- Instrumental/no-vocal by default.
- Follow `../suno-v55-instrumental-format.md`.
- Use bracket-only Suno instrumental metatags in the lyrics/custom-lyrics field.
- Fill Suno Advanced Options excluded styles with vocal-related exclusions.
- Target roughly 3:00-3:30 per track; returned tracks up to 4:45 are acceptable when they end cleanly, but do not intentionally ask for long tracks. Do not use fade-out endings; prefer a natural final cadence or resolved ending.
- Prioritize tension, atmosphere, and repeat listening. Avoid jump-scare sound design that becomes annoying over one hour.
- Do not use existing movie, game, anime, TV, crime victim, celebrity, or franchise names. Keep concepts original and generic.

## Visual Direction

- No fixed recurring character or mascot.
- Use cinematic illustrated/stylized visuals: archive rooms, noir streets, evidence boards, foggy roads, abandoned stations, observatory rooms, ruins, maps, tape recorders, files, monitors, or symbolic mystery objects.
- Avoid gore, real victims, real crime evidence, weapons pointed at people, minors in danger, or explicit violent scenes.
- Thumbnail text should be short and strong: `MYSTERY`, `DARK CASE`, `NOIR`, `INVESTIGATION`, `URBAN LEGEND`, `DOCUMENTARY`, `COLD CASE`, or `NIGHT FILES`.

## Good Fresh Concept Shapes

- `[playlist] Midnight Mystery Documentary BGM | Dark Cases, Archives and Investigation Music`
- `[playlist] Noir Investigation BGM | Rainy City, Cold Clues and Late Night Focus`
- `[playlist] Urban Legend Dark Ambient | Empty Roads, Strange Lights and Story Music`
- `[playlist] Ancient Ruins Mystery BGM | Lost Temples, Maps and Documentary Tension`

## Bad Directions

- Narrated videos, debate shows, or AI commentary until the app has a separate narration/video pipeline.
- Pop vocals or lyric-based songs.
- True-crime content that names real victims, suspects, or ongoing cases.
- Horror visuals that look graphic, exploitative, or too shocking for background listening.
- Generic titles like `Mystery Music`, `Dark BGM`, or `Cinematic Playlist` by themselves.
