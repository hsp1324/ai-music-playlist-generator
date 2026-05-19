# OpenClaw Channel Concept Planner: The Old Verse

Use this after the selected channel is `The Old Verse`. This document decides the next playlist concept. Use `../openclaw-channel-profiles/the-old-verse.md` afterward for cover, thumbnail, and short loop-video production rules.

## Channel Promise

The Old Verse is an Old Testament scripture-inspired music channel.

It follows the Old Testament in canonical order, starting from Genesis 1:1, and turns each passage's meaning, scene, conflict, promise, lament, wisdom, or worship mood into original songs.

This is not a Bible-reading channel. Do not simply narrate verses. Reinterpret the passage as music: meditation songs, cinematic worship, ancient biblical ballads, psalm-like prayer music, and scripture-inspired story songs.

The audience should immediately understand: Old Testament stories and messages turned into original Bible music.

Public titles must include the passage or passage theme, but they should not become generic religious keyword piles. Before finalizing metadata, check every localized title in its own language and reject vague tails such as `Hope Energy`, `Prayer Focus Music`, `Bible Music`, or literal equivalents without a clear passage/theme/style. The title should tell viewers what scripture section inspired the release and what kind of worship/scripture music they are getting in natural local wording.

## Sequence Rule

- Follow [../openclaw-scripture-sequence.md](../openclaw-scripture-sequence.md) before choosing the passage. The deployed web app ledger is mandatory, not optional.
- Always inspect recent `The Old Verse` releases in `scripts/openclaw-release list-releases`, then reserve the next passage from the web app with `scripts/openclaw-release openclaw-scripture-reserve`.
- Continue from the app-returned passage. Do not jump randomly to Psalms, Exodus, prophets, or famous stories unless the app sequence has reached them or the human explicitly asks and the app ledger is updated.
- If there is no prior app catalog history, the app starts with `Genesis 1:1-5`.
- Create the release first, then reserve the chosen passage as `in_progress` with `scripts/openclaw-release openclaw-scripture-reserve` before opening Suno.
- Put the passage reference in the private plan, title, and description, for example `Genesis 1:1-5`.
- For a 40-minute playlist, choose a coherent passage block, usually one scene or one short chapter section. Do not cover too much scripture at once.
- After successful YouTube upload/scheduling, mark the passage as `scheduled` or `published` with `scripts/openclaw-release openclaw-scripture-complete`.
- Do not compare against a local ledger and do not stop because title wording differs. The web app rejects duplicate active passages; use its response as the source of truth.

## Scripture Handling

- Do not copy long passages from modern copyrighted Bible translations into lyrics or public descriptions.
- Use brief references and original paraphrase. If a direct quote is needed, keep it very short or use public-domain wording only when you are sure.
- Avoid doctrinal arguments, denominational claims, or speculative theology. Keep the tone reverent, biblical, and broadly Christian/Judeo-Christian friendly.
- Do not depict God the Father directly in visuals. Use symbolic light, sky, cloud, fire, water, stars, altar, scroll, road, wilderness, ark, tent, temple, or landscape imagery.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `The Old Verse` releases and avoid repeating:

- The same passage range.
- The same biblical scene, such as creation light, Eden garden, flood water, desert road, covenant stars, Exodus sea, tabernacle, temple, psalm lament, or prophetic vision.
- The same release-level music lane or instrument palette, such as scripture jazz, gospel R&B/soul, acoustic scripture folk, cinematic strings, ancient harp/lyre, frame drums, piano worship ballad, choir-backed worship, flute, or desert percussion.
- The same emotional direction, such as awe, repentance, covenant hope, lament, wilderness trust, deliverance, wisdom, or prophetic warning.
- The same thumbnail phrase, such as `GENESIS SONGS`, `OLD TESTAMENT`, `BIBLE MUSIC`, `PSALMS MUSIC`, or `SCRIPTURE SONGS`.

## Concept Lanes

