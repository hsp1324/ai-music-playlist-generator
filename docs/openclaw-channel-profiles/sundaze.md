# OpenClaw Channel Profile: sundaze

Use this profile only after channel selection returns `sundaze`, or when the human explicitly says to upload to `sundaze`.

## Routing Contract

- This profile is for English/American pop playlist releases: English-language pop, American pop, US/UK pop, western pop, mainstream vocal pop, dance-pop, synth-pop, pop-rock, Pop R&B, pop hip-hop, indie pop, bedroom pop, alt-pop, acoustic pop, singer-songwriter pop, folk-pop, country pop, Americana pop, soft rock, adult-contemporary pop, pop-punk, Y2K/recession pop, disco/funk pop, Afrobeats, Afropop, and Amapiano-pop.
- Treat `sundaze` as the US/English-pop playlist counterpart to `Tokyo Daydream Radio`.
- Do not route J-pop/Japanese pop to this channel. Use `Tokyo Daydream Radio` for Japanese pop and `Solwave Radio` for Latin/Spanish pop.
- Do not route Spanish-language Latin pop to this channel. Use `Solwave Radio` for Latin/Spanish pop. English-forward Afropop/Amapiano-pop can use `sundaze`; no-vocal Afro house or club/DJ mix concepts belong on `Club Bloom`.
- Music defaults to vocal songs with original English lyrics unless the human explicitly asks for instrumental/BGM/no vocals.

## Visual Identity

- sundaze must use photorealistic English/American lifestyle still-image visuals by default, similar to HaruHaru and Solwave Radio. This is the normal automation path, not a fallback; do not use anime, illustrated, stylized, abstract, or generic graphic visuals for normal sundaze releases.
- Let the playlist concept decide the exact scene, but keep the image modern, bright, pop-friendly, and immediately English/American-pop-coded.
- Use a casual friend-taken phone-photo or natural lifestyle snapshot feeling rather than a glossy studio shoot, fashion campaign, or over-polished AI portrait.
- Good scene families: open highway at golden hour, summer car stop, city rooftop, beach boardwalk, cafe terrace, country road, Americana diner, bedroom-pop room, indie record shop, festival lawn, neon night drive, or casual downtown walk.
- Main subjects can be a stylish clearly adult woman, stylish adult man, tasteful adult couple, or adult friend pair when the release concept supports it. Faces may be visible, but prefer natural side, three-quarter, candid looking-away, laughing, or medium/framed-with-scene compositions over tight straight-on beauty close-ups.
- Styling should feel pop-natural and current: denim, leather jacket, sundress, casual streetwear, country-pop road-trip outfit, festival outfit, cafe outfit, or warm summer-night clothing.
- Do not force people into every visual. Use people only when they strengthen the playlist concept and thumbnail appeal.
- Keep it non-explicit: no nudity, no visible nipples/genitals, no transparent clothing revealing intimate areas, no underwear-focus, no fetish framing, no minors or teen-looking subjects, and no sexual acts. The subject should read as confident/pop-stylish rather than pornographic.
- Do not add logos, channel names, title sentences, lyric text, subtitles, UI, badges, stickers, waveform graphics, spectrum bars, or unrelated words to the cover, thumbnail, first frame, or still-image render source.
- sundaze no longer needs a provider loop video during normal automation. Use a high-quality photorealistic still cover/thumbnail package and let the app render the final video from the still image with app-managed lyrics at lower-left and spectrum at lower-right.

## Cover

- Create one final photorealistic 16:9 cover first, preferably 1920x1080 or higher.
- The cover is the playback visual for the still-image render.
- Do not put `sundaze`, the channel name, a channel logo, or a brand line on the cover/first-frame.
- By default, keep the cover clean and text-free. If text is useful for the release concept, use only one small integrated upper-left English-pop lane phrase such as `POP R&B`, `DANCE POP`, `SYNTH POP`, `COUNTRY POP`, `AMERICANA POP`, `INDIE POP`, `POP ROCK`, `AFRO POP`, `AMAPIANO POP`, `FEEL GOOD POP`, `SUMMER POP`, or `NIGHT DRIVE`.
- Leave clean lower-left and lower-right space when possible, because the app places lyric subtitles near the lower-left and the spectrum overlay near the lower-right in the final render.
- Do not add title sentences, duration text, lyrics, subtitles, UI, logos, spectrum bars, waveform graphics, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Keep the same photorealistic casual lifestyle image package. Add one short readable pop click phrase matched to the playlist concept, preferably integrated in upper-left negative space, for example `POP HITS`, `SUMMER POP`, `NIGHT DRIVE`, `DANCE POP`, `POP R&B`, `COUNTRY POP`, `AMERICANA POP`, `INDIE POP`, `POP ROCK`, `AFRO POP`, `AMAPIANO POP`, `FEEL GOOD POP`, or `HEARTBREAK POP`.
- The thumbnail may slightly improve contrast/readability, but it should still feel like a natural friend-taken photo, not a polished campaign key visual.
- Text should feel integrated into the photo, not like a pasted sticker, badge, button, or hard box. The text background must stay transparent: letters sit directly on the photo, with readability from font weight, color, subtle shadow, thin outline, or local contrast only. Do not add black boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, stickers, badges, pills, capsules, or any filled label shape behind text. Keep the main subject visually important and do not push the subject into an awkward crop.
- Do not add `SUNDAZE`, the channel name, or a channel logo.
- Keep all thumbnail text inside safe margins with breathing room. Reject/regenerate if text is clipped, cramped inside a shape, too close to the edge, pasted over the art, separated from the scene, or placed on any filled/black/semi-transparent background.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Still-Image Video Render

