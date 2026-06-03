# OpenClaw Channel Concept Planner: 불송

Use this after the selected channel is `불송`. `불송` is the Buddhist scripture music channel.

## Channel Promise

불송 is for modern Buddhist scripture-inspired vocal music. It turns Buddhist teachings, sutra themes, Dhammapada-style wisdom, mindfulness, compassion, impermanence, non-attachment, suffering and release, and awakening imagery into original modern songs.

This is not a chanting archive, sermon channel, literal scripture-reading channel, trot channel, or old Korean cabaret-pop channel. OpenClaw should create modern lyric songs that communicate the teaching in accessible language. The default and preferred release lane is hip-hop/rap-based: `불교 힙합`, `불경 힙합`, mindful hip-hop, Buddhist hip-hop, Korean Buddhist rap, mellow boom bap, soulful hip-hop, or Buddhist hip-hop soul. Use R&B, jazz, acoustic, pop, lo-fi, or cinematic lanes only when the human explicitly asks for that lane or when completing an already-started release in that lane.

The audience should immediately understand: Buddhist wisdom and sutra-inspired teachings reworked as modern Korean hip-hop songs.

## Overnight Privacy Rule

Publish 불송 through the app normally. The app schedules 불송 uploads as public daily at 07:00 Asia/Seoul, unless the human explicitly pauses the channel.

## Source Material Direction

OpenClaw does not need to quote long scripture passages. Use short references, themes, and original paraphrase.

Good starting source lanes:

- Dhammapada / 법구경 style wisdom: mind, heedfulness, anger, self-mastery, compassion, peace.
- Heart Sutra / 반야심경 themes: emptiness, form, perception, release from fear, wisdom beyond attachment.
- Lotus Sutra / 묘법연화경 themes: compassion, skillful means, persistence, universal awakening.
- Diamond Sutra / 금강경 themes: non-attachment, illusion of fixed self, generosity without clinging.
- General Buddhist teaching themes: four noble truths, eightfold path, impermanence, karma, mindfulness, loving-kindness, letting go.

If unsure where to start, use a Dhammapada-style sequence. Pick one compact theme section per 40-minute release, not a whole scripture. Do not pretend to quote exact chapters if you did not verify the structure; title it as `Dhammapada-Inspired`, `Heart Sutra-Inspired`, or `Buddhist Wisdom Songs` when appropriate.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `불송` releases and avoid repeating:

- The same scripture/theme section.
- The same release-level music lane.
- The same thumbnail phrase.
- The same visual scene.

## Concept Lanes

- Default Buddhist hip-hop / 불교 힙합: clear rhythm, Korean rap verses, sung hooks, warm bass, mellow drums, wisdom about the mind and choices.
- Mellow boom bap Buddhist rap: dusty but clean drums, Rhodes or piano, clear Korean rap, calm hook, no vinyl/static noise texture.
- Buddhist hip-hop soul: rap/sung balance, soulful chords, airy hook, modern Korean vocal tone, compassion and letting-go imagery.
- Buddhist trap-soul: restrained 808s, modern rap cadence, spacious pads, meditative but still clearly hip-hop.
- R&B/soul, jazz, acoustic, pop, lo-fi, or cinematic lanes are secondary exceptions. Use them only if the human explicitly requests that lane or if an in-progress release is already clearly in that lane.

## Music Direction

- Vocal songs with original lyrics are the default.
- Korean lyrics are the default unless the human explicitly asks for another language.
- Every track in one release must stay inside one coherent style family. By default, that family should be hip-hop/rap-based for 불송. If the title says Buddhist hip-hop, all tracks must be hip-hop/rap-based. Do not mix jazz, pop, R&B, acoustic, or cinematic tracks into a hip-hop release.
- Avoid trot, ppongjjak, and old Korean cabaret-pop completely unless the human explicitly asks for them. Do not use Korean trot rhythm, two-beat ppongjjak bounce, trot vocal ornaments, accordion/brass trot clichés, nightclub/cabaret trot arrangement, or old-TV trot mood.
- In Suno Advanced Options / excluded styles for 불송, include blockers such as `trot, Korean trot, ppongjjak, 뽕짝, 트로트, trot vocal, cabaret trot, old Korean trot, two-beat trot bounce, accordion trot, brass trot`.
- Prefer hip-hop vocabulary in Suno style prompts: Korean Buddhist hip-hop, mindful hip-hop, mellow boom bap, soulful hip-hop, Korean rap, spoken rap verses, sung hook, Rhodes keys, warm bass, restrained drums, airy hook, clear Korean vocals. Public titles, thumbnail phrases, descriptions, and tags must use plain audience-friendly wording such as `불교 힙합`, `불경 힙합`, `Buddhist hip-hop`, or `Korean Buddhist rap`, not obscure coined genre labels.
- Lyrics should sound like real songs, not a lecture. Use images, hooks, and emotional arcs while keeping the teaching clear.
- Do not copy long scripture text, modern translations, temple liturgy, or chants.
- Avoid naming living teachers, temples, sectarian claims, protected songs, or specific artist styles.
- Keep the tone respectful, contemplative, modern, and broadly accessible.

