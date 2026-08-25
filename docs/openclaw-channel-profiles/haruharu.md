# OpenClaw Channel Profile: HaruHaru

Use this profile only after channel selection returns `HaruHaru`, or when the human explicitly says to upload to `HaruHaru`.

## Routing Contract

- This profile is for Korean-language hip K-pop vocal releases: K-pop hip-hop, rap-pop, K-pop trap, boom bap-influenced Korean pop, Korean R&B, neo-soul pop, dark street-pop, and similar Korean vocal tracks with rap/R&B attitude.
- Music defaults to original Korean vocal songs with lyrics.
- For lyrics only, do not use `홍대`, `Hongdae`, `커튼`, `curtain`, `네오`, `neo`, `네온`, `네온사인`, `neon`, `neon sign`, or `neon signs`, including compounds, translations, alternate spacing, or casing. Do not replace them with close scene-setting variants. Avoid turning incidental neighborhoods, room decor, signage, or props into repeated lyric hooks; prefer natural emotional detail and song-specific imagery. Scan and rewrite the lyric before upload if any banned term remains. This does not restrict relevant visual or metadata planning.
- Do not choose city-pop as the default new HaruHaru direction unless the human explicitly asks for that exact lane or an existing in-progress release is already clearly city-pop. If a HaruHaru release is city-pop, keep reused/backfill tracks city-pop-related; if it is not city-pop, do not mix city-pop tracks into it.
- Do not route J-pop/Japanese pop here; use `Tokyo Daydream Radio`.
- Do not route English/American pop here; use `sundaze`.
- Do not route Latin/Spanish pop here; use `Solwave Radio`.
- Do not route instrumental/BGM/no-vocal releases here unless the human explicitly asks for a Korean-pop-flavored instrumental.
- Do not use existing popular-song remake/cover concepts here; those are manual-only and not part of HaruHaru automation.

## Visual Identity

- HaruHaru now defaults to photorealistic Korean lifestyle still-image visuals, not animated/anime rotation.
- The visual should feel like an attractive adult's natural Instagram-style daily-life photo or casual street snapshot: Hongdae street, Hongdae record shop, club-side alley, Itaewon night street, late-night cafe exterior, subway exit, rainy crosswalk, rooftop after dark, streetwear boutique, small music bar, or convenience-store corner.
- Prefer an ordinary-person camera feel over a professional model shoot. The image should look like a friend took it while walking around Hongdae or another Seoul nightlife street, not like a studio photographer, fashion campaign, or glossy AI portrait.
- The default subject should be a stylish clearly adult woman in hip Korean streetwear. Handsome stylish adult men or tasteful adult couple/friend pairs are allowed when the release concept supports it.
- Faces do not need to be hidden, but avoid tight straight-on beauty close-ups where the face fills the frame. Prefer a natural three-quarter view, side profile, candid looking-away pose, laughing/smiling travel moment, or slightly farther medium/waist-up framing where the scene also matters.
- Avoid idol-inspired styling as the default. The subject should feel like a stylish adult listener or street-fashion friend, not an idol member, trainee, studio model, or beauty campaign face. She must be fictional and natural: no real celebrity/idol lookalikes, no plastic-perfect AI face, no doll-like symmetry, and no over-retouched skin. Vary face shapes, expressions, distance from camera, hair, outfits, and scene types across releases.
- Keep the subject clearly adult. Do not use minors, teen-coded styling, school uniforms, childlike poses, celebrity likenesses, or idol-member lookalikes.
- Styling should be fashionable, cool, adult, and natural: oversized jacket, leather jacket, denim, cargo pants, hoodie, cap or beanie when natural, crossbody bag, boots/sneakers, layered streetwear, or understated Korean nightlife styling. Avoid school uniforms, childlike styling, and glossy idol-stage outfits.
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
- Good cover directions: stylish adult woman in oversized jacket on a Hongdae street at dusk; friend-taken slightly motion-blurred photo outside a record shop; candid adult woman in leather jacket near a neon alley; adult woman with headphones at a rainy Seoul crosswalk; streetwear look near a subway exit; casual phone snapshot outside a small music bar; confident three-quarter profile on an Itaewon evening street.
- For hip-hop/rap-pop/trap/R&B HaruHaru releases, default to casual phone-photo energy: dusk or night street light, imperfect crop, mild motion softness, slight focus shake, realistic compression, candid side glance, visible street context, and non-studio background. Do not make the person look like an AI model posing for a headshot.
- Keep the subject visible but not always close. Medium-wide, waist-up, or farther full-body framing is acceptable and often better than a centered face close-up, especially when the location and mood add click value.
- Do not add title sentences, duration text, lyrics, subtitles, UI, logos, spectrum bars, waveform graphics, or unrelated words to the cover.

## YouTube Thumbnail

