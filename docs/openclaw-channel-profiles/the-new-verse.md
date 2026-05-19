# OpenClaw Channel Profile: The New Verse

Use this profile only after channel selection returns `The New Verse`, or when the human explicitly says to upload to `The New Verse`.

## Routing Contract

- Explicit channel request wins.
- The New Verse is for New Testament scripture-inspired worship pop, prayer songs, Gospel-based songs, grace music, and Bible verse songs.
- It follows the New Testament sequence from Matthew onward. Do not use this profile for Old Testament-focused releases; use `The Old Verse` instead.
- Do not use this profile for generic BGM, EDM, pop without scripture direction, or popular-song covers.

## Visual Identity

- Mood: warm, gracious, worshipful, hopeful, intimate, reverent.
- Style must be illustrated, anime, painterly, warm worship-art, cinematic Gospel scene, or stylized biblical landscape. Avoid photorealistic/live-action looks.
- Let the selected passage decide the scene and subject.
- Be respectful with Jesus-related visuals; symbolic scenes are safer than face-focused portraits.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
- The cover must include only a large lower-left `The New Verse` channel brand label.
- Make `The New Verse` clearly readable on mobile playback. Target roughly 18-24% of image width, or 5-6% of image height for text cap height.
- Do not add title text, verse text, scripture paragraphs, genre text, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.
- Match the scene to the selected New Testament passage: road, hillside, Galilee shore, table, lamp, doorway, empty tomb light, cross silhouette, prayer hands, scroll, or warm worship landscape.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable click text that connects to the selected passage, Gospel/New Testament theme, and worship/prayer listening lane. Generic text such as `GOSPEL SONGS`, `NEW TESTAMENT`, `JESUS MUSIC`, `GRACE MUSIC`, `SCRIPTURE SONGS`, or `WORSHIP POP` may be used as part of the layout, but do not leave the thumbnail as only `GOSPEL SONGS` plus `THE NEW VERSE` when the release has a specific passage and theme.
- Good thumbnail wording should feel like a natural YouTube worship thumbnail, not a raw genre tag. Prefer a passage/book cue, a clear theme cue, or a prayer/worship cue when it helps viewers understand what this release is about.
- Add `THE NEW VERSE` as the brand line. Keep this brand line visually consistent with the lower-left cover channel label.
- Keep `THE NEW VERSE` as plain integrated typography, preferably directly under or near the main click text. Do not put it inside a rounded yellow pill, capsule, button, sticker, badge, label tag, or detached floating plaque.
- Keep all thumbnail text inside safe margins with breathing room. Reject/regenerate if the brand line is clipped, cramped inside a shape, too close to the edge, pasted over the art, or separated from the headline layout.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.
- Do not paste long scripture text onto the thumbnail.

## Loop Video

- Use Dreamina/Seedance or Gemini only for the moving clip.
- For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `6 seconds`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `6 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
- Animate the selected cover concept with warm worshipful motion: sunrise light, candle glow, dust in light, gentle wind, sea shimmer, open doorway light, fabric movement, lamp flame, or soft cloud movement when appropriate.
- Preserve the large, readable lower-left `The New Verse` text exactly for the full clip.
- The final moment should stay close to the opening composition so the app can repeat it smoothly.
- Do not add subtitles, lyrics, verse text, title text, duration text, UI, logos, protected film imagery, or photorealistic reenactment footage.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "The New Verse".
Create one continuous animated scripture-inspired worship music visualizer shot for a New Testament release.
Preserve the opening composition, lighting, palette, illustrated/stylized visual language, and the specific Gospel/New Testament scene from the first frame.
Preserve the large, readable lower-left "The New Verse" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
Animate warm worshipful environmental motion naturally present in the scene: sunrise light, candle glow, dust in light, gentle wind, sea shimmer, open doorway light, fabric movement, lamp flame, or soft cloud movement when appropriate.
The motion must progress naturally for the full clip. Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should preserve the same crop, framing, camera distance, lighting, palette, and subject placement; only ambient details may differ.
Stable composition, no hard cuts, no photorealism, no live action, no disrespectful Jesus depiction, no protected characters, no other text, no subtitles, no logos, no UI.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds vague, doctrinally awkward, or less clickable, rewrite it while keeping the passage reference, New Testament theme, and broad music style truthful.
- Default metadata language should be English unless the human asks otherwise.
- Include the passage reference in the main title, every localized title, and the description, for example `Matthew 1:1-17`.
- The first description paragraph must clearly say which passage inspired the music and what Gospel/New Testament theme was adapted, for example grace, mercy, discipleship, healing, prayer, resurrection hope, or kingdom teaching.
- Also include one natural music-style sentence in the description, such as `This release is arranged as modern scripture worship with warm piano, acoustic guitar, soft drums, and congregational vocal songs.` Do not hide the style, but keep it descriptive rather than technical.
- Titles should include New Testament/Gospel/worship keywords plus a listening use case such as prayer, worship, reflection, hope, or quiet focus.
- Make titles broad and public-facing first. Use exact passage scene details as atmosphere unless they are the strongest searchable hook.
- Keep each release in one coherent style family, with controlled variety across tracks. Do not make one playlist jump randomly between unrelated styles.
- Rotate the release-level music lane across New Verse uploads instead of defaulting to the same generic holy worship / soft hymn sound every time. Pick one lane for the whole release before generating tracks, then keep every track inside that family so the public title can truthfully name the genre.
- Valid release-level lanes include gospel R&B / soul, modern worship pop, scripture jazz, acoustic gospel, piano worship ballads, choir-backed gospel, neo-soul prayer songs, and cinematic Gospel worship. Use these as direction, not fixed title templates.
- If the selected lane is jazz, make the whole release jazz-based. If it is R&B, make the whole release R&B/soul-based. Do not mix jazz, R&B, pop, choir, and acoustic tracks in one release unless the selected lane is an intentional fusion and the title says so.
- Include the selected lane naturally in the title and description, for example as `New Testament R&B Worship`, `Gospel Soul Bible Songs`, `Matthew Scripture Jazz`, `Acoustic Gospel Prayer Songs`, or another natural public-facing phrase that fits the passage.
- Avoid denominational claims, copyrighted translation names, and protected media references.
