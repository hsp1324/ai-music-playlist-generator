# OpenClaw Channel Profile: BibliaCanto

Use this profile only after channel selection returns `BibliaCanto`, or when the human explicitly says to upload scripture music to `BibliaCanto`.

## Routing Contract

- Explicit channel request wins.
- BibliaCanto is now the combined scripture channel for Old Testament and New Testament songs arranged as modern, secular-pop-adjacent scripture music: hip-hop, rap-pop, trap-soul, boom bap, R&B, alt-R&B, neo-soul, K-pop-inspired pop, Afropop/Amapiano-pop, and synth-pop.
- It follows two app-managed scripture branches: Old Testament from Genesis onward and New Testament from Matthew onward. New Testament releases still upload to `BibliaCanto`; `불송` is reserved for Buddhist scripture-inspired music, not Bible uploads.
- Do not use this profile for fantasy/game OST, generic BGM, EDM, unrelated pop, popular-song covers, or church-style worship/gospel releases.

## Visual Identity

- Mood: reverent, ancient, cinematic, contemplative, story-driven, but not church-branded.
- Style must be illustrated, anime, painterly, storybook, illuminated-manuscript, or stylized biblical landscape. Avoid photorealistic/live-action looks.
- Let the selected passage decide the scene and subject for both the cover image and YouTube thumbnail. Do not use a generic Bible poster background when a concrete passage scene or theme is available.
- Prefer symbolic biblical imagery over direct depiction of God the Father.

## Cover

- Create one final 16:9 cover first.
- The cover is the playback visual and first-frame reference for Dreamina/Seedance/Gemini.
- Do not put `BibliaCanto`, `Old Verse`, `New Verse`, the channel name, a channel logo, or a brand line on the cover/first-frame.
- If text is useful, use the exact selected passage range and/or modern music lane, such as `Genesis 1:1-5`, `Matthew 1:18-25`, `Old Testament Hip-Hop`, `New Testament R&B`, `Bible K-Pop`, or `Scripture Rap`.
- Do not add scripture paragraphs, title sentences, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.
- Match the cover scene to the selected passage and branch. Old Testament examples: creation waters, Eden, wilderness, covenant stars, ark, desert road, tabernacle, temple, psalm imagery, or prophetic landscape. New Testament examples: road, hillside, Galilee shore, table, lamp, doorway, empty tomb light, cross silhouette, prayer hands, scroll, or warm passage-based landscape.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative, so the thumbnail keeps the same passage-based scene instead of becoming a generic Bible poster.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Put the exact selected passage range from the public title on the thumbnail, such as `Genesis 1:1-5` or `Matthew 1:18-25`, unless the human explicitly asks for no passage text. Add short readable click text that connects to that passage, book, theme, and modern hip-hop/R&B/K-pop-style listening lane.
- Do not use `Old Verse`, `New Verse`, `The Old Verse`, `The New Verse`, `OLD VERSE`, or `NEW VERSE` anywhere on BibliaCanto visuals. Avoid making `OLD TESTAMENT` or `NEW TESTAMENT` the largest thumbnail headline when a specific passage range is available; the passage range should be the identifying text.
- Generic text such as `OLD TESTAMENT HIP-HOP`, `NEW TESTAMENT R&B`, `BIBLE K-POP`, `SCRIPTURE RAP`, `PSALMS HIP-HOP`, or `EXODUS TRAP` may be used as secondary support, but do not leave the thumbnail as only a broad genre label when the release has a specific passage and theme.
- Good thumbnail wording should feel like a natural YouTube Bible music thumbnail for modern listeners, not a raw genre tag or a church-service poster. Prefer a passage/book cue, a clear theme cue, or a modern style cue when it helps viewers understand what this release is about.
- Do not add `BIBLIACANTO`, the channel name, or a channel logo.
- Do not use a black text box or hard rectangular background behind text. All passage and support text must sit directly on the image with a transparent background; use font weight, color, subtle shadow, thin outline, or local contrast for readability instead of black boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, stickers, badges, pills, capsules, or any filled label shape.
- Keep all thumbnail text inside safe margins with breathing room. Reject/regenerate if text is clipped, cramped inside a shape, too close to the edge, pasted over the art, or separated from the scene.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.
- Do not paste long scripture text onto the thumbnail.