- Do not create a Gemini, Dreamina, or Seedance loop video for normal sundaze releases.
- Do not upload `--loop-video` for normal sundaze releases.
- Queue the app render as a still image with lower-left lyrics and lower-right spectrum:

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

- The app lyric subtitles belong near the lower-left and the spectrum overlay belongs near the lower-right of the final rendered MP4.
- If the cover composition would make the lower-left lyrics or lower-right spectrum unreadable, remake the static cover/thumbnail with cleaner space instead of baking boxes, waveform graphics, or lyrics into the image.
- Only use a provider loop video for sundaze when the human explicitly asks for a moving visual.

Provider-video prompt shape, only when a human explicitly requests motion:

```text
Use the uploaded first-frame image as the exact starting frame.
Create one uninterrupted animated English/American pop playlist visual take.
Preserve the opening composition, lighting, palette, subject placement, casual friend-taken phone-photo English/American lifestyle language, clothing colors, face identity, and camera distance.
Animate natural motion that fits the specific playlist concept and pop mood.
If the first frame already contains a short pop/style phrase, keep it stable and readable. Do not invent a channel name.
The final moment should remain close to the opening composition, camera distance, lighting, palette, and subject placement without becoming frozen.
No new text, subtitles, logos, UI, channel branding, title sentences, lyrics, waveform graphics, or spectrum bars.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds awkward, weak, or less clickable, rewrite it while keeping the English-pop identity and real listening use case truthful.
- Main upload metadata should be English. Use `--default-language en` when OpenClaw approves metadata manually.
- Provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Turkish, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese metadata.
- The top-level `--title` / `--description-file` and `--en-title` / `--en-description-file` should match.
- Localized YouTube titles may be natural adaptations in each language instead of exact English copies. If a literal translation is awkward or less clickable, rewrite the localized title while keeping the English-pop identity and actual listening use case truthful.
- In every localized description, keep timestamped tracklist song titles in English exactly as the English description. Translate only the surrounding description prose, recommended use-case line, and hashtag line.
- Playlist titles must start with `[playlist]` and should feel like curated editorial playlists, not raw workspace names. Do not write short generic titles such as `Golden Hour Drive Pop`, `English Pop`, or `American Pop` by themselves.
- Use an `Essential`-style playlist title shape with the selected genre lane near the front: a vivid situation or emotion + Pop R&B / pop hip-hop / dance-pop / synth-pop / pop-rock / country pop / Americana pop / indie pop / bedroom pop / alt-pop / acoustic pop / singer-songwriter pop / folk-pop / soft rock / pop-punk / Y2K pop / disco-pop / funk-pop / Afropop / Amapiano-pop identity + a listening use case. The title should make the click promise obvious before the viewer opens the video.
- Keep the whole release in one lane such as Pop R&B, pop hip-hop, dance-pop, synth-pop, pop-rock, country pop, Americana pop, indie pop, bedroom pop, alt-pop, acoustic pop, singer-songwriter pop, folk-pop, soft rock, adult-contemporary pop, pop-punk, Y2K/recession pop, disco/funk pop, Afrobeats, Afropop, or Amapiano-pop, and name that lane in the title/description when accurate.
- Reused tracks must be genre-compatible with the title. If the back-half reuse pool is mostly broader feel-good pop, park-walk pop, pop-rock, indie-pop, or road-trip pop, title the release as that broader lane. Do not leave `pop hip-hop` / `rap-pop` in the title, localized titles, description, tags, cover text, or thumbnail text unless most tracks actually carry that lane in their stored style/prompt.
- Make the title broad and public-facing first. The cover/video scene can be specific, but do not let a narrow scene name become the main hook unless it is the strongest searchable phrase.
- Match listening use cases to the actual energy. For energetic rooftop, club, dance-pop, bass-heavy, or workout-feeling releases, prefer getting ready, workout, running, party warmup, driving, nightlife, and confidence. Avoid `focus`, `study`, or `quiet work` unless the rendered audio is genuinely calm enough for those uses.
- Strong examples:
  `[playlist] Sunset Highway Pop-Rock Drive | Windows Down Road Trip Music`
  `[playlist] Feel-Good Pop R&B Essentials | Summer Drive, Walk and Good Days`
  `[playlist] Country Pop Road Trip | Highway Songs for Summer Nights`
  `[playlist] Afropop Summer Nights | English Pop Dance Songs for Beach Drives`
  `[playlist] Late Night English Pop Mix | City Lights, Heartbreak and Drive Music`
  `[playlist] Golden Hour Soul-Pop Drive | Warm Vocals, Open Roads and Good Days`
- Every track should have original English lyrics and a distinct hook concept unless the human explicitly requested instrumental/no-vocal.
- Lyrics are judged by song quality first: melody fit, vocal tone, hook, emotional arc, and replay value. They do not need to mention the title/use case.
