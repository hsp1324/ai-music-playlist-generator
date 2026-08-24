# OpenClaw Channel Concept Planner: BibliaCanto

Use this after the selected upload channel is `BibliaCanto`. This document decides the next scripture playlist concept for either the Old Testament branch or the New Testament branch. Use `../openclaw-channel-profiles/the-old-verse.md` afterward for cover, thumbnail, and short loop-video production rules.

Mandatory vocal arrangement override: read
[../openclaw-vocal-arrangement-policy.md](../openclaw-vocal-arrangement-policy.md)
first. Every new BibliaCanto vocal release uses exactly one of themed
large-scale orchestral vocal, piano-only vocal, or acoustic-guitar-only vocal.
The legacy scripture hip-hop/R&B/K-pop lanes below guide English lyric delivery,
discovery packaging, and catalog labels only; they cannot add beat-led or
full-band accompaniment. Do not turn orchestral work into gospel or worship.

## Channel Promise

BibliaCanto is the combined scripture-inspired music channel for both Old Testament and New Testament releases.

It follows two canonical app-managed branches:

- Old Testament branch: starts from Genesis 1:1 and uploads around 07:00.
- New Testament branch: starts from Matthew 1:1 and uploads around 16:00.

Each passage's meaning, scene, conflict, promise, lament, wisdom, grace, mercy, discipleship, kingdom teaching, courage, doubt, or hope becomes original songs.

This is not a Bible-reading channel. Do not simply narrate verses. Reinterpret the passage as modern playlist-ready music: scripture hip-hop, Bible R&B, K-pop-inspired scripture pop, trap-soul, boom-bap scripture rap, alt-R&B, neo-soul, and other trendy secular-pop-adjacent styles.

The audience should immediately understand: Bible passages turned into original scripture songs, with clear Old Testament or New Testament labeling.

Public titles must include the passage or passage theme and must say Old Testament or New Testament. They should not become generic religious keyword piles. Before finalizing metadata, check every localized title in its own language and reject vague tails such as `Hope Energy`, `Prayer Focus Music`, `Bible Music`, `Worship Music`, or literal equivalents without a clear passage/theme/style. The title should tell viewers what scripture section inspired the release and what kind of modern scripture hip-hop/R&B/K-pop-style music they are getting in natural local wording.

## Sequence Rule

- Follow [../openclaw-scripture-sequence.md](../openclaw-scripture-sequence.md) before choosing the passage. The deployed web app ledger is mandatory, not optional.
- Always inspect recent `BibliaCanto` releases in `scripts/openclaw-release list-releases`, then reserve the next passage from the web app with `scripts/openclaw-release openclaw-scripture-reserve`.
- For Old Testament, reserve with `--channel-title "BibliaCanto"`.
- For New Testament, reserve with `--channel-title "New Testament"`, but still create/publish the release with `--youtube-channel-title "BibliaCanto"`.
- Continue from the app-returned passage. Do not jump randomly to Psalms, Exodus, prophets, or famous stories unless the app sequence has reached them or the human explicitly asks and the app ledger is updated.
- If there is no prior app catalog history, the Old Testament branch starts with `Genesis 1:1-5` and the New Testament branch starts with `Matthew 1:1-17`.
- Create the release first, then reserve the chosen passage as `in_progress` with `scripts/openclaw-release openclaw-scripture-reserve` before opening Suno.
- Put the passage reference in the private plan, title, and description, for example `Genesis 1:1-5`.
- For cover, thumbnail, and loop-video planning, never use `Old Verse`, `New Verse`, `The Old Verse`, `The New Verse`, `BibliaCanto`, or any channel branding as visible text. Use the exact selected passage range from the title, such as `Genesis 1:1-5` or `Matthew 1:18-25`, plus a short passage theme or music lane when useful.
- For a 40-minute playlist, choose a coherent passage block, usually one scene or one short chapter section. Do not cover too much scripture at once.
- After successful YouTube upload/scheduling, mark the passage as `scheduled` or `published` with `scripts/openclaw-release openclaw-scripture-complete`.
- Do not compare against a local ledger and do not stop because title wording differs. The web app rejects duplicate active passages; use its response as the source of truth.

## Scripture Handling

- Do not copy long passages from modern copyrighted Bible translations into lyrics or public descriptions.
- Use brief references and original paraphrase. If a direct quote is needed, keep it very short or use public-domain wording only when you are sure.
- Avoid doctrinal arguments, denominational claims, or speculative theology. Keep the tone reverent, biblical, and broadly Christian/Judeo-Christian friendly.
- Do not depict God the Father directly in visuals. Use symbolic light, sky, cloud, fire, water, stars, altar, scroll, road, wilderness, ark, tent, temple, or landscape imagery.