## Visual Direction

- Calm modern Buddhist visual identity: a respectful photorealistic Buddha / Buddha-inspired figure with a warm gentle expression, listening to music while reading or holding an open Buddhist sutra in a quiet temple, meditation room, candlelit study, rain garden, or mountain retreat.
- Photorealistic or premium cinematic-real Buddhist imagery is the default, and the cover/thumbnail/loop first frame must center the Buddha-reading-sutra scene rather than only symbolic background objects.
- Background-only scenes are not acceptable for 불송 final assets. If the output is only a temple path, lotus pond, lanterns, mountains, incense, abstract Buddhist symbols, or a statue-like wallpaper without the open sutra and subtle music cue, regenerate before uploading.
- Use supporting details such as lanterns, lotus, incense smoke, candlelight, prayer beads, warm window light, paper texture, wooden table, temple architecture, rain on stone, or quiet garden foliage. Keep the music cue subtle and respectful, such as a small speaker or understated headphones nearby.
- Cute/gentle animation visuals are no longer the normal default. Use them only when the human explicitly asks or when the release concept very clearly needs a softer animated treatment.
- Avoid parody, caricature, or exoticized religious imagery.
- Do not depict the Buddha singing, dancing, performing, posing like an idol/model, surrounded by exaggerated fantasy effects, or reduced to a cheap statue wallpaper. A serene face is allowed, but keep the sutra, listening cue, and respectful environment visible.
- Cover, YouTube thumbnail, first-frame, and loop video must all use the same Buddha-reading-sutra image package for 불송. It may contain one short Korean passage/theme + hip-hop style phrase, such as `법구경 힙합`, `불경 힙합`, `마음챙김 랩`, `자비 힙합`, or `반야심경 랩`, but never the `불송` channel label or obscure coined genre wording.
- Do not create a separate channel-branded thumbnail for 불송. Reuse the same cover/first-frame package as the YouTube thumbnail and pass `--allow-cover-as-thumbnail` when using the helper.

## Good Fresh Concept Shapes

- `[playlist] 마음을 다스리는 불경 힙합 | 법구경에서 영감을 받은 한국어 랩`
- `[playlist] 연꽃처럼 버티는 불교 힙합 | 흔들릴 때 듣는 한국어 랩`
- `[playlist] 내려놓는 마음의 불경 힙합 | 집착을 비우는 Korean Buddhist Rap`
- `[playlist] 반야심경에서 영감 받은 힙합 | 두려움을 내려놓는 한국어 랩`
- `[playlist] 자비를 배우는 불교 힙합 | 조용한 밤 마음챙김 랩`

## Bad Directions

- Generic meditation BGM with no lyrics or teaching.
- Literal scripture reading, chanting, or sermon format.
- Randomly mixing jazz, hip-hop, R&B, folk, and cinematic pop in one release.
- Using obscure coined genre labels in YouTube titles, thumbnail phrases, descriptions, or tags instead of plain public hip-hop wording.
- Making non-hip-hop 불송 releases by default when the human did not ask for them.
- Any trot, ppongjjak, cabaret trot, old-TV trot, or accordion/brass trot feel.
- Copying long translated sutra passages.
- Using Buddhist words as decoration while the lyrics say nothing about the teaching.
- Forcing private visibility or bypassing the app's daily 07:00 Asia/Seoul schedule without an explicit human pause.
