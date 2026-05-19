# OpenClaw Channel Concept Planner: The New Verse

Use this after the selected channel is `The New Verse`. This document decides the next playlist concept. Use `../openclaw-channel-profiles/the-new-verse.md` afterward for cover, thumbnail, and short loop-video production rules.

## Channel Promise

The New Verse is a New Testament scripture-inspired worship music channel.

It follows the New Testament in canonical order, starting from Matthew 1:1, and turns each passage's message, scene, parable, prayer, grace, cross, resurrection hope, apostolic teaching, or Revelation imagery into original songs.

This is not a Bible-reading channel. Do not simply narrate verses. Reinterpret the passage as modern worship pop, prayer songs, warm gospel-influenced songs, scripture ballads, and Bible-based praise music.

The audience should immediately understand: New Testament messages turned into original worship songs.

Public titles must include the passage or Gospel theme, but they should not become generic worship keyword piles. Before finalizing metadata, check every localized title in its own language and reject vague tails such as `Grace Energy`, `Prayer Focus Music`, `Worship Music`, or literal equivalents without a clear passage/theme/style. The title should tell viewers what New Testament section inspired the release and what kind of worship music they are getting in natural local wording.

## Sequence Rule

- Follow [../openclaw-scripture-sequence.md](../openclaw-scripture-sequence.md) before choosing the passage. The deployed web app ledger is mandatory, not optional.
- Always inspect recent `The New Verse` releases in `scripts/openclaw-release list-releases`, then reserve the next passage from the web app with `scripts/openclaw-release openclaw-scripture-reserve`.
- Continue from the app-returned passage. Do not jump randomly to John, Romans, Revelation, or famous Jesus sayings unless the app sequence has reached them or the human explicitly asks and the app ledger is updated.
- If there is no prior app catalog history, the app starts with `Matthew 1:1-17`.
- Create the release first, then reserve the chosen passage as `in_progress` with `scripts/openclaw-release openclaw-scripture-reserve` before opening Suno.
- Put the passage reference in the private plan, title, and description, for example `Matthew 1:1-17`.
- For a 40+ minute playlist, choose a coherent passage block, usually one scene, teaching section, parable, or short chapter section. Do not cover too much scripture at once.
- After successful YouTube upload/scheduling, mark the passage as `scheduled` or `published` with `scripts/openclaw-release openclaw-scripture-complete`.
- Do not compare against a local ledger and do not stop because title wording differs. The web app rejects duplicate active passages; use its response as the source of truth.

## Scripture Handling

- Do not copy long passages from modern copyrighted Bible translations into lyrics or public descriptions.
- Use brief references and original paraphrase. If a direct quote is needed, keep it very short or use public-domain wording only when you are sure.
- Keep the tone broadly Christian, worshipful, gracious, and non-argumentative.
- Be respectful with depictions of Jesus. Prefer symbolic light, road, table, empty tomb, sea, bread, lamp, cross silhouette, hands, doorway, hillside, or disciples-from-behind imagery over realistic face-focused portraits.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `The New Verse` releases and avoid repeating:

- The same passage range.
- The same New Testament scene, such as genealogy, Bethlehem, baptism, wilderness, Galilee road, parable field, stormy sea, table fellowship, cross, empty tomb, upper room, church letters, or Revelation vision.
- The same release-level music lane or worship palette, such as gospel R&B/soul, scripture jazz, modern worship pop, piano worship, acoustic guitar ballad, warm gospel choir pads, soft drums, synth worship, strings, neo-soul prayer songs, or intimate prayer music.
- The same emotional direction, such as grace, surrender, hope, repentance, healing, joy, discipleship, resurrection, or comfort.
- The same thumbnail phrase, such as `GOSPEL SONGS`, `NEW TESTAMENT`, `JESUS MUSIC`, `GRACE MUSIC`, or `WORSHIP POP`.

## Concept Lanes