## Recent Release Check

From `scripts/openclaw-release list-releases`, inspect recent `BibliaCanto` releases and avoid repeating:

- The same passage range.
- The same biblical scene, such as creation light, Eden garden, flood water, desert road, covenant stars, Exodus sea, tabernacle, temple, psalm lament, or prophetic vision.
- The same release-level music lane or instrument palette, such as scripture hip-hop, trap-soul, boom-bap scripture rap, Bible R&B, alt-R&B, neo-soul, K-pop-inspired scripture pop, dark street-pop, Afropop/Amapiano-pop, synth-pop, 808 drums, or sung-rap hooks.
- The same emotional direction, such as awe, repentance, covenant hope, lament, wilderness trust, deliverance, wisdom, or prophetic warning.
- The same thumbnail phrase, such as `GENESIS SONGS`, `OLD TESTAMENT`, `BIBLE MUSIC`, `PSALMS MUSIC`, or `SCRIPTURE SONGS`.

## Concept Lanes

Old Testament branch:

- Creation and wonder: cinematic alt-R&B, synth-pop, atmospheric trap drums, light, stars, water, breath.
- Eden and fall: moody R&B, K-pop-style ballad-pop with a rap bridge, garden atmosphere, warning, loss, mercy.
- Noah and flood: dark hip-hop story song, trap-pop, rain, ark, judgment, rescue, covenant.
- Patriarchs: desert-road alt-R&B, Afrobeat-pop, family, promise, waiting.
- Exodus: triumphant hip-hop, trap-soul, percussive rap-pop, sea crossing, wilderness trust.
- Law and tabernacle: sleek R&B, neo-soul, restrained modern pop, lampstand, altar, covenant order.
- Psalms and wisdom: boom bap, lofi hip-hop with sung hooks, neo-soul, lament, wisdom, trust.
- Prophets: dark drill-lite, industrial hip-hop, trap, exile, restoration, justice, warning.

New Testament branch:

- New Testament opening: promise, lineage, waiting, arrival, fulfillment, arranged as alt-R&B or K-pop-inspired pop.
- Jesus birth and early life: modern R&B/pop, warm synth-pop, family, promise, wonder, not carol or worship music.
- Kingdom teaching: rap-pop, K-pop hip-hop, parables, mercy, forgiveness, discipleship.
- Miracles and healing: hopeful R&B, neo-soul, melodic hip-hop, restoration, trust.
- Cross and resurrection: cinematic trap-soul, alt-pop, R&B, grace, victory, hope, no worship chorus.
- Acts and early church: energetic hip-hop, Afropop, Amapiano-pop, courage, mission, community.
- Epistles: R&B, rap-pop, neo-soul, love, endurance, wisdom, encouragement.
- Revelation: dark synth-pop, trap, cinematic street-pop, awe, hope, restoration, symbolic imagery.

## Music Direction

- Vocal songs with original lyrics are the default and expected output.
- Do not make instrumental/no-vocal BibliaCanto releases unless the human explicitly asks for BGM or instrumental meditation.
- Lyrics must be in English by default. Do not write Korean, Japanese, Spanish, Latin, Hebrew, or other-language lyrics for BibliaCanto scripture releases unless the human explicitly asks for that language.
- Lyrics must be original, song-first, and spiritually coherent. The passage inspires the song, but the song should still have a strong hook, emotional arc, and natural melody.
- Choose one primary style family for each release and write it in the private plan before creating songs. BibliaCanto must not sound like standard church music. Never choose Gospel music, gospel choir, worship, praise band, CCM, hymns, congregational singing, choir-backed worship, piano worship ballads, Christian-rock worship, pipe-organ church music, altar-call music, or generic holy worship.
- Good lanes include scripture hip-hop, Bible R&B, K-pop-inspired scripture pop, scripture rap-pop, trap-soul scripture songs, boom-bap Bible rap, alt-R&B scripture songs, neo-soul scripture songs, Afropop/Amapiano-pop scripture songs, dark street-pop scripture, or synth-pop scripture songs. Vary tracks inside the chosen lane; do not mix unrelated genres just to create variety.
- If the chosen lane is hip-hop, all tracks should be hip-hop/rap-pop/trap/boom-bap based. If it is R&B, all tracks should stay R&B/alt-R&B/neo-soul based. If it is K-pop-inspired, use K-pop production, hooks, and rap-pop energy while keeping English lyrics unless the human explicitly asks for another language. The lane must be specific enough that the final title can truthfully name it.
- Metadata must tell viewers the branch, selected passage/theme, and broad music style family. Put the exact scripture reference and theme in the title/first paragraph, and put the style in the description.
- Do not force chapter/verse numbers into choruses. Mention references in metadata, not necessarily in lyrics.
- Do not put duration caps or lower-bound duration phrases such as `less than 4 minutes`, `under 4 minutes`, `at least 2 minutes`, `minimum 2 minutes`, or `2 minutes or longer` into Suno fields unless the human explicitly asks for that wording. Build each scripture-inspired prompt/lyrics file as a full song meant to naturally land around 4 minutes or longer: natural intro, developed first and second verse, chorus or refrain returns, bridge/breakdown or final lift, and resolved ending. Tracks shorter than 4:00 are still valid uploads when they fit. Tracks from 1:00 to 1:59 should be uploaded/used and recorded for later analysis; only stop and report tracks under 1:00 unless the channel-specific workflow says otherwise. Complete 5+ minute tracks are allowed.
- Put Suno church-style blockers into excluded styles for every BibliaCanto track: gospel, gospel choir, worship, praise band, CCM, hymn, hymnal, church choir, choir-backed worship, congregational singing, Christian rock worship, piano worship, pipe organ, church service, altar call, sermon, preacher, pastor.
- Avoid producer tags, specific artist references, protected worship brands, church names, celebrity pastors, and modern Bible translation names.

