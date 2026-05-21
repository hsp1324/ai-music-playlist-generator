# OpenClaw Channel Profile: BibliaCanto

Use this profile only after channel selection returns `BibliaCanto`, or when the human explicitly says to upload scripture music to `BibliaCanto`.

## Routing Contract

- Explicit channel request wins.
- BibliaCanto is now the combined scripture channel for Old Testament and New Testament songs, biblical meditation music, cinematic worship, psalm-like prayer music, Gospel worship, and Bible story ballads.
- It follows two app-managed scripture branches: Old Testament from Genesis onward and New Testament from Matthew onward. New Testament releases still upload to `BibliaCanto`; `불송` is reserved for Buddhist scripture-inspired music, not Bible/Gospel uploads.
- Do not use this profile for fantasy/game OST, generic BGM, EDM, pop, or popular-song covers.

## Visual Identity

- Mood: reverent, ancient, cinematic, contemplative, sacred, story-driven.
- Style must be illustrated, anime, painterly, storybook, illuminated-manuscript, or stylized biblical landscape. Avoid photorealistic/live-action looks.
- Let the selected passage decide the scene and subject.
- Prefer symbolic biblical imagery over direct depiction of God the Father.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
- Do not put `BibliaCanto`, `Old Verse`, `New Verse`, the channel name, a channel logo, or a brand line on the cover/first-frame.
- If text is useful, use the exact selected passage range and/or music lane, such as `Genesis 1:1-5`, `Matthew 1:18-25`, `Old Testament Jazz`, `Gospel R&B`, or `Scripture Worship`.
- Do not add scripture paragraphs, title sentences, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.
- Match the scene to the selected passage and branch. Old Testament examples: creation waters, Eden, wilderness, covenant stars, ark, desert road, tabernacle, temple, psalm imagery, or prophetic landscape. New Testament examples: road, hillside, Galilee shore, table, lamp, doorway, empty tomb light, cross silhouette, prayer hands, scroll, or warm worship landscape.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Put the exact selected passage range from the public title on the thumbnail, such as `Genesis 1:1-5` or `Matthew 1:18-25`, unless the human explicitly asks for no passage text. Add short readable click text that connects to that passage, book, theme, and worship/reflection listening lane.
- Do not use `Old Verse`, `New Verse`, `The Old Verse`, `The New Verse`, `OLD VERSE`, or `NEW VERSE` anywhere on BibliaCanto visuals. Avoid making `OLD TESTAMENT` or `NEW TESTAMENT` the largest thumbnail headline when a specific passage range is available; the passage range should be the identifying text.
- Generic text such as `GENESIS SONGS`, `GOSPEL SONGS`, `BIBLE MUSIC`, `PSALMS MUSIC`, `SCRIPTURE SONGS`, or `EXODUS MUSIC` may be used as secondary support, but do not leave the thumbnail as only a broad genre label when the release has a specific passage and theme.
- Good thumbnail wording should feel like a natural YouTube Bible/worship thumbnail, not a raw genre tag. Prefer a passage/book cue, a clear theme cue, or a prayer/reflection cue when it helps viewers understand what this release is about.
- Do not add `BIBLIACANTO`, the channel name, or a channel logo.
- Do not use a black text box or hard rectangular background behind text.
- Keep all thumbnail text inside safe margins with breathing room. Reject/regenerate if text is clipped, cramped inside a shape, too close to the edge, pasted over the art, or separated from the scene.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.
- Do not paste long scripture text onto the thumbnail.

## Loop Video