- Creation and wonder: cinematic worship, strings, choir-like pads, light, stars, water, breath.
- Eden and fall: gentle ballad, garden atmosphere, innocence, warning, loss, mercy.
- Noah and flood: cinematic story song, rain, ark, judgment, rescue, covenant.
- Patriarchs: desert road ballads, covenant stars, family, promise, waiting.
- Exodus: deliverance songs, sea crossing, wilderness trust, pillar of fire/cloud.
- Law and tabernacle: reverent worship, sacred space, lampstand, altar, holiness.
- Psalms and wisdom: prayer songs, lament, praise, wisdom, trust, royal/temple imagery.
- Prophets: cinematic warning and hope, exile, restoration, justice, comfort.

## Music Direction

- Vocal songs with original lyrics are the default and expected output.
- Do not make instrumental/no-vocal Old Verse releases unless the human explicitly asks for BGM or instrumental meditation.
- Lyrics must be in English by default. Do not write Korean, Japanese, Spanish, Latin, Hebrew, or other-language lyrics for The Old Verse unless the human explicitly asks for that language.
- Lyrics must be original, song-first, and spiritually coherent. The passage inspires the song, but the song should still have a strong hook, emotional arc, and natural melody.
- Choose one primary style family for each release and write it in the private plan before creating songs. Rotate this lane across uploads instead of defaulting to generic holy worship. Good lanes include scripture jazz, gospel R&B/soul, acoustic scripture folk, cinematic orchestral scripture music, psalm-like prayer ballads, piano worship, choir-backed worship, ancient-folk worship, or gentle desert-road story songs. Vary tracks inside the chosen lane; do not mix unrelated genres just to create variety.
- If the chosen lane is jazz, all tracks should be jazz-based. If it is R&B/soul, all tracks should stay R&B/soul-based. The lane must be specific enough that the final title can truthfully name it.
- Metadata must tell viewers both the selected passage/theme and the broad music style family. Put the exact scripture reference and theme in the title/first paragraph, and put the style in the description.
- Do not force chapter/verse numbers into choruses. Mention references in metadata, not necessarily in lyrics.
- Suno duration wording should be minimal: use only `less than 4 minutes` or `under 4 minutes` when a duration hint is needed.
- Avoid producer tags, specific artist references, protected worship brands, church names, celebrity pastors, and modern Bible translation names.

## Visual Direction

- Illustrated, anime, painterly, storybook, ancient manuscript, cinematic biblical landscape, or stylized worship-art look.
- Visuals can include creation light over waters, stars, wilderness, tents, scrolls, stone paths, ark silhouettes, desert mountains, olive trees, ancient city gates, temple light, or symbolic fire/cloud.
- Do not make photorealistic biblical reenactment footage.
- Do not use protected film/TV/game designs.
- Thumbnail text should be clear and searchable: `GENESIS SONGS`, `OLD TESTAMENT`, `BIBLE MUSIC`, `PSALMS MUSIC`, `SCRIPTURE SONGS`, or `EXODUS MUSIC`.

## Good Fresh Concept Shapes

- `[playlist] Genesis 1:1-5 Creation Songs | Old Testament Music for Worship and Reflection`
- `[playlist] Genesis 2:4-17 Eden Garden Songs | Scripture Music for Prayer and Quiet Focus`
- `[playlist] Genesis 6:9-22 Noah's Ark Songs | Old Testament Music for Faith and Reflection`
- `[playlist] Genesis 15 Covenant Songs | Bible Music for Prayer, Hope and Waiting`

## Bad Directions

- Randomly selecting famous Old Testament stories out of order.
- Long copied Bible passages as lyrics.
- Debate/apologetics content instead of music.
- Generic fantasy OST that belongs on Storylight OST.
- Generic church piano BGM with no clear passage reference.
- Vague scripture titles that omit the passage/theme or read like abstract keyword tags instead of Old Testament music.
