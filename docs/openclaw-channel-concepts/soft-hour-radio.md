# OpenClaw Channel Concept Planner: Soft Hour Radio

## Publishing schedule — effective 2026-10-19

Every channel publishes at most one video each Wednesday at 07:00 Asia/Seoul (Tuesday 22:00 UTC). This overrides all older daily, dual-slot, and branch-specific times below. Upload/render/metadata preparation may continue on other days; public publication must use the server-calculated weekly slot.
Cinematic Pulse shares ONE weekly channel slot: orchestra on 2026-10-21, cute_game on 2026-10-28, orchestra on 2026-11-04, alternating every week thereafter. Each lane therefore publishes every 14 days, always at 07:00. Set the exact lane; do not schedule two videos on the same Wednesday. Do not manually reintroduce daily timestamps. Follow `docs/openclaw-weekly-publishing.md`.

## Prospective policy update — 2026-10-02

Read [audience-first image copy](../openclaw-thumbnail-copy-policy.md) and [Suno v6 generation/reuse](../openclaw-suno-v6-policy.md) before new work. Preserve existing songs, images, releases, jobs, and approved briefs; continue them unchanged. For new releases, bare genre labels are not primary image hooks; new songs use verified standard v6, reuse is v6-only except human-Good legacy tracks at the tail, and global shuffle must not defeat that order. Existing text-free defaults and routing exclusions remain in force.

New copy direction for this channel: `A Quiet Place to Focus` or `Piano for a Slow Morning`. These are examples, not fixed slogans; keep the actual music promise and channel language truthful.
Use this after the selected channel is `Soft Hour Radio`. This document decides the next playlist concept. Use `../openclaw-channel-profiles/soft-hour-radio.md` afterward for cover, thumbnail, and short loop-video production rules.

## Channel Promise

Soft Hour Radio is for long-listening piano BGM in two equal lanes: the existing calm real-world solo-piano package and original Japanese anime/game OST-style piano music. Both lanes serve study, work, reading, sleep, rest, cafe, focus, gentle adventure, and calm background use.

The audience should immediately understand the practical listening use case.

Visual scenes can be specific, such as a pottery studio, greenhouse, library desk, cottage kitchen, or quiet workshop, but the public title and main description should stay broad enough for general listeners. Lead with useful situations like study, work, reading, writing, focus, rest, sleep, cafe, or calm handwork. Mention the niche scene only as visual atmosphere or a secondary detail unless the human explicitly asks for a niche title.

Before finalizing metadata, check the main title and every localized title in its own language. Reject titles that are just soft nouns or props glued together, such as `Warm Ceramic Morning Focus`, `Mug Steam Study Energy`, or literal equivalents that do not clearly say why someone should click. Prefer practical BGM promises like quiet study, cafe work, reading, rest, sleep, focus, or calm background music, rewritten naturally per language.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `Soft Hour Radio` releases and avoid repeating:

- The same use case, such as study, work, sleep, reading, rest, cafe, or focus.
- The same setting, such as rain, forest, ocean, fireplace, window, morning, late night, garden, or cottage.
- The same piano lane and setting combination, such as rainy reading felt piano, cafe work solo piano, sleep piano, morning focus piano, fireplace piano, or greenhouse study piano.
- Repeating the same thumbnail hook or feeling; check recent copy under [the new copy policy](../openclaw-thumbnail-copy-policy.md).
- The same visual scene if it was used recently.

First run `scripts/openclaw-release soft-hour-lane`. Use its `next_lane` and store it with `create-release --soft-hour-lane classic_piano|anime_game_ost`. The command alternates against the latest classified Soft Hour release, which keeps the long-run output at 50:50 instead of allowing random streaks. If the latest 3 Soft Hour releases share the same setting, use case, tempo/energy, or thumbnail phrase, choose a different one inside the selected lane.

## Concept Lanes

Choose exactly one top-level lane, then combine one use case, one setting, and one piano sub-lane:

Also follow [../openclaw-channel-genre-taxonomy.md](../openclaw-channel-genre-taxonomy.md). Make each video specific, such as rainy reading solo piano, cafe work piano, deep sleep felt piano, forest morning piano, quiet focus piano, or fireplace rest piano, while the app assigns it to a broader YouTube playlist bucket such as `Piano BGM`, `Sleep & Relax BGM`, or `Study & Focus BGM`.

- Study or work: clean solo piano, felt piano, warm room tone, steady low-fatigue phrasing.
- Reading or rest: rainy window solo piano, fireplace piano, slow melodic piano, quiet pedal resonance.
- Sleep: deep night felt piano, sparse left hand, very soft dynamics, resolved endings.
- Focus: forest morning piano, library desk piano, minimal repeating motif, no percussion.
- Cafe: afternoon counter solo piano, candle table piano, warm upright/felt piano, no jazz trio.
- Relaxation: moonlit room piano, garden-window piano, slow expressive solo piano, gentle cadence.

### `classic_piano` — current Soft Hour concept

- Keep the current calm, practical solo/felt/upright piano sound and premium real-world cover system.
- Favor quiet study, cafe work, reading, sleep, rain, rest, forest morning, greenhouse, cottage, and warm-room concepts.

### `anime_game_ost` — Japanese animation/game OST piano concept

- Write an original piano-led instrumental that feels at home in a warm Japanese animation or fantasy/adventure game soundtrack without copying any existing melody, harmony sequence, arrangement, title, character, or franchise.
- The emotional range can be bright and lively, gently bouncy, warmly nostalgic, peaceful, tender, or quietly hopeful. A calm track is valid when the anime/game OST identity remains unmistakable; do not force every cue to be fast.
- Use memorable lyrical piano motifs, clear melodic storytelling, graceful theme development, light-footed left-hand motion or broken-chord momentum when appropriate, colorful major/add9/sus harmony, and a satisfying theme return. Avoid dark trailer scoring, huge battle orchestra, ominous ambience, or generic sleep-piano drift with no theme.
- Good concept families include a sunlit fantasy-town morning, first journey, lakeside memory, sky-island breeze, flower-field reunion, observatory night, peaceful railway departure, cozy item shop, forest save point, or hopeful ending scene. These are original mood families, not references to a real game scene.
- The user mentioned existing soundtrack pieces only as an emotional compass. Never put `TalesWeaver`, `Reminiscence`, `Second Run`, a composer, a franchise, or an imitation request into Suno, image, video, metadata, or public titles. Translate the request into the broad musical traits above.

Do not choose lofi beats, Rhodes, guitar-led, ambient-pad, jazz-trio, bossa, drum/percussion, or unrelated mixed-instrument BGM. `classic_piano` stays solo piano. `anime_game_ost` may use only the restrained support color explicitly allowed below and must remain unmistakably piano-led.

## Music Direction

