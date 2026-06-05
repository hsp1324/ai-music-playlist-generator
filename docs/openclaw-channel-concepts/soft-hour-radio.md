# OpenClaw Channel Concept Planner: Soft Hour Radio

Use this after the selected channel is `Soft Hour Radio`. This document decides the next playlist concept. Use `../openclaw-channel-profiles/soft-hour-radio.md` afterward for cover, thumbnail, and short loop-video production rules.

## Channel Promise

Soft Hour Radio is now for long-listening solo piano BGM: study, work, reading, sleep, rest, cafe, focus, and calm background use.

The audience should immediately understand the practical listening use case.

Visual scenes can be specific, such as a pottery studio, greenhouse, library desk, cottage kitchen, or quiet workshop, but the public title and main description should stay broad enough for general listeners. Lead with useful situations like study, work, reading, writing, focus, rest, sleep, cafe, or calm handwork. Mention the niche scene only as visual atmosphere or a secondary detail unless the human explicitly asks for a niche title.

Before finalizing metadata, check the main title and every localized title in its own language. Reject titles that are just soft nouns or props glued together, such as `Warm Ceramic Morning Focus`, `Mug Steam Study Energy`, or literal equivalents that do not clearly say why someone should click. Prefer practical BGM promises like quiet study, cafe work, reading, rest, sleep, focus, or calm background music, rewritten naturally per language.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `Soft Hour Radio` releases and avoid repeating:

- The same use case, such as study, work, sleep, reading, rest, cafe, or focus.
- The same setting, such as rain, forest, ocean, fireplace, window, morning, late night, garden, or cottage.
- The same piano lane and setting combination, such as rainy reading felt piano, cafe work solo piano, sleep piano, morning focus piano, fireplace piano, or greenhouse study piano.
- The same thumbnail phrase, such as `CAFE PIANO`, `FOCUS MUSIC`, `DEEP SLEEP`, or `RAINY NIGHT`.
- The same visual scene if it was used recently.

If the latest 3 Soft Hour releases share the same setting, use case, tempo/energy, or thumbnail phrase, choose a different one. The instrument stays solo piano.

## Concept Lanes

Combine one use case, one setting, and one solo-piano lane:

Also follow [../openclaw-channel-genre-taxonomy.md](../openclaw-channel-genre-taxonomy.md). Make each video specific, such as rainy reading solo piano, cafe work piano, deep sleep felt piano, forest morning piano, quiet focus piano, or fireplace rest piano, while the app assigns it to a broader YouTube playlist bucket such as `Piano BGM`, `Sleep & Relax BGM`, or `Study & Focus BGM`.

- Study or work: clean solo piano, felt piano, warm room tone, steady low-fatigue phrasing.
- Reading or rest: rainy window solo piano, fireplace piano, slow melodic piano, quiet pedal resonance.
- Sleep: deep night felt piano, sparse left hand, very soft dynamics, resolved endings.
- Focus: forest morning piano, library desk piano, minimal repeating motif, no percussion.
- Cafe: afternoon counter solo piano, candle table piano, warm upright/felt piano, no jazz trio.
- Relaxation: moonlit room piano, garden-window piano, slow expressive solo piano, gentle cadence.

Do not choose lofi beats, Rhodes, guitar, strings, ambient pads, jazz trio, bossa, drums, percussion, or mixed-instrument BGM for new Soft Hour Radio work unless the human explicitly changes this rule later.

## Music Direction

- Instrumental/no-vocal by default.
- Solo piano only by default.
- Follow `../suno-v55-instrumental-format.md`.
- Use bracket-only Suno instrumental metatags in the lyrics/custom-lyrics field.
- The first roughly 10 minutes of every new Soft Hour playlist should be newly generated solo piano tracks. Use `solo piano`, `felt piano`, `upright piano`, `quiet piano`, or `calm piano` directly in every Suno style/settings field.
- Fill Suno Advanced Options excluded styles with vocal-related, artificial-noise, and non-piano arrangement exclusions: vocals, singing, humming, spoken word, lyrics, guitar, strings, pads, synth pads, Rhodes, electric piano, organ, bass, drums, beats, percussion, lofi beats, jazz trio, bossa, sax, flute, choir, orchestra.
- Do not force Soft Hour Radio tracks under 4 minutes, and do not use two-minute lower-bound wording in Suno fields. Prompt for around 4 minute full-length complete cues, then verify the downloaded duration. Longer complete tracks, including 5+ minute cues, are allowed.
- After the fresh 10-minute solo-piano block is uploaded, let the app reuse previous same-channel similar tracks for the remaining duration. Reuse is piano-first: previous Soft Hour solo-piano tracks should be selected before any fallback material. If there are not enough piano tracks to approach one hour, similar existing Soft Hour music may fill the remaining back half instead of blocking.
- Keep the newly generated solo-piano tracks at the beginning of the final render. If order randomization is used, it may shuffle the new solo-piano tracks among themselves, but the reused back-half tracks must stay after that fresh lead block.
- Prioritize low listener fatigue, smooth flow, and practical usefulness.

## Visual Direction

- No fixed mascot, fixed character count, or required walking composition.
- The scene should be restrained and useful for long listening.
- Use high-quality photorealistic real-world BGM imagery by default while keeping the established calm Soft Hour background feeling: quiet cafe, study desk, rain window, greenhouse, reading room, cottage, workshop, sleep room, or similar restful spaces.
- Use a completely static locked-off camera in the short loop. There should be no pan, zoom, dolly, handheld drift, camera breathing, or parallax camera movement.
- Use only subtle environmental motion that naturally belongs in the same photorealistic scene, such as rain on glass, cup steam, lamp flicker, curtain edge movement, dust in light, smoke, firelight, reflections, or leaves.
- Thumbnail text should name the use case or mood, not a vague poetic title.

## Good Fresh Concept Shapes

- `[playlist] 조용히 집중하고 싶을 때 듣는 피아노 BGM | 공부와 작업을 위한 솔로 피아노`
- `[playlist] Rainy Window Piano BGM | Soft Solo Piano for Reading and Quiet Work`
- `[playlist] 잠들기 전 틀어놓는 잔잔한 피아노 | 깊은 밤 휴식과 수면 BGM`
- `[playlist] Cafe Piano for Work | Calm Solo Piano Music for Focus and Reading`
- `[playlist] 따뜻한 방에서 쉬는 피아노 연주곡 | 독서, 휴식, 조용한 저녁 BGM`

## Bad Directions

- Vocal tracks unless the human explicitly asks.
- Non-piano Soft Hour tracks: guitar, Rhodes, strings, lofi beats, jazz trio, bossa, synth pads, ambient pads, drums, percussion, or mixed-instrument cafe BGM.
- Reusing the same solo piano cafe setting every time.
- Generic titles that do not include a use case.
- Titles that are too niche for discovery, such as leading with pottery, glazing, kiln rooms, or other craft-specific terms when the music is really general focus/work/rest BGM.
- Titles that read like translated keyword fragments instead of natural BGM copy.
- Visuals that are too busy, flashy, or character-driven for background listening.