## Loop Video

- Use Dreamina/Seedance or Gemini only for the moving clip.
- For Dreamina/Seedance, use `Seedance 2.0 Mini`, first-frame/start-frame only, no Omni Reference, no last-frame/end-frame reference, `16:9`, `720p`, exactly `10 seconds`. Do not upload both first and last frames, because Dreamina switches that setup back to `Seedance 2.0 Fast`. For Gemini, use image-to-video/Create video from the same first-frame cover, choose `16:9` when available, do not mention duration, and download the generated MP4 as-is after inspection; try Gemini first unless its 24 hour cooldown is active; count only successful Gemini video generations, and after the 3rd successful Gemini video use Dreamina/Seedance until 24 hours have passed from that 3rd generation.
- Do not put `10 seconds`, `5 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the generation prompt. Do not mention duration in Gemini prompts. Set duration only in Dreamina/Seedance controls.
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
- The first description paragraph must clearly say which passage inspired the music and what theme was adapted. Old Testament examples include creation, covenant, wilderness trust, lament, deliverance, wisdom, or prophetic hope. New Testament examples include grace, mercy, discipleship, healing, resurrection hope, or kingdom teaching.
- Also include one natural music-style sentence in the description, such as `This release turns Genesis 1:1-5 into modern scripture hip-hop and R&B with sung hooks, 808 drums, and cinematic synths.` Do not hide the style, but keep it descriptive rather than technical.
- Titles should include Old Testament or New Testament/Bible/scripture keywords plus a clear modern style and listening use case, such as hip-hop, R&B, K-pop-inspired pop, rap, night listening, reflection, study, hope, or focus.
- Make titles broad and public-facing first. Use exact passage scene details as atmosphere unless they are the strongest searchable hook.
- Keep each release in one coherent style family, with controlled variety across tracks. Do not make one playlist jump randomly between unrelated styles.
- Rotate the release-level music lane across BibliaCanto uploads instead of defaulting to church music. Pick one lane for the whole release before generating tracks, then keep every track inside that family so the public title can truthfully name the genre.
- Valid release-level lanes include scripture hip-hop, Bible R&B, K-pop-inspired scripture pop, scripture rap-pop, trap-soul scripture songs, boom-bap Bible rap, alt-R&B scripture songs, neo-soul scripture songs, Afropop/Amapiano-pop scripture songs, dark street-pop scripture, and synth-pop scripture songs. Use these as direction, not fixed title templates.
- Never choose Gospel music, gospel choir, worship, praise band, CCM, hymns, congregational singing, choir-backed worship, piano worship ballads, Christian-rock worship, pipe-organ church music, altar-call music, or generic holy worship for BibliaCanto Suno work. Add these church-style terms to Suno excluded styles.
- If the selected lane is hip-hop, make the whole release hip-hop/rap-pop/trap/boom-bap based. If it is R&B, make the whole release R&B/alt-R&B/neo-soul based. If it is K-pop-inspired, use K-pop production, hooks, and rap-pop energy while keeping English lyrics unless the human explicitly asks for another language.
- Include the selected lane naturally in the title and description, for example as `Genesis Creation Hip-Hop`, `Old Testament Trap-Soul`, `Matthew New Testament R&B`, `Bible K-Pop Scripture Songs`, or another natural public-facing phrase that fits the passage.
- The app will add each uploaded scripture release to `Old Testament Songs` or `New Testament Songs` and also to one modern style playlist when the lane is clear. Make the lane obvious in the title/description/tags so classification works.
- Avoid denominational claims, copyrighted translation names, and protected media references.