- Instrumental/no-vocal by default.
- Piano-led and solo-piano-first in both lanes. Keep `classic_piano` strictly solo/felt/upright piano. Keep `anime_game_ost` centered on piano; default to solo piano, with only extremely restrained music-box/celesta, soft strings, or a light woodwind color when it materially helps the game-OST storytelling and the release concept explicitly calls for it.
- Follow `../suno-v55-instrumental-format.md`.
- Use bracket-only Suno instrumental metatags in the lyrics/custom-lyrics field.
- Generate about three new piano tracks for every normal new Soft Hour playlist, usually producing roughly 10-12 minutes of fresh audio. Do not generate more than three unless one is unusable or the human explicitly asks. Put the selected lane and concrete piano wording in every Suno style/settings field: `solo piano`, `felt piano`, `upright piano`, `quiet piano`, or `Japanese anime/game OST-style piano` as appropriate.
- For `classic_piano`, keep the existing non-piano arrangement exclusions. For `anime_game_ost`, always exclude vocals, singing, humming, spoken word, lyrics, drums, beats, percussion, lofi beats, jazz trio, bossa, EDM, rock band, trailer music, epic battle orchestra, dark ambient, and horror; also exclude any support instrument not intentionally allowed by the selected concept.
- Do not force Soft Hour Radio tracks under 4 minutes, and do not use two-minute lower-bound wording in Suno fields. Build each bracket-only piano flow as a full cue meant to naturally land around 4 minutes or longer: intro motif, first theme, second developed theme, middle variation, final theme return, and resolved outro. Tracks shorter than 4:00 are still valid uploads when they fit; only tracks under 1:00 are a default blocker. Longer complete tracks, including 5+ minute cues, are allowed.
- After the roughly three-track fresh piano block is uploaded, let the app reuse previous same-channel, same-lane or closely compatible piano tracks for the remaining duration. If there are not enough compatible piano tracks to approach one hour, use the fresh block instead of filling an `anime_game_ost` release with unrelated sleep/cafe piano.
- Keep the newly generated piano tracks at the beginning of the final render. If order randomization is used, it may shuffle the new tracks among themselves, but reused back-half tracks must stay after that fresh lead block.
- Prioritize low listener fatigue, smooth flow, and practical usefulness.

## Visual Direction

- No fixed mascot, fixed character count, or required walking composition.
- The scene should be restrained and useful for long listening.
- Follow the selected visual lane. `classic_piano` uses high-quality photorealistic real-world BGM imagery. `anime_game_ost` uses bright premium original Japanese-animation/game-key-art illustration with an inviting fantasy/adventure scene. Calm illustrated scenes are allowed; “bright” means clear, warm, hopeful visual energy, not mandatory neon saturation or frantic action.
- Use a completely static locked-off camera in the short loop. There should be no pan, zoom, dolly, handheld drift, camera breathing, or parallax camera movement.
- Use only subtle lane-matched environmental motion. `classic_piano` can use rain, steam, lamp flicker, curtains, dust, firelight, reflections, or leaves. `anime_game_ost` can use petals, grass, clouds, water sparkle, hair/cloth settling, magical motes, distant windmills, or warm light shimmer.
- Thumbnail text should name the use case or mood, not a vague poetic title.

## Good Fresh Concept Shapes

- `[playlist] 조용히 집중하고 싶을 때 듣는 피아노 BGM | 공부와 작업을 위한 솔로 피아노`
- `[playlist] Rainy Window Piano BGM | Soft Solo Piano for Reading and Quiet Work`
- `[playlist] 잠들기 전 틀어놓는 잔잔한 피아노 | 깊은 밤 휴식과 수면 BGM`
- `[playlist] Cafe Piano for Work | Calm Solo Piano Music for Focus and Reading`
- `[playlist] 따뜻한 방에서 쉬는 피아노 연주곡 | 독서, 휴식, 조용한 저녁 BGM`
- `[playlist] 모험이 시작될 것 같은 피아노 OST | 잔잔하게 듣는 애니·게임 감성 BGM`
- `[playlist] Sunlit Fantasy Game Piano | Gentle Anime-Style OST Music for Study and Rest`

## Bad Directions

- Vocal tracks unless the human explicitly asks.
- Non-piano-led Soft Hour tracks: guitar-led, Rhodes-led, lofi beats, jazz trio, bossa, synth-pad ambient, drums/percussion, or unrelated mixed-instrument cafe BGM. A tiny explicitly planned support color in `anime_game_ost` is not permission to turn the release into full orchestra.
- Reusing the same solo piano cafe setting every time.
- Generic titles that do not include a use case.
- Titles that are too niche for discovery, such as leading with pottery, glazing, kiln rooms, or other craft-specific terms when the music is really general focus/work/rest BGM.
- Titles that read like translated keyword fragments instead of natural BGM copy.
- Visuals that are too busy or flashy for background listening, generic low-quality anime art, protected franchise lookalikes, or mismatched music/image lanes.