## YouTube Playlist Assignment

- The app automatically adds uploaded scripture videos to testament playlists on `BibliaCanto`.
- Old Testament branch videos go to `Old Testament Songs`.
- New Testament branch videos go to `New Testament Songs`.
- The app also adds each video to one style playlist when the release lane is clear, such as `Scripture Hip-Hop Songs`, `Scripture R&B Songs`, `Bible K-Pop Songs`, `Scripture Trap Songs`, `Bible Neo-Soul Songs`, `Bible Afropop Songs`, or `Scripture Synth-Pop Songs`.
- Do not create or choose `Gospel Worship Songs`, `Piano Worship Songs`, `Cinematic Worship Songs`, or `Modern Worship Pop Songs` for new BibliaCanto releases. Every Bible video still goes first into exactly one branch playlist: `Old Testament Songs` or `New Testament Songs`.
- Make the release-level lane explicit in the plan, title, description, tags, or metadata text so the app and future operators can classify the video. A single video should normally land in two playlists: testament branch plus style.

## Visual Direction

- Illustrated, anime, painterly, storybook, ancient manuscript, cinematic biblical landscape, or stylized scripture-art look.
- Visuals can include creation light over waters, stars, wilderness, tents, scrolls, stone paths, ark silhouettes, desert mountains, olive trees, ancient city gates, temple light, symbolic fire/cloud, Galilee shoreline, empty tomb light, bread and cup symbolism, hillside teaching, prayer hands, or warm doorway light.
- Do not make photorealistic biblical reenactment footage.
- Do not use protected film/TV/game designs.
- Thumbnail text should be clear and searchable and branch-aware: `GENESIS 1:1-5`, `OLD TESTAMENT HIP-HOP`, `NEW TESTAMENT R&B`, `BIBLE K-POP`, `SCRIPTURE RAP`, `MATTHEW R&B`, `PSALMS HIP-HOP`, or `EXODUS TRAP`.

## Good Fresh Concept Shapes

- `[playlist] Genesis 1:1-5 Creation Hip-Hop | Old Testament Rap & R&B Songs`
- `[playlist] Genesis 2:4-17 Eden Trap-Soul | Old Testament Story Rap`
- `[playlist] Genesis 6:9-22 Noah's Ark Drill-Pop | Old Testament Hip-Hop Story Songs`
- `[playlist] Genesis 15 Covenant R&B | Old Testament Neo-Soul Songs`
- `[playlist] Matthew 1:18-25 Emmanuel K-Pop R&B | New Testament Scripture Songs`
- `[playlist] Matthew 5:13-16 Salt and Light R&B | New Testament Alt-R&B Songs`

## Bad Directions

- Randomly selecting famous Old Testament or New Testament passages out of order.
- Long copied Bible passages as lyrics.
- Debate/apologetics content instead of music.
- Generic fantasy OST that belongs on Storylight OST.
- Gospel, worship, holy, hymn, praise-band, church choir, or generic church piano styles.
- Vague scripture titles that omit the passage/theme/branch or read like abstract keyword tags instead of Bible music.