- Gospel beginning: promise, lineage, waiting, arrival, fulfillment.
- Jesus birth and early life: gentle worship ballads, light, family, promise, wonder.
- Kingdom teaching: modern worship pop, parables, mercy, forgiveness, discipleship.
- Miracles and healing: hopeful praise, prayer, restoration, trust.
- Cross and resurrection: reverent ballads, cinematic worship, grace, victory, hope.
- Acts and early church: movement, courage, Spirit, mission, community.
- Epistles: prayer songs, grace, love, endurance, wisdom, church encouragement.
- Revelation: awe, hope, worship, restoration, symbolic cinematic worship.

## Music Direction

- Vocal worship songs with original lyrics are the default and expected output.
- Do not make instrumental/no-vocal New Verse releases unless the human explicitly asks for BGM or instrumental prayer music.
- Lyrics must be in English by default. Do not write Korean, Japanese, Spanish, Latin, Hebrew, or other-language lyrics for The New Verse unless the human explicitly asks for that language.
- Lyrics must be original, song-first, and worshipful. The passage inspires the song, but the song should still have a strong hook, emotional arc, and natural melody.
- Choose one primary style family for each release and write it in the private plan before creating songs. Rotate this lane across uploads instead of defaulting to generic holy worship. Good lanes include gospel R&B/soul, modern worship pop, scripture jazz, acoustic gospel, piano worship ballads, choir-backed gospel, neo-soul prayer songs, cinematic Gospel worship, or intimate prayer songs. Vary tracks inside the chosen lane; do not mix unrelated genres just to create variety.
- If the chosen lane is jazz, all tracks should be jazz-based. If it is R&B/soul, all tracks should stay R&B/soul-based. The lane must be specific enough that the final title can truthfully name it.
- Metadata must tell viewers both the selected passage/theme and the broad music style family. Put the exact scripture reference and theme in the title/first paragraph, and put the style in the description.
- Do not force chapter/verse numbers into choruses. Mention references in metadata, not necessarily in lyrics.
- For worship pop, use natural modern song structure: verse, pre-chorus, chorus, bridge, final chorus when appropriate.
- Suno duration wording should be minimal: use only `less than 4 minutes` or `under 4 minutes` when a duration hint is needed.
- Avoid producer tags, specific artist references, protected worship brands, church names, celebrity pastors, and modern Bible translation names.

## Visual Direction

- Illustrated, anime, painterly, warm worship-art, cinematic Gospel scene, or stylized biblical landscape.
- Visuals can include a road at sunrise, candlelit table, hillside, Galilee shoreline, open doorway, empty tomb light, bread and cup symbolism, hands in prayer, scroll, lamp, or a cross silhouette.
- Avoid photorealistic/live-action Jesus reenactment footage.
- Do not use protected film/TV designs.
- Thumbnail text should be clear and searchable: `GOSPEL SONGS`, `NEW TESTAMENT`, `JESUS MUSIC`, `GRACE MUSIC`, `SCRIPTURE SONGS`, or `WORSHIP POP`.

## Good Fresh Concept Shapes

- `[playlist] Matthew 1:1-17 Gospel Songs | New Testament Worship Music for Prayer`
- `[playlist] Matthew 2:1-12 Star of Bethlehem Songs | Gospel Music for Hope and Wonder`
- `[playlist] Matthew 5:1-12 Beatitudes Worship | New Testament Songs for Prayer`
- `[playlist] Matthew 28:1-10 Resurrection Hope Songs | New Testament Worship for Faith`

## Bad Directions

- Randomly selecting famous New Testament passages out of order.
- Long copied Bible passages as lyrics.
- Sermon/apologetics/debate content instead of music.
- Generic church piano BGM with no clear passage reference.
- Old Testament-focused concepts that belong on The Old Verse.
- Vague worship titles that omit the passage/theme or read like abstract keyword tags instead of New Testament music.
