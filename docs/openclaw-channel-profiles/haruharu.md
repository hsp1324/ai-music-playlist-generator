# OpenClaw Channel Profile: HaruHaru

Use this profile only after channel selection returns `HaruHaru`, or when the human explicitly says to upload to `HaruHaru`.

## Routing Contract

- This profile is for Korean-language K-pop vocal releases: K-pop, Korean dance-pop, idol-pop inspired music, Korean synth-pop, Korean pop-rock, Korean R&B pop, and similar Korean vocal pop.
- Music defaults to original Korean vocal songs with lyrics.
- Do not route J-pop/Japanese pop here; use `Tokyo Daydream Radio`.
- Do not route English/American pop here; use `sundaze`.
- Do not route Latin/Spanish pop here; use `Solwave Radio`.
- Do not route instrumental/BGM/no-vocal releases here unless the human explicitly asks for a Korean-pop-flavored instrumental.
- Do not use existing popular-song remake/cover concepts here; those are manual-only and not part of HaruHaru automation.

## Visual Identity

- HaruHaru now defaults to photorealistic Korean lifestyle still-image visuals, not animated/anime rotation.
- The visual should feel like an attractive adult's natural Instagram-style daily-life photo: Hongdae street, Itaewon night/cafe street, Seoul cafe terrace, seaside trip, beach road, Han River sunset, city crosswalk, rooftop, subway exit, record shop, boutique, or rainy window.
- Main subjects can be a stylish adult woman, a handsome stylish adult man, or a tasteful adult couple/friend pair when the release concept supports it.
- Faces do not need to be hidden. A natural face, three-quarter view, side profile, soft eye contact, or candid looking-away pose is allowed and preferred when it feels like real daily life.
- Keep the subject clearly adult. Do not use minors, teen-coded styling, school uniforms, childlike poses, celebrity likenesses, or idol-member lookalikes.
- Styling should be fashionable, pretty, cool, and natural: casual streetwear, cafe outfit, beach resort outfit, leather jacket, knitwear, denim, coat, summer dress, or clean Korean fashion editorial styling.
- Keep it non-explicit: no nudity, no visible nipples/genitals, no transparent clothing revealing intimate areas, no underwear-focus, no fetish framing, no sexual acts, and no pornographic posing.
- Do not add logos, channel names, style words, title text, sticker-like labels, UI, captions, or decorative badges to the cover, thumbnail, or still frame by default.
- HaruHaru no longer needs a provider loop video during normal automation. Use a high-quality still cover/thumbnail package and let the app render the final video from the still image.
- The final app render should add only the app-managed audio spectrum near the lower-right and app-managed lyric subtitles near the lower-left. OpenClaw must not bake spectrum bars, waveform graphics, or lyric text into the static cover/thumbnail.

## Cover

- Create one final photorealistic 16:9 cover first, preferably 1920x1080 or higher.
- The cover is the playback visual for the still-image render.
- Do not put `HaruHaru`, the channel name, a channel logo, or a brand line on the cover/first-frame.
- Do not put Korean pop lane text such as `K-POP`, `K-R&B`, `DANCE POP`, `SYNTH POP`, or `POP ROCK` on the cover unless the human explicitly asks.
- Leave safe negative space around the lower-left and lower-right when possible, because the app may place lyrics at lower-left and spectrum at lower-right in the final render.
- Good cover directions: stylish adult woman in profile at a Hongdae cafe window; handsome stylish adult man on an Itaewon evening street; adult woman on a seaside road with wind in hair; fashionable adult couple near a Seoul cafe street; natural candid portrait at a rainy city crosswalk.
- Do not add title sentences, duration text, lyrics, subtitles, UI, logos, spectrum bars, waveform graphics, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same face, subject placement, lighting, palette, props, clothing colors, and camera angle from the cover.
- By default, do not add thumbnail text. The HaruHaru thumbnail should look like a premium natural lifestyle photo, not a graphic poster.
- If the human explicitly requests text later, keep it very small and integrated; never add the channel name or a logo.
- Do not add `HARUHARU`, the channel name, or a channel logo.
- Keep the main subject visually important; text must fit around the subject and must not push the subject into an awkward crop.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers.

## Still-Image Video Render

- Do not create a Gemini, Dreamina, or Seedance loop video for normal HaruHaru releases.
- Do not upload `--loop-video` for normal HaruHaru releases.
- Queue the app render as still image:

```bash
scripts/openclaw-release render-video \
  --release-id RELEASE_ID \
  --allow-still-image-video \
  --video-render-source-mode still_image \
  --video-render-resolution 1080p \
  --video-spectrum-overlay-style bars \
  --lyrics-overlay \
  --lyrics-overlay-style editorial-lower-left
```

- The app spectrum overlay belongs near the lower-right of the final rendered MP4.
- The app lyric overlay belongs near the lower-left of the final rendered MP4.
- If the cover composition would make lower-left lyrics or lower-right spectrum unreadable, remake the static cover/thumbnail with more clean space in those areas instead of baking text boxes into the image.
- Only use a provider loop video for HaruHaru when the human explicitly asks for a moving visual. In that exception, follow the general provider-video safety rules and still avoid channel names/logos/text.

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds awkward, weak, or less clickable, rewrite it while keeping the K-pop identity, emotion, and real listening use case truthful.
- Main upload metadata should be Korean. Use `--default-language ko` when OpenClaw approves metadata manually.
- Provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Turkish, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese metadata.
- The top-level `--title` / `--description-file` and `--ko-title` / `--ko-description-file` should match.
- Playlist titles must start with `[playlist]` and should feel like curated editorial K-pop playlists, not raw workspace names.
- Use a title shape with the specific genre lane near the front, then a clear use case or emotion. Good examples: `[playlist] K-POP 힙합 믹스 | 운동, 러닝, 외출 준비, 자신감 충전`, `[playlist] Korean R&B 플레이리스트 | 이별, 늦은 밤, 혼자 듣는 노래`, `[playlist] K-POP 신스팝 드라이브 | 밤길, 도시 불빛, 자신감 충전`.
- Keep the whole release in one lane such as K-pop hip-hop, Korean R&B pop, dance-pop, synth-pop, pop-rock, soul/neo-soul pop, or ballad-pop, and name that lane in the title/description when accurate.
- Do not use the visual scene as the main title hook unless it is broadly searchable. A rooftop, rainy street, practice room, cafe, or bus stop can guide cover/video mood, but the title should usually focus on K-pop energy, workout, running, getting ready, party warmup, night drive, heartbreak, confidence, or feel-good listening.
- Every track should have original Korean lyrics and a distinct hook concept unless the human explicitly requested instrumental/no-vocal.
- Lyrics are judged by song quality first: melody fit, beat, vocal tone, hook, emotional arc, and replay value. They do not need to mention the title/use case.
- In localized descriptions, preserve timestamps exactly. Translate surrounding prose, recommended-use lines, hashtags, and track titles naturally for that language unless the human asks to keep Korean track titles.