- Create the thumbnail from the final cover as an image-to-image edit/reference derivative.
- Preserve the same face, subject placement, lighting, palette, props, clothing colors, and camera angle from the cover.
- By default, do not add thumbnail text. The HaruHaru thumbnail should look like a premium natural lifestyle photo, not a graphic poster.
- The thumbnail scene must support the title hook. If the title hook is about a date/crush, use a believable going-to-meet-someone or Hongdae date-beforegoing mood. If it is about confidence/glow-up, use a stylish adult going-out streetwear mood. If it is about breakup recovery, use cool self-possessed night-out energy rather than sad generic imagery.
- The thumbnail may crop slightly closer for readability, but it should still feel like a normal friend-taken street photo. Slight motion blur or imperfect focus is acceptable when it reads as a real phone snapshot. Do not turn the derivative into a straight-on AI beauty portrait.
- If the human explicitly requests text later, keep it very small and integrated with a transparent background; never add the channel name or a logo. Do not put text inside black boxes, semi-transparent dark panels, white or colored rectangles, gradient scrims, stickers, badges, pills, capsules, or any filled label shape.
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
- HaruHaru titles must not keep copying one fixed formula. Start with `[playlist]`, keep the main title under 100 characters, then rotate between curiosity-led and searchable title shapes. Compare against at least the latest 15 HaruHaru titles before approval; if the new title reuses the same first-half hook family, same listening situation, or same sentence skeleton, rewrite it.
- Avoid overusing `상황에 듣기 좋은`, `기분 좋아지는`, `자신감 올리는`, `홍대 가기 전`, `답장 오기 전까지`, and `노래모음`. These phrases are allowed only when they are clearly the best natural copy and have not appeared in recent HaruHaru uploads. Rotate endings such as `K-힙합 믹스`, `랩팝 모음`, `Korean R&B`, `밤에 틀어놓는 노래`, `외출 준비 음악`, `러닝 K-POP`, or `새벽 R&B` when accurate.
- Use one of several title structures instead of a single template:
  - Dialogue hook first: `[playlist] 오늘 연락하지 마 | 혼자 나갈 때 켜는 다크 K-POP 트랩`
  - Genre/use-case first: `[playlist] 붐뱁 K-POP으로 걷는 밤 | 홍대 골목에서 듣는 랩팝 믹스`
  - Immediate payoff first: `[playlist] 첫 곡부터 고개 까딱이는 K-힙합 | 약속 전 텐션 올리는 음악`
  - Mini-story first: `[playlist] 안 꾸민 척 나가는 밤 | 친구가 찍어준 듯한 Seoul R&B`
  - Mood identity first: `[playlist] 차갑게 예쁜 밤공기 | 도도하게 걷는 Korean R&B`
  - Searchable lane first when the genre is the strongest hook: `[playlist] K-POP Trap Night Mix | 러닝과 외출 준비를 위한 K-랩`
- Keep the title truthful to the audio lane. If the release is boom bap, say boom bap/붐뱁; if it is trap, say trap/트랩; if it is Korean R&B or neo-soul, say R&B/neo-soul. Do not label a mixed or weakly matching release as a sharper lane only for clicks.
- Keep the whole release in one lane such as K-pop hip-hop, rap-pop, K-pop trap, boom bap K-pop, Korean R&B, neo-soul pop, or dark street-pop, and name that lane in the title/description when accurate. Avoid new city-pop and generic idol dance-pop planning unless the human explicitly asks; if a release is explicitly city-pop, do not backfill it with unrelated hip-hop/R&B/ballad tracks.
- Backfill/reuse must match the detailed lane, not only the broad `K-pop` channel identity. For example, a boom-bap release should use boom-bap/rap-pop backfill, a trap release should use trap backfill, and an R&B/neo-soul release should use R&B/neo-soul backfill. If matching material is scarce, follow [openclaw-one-hour-new-audio-policy.md](../openclaw-one-hour-new-audio-policy.md): generate additional same-lane Suno tracks until the new playlist reaches one hour; never fill with unrelated K-pop, dance-pop, synth-pop, pop-rock, or ballad tracks.
- If you intentionally arrange tracks by genre confidence, keep strongest same-lane tracks first and any weaker/manual fallback tracks last. Do not pass `--randomize-order` for that release; if randomization is unavoidable, the app preserves reused back-half tracks after the fresh lead block.
- Do not use the visual scene as the main title hook unless it is broadly clickable. The title hook should usually be a human phrase around dating, crush, confidence, getting ready, night out, glow-up, breakup recovery, walking, driving, or weekend energy. The thumbnail should then make that hook feel visually true through the setting, outfit, pose, and mood.
- Keep the hook tasteful. Do not imply explicit/sexual content, real-person humiliation, dangerous behavior, or a false premise that the tracks and thumbnail do not support.
- Every track should have original Korean lyrics and a distinct hook concept unless the human explicitly requested instrumental/no-vocal.
- Lyrics are judged by song quality first: melody fit, beat, vocal tone, hook, emotional arc, and replay value. They do not need to mention the title/use case.
- In localized descriptions, preserve timestamps exactly. Translate surrounding prose, recommended-use lines, hashtags, and track titles naturally for that language unless the human asks to keep Korean track titles.
