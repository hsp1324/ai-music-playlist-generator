# OpenClaw Channel Profile: The Old Verse

Use this profile only after channel selection returns `The Old Verse`, or when the human explicitly says to upload to `The Old Verse`.

## Routing Contract

- Explicit channel request wins.
- The Old Verse is for Old Testament scripture-inspired songs, biblical meditation music, cinematic worship, psalm-like prayer music, and ancient Bible story ballads.
- It follows the Old Testament sequence from Genesis onward. Do not use this profile for New Testament/Gospel/Jesus-focused releases; use `The New Verse` instead.
- Do not use this profile for fantasy/game OST, generic BGM, EDM, pop, or popular-song covers.

## Visual Identity

- Mood: reverent, ancient, cinematic, contemplative, sacred, story-driven.
- Style must be illustrated, anime, painterly, storybook, illuminated-manuscript, or stylized biblical landscape. Avoid photorealistic/live-action looks.
- Let the selected passage decide the scene and subject.
- Prefer symbolic biblical imagery over direct depiction of God the Father.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
- The cover must include only a large lower-left `The Old Verse` channel brand label.
- Make `The Old Verse` clearly readable on mobile playback. Target roughly 18-24% of image width, or 5-6% of image height for text cap height.
- Do not add title text, verse text, scripture paragraphs, genre text, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.
- Match the scene to the selected Old Testament passage: creation waters, Eden, wilderness, covenant stars, ark, desert road, tabernacle, temple, psalm imagery, or prophetic landscape.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable click text, for example `GENESIS SONGS`, `OLD TESTAMENT`, `BIBLE MUSIC`, `PSALMS MUSIC`, `SCRIPTURE SONGS`, or `EXODUS MUSIC`.
- Add `THE OLD VERSE` as the brand line. Keep this brand line visually consistent with the lower-left cover channel label.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.
- Do not paste long scripture text onto the thumbnail.

## Loop Video

- Use Dreamina/Seedance or Gemini only for the moving clip.
- For Dreamina/Seedance, use `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `6 seconds`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `6 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
- Animate the selected cover concept with reverent environmental motion: slow light over water, drifting stars, candle or oil-lamp glow, scroll dust, desert wind, cloud/fire glow, rain, water shimmer, leaves, or temple light when appropriate.
- Preserve the large, readable lower-left `The Old Verse` text exactly for the full clip.
- The final moment should stay close to the opening composition so the app can repeat it smoothly.
- Do not add subtitles, lyrics, verse text, title text, duration text, UI, logos, protected film imagery, or photorealistic reenactment footage.

Prompt shape:

```text
Use the uploaded first-frame image as the exact starting frame. It contains the exact large, readable lower-left channel brand label "The Old Verse".
Create one continuous animated scripture-inspired music visualizer shot for an Old Testament Bible music release.
Preserve the opening composition, lighting, palette, illustrated/stylized visual language, and the specific biblical scene from the first frame.
Preserve the large, readable lower-left "The Old Verse" text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, shrink, flicker, or change it.
Animate reverent environmental motion naturally present in the scene: slow light movement, stars, candle or oil-lamp glow, scroll dust, desert wind, cloud/fire glow, rain, water shimmer, leaves, or temple light when appropriate.
The motion must progress naturally for the full clip. Do not repeat any segment. Do not ping-pong or restart motion.
The final moment should preserve the same crop, framing, camera distance, lighting, palette, and subject placement; only ambient details may differ.
Stable composition, no hard cuts, no photorealism, no live action, no direct depiction of God the Father, no protected characters, no other text, no subtitles, no logos, no UI.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds vague, doctrinally awkward, or less clickable, rewrite it while keeping the passage reference, Old Testament theme, and broad music style truthful.
- Default metadata language should be English unless the human asks otherwise.
- Include the passage reference in the main title, every localized title, and the description, for example `Genesis 1:1-5`.
- The first description paragraph must clearly say which passage inspired the music and what theme was adapted, for example creation, covenant, wilderness trust, lament, deliverance, wisdom, or prophetic hope.
- Also include one natural music-style sentence in the description, such as `This release is arranged as cinematic scripture worship with acoustic folk, strings, and prayerful vocal songs.` Do not hide the style, but keep it descriptive rather than technical.
- Titles should include Old Testament/Bible/scripture keywords plus a listening use case such as worship, reflection, prayer, study, or quiet focus.
- Make titles broad and public-facing first. Use exact passage scene details as atmosphere unless they are the strongest searchable hook.
- Keep each release in one coherent style family, with controlled variety across tracks. Do not make one playlist jump randomly between unrelated styles. For example, use a cinematic scripture-folk / ancient worship / psalm-like prayer lane, then vary tempo, instrumentation, and emotional intensity inside that lane.
- Avoid denominational claims, copyrighted translation names, and protected media references.