- Use Dreamina/Seedance or Gemini only for the moving clip.
- For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `7 seconds`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `7 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
- Animate the selected cover concept with reverent environmental motion: slow light over water, drifting stars, candle or oil-lamp glow, scroll dust, desert wind, cloud/fire glow, rain, water shimmer, leaves, or temple light when appropriate.
- If the first frame contains a passage range or short style phrase, keep it stable and readable. Do not invent a channel name.
- Queue final render with `--video-spectrum-overlay-style none`. BibliaCanto must not use app-rendered spectrum bars, radial/multiwave/pulse visualizers, waveform overlays, dots, particles, or equalizer graphics.
- The final moment should stay close to the opening composition so the app can repeat it smoothly.
- Do not add subtitles, lyrics, long verse text, title text, duration text, UI, logos, protected film imagery, or photorealistic reenactment footage. The exact short passage range from the title is allowed when it is already designed into the first frame.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame.
Create one uninterrupted scripture-inspired music visual take for a Bible music release inspired by the exact passage range shown in the public title.
Preserve the opening composition, lighting, palette, illustrated/stylized visual language, and the specific biblical scene from the first frame.
If the first frame includes a passage range such as "Genesis 1:1-5" or "Matthew 1:18-25", keep that passage text stable and readable. Do not invent a channel name.
Animate reverent environmental motion naturally present in the scene: slow light movement, stars, candle or oil-lamp glow, scroll dust, desert wind, cloud/fire glow, rain, water shimmer, leaves, temple light, sunrise, sea shimmer, open doorway light, or soft cloud movement when appropriate.
The final moment should preserve the same crop, framing, camera distance, lighting, palette, and subject placement; only ambient details may differ.
No photorealism, live action, direct depiction of God the Father, protected characters, Old Verse/New Verse labels, new text, subtitles, logos, or UI.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds vague, doctrinally awkward, or less clickable, rewrite it while keeping the passage reference, Old Testament theme, and broad music style truthful.
- Default metadata language should be English unless the human asks otherwise.
- Include the passage reference and testament branch in the main title, every localized title, and the description, for example `Genesis 1:1-5` plus `Old Testament` or `Matthew 1:18-25` plus `New Testament`.
- The first description paragraph must clearly say which passage inspired the music and what theme was adapted. Old Testament examples include creation, covenant, wilderness trust, lament, deliverance, wisdom, or prophetic hope. New Testament examples include grace, mercy, discipleship, healing, prayer, resurrection hope, or kingdom teaching.
- Also include one natural music-style sentence in the description, such as `This release is arranged as cinematic scripture worship with acoustic folk, strings, and prayerful vocal songs.` Do not hide the style, but keep it descriptive rather than technical.
- Titles should include Old Testament or New Testament/Bible/scripture keywords plus a listening use case such as worship, reflection, prayer, study, hope, or quiet focus.
- Make titles broad and public-facing first. Use exact passage scene details as atmosphere unless they are the strongest searchable hook.
- Keep each release in one coherent style family, with controlled variety across tracks. Do not make one playlist jump randomly between unrelated styles.
- Rotate the release-level music lane across BibliaCanto uploads instead of defaulting to the same generic holy worship / cinematic hymn sound every time. Pick one lane for the whole release before generating tracks, then keep every track inside that family so the public title can truthfully name the genre.
- Valid release-level lanes include scripture jazz, gospel R&B / soul, acoustic scripture folk/gospel, modern worship pop, cinematic orchestral scripture music, psalm-like prayer ballads, piano worship, choir-backed worship/gospel, neo-soul prayer songs, and ancient-folk worship. Use these as direction, not fixed title templates.
- If the selected lane is jazz, make the whole release jazz-based. If it is R&B, make the whole release R&B/soul-based. Do not mix jazz, R&B, folk, and orchestral tracks in one release unless the selected lane is an intentional fusion and the title says so.
- Include the selected lane naturally in the title and description, for example as `Old Testament Jazz Worship`, `Genesis Scripture Jazz`, `Gospel R&B Bible Songs`, `Acoustic Scripture Folk`, or another natural public-facing phrase that fits the passage.
- The app will add each uploaded scripture release to `Old Testament Songs` or `New Testament Songs` and also to one style playlist when the lane is clear. Make the lane obvious in the title/description/tags so classification works. `Gospel Worship Songs` is only for gospel/choir-based lanes; it does not replace the Old/New Testament branch playlist.
- Avoid denominational claims, copyrighted translation names, and protected media references.
