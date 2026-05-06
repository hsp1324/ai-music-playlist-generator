# OpenClaw Channel Concept Planner: Soft Hour Radio

Use this after the selected channel is `Soft Hour Radio`. This document decides the next playlist concept. Use `../openclaw-channel-profiles/soft-hour-radio.md` afterward for cover, thumbnail, and 10 second loop-video production rules.

## Channel Promise

Soft Hour Radio is for long-listening BGM: study, work, reading, sleep, rest, cafe, focus, and calm background use.

The audience should immediately understand the practical listening use case.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `Soft Hour Radio` releases and avoid repeating:

- The same use case, such as study, work, sleep, reading, rest, cafe, or focus.
- The same setting, such as rain, forest, ocean, fireplace, window, morning, late night, garden, or cottage.
- The same instrument palette, such as solo piano, felt piano, acoustic guitar, Rhodes, strings, lofi drums, or ambient pads.
- The same thumbnail phrase, such as `CAFE PIANO`, `FOCUS MUSIC`, `DEEP SLEEP`, or `RAINY NIGHT`.
- The same visual scene if it was used recently.

If the latest 3 Soft Hour releases share the same primary instrument or setting, choose a different one.

## Concept Lanes

Combine one use case, one setting, and one instrument palette:

- Study or work: cafe piano, Rhodes, soft lofi drums, warm room tone.
- Reading or rest: rainy window, fireplace, soft acoustic guitar, quiet strings.
- Sleep: deep night, ocean room, slow felt piano, ambient pads.
- Focus: forest morning, library desk, gentle guitar, minimal percussion.
- Cafe: afternoon counter, candle table, solo piano, upright bass, brush drums.
- Relaxation: garden path, moonlit room, curtains, harp, soft synth textures.

## Music Direction

- Instrumental/no-vocal by default.
- Follow `../suno-v55-instrumental-format.md`.
- Use bracket-only Suno instrumental metatags in the lyrics/custom-lyrics field.
- Fill Suno Advanced Options excluded styles with vocal-related exclusions.
- Target roughly 3:00-3:30 per track; returned tracks up to 4:20 are acceptable, but do not intentionally ask for 4-minute tracks.
- Prioritize low listener fatigue, smooth flow, and practical usefulness.

## Visual Direction

- No fixed mascot, fixed character count, or required walking composition.
- The scene should be restrained and useful for long listening.
- Use calm but clearly visible environmental motion in the 10 second loop.
- Thumbnail text should name the use case or mood, not a vague poetic title.

## Good Fresh Concept Shapes

- `[playlist] Rainy Window Reading BGM | Calm Piano and Soft Room Ambience`
- `[playlist] Forest Morning Focus Music | Gentle Guitar, Air and Warm Light`
- `[playlist] Ocean Room Sleep BGM | Slow Felt Piano and Deep Night Rest`
- `[playlist] Fireplace Work BGM | Soft Acoustic, Warm Room and Focus`

## Bad Directions

- Vocal tracks unless the human explicitly asks.
- Reusing solo piano cafe every time.
- Generic titles that do not include a use case.
- Visuals that are too busy, flashy, or character-driven for background listening.
