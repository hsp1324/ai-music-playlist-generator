# OpenClaw Channel Profile: Soft Hour Radio

Use this profile only after channel selection returns `Soft Hour Radio`, or when the human explicitly says to upload to `Soft Hour Radio`.

## Routing Contract

- Explicit channel request wins. If the human says `Soft Hour Radio에 올려줘`, this profile is mandatory even if the music mentions Japan, J-pop, city-pop, or anime influence.
- Do not use the Tokyo Daydream Radio three-people-walking signature unless the human explicitly asks for that exact visual.
- Default content is background/cafe/sleep/study/work/chill/BGM. These releases are usually instrumental/no-vocal unless the human asks for vocals.

## Visual Identity

- Mood: calm, useful, warm, focused, restful, long-listening friendly.
- Good scenes: cafe window, piano room, moonlit bedroom, soft rain on glass, forest light, ocean horizon, candle detail, desk lamp, bookshelf, slow landscape, warm abstract light, close-up instrument detail.
- Human presence is optional and subtle. If people appear, do not default to three people walking away from the camera.
- Style must be animated, anime, illustrated, or stylized. Avoid photorealistic/live-action looks.

## Cover

- Create one final clean 16:9 cover first.
- The cover is the playback visual and Dreamina/Seedance first frame.
- Keep it text-free by default.
- If the human explicitly asks for channel text inside the video, the cover may contain only a small lower-left `Soft Hour Radio` label.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Add short readable use-case/mood text, for example `CAFE PIANO`, `FOCUS MUSIC`, `STUDY BGM`, `DEEP SLEEP`, `RAINY NIGHT`, or `CALM READING`.
- Add smaller `SOFT HOUR RADIO` as the brand line.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, or clocks unless the human explicitly asks.

## Loop Video

- Use Dreamina/Seedance only for the moving clip.
- Use Dreamina/Seedance `2.0 Fast`, first-frame only, no Omni Reference, no last-frame reference, `16:9`, `720p`, exactly `8 seconds`.
- Do not put `8 seconds`, `16:9`, `720p`, `loop`, `seamless loop`, `repeat`, or `cyclic` in the Dreamina prompt. Set those in the UI controls.
- The loop video should be calm environmental motion: soft rain, candle flicker, drifting dust, slow moonlight, gentle curtains, ocean shimmer, forest light, piano-room ambience, or warm abstract light.

Prompt shape:

```text
Use the uploaded clean text-free first-frame image as the exact starting frame.
Create one continuous calm animated music visualizer shot for a Soft Hour Radio background-music release.
Do not use the Tokyo three-people-walking signature unless explicitly requested.
Preserve the opening composition, lighting, palette, and illustrated/stylized visual language.
Adapt the motion to the release mood with slow environmental motion.
The motion must progress naturally for the full clip.
Do not repeat any segment. Do not ping-pong or restart motion.
Stable composition, no hard cuts, no photorealism, no live action, no camera-photo realism, no text, no subtitles, no logos, no UI, no unwanted people or characters.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Titles should include listening use cases such as study, work, sleep, reading, rest, cafe, focus, or relaxation.
- Korean copy must not use `인스트루멘털`, `인스투르멘털`, or `인스트루멘탈`; use `BGM`, `가사 없는 BGM`, `보컬 없는 BGM`, or `연주곡`.
