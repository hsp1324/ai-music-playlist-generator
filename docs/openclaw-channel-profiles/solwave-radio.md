# OpenClaw Channel Profile: Solwave Radio

Use this profile only after channel selection returns `Solwave Radio`, or when the human explicitly says to upload to `Solwave Radio`.

## Routing Contract

- This profile is for Latin/Spanish-language music: Latin pop, Spanish pop, urbano latino, reggaeton pop, bachata pop, salsa pop, cumbia pop, tropical dance-pop, verano latino, and similar vocal releases.
- Treat `Solwave Radio` as the Spanish/Latin counterpart to `Tokyo Daydream Radio`.
- Do not route English pop to this channel. Use `sundaze` for English/American pop and `Tokyo Daydream Radio` for Japanese pop.
- Music defaults to vocal songs with original Spanish lyrics unless the human explicitly asks for instrumental/BGM/no vocals.

## Visual Identity

- Solwave Radio now defaults to photorealistic Latin/Spanish lifestyle visuals with a casual friend-taken Instagram phone-photo feeling: travel, nightlife, romance, beach, terrace, road-trip, or city-street moments that feel posted by a friend rather than shot by a professional photographer.
- Let the playlist concept decide the exact scene, but keep the image warm, rhythmic, natural, and immediately Latin/Spanish-pop-coded. Avoid studio portraits, glossy fashion campaigns, commercial ads, and over-polished photographer/editorial lighting.
- Good scene families: Latin coastal cafe terrace, warm city street after rain, beach road at golden hour, rooftop fiesta, tropical rain window, plaza dance night, seaside drive, open-air bar, summer balcony, night-market street, or poolside resort walkway.
- Main subjects can be a stylish clearly adult Latina woman, stylish adult Latino man, tasteful adult couple, or adult friend pair when the release concept supports it. Faces may be visible, including natural side profile, three-quarter view, soft eye contact, candid looking-away poses, laughing, dancing lightly, or glancing at the phone.
- Styling should be fashionable, confident, warm, and natural: summer-night outfit, resort outfit, linen, satin blouse, light jacket, denim, streetwear, or tastefully layered beachwear that feels like a real night out, not an editorial shoot.
- Prefer ordinary smartphone snapshot details: slightly imperfect framing, mild motion softness, natural phone-camera depth, warm mixed street/cafe lighting, small real-world imperfections, and enough background environment to feel like a real night out. Avoid tight straight-on AI-beauty close-ups, face-filling model portraits, doll-like symmetry, plastic skin, and professional photoshoot poses.
- Keep it non-explicit: no nudity, no visible nipples/genitals, no transparent clothing revealing intimate areas, no underwear-focus, no fetish framing, no minors or teen-looking subjects, and no sexual acts. The subject should read as confident/pop-stylish rather than pornographic.
- Do not add logos, channel names, title sentences, lyric text, subtitles, UI, badges, stickers, waveform graphics, spectrum bars, or unrelated words to the cover, thumbnail, first frame, or still-image render source.
- Solwave Radio no longer needs a provider loop video during normal automation. Use a high-quality still cover/thumbnail package and let the app render the final video from the still image with app-managed lyrics at lower-left and spectrum at lower-right.

## Cover

- Create one final photorealistic 16:9 cover first, preferably 1920x1080 or higher.
- The cover is the playback visual for the still-image render.
- Do not put `Solwave Radio`, the channel name, a channel logo, or a brand line on the cover/first-frame.
- By default, keep the cover clean and text-free. If text is useful for the release concept, use only one small integrated upper-left Latin/Spanish lane phrase such as `POP LATINO`, `REGGAETON SUAVE`, `BACHATA POP`, `LATIN R&B`, `VERANO LATINO`, or `NOCHE LATINA`.
- The cover should feel like a friend snapped it on a recent phone for Instagram: candid, relaxed, slightly imperfect, and place-aware. Do not make it look like a studio shoot, fashion editorial, luxury ad, or professional photographer portfolio image.
- Do not add title sentences, duration text, lyrics, subtitles, UI, logos, or unrelated words to the cover.
- Leave clean lower-left and lower-right space when possible, because the app places lyric subtitles near the lower-left and the spectrum overlay near the lower-right in the final render.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same scene, subject placement, lighting, palette, props, and camera angle from the cover.
- Keep the same photorealistic friend-taken Instagram phone-photo image package. Add one short readable Latin/Spanish click phrase matched to the playlist concept, preferably integrated in upper-left negative space, for example `LATIN POP`, `REGGAETON`, `VERANO LATINO`, `SPANISH POP`, `FIESTA LATINA`, `BACHATA POP`, `LATIN R&B`, or `NOCHE LATINA`.
- The thumbnail may slightly improve contrast/readability, but it should still feel like a real friend/phone photo, not a polished campaign key visual.
- Text should feel integrated into the photo, not like a pasted sticker, badge, button, or hard box. The text background must stay transparent: letters sit directly on the photo, with readability from font weight, color, subtle shadow, thin outline, or local contrast only. Do not add black boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, stickers, badges, pills, capsules, or any filled label shape behind text. Keep the main subject visually important and do not push the subject into an awkward crop.
- Do not add `SOLWAVE RADIO`, the channel name, or a channel logo.
- Do not add duration badges such as `1 HOUR`, `60 MIN`, clocks, or timers unless the human explicitly asks.

## Still-Image Video Render

- Do not create a Gemini, Dreamina, or Seedance loop video for normal Solwave Radio releases.
- Do not upload `--loop-video` for normal Solwave Radio releases.
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
- Only use a provider loop video for Solwave Radio when the human explicitly asks for a moving visual. In that exception, follow the general provider-video safety rules and still avoid channel names/logos/text.

Provider-video prompt shape, only when a human explicitly requests motion:

```text
Use the uploaded first-frame image as the exact starting frame.
Create one uninterrupted animated Latin/Spanish pop visual take.
Preserve the opening composition, lighting, palette, subject placement, casual friend-taken phone-photo Latin/Spanish lifestyle language, clothing colors, face identity, and camera distance.
Animate natural motion that fits the specific playlist concept and Latin pop mood: rain shimmer, terrace lights, palm leaves, city reflections, ocean wind, fabric/hair movement, dancing background silhouettes, or warm cafe/bar light flicker when present.
If the first frame already contains a short Latin/Spanish style phrase, keep it stable and readable. Do not invent a channel name.
The final moment should remain close to the opening composition, camera distance, lighting, palette, and subject placement without becoming frozen.
No new text, subtitles, logos, UI, channel branding, title sentences, lyrics, waveform graphics, or spectrum bars.
```

## Metadata

- Use [../openclaw-youtube-metadata.md](../openclaw-youtube-metadata.md).
- Localized YouTube titles must be natural transcreations in each language. If a literal translation sounds awkward, weak, or less clickable, rewrite it while keeping the Latin/Spanish-pop identity and real listening use case truthful.
- Main upload metadata should be Spanish. Use `--default-language es` when OpenClaw approves metadata manually.
- Provide Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Turkish, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese metadata.
- The top-level `--title` / `--description-file` and `--es-title` / `--es-description-file` should match.
- Playlist titles must start with `[playlist]` and should feel like curated editorial playlists, not raw workspace names. Do not write short generic titles such as `Ruta Dorada Pop`, `Latin Pop`, `Spanish Pop`, or `Pop para manejar` by themselves.
- Use an `Essential`-style title shape with the selected genre lane near the front: a vivid situation or emotion + Pop Latino / reggaeton pop / urbano latino / bachata pop / salsa pop / cumbia pop / Latin R&B / Latin soul identity + a listening use case. The title should make the click promise obvious before the viewer opens the video.
- Keep the whole release in one lane such as Pop Latino, reggaeton pop, urbano latino, bachata pop, salsa pop, cumbia pop, Latin R&B, Spanish R&B, or Latin soul, and name that lane in the title/description when accurate.
- Make the title broad and public-facing first. The cover/video scene can be specific, but do not let a narrow scene name become the main hook unless it is the strongest searchable phrase.
- Good Solwave title ingredients: `Pop Latino`, `Spanish Pop`, `Reggaeton Suave`, `Urbano Latino`, `Bachata Pop`, `Salsa Pop`, `Cumbia Pop`, `Latin R&B`, `Latin Soul`, `Verano Latino`, `Noche Latina`, `Ruta al Atardecer`, `Carretera`, `Playa`, `Fiesta`, `Baila`, `Drive`, `Caminar`, `Workout`, `Romance`, `Buenas Vibras`.
- Strong examples:
  `[playlist] Pop Latino para Ruta al Atardecer | Carretera, Verano y Buenas Vibras`
  `[playlist] Spanish Pop Essentials para Manejar | Sol, Ventanas Abajo y Road Trip`
  `[playlist] Reggaeton Suave de Noche | Latin Pop para Playa, Drive y Fiesta`
  `[playlist] Latin R&B de Noche | Romance, Drive y Buenas Vibras`
- Avoid repeating `lista de reproducción` after `[playlist]`; use `mix`, `music`, `música`, `radio`, or the use case instead.
- Every track should have original Spanish lyrics and a distinct hook concept unless the human explicitly requested instrumental/no-vocal.
- Lyrics are judged by song quality first: melody fit, rhythm, vocal tone, hook, emotional arc, and replay value. They do not need to mention the title/use case.
